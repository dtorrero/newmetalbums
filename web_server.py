#!/usr/bin/env python3
"""
FastAPI Web Server for Metal Albums Database
Serves API endpoints and static frontend files
"""

import asyncio
import threading
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, date
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import uvicorn
import logging
from pathlib import Path
from db_manager import AlbumsDatabase, ingest_json_files
from scraper import MetalArchivesScraper
from models import (
    Album, PlaylistCreate, PlaylistUpdate, PlaylistItemCreate,
    PlaylistItemResponse, PlaylistResponse, ReorderRequest
)
from auth_manager import AuthManager
from genre_parser import GenreParser
from platform_verifier import PlatformVerifier
from youtube_cache_manager import YouTubeCacheManager
from youtube_download_manager import YouTubeDownloadManager
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global database instance
db = AlbumsDatabase()

# Global auth manager instance
auth_manager = AuthManager()

# Global YouTube cache manager
youtube_cache = YouTubeCacheManager(
    cache_dir=str(config.YOUTUBE_CACHE_DIR),
    max_size_gb=config.YOUTUBE_CACHE_MAX_SIZE_GB
)

# Global YouTube download manager (handles parallel downloads)
youtube_download_manager = None  # Will be initialized in lifespan

# Track active downloads to prevent duplicates and allow cancellation
active_downloads: Dict[str, asyncio.Task] = {}
download_locks: Dict[str, asyncio.Lock] = {}

# Global scraping lock to prevent multiple instances
scraping_lock = asyncio.Lock()

# Security scheme for JWT tokens
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global youtube_download_manager
    
    # Startup
    db.connect()
    db.create_tables()  # Create tables if they don't exist
    logger.info("🗄️ Database connected and initialized")
    
    # Initialize YouTube download manager
    max_parallel = db.get_setting('youtube_parallel_downloads')
    if max_parallel is None:
        max_parallel = config.YOUTUBE_PARALLEL_DOWNLOADS
    
    youtube_download_manager = YouTubeDownloadManager(
        cache_dir=config.YOUTUBE_CACHE_DIR,
        youtube_cache_manager=youtube_cache,
        max_parallel=int(max_parallel),
        download_timeout=config.YOUTUBE_DOWNLOAD_TIMEOUT
    )
    
    # Start download workers
    await youtube_download_manager.start_workers()
    logger.info("🎬 YouTube download manager started")
    
    yield
    
    # Shutdown
    if youtube_download_manager:
        await youtube_download_manager.stop_workers()
        logger.info("🎬 YouTube download manager stopped")
    
    db.close()
    logger.info("🗄️ Database disconnected")

app = FastAPI(
    title="Metal Albums API",
    description="API for browsing metal album releases",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global scraping status
scraping_status = {
    "is_running": False,
    "current_date": None,
    "progress": 0,
    "total": 0,
    "status_message": "Ready",
    "start_time": None,
    "end_time": None,
    "error": None,
    "should_stop": False,
    "rate_limited": False
}

# Pydantic models for admin endpoints
class ScrapeRequest(BaseModel):
    date: str  # Format: DD-MM-YYYY
    download_covers: bool = True
    force_rescrape: bool = False
    
class DeleteDateRequest(BaseModel):
    date: str  # Format: DD-MM-YYYY or YYYY-MM-DD
    
class DeleteRangeRequest(BaseModel):
    start_date: str
    end_date: str

# Authentication models
class SetupRequest(BaseModel):
    password: str

class LoginRequest(BaseModel):
    password: str
    remember_me: bool = False

class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str
    expires_hours: Optional[int] = None

# Authentication middleware
async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token for admin access"""
    if not auth_manager.verify_token(credentials.credentials):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


@app.get("/api/dates")
async def get_available_dates():
    """Get all available release dates with album counts"""
    try:
        dates = db.get_available_dates()
        return {"dates": dates, "total": len(dates)}
    except Exception as e:
        logger.error(f"Error fetching dates: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dates")

@app.get("/api/dates/grouped")
async def get_dates_grouped(
    view: str = Query('day', description="View mode: day, week, or month")
):
    """Get dates grouped by day, week, or month with aggregated statistics"""
    try:
        if view not in ['day', 'week', 'month']:
            raise HTTPException(status_code=400, detail="Invalid view mode. Must be 'day', 'week', or 'month'")
        
        periods = db.get_dates_grouped(view)
        return {"periods": periods, "total": len(periods), "view": view}
    except ValueError as e:
        logger.error(f"Invalid view mode: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching grouped dates: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch grouped dates")

@app.get("/api/albums/{release_date}")
async def get_albums_by_date(release_date: str):
    """Get all albums for a specific release date"""
    try:
        albums = db.get_albums_by_date(release_date)
        return {"albums": albums, "total": len(albums), "date": release_date}
    except Exception as e:
        logger.error(f"Error fetching albums for {release_date}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch albums")

@app.get("/api/albums/period/{period_type}/{period_key}")
async def get_albums_by_period(
    period_type: str,
    period_key: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    genres: Optional[str] = Query(None, description="Comma-separated list of genre filters"),
    search: Optional[str] = Query(None, description="Search query for album/band/genre")
):
    """Get albums for a specific period (day/week/month) with pagination and filtering"""
    try:
        if period_type not in ['day', 'week', 'month']:
            raise HTTPException(status_code=400, detail="Invalid period_type. Must be 'day', 'week', or 'month'")
        
        # Parse genre filters
        genre_filters = None
        if genres:
            genre_filters = [g.strip() for g in genres.split(',') if g.strip()]
        
        offset = (page - 1) * limit
        result = db.get_albums_by_period(
            period_type, 
            period_key, 
            limit, 
            offset,
            genre_filters=genre_filters,
            search_query=search
        )
        
        # Add pagination metadata
        result['page'] = page
        result['total_pages'] = (result['total'] + limit - 1) // limit  # Ceiling division
        result['filters'] = {
            'genres': genre_filters,
            'search': search
        }
        
        return result
    except ValueError as e:
        logger.error(f"Invalid period parameters: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching albums for period {period_type}/{period_key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch albums")

@app.get("/api/search")
async def search_albums(
    q: Optional[str] = Query(None, description="Search query"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    country: Optional[str] = Query(None, description="Filter by country"),
    limit: int = Query(50, description="Maximum results")
):
    """Search albums with optional filters"""
    try:
        # Basic search implementation
        cursor = db.connection.cursor()
        
        conditions = []
        params = []
        
        if q:
            conditions.append("(album_name LIKE ? OR band_name LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        
        if genre:
            conditions.append("genre LIKE ?")
            params.append(f"%{genre}%")
        
        if country:
            conditions.append("country_of_origin LIKE ?")
            params.append(f"%{country}%")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT * FROM albums 
            WHERE {where_clause}
            ORDER BY release_date DESC, band_name, album_name
            LIMIT ?
        """
        params.append(limit)
        
        cursor.execute(query, params)
        albums = [dict(row) for row in cursor.fetchall()]
        
        # Add tracks for each album
        for album in albums:
            cursor.execute("""
                SELECT track_number, track_name, track_length, lyrics_url
                FROM tracks 
                WHERE album_id = ? 
                ORDER BY CAST(track_number AS INTEGER)
            """, (album['album_id'],))
            album['tracklist'] = [dict(row) for row in cursor.fetchall()]
        
        return {"albums": albums, "total": len(albums), "query": q}
        
    except Exception as e:
        logger.error(f"Error searching albums: {e}")
        raise HTTPException(status_code=500, detail="Failed to search albums")

@app.get("/api/stats")
async def get_database_stats():
    """Get database statistics"""
    try:
        cursor = db.connection.cursor()
        
        # Total albums
        cursor.execute("SELECT COUNT(*) as total FROM albums")
        total_albums = cursor.fetchone()['total']
        
        # Total tracks
        cursor.execute("SELECT COUNT(*) as total FROM tracks")
        total_tracks = cursor.fetchone()['total']
        
        # Albums by genre
        cursor.execute("""
            SELECT genre, COUNT(*) as count 
            FROM albums 
            WHERE genre IS NOT NULL AND genre != ''
            GROUP BY genre 
            ORDER BY count DESC 
            LIMIT 10
        """)
        genres = [dict(row) for row in cursor.fetchall()]
        
        # Albums by country
        cursor.execute("""
            SELECT country_of_origin as country, COUNT(*) as count 
            FROM albums 
            WHERE country_of_origin IS NOT NULL AND country_of_origin != ''
            GROUP BY country_of_origin 
            ORDER BY count DESC 
            LIMIT 10
        """)
        countries = [dict(row) for row in cursor.fetchall()]
        
        # Recent dates
        cursor.execute("""
            SELECT release_date, COUNT(*) as count 
            FROM albums 
            WHERE release_date IS NOT NULL AND release_date != ''
            GROUP BY release_date 
            ORDER BY release_date DESC 
            LIMIT 5
        """)
        recent_dates = [dict(row) for row in cursor.fetchall()]
        
        return {
            "total_albums": total_albums,
            "total_tracks": total_tracks,
            "top_genres": genres,
            "top_countries": countries,
            "recent_dates": recent_dates
        }
        
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Metal Albums API is running"}

# ============================================================================
# GENRE ENDPOINTS
# ============================================================================

@app.get("/api/genres")
async def get_genres(
    category: Optional[str] = Query(None, description="Filter by category: base, modifier, style"),
    limit: int = Query(100, description="Maximum results"),
    include_stats: bool = Query(True, description="Include album counts")
):
    """Get all genres with optional filtering and statistics"""
    try:
        db = AlbumsDatabase()
        db.connect()
        
        genres = db.get_all_genres(category=category, limit=limit)
        
        return {
            "genres": genres,
            "total": len(genres),
            "category": category,
            "include_stats": include_stats
        }
        
    except Exception as e:
        logger.error(f"Error fetching genres: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch genres")
    finally:
        db.close()

@app.get("/api/genres/search")
async def search_genres(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, description="Maximum results")
):
    """Search genres with autocomplete functionality"""
    try:
        db = AlbumsDatabase()
        db.connect()
        
        genres = db.search_genres(query=q, limit=limit)
        
        # Generate suggestions based on partial matches
        suggestions = []
        if len(genres) < limit:
            # Add some common genre suggestions if not enough results
            common_genres = ["Black Metal", "Death Metal", "Thrash Metal", "Heavy Metal", 
                           "Doom Metal", "Power Metal", "Progressive Metal"]
            for genre in common_genres:
                if q.lower() in genre.lower() and genre not in [g['genre_name'] for g in genres]:
                    suggestions.append(genre)
        
        return {
            "genres": genres,
            "total": len(genres),
            "query": q,
            "suggestions": suggestions[:5]  # Limit suggestions
        }
        
    except Exception as e:
        logger.error(f"Error searching genres: {e}")
        raise HTTPException(status_code=500, detail="Failed to search genres")
    finally:
        db.close()

@app.get("/api/genres/{genre_name}")
async def get_genre_details(genre_name: str):
    """Get detailed information about a specific genre"""
    try:
        db = AlbumsDatabase()
        db.connect()
        
        # Get genre from taxonomy
        cursor = db.connection.cursor()
        cursor.execute('''
            SELECT gt.*, COALESCE(gs.album_count, 0) as album_count,
                   gs.date_range_start, gs.date_range_end
            FROM genre_taxonomy gt
            LEFT JOIN genre_stats gs ON gt.genre_name = gs.genre_name
            WHERE gt.genre_name = ? OR gt.normalized_name = ?
        ''', (genre_name, genre_name))
        
        genre_info = cursor.fetchone()
        if not genre_info:
            raise HTTPException(status_code=404, detail=f"Genre '{genre_name}' not found")
        
        genre_dict = dict(genre_info)
        
        # Parse aliases JSON
        if genre_dict.get('aliases'):
            try:
                genre_dict['aliases'] = json.loads(genre_dict['aliases'])
            except:
                genre_dict['aliases'] = []
        
        # Get related genres (same parent or children)
        related_genres = []
        if genre_dict.get('parent_genre'):
            cursor.execute('''
                SELECT genre_name, album_count FROM genre_taxonomy gt
                LEFT JOIN genre_stats gs ON gt.genre_name = gs.genre_name
                WHERE gt.parent_genre = ? AND gt.genre_name != ?
                ORDER BY gs.album_count DESC
                LIMIT 5
            ''', (genre_dict['parent_genre'], genre_name))
            related_genres = [dict(row) for row in cursor.fetchall()]
        
        genre_dict['related_genres'] = related_genres
        
        return genre_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching genre details for {genre_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch genre details")
    finally:
        db.close()

@app.get("/api/genres/{genre_name}/related")
async def get_related_genres(
    genre_name: str,
    limit: int = Query(10, description="Maximum related genres")
):
    """Get genres related to the specified genre"""
    try:
        db = AlbumsDatabase()
        db.connect()
        
        # Get genres that frequently appear together with this genre
        cursor = db.connection.cursor()
        cursor.execute('''
            SELECT pg2.genre_name, COUNT(*) as co_occurrence,
                   AVG(pg2.confidence) as avg_confidence
            FROM parsed_genres pg1
            JOIN parsed_genres pg2 ON pg1.album_id = pg2.album_id
            WHERE pg1.genre_name = ? AND pg2.genre_name != ?
            GROUP BY pg2.genre_name
            ORDER BY co_occurrence DESC, avg_confidence DESC
            LIMIT ?
        ''', (genre_name, genre_name, limit))
        
        related = [dict(row) for row in cursor.fetchall()]
        
        return {
            "genre": genre_name,
            "related_genres": related,
            "total": len(related)
        }
        
    except Exception as e:
        logger.error(f"Error fetching related genres for {genre_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch related genres")
    finally:
        db.close()

@app.get("/api/albums/by-genre/{genre_name}")
async def get_albums_by_genre(
    genre_name: str,
    date: Optional[str] = Query(None, description="Filter by specific date"),
    date_from: Optional[str] = Query(None, description="Filter from date"),
    date_to: Optional[str] = Query(None, description="Filter to date"),
    limit: int = Query(50, description="Maximum results"),
    offset: int = Query(0, description="Pagination offset")
):
    """Get albums filtered by genre with optional date filtering"""
    try:
        db = AlbumsDatabase()
        db.connect()
        
        albums = db.get_albums_by_genre(
            genre_name=genre_name,
            date=date,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset
        )
        
        # Get total count for pagination
        cursor = db.connection.cursor()
        count_query = '''
            SELECT COUNT(DISTINCT a.album_id)
            FROM albums a
            JOIN parsed_genres pg ON a.album_id = pg.album_id
            WHERE pg.genre_name = ?
        '''
        params = [genre_name]
        
        if date:
            count_query += ' AND a.release_date = ?'
            params.append(date)
        elif date_from and date_to:
            count_query += ' AND a.release_date BETWEEN ? AND ?'
            params.extend([date_from, date_to])
        elif date_from:
            count_query += ' AND a.release_date >= ?'
            params.append(date_from)
        elif date_to:
            count_query += ' AND a.release_date <= ?'
            params.append(date_to)
        
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        return {
            "albums": albums,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "genre": genre_name,
            "filters": {
                "date": date,
                "date_from": date_from,
                "date_to": date_to
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching albums by genre {genre_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch albums by genre")
    finally:
        db.close()

@app.get("/api/genres/stats")
async def get_genre_statistics():
    """Get comprehensive genre statistics"""
    try:
        db = AlbumsDatabase()
        db.connect()
        
        stats = db.get_genre_statistics()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error fetching genre statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch genre statistics")
    finally:
        db.close()

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

async def run_scraper_task_with_lock(scrape_date: str, download_covers: bool = True):
    """Wrapper function that runs scraper task with lock protection"""
    async with scraping_lock:
        logger.info(f"🔒 Acquired scraping lock for date: {scrape_date}")
        try:
            await run_scraper_task(scrape_date, download_covers)
        except Exception as e:
            logger.error(f"Error in locked scraper task: {e}")
            raise
        finally:
            logger.info(f"🔓 Released scraping lock for date: {scrape_date}")

async def queue_youtube_downloads_for_date(start_date: str, end_date: str) -> Dict:
    """
    Queue YouTube downloads for all verified albums in a date range.
    Uses a separate download manager instance with configurable parallelism.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        Dictionary with download statistics
    """
    try:
        logger.info(f"🎬 [POST-SCRAPE] Queuing YouTube downloads for {start_date} to {end_date}")
        
        # Get post-scrape parallel download setting
        post_scrape_parallel = db.get_setting('youtube_post_scrape_downloads')
        if post_scrape_parallel is None:
            post_scrape_parallel = config.YOUTUBE_POST_SCRAPE_DOWNLOADS
        post_scrape_parallel = int(post_scrape_parallel)
        
        logger.info(f"🎬 [POST-SCRAPE] Using {post_scrape_parallel} parallel download(s)")
        
        # Query albums with verified YouTube URLs in date range
        cursor = db.connection.cursor()
        cursor.execute('''
            SELECT album_id, youtube_embed_url, youtube_video_url
            FROM albums
            WHERE release_date BETWEEN ? AND ?
            AND playable_verified = 1
            AND (youtube_embed_url IS NOT NULL OR youtube_video_url IS NOT NULL)
        ''', (start_date, end_date))
        
        albums = cursor.fetchall()
        logger.info(f"🎬 [POST-SCRAPE] Found {len(albums)} albums with YouTube URLs")
        
        if not albums:
            return {'queued': 0, 'skipped': 0, 'total': 0}
        
        # Extract video IDs from URLs
        video_ids = []
        import re
        
        for album_id, youtube_embed_url, youtube_video_url in albums:
            # Try to extract video ID from either URL
            video_id = None
            
            if youtube_video_url:
                # Extract from video URL: https://www.youtube.com/watch?v=VIDEO_ID
                match = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', youtube_video_url)
                if match:
                    video_id = match.group(1)
            
            if not video_id and youtube_embed_url:
                # Extract from embed URL: https://youtube-nocookie.com/embed/VIDEO_ID
                match = re.search(r'/embed/([a-zA-Z0-9_-]{11})', youtube_embed_url)
                if match:
                    video_id = match.group(1)
            
            if video_id:
                # Check if already cached
                cached_file = youtube_cache.get_cached_file(video_id)
                if not cached_file:
                    video_ids.append(video_id)
                    logger.debug(f"🎬 [POST-SCRAPE] Queuing {video_id} for album {album_id}")
                else:
                    logger.debug(f"🎬 [POST-SCRAPE] Skipping {video_id} (already cached)")
        
        logger.info(f"🎬 [POST-SCRAPE] Queuing {len(video_ids)} videos for download ({len(albums) - len(video_ids)} already cached)")
        
        # Queue all videos using the main download manager
        # Note: We use the same download manager but it will respect the queue
        for video_id in video_ids:
            await youtube_download_manager.download_video(video_id, priority=False)
        
        return {
            'queued': len(video_ids),
            'skipped': len(albums) - len(video_ids),
            'total': len(albums)
        }
        
    except Exception as e:
        logger.error(f"🎬 [POST-SCRAPE] Error queuing downloads: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'queued': 0, 'skipped': 0, 'total': 0, 'error': str(e)}

async def run_scraper_task(scrape_date: str, download_covers: bool = True):
    """Background task to run the scraper"""
    global scraping_status
    
    # Define JSON filename early for cleanup purposes
    json_filename = f"data/albums_{scrape_date}.json"
    database_ingested = False  # Track if data was successfully saved to database
    
    try:
        scraping_status.update({
            "is_running": True,
            "current_date": scrape_date,
            "progress": 0,
            "total": 0,
            "status_message": "Initializing scraper...",
            "error": None,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "should_stop": False,
            "rate_limited": False
        })
        
        # Initialize scraper with stop callback
        def check_stop():
            return scraping_status["should_stop"]
        
        scraper = MetalArchivesScraper(headless=True, stop_callback=check_stop)
        await scraper.initialize()
        
        scraping_status["status_message"] = f"Scraping albums for {scrape_date}..."
        
        # Run the scraper
        date_obj = datetime.strptime(scrape_date, "%d-%m-%Y").date()
        
        # Check for stop signal before starting
        if scraping_status["should_stop"]:
            raise Exception("Scraping stopped by user")
            
        albums_data = await scraper.search_albums_by_date(date_obj)
        
        # Check if we got rate limited (empty results or specific error patterns)
        if not albums_data:
            scraping_status["rate_limited"] = True
            scraping_status["status_message"] = "No albums found - possibly rate limited by Metal Archives"
            logger.warning(f"No albums found for {scrape_date} - possible rate limiting")
        
        # Convert to Album objects if needed
        albums = []
        for i, album_data in enumerate(albums_data):
            # Check for stop signal during processing
            if scraping_status["should_stop"]:
                raise Exception("Scraping stopped by user")
                
            album = Album.from_scraped_data(album_data)
            if download_covers:
                await scraper.download_cover(album_data)
            albums.append(album)
            
            # Update progress
            scraping_status["progress"] = i + 1
            scraping_status["total"] = len(albums_data)
        
        scraping_status.update({
            "progress": len(albums),
            "total": len(albums),
            "status_message": f"Scraped {len(albums)} albums, saving to database..."
        })
        
        # Save to JSON file - flatten band data for database compatibility
        # json_filename already defined at function start
        flattened_albums = []
        for album in albums:
            album_dict = album.model_dump(by_alias=True)
            
            # Flatten band data to top level
            if 'band' in album_dict:
                band_data = album_dict.pop('band')
                album_dict.update({
                    'band_name': band_data.get('name', ''),
                    'band_url': band_data.get('url', ''),
                    'band_id': band_data.get('id', ''),
                    'country_of_origin': band_data.get('country_of_origin', ''),
                    'location': band_data.get('location', ''),
                    'genre': band_data.get('genre', ''),
                    'themes': band_data.get('themes', ''),
                    'current_label': band_data.get('current_label', ''),
                    'years_active': band_data.get('years_active', '')
                })
            
            # Ensure release_date_raw is included (may be missing from Album model)
            if 'release_date_raw' not in album_dict:
                # Extract from details if available
                details = album_dict.get('details', {})
                album_dict['release_date_raw'] = details.get('release_date_', '')
            
            flattened_albums.append(album_dict)
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(flattened_albums, f, indent=2, ensure_ascii=False)
        
        # Ingest into database
        ingest_json_files(db, json_filename)
        database_ingested = True  # Mark successful database ingestion
        
        # Parse genres for all albums
        scraping_status["status_message"] = "Parsing genres..."
        genre_parser = GenreParser()
        
        for album in albums:
            # Check if album has band and band has genre attribute
            if hasattr(album, 'band') and album.band and hasattr(album.band, 'genre') and album.band.genre and album.band.genre.strip():
                try:
                    logger.debug(f"Parsing genres for album {album.id}: {album.band.genre}")
                    parsed_genres = genre_parser.parse_genre_string(album.band.genre)
                    genre_data = []
                    
                    for parsed_genre in parsed_genres:
                        # Add main genre
                        if parsed_genre.main:
                            genre_data.append({
                                'genre_name': parsed_genre.main,
                                'genre_type': 'main',
                                'confidence': parsed_genre.confidence,
                                'period': parsed_genre.period
                            })
                        
                        # Add modifiers
                        for modifier in parsed_genre.modifiers:
                            genre_data.append({
                                'genre_name': modifier,
                                'genre_type': 'modifier',
                                'confidence': parsed_genre.confidence * 0.8,
                                'period': parsed_genre.period
                            })
                        
                        # Add related genres
                        for related in parsed_genre.related:
                            genre_data.append({
                                'genre_name': related,
                                'genre_type': 'related',
                                'confidence': parsed_genre.confidence * 0.7,
                                'period': parsed_genre.period
                            })
                    
                    # Insert parsed genres into database
                    if genre_data:
                        db.insert_parsed_genres(album.id, genre_data)
                        
                        # Update genre taxonomy
                        for genre_item in genre_data:
                            genre_name = genre_item['genre_name']
                            normalized_name = genre_parser.normalize_genre(genre_name)
                            category = 'base' if genre_item['genre_type'] == 'main' else genre_item['genre_type']
                            
                            db.upsert_genre_taxonomy(
                                genre_name=genre_name,
                                normalized_name=normalized_name,
                                category=category
                            )
                
                except Exception as e:
                    logger.warning(f"Failed to parse genres for album {album.id}: {e}")
            else:
                # Log albums without genre information for debugging
                if hasattr(album, 'id'):
                    logger.debug(f"Album {album.id} has no genre information to parse")
        
        # Update genre statistics
        db.update_genre_statistics()
        logger.info(f"Genre parsing completed for {len(albums)} albums")
        
        # Close scraper before verification
        await scraper.close()
        
        # Auto-verify playable URLs after successful scraping
        logger.info(f"🎵 Starting automatic verification for {scrape_date}...")
        scraping_status.update({
            "status_message": f"Scraped {len(albums)} albums. Now verifying playable URLs...",
            "progress": len(albums),
            "total": len(albums)
        })
        
        try:
            from batch_verifier import BatchVerifier
            verifier = BatchVerifier(db, headless=True)
            await verifier.initialize()
            
            # Convert date format from DD-MM-YYYY to YYYY-MM-DD for database query
            date_obj_for_verify = datetime.strptime(scrape_date, "%d-%m-%Y")
            db_date_format = date_obj_for_verify.strftime("%Y-%m-%d")
            
            verification_stats = await verifier.verify_date_range(
                db_date_format,
                db_date_format,
                min_similarity=75
            )
            
            await verifier.close()
            
            logger.info(f"✓ Verification complete: {verification_stats['verified']}/{verification_stats['total']} albums verified")
            
            # Queue YouTube downloads for verified albums
            download_stats = await queue_youtube_downloads_for_date(db_date_format, db_date_format)
            
            scraping_status.update({
                "is_running": False,
                "status_message": f"Successfully scraped {len(albums)} albums, verified {verification_stats['verified']} playable URLs, and queued {download_stats['queued']} YouTube downloads for {scrape_date}",
                "end_time": datetime.now().isoformat(),
                "should_stop": False,
                "rate_limited": False,
                "verification_stats": verification_stats,
                "download_stats": download_stats
            })
            
        except Exception as verify_error:
            logger.error(f"Verification failed: {verify_error}")
            scraping_status.update({
                "is_running": False,
                "status_message": f"Successfully scraped {len(albums)} albums for {scrape_date}. Verification failed: {str(verify_error)}",
                "end_time": datetime.now().isoformat(),
                "should_stop": False,
                "rate_limited": False,
                "verification_error": str(verify_error)
            })
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        
        # Cleanup partial JSON file if database ingestion wasn't completed
        if not database_ingested and os.path.exists(json_filename):
            try:
                os.remove(json_filename)
                logger.info(f"🧹 Cleaned up partial JSON file: {json_filename}")
            except OSError as cleanup_error:
                logger.warning(f"Could not remove partial JSON file {json_filename}: {cleanup_error}")
        
        # Provide user-friendly error messages
        error_message = str(e)
        
        # Reset rate_limited flag by default
        rate_limited = False
        
        if "stopped by user" in error_message.lower():
            status_message = "Scraping stopped by user"
        elif "timeout" in error_message.lower():
            status_message = "Scraping failed: Possible timeout. Try again later."
            rate_limited = True
        elif "rate limit" in error_message.lower() or "rate-limit" in error_message.lower():
            status_message = "Scraping failed: Rate limited by Metal Archives. Try again later."
            rate_limited = True
        elif "connection" in error_message.lower():
            status_message = "Scraping failed: Network connection error"
        else:
            status_message = f"Scraping failed: {error_message}"
        
        scraping_status.update({
            "is_running": False,
            "error": error_message,
            "status_message": status_message,
            "end_time": datetime.now().isoformat(),
            "should_stop": False,  # Reset stop flag after handling
            "rate_limited": rate_limited  # Only set to True for actual rate limiting
        })
        
        # Cleanup scraper if it was initialized
        try:
            await scraper.close()
        except:
            pass

@app.post("/api/admin/scrape")
async def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks, token: str = Depends(verify_admin_token)):
    """Trigger manual scraping for a specific date"""
    # Validate date format first
    try:
        datetime.strptime(request.date, "%d-%m-%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use DD-MM-YYYY")
    
    # PRIORITY CHECK: If scraping is already running, show current operation details
    if scraping_status["is_running"] or scraping_lock.locked():
        current_date = scraping_status.get("current_date", "unknown date")
        current_status = scraping_status.get("status_message", "running")
        
        # Create a more informative error message
        if scraping_status.get("should_stop"):
            detail = f"Scraping is currently stopping (was processing {current_date}). Please wait for it to complete before starting a new operation."
        else:
            detail = f"Scraping is already in progress for {current_date} ({current_status}). Please wait for the current operation to complete or stop it first."
        
        raise HTTPException(status_code=409, detail=detail)
    
    # Check if data already exists for this date (convert to database format)
    db_date = datetime.strptime(request.date, "%d-%m-%Y").strftime("%Y-%m-%d")
    existing_data = db.check_date_exists(db_date)
    if existing_data and not getattr(request, 'force_rescrape', False):
        # Get count of existing albums for this date
        existing_count = db.get_albums_count_by_date(db_date)
        raise HTTPException(
            status_code=409, 
            detail=f"Data already exists for {request.date} ({existing_count} albums). Use force_rescrape=true to overwrite existing data."
        )
    
    # Start background scraping task with lock protection
    background_tasks.add_task(run_scraper_task_with_lock, request.date, request.download_covers)
    
    return {
        "message": f"Scraping started for {request.date}",
        "date": request.date,
        "download_covers": request.download_covers
    }

@app.get("/api/admin/scrape/status")
async def get_scrape_status(token: str = Depends(verify_admin_token)):
    """Get current scraping status"""
    # Add lock status and enhanced information
    status_with_lock = scraping_status.copy()
    status_with_lock["lock_held"] = scraping_lock.locked()
    
    # Add user-friendly status description
    if status_with_lock.get("is_running"):
        if status_with_lock.get("should_stop"):
            status_with_lock["user_friendly_status"] = f"Stopping scraping for {status_with_lock.get('current_date', 'unknown date')}"
        else:
            status_with_lock["user_friendly_status"] = f"Scraping in progress for {status_with_lock.get('current_date', 'unknown date')}"
    else:
        status_with_lock["user_friendly_status"] = "Ready to start scraping"
    
    return status_with_lock

@app.post("/api/admin/scrape/stop")
async def stop_scraping(token: str = Depends(verify_admin_token)):
    """Stop the currently running scraping process"""
    if not scraping_status.get("is_running"):
        raise HTTPException(status_code=400, detail="No scraping process is currently running")
    
    scraping_status["should_stop"] = True
    scraping_status["status_message"] = "Stopping scraping process..."
    
    return {"message": "Stop signal sent to scraping process"}

@app.get("/api/youtube/audio/{video_id}")
async def get_youtube_audio(video_id: str):
    """
    Serve cached YouTube audio file.
    
    NEW BEHAVIOR:
    - Only serves files that are already cached
    - Returns 404 if file is not available
    - Does NOT initiate downloads (use /api/youtube/queue endpoint to queue downloads)
    
    This prevents blocking the player while waiting for downloads.
    """
    from fastapi.responses import FileResponse
    
    logger.info(f"🎬 [YOUTUBE/AUDIO] Request for video: {video_id}")
    
    # Check if already cached
    cached_file = youtube_cache.get_cached_file(video_id)
    if cached_file:
        file_size_mb = cached_file.stat().st_size / 1024 / 1024
        logger.info(f"🎬 [YOUTUBE/AUDIO] ✅ Serving from cache: {cached_file.name} ({file_size_mb:.2f} MB)")
        
        # Determine media type
        media_type = "audio/webm"
        if cached_file.suffix == '.mp4' or cached_file.suffix == '.m4a':
            media_type = "audio/mp4"
        elif cached_file.suffix == '.opus':
            media_type = "audio/opus"
        elif cached_file.suffix == '.ogg':
            media_type = "audio/ogg"
        
        return FileResponse(
            cached_file,
            media_type=media_type,
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=31536000",
            }
        )
    
    # Not cached - check if currently downloading
    download_status = youtube_download_manager.get_download_status(video_id)
    if download_status:
        logger.info(f"🎬 [YOUTUBE/AUDIO] ⏳ {video_id} is {download_status.status.value}")
        raise HTTPException(
            status_code=202,  # Accepted - processing
            detail=f"Audio file is being downloaded. Status: {download_status.status.value}"
        )
    
    # Not cached and not downloading
    logger.warning(f"🎬 [YOUTUBE/AUDIO] ❌ {video_id} not available")
    raise HTTPException(
        status_code=404,
        detail="Audio file not available. Please queue it for download first."
    )

@app.get("/api/youtube/audio/{video_id}/info")
async def get_youtube_audio_info(video_id: str):
    """
    Get information about a YouTube audio file (size, download status).
    Used by frontend to show download notifications.
    """
    import yt_dlp
    
    # Check if already cached
    cached_file = youtube_cache.get_cached_file(video_id)
    if cached_file:
        file_size_mb = cached_file.stat().st_size / 1024 / 1024
        return {
            "cached": True,
            "size_mb": round(file_size_mb, 1),
            "estimated_time": "0s"
        }
    
    # Not cached - get file size estimate
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        def get_info():
            ydl_opts_info = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                return ydl.extract_info(video_url, download=False)
        
        info_only = await asyncio.to_thread(get_info)
        
        if info_only:
            filesize = info_only.get('filesize') or info_only.get('filesize_approx', 0)
            filesize_mb = filesize / 1024 / 1024 if filesize else 0
            
            # Estimate download time (assuming ~2 MB/s average download speed)
            estimated_time = "unknown"
            if filesize_mb > 0:
                estimated_seconds = filesize_mb / 2.0
                if estimated_seconds < 60:
                    estimated_time = f"{int(estimated_seconds)}s"
                else:
                    estimated_time = f"{int(estimated_seconds / 60)}m {int(estimated_seconds % 60)}s"
            
            return {
                "cached": False,
                "size_mb": round(filesize_mb, 1),
                "estimated_time": estimated_time
            }
    except Exception as e:
        logger.error(f"Error getting audio info: {e}")
        return {
            "cached": False,
            "size_mb": 0,
            "estimated_time": "unknown"
        }

@app.post("/api/youtube/queue")
async def queue_youtube_download(video_ids: List[str], current_index: int = 0):
    """
    Queue YouTube videos for download.
    
    Args:
        video_ids: List of YouTube video IDs to download
        current_index: Index of currently playing track (gets priority)
    
    Returns:
        Status of queued downloads
    """
    if not video_ids:
        raise HTTPException(status_code=400, detail="No video IDs provided")
    
    logger.info(f"🎬 [YOUTUBE/QUEUE] Received request to queue {len(video_ids)} videos")
    
    # Queue the playlist for download
    await youtube_download_manager.download_playlist(video_ids, current_index)
    
    # Get status of each video
    statuses = []
    for video_id in video_ids:
        cached_file = youtube_cache.get_cached_file(video_id)
        if cached_file:
            statuses.append({
                "video_id": video_id,
                "status": "cached",
                "size_mb": round(cached_file.stat().st_size / 1024 / 1024, 1)
            })
        else:
            download_status = youtube_download_manager.get_download_status(video_id)
            if download_status:
                statuses.append({
                    "video_id": video_id,
                    "status": download_status.status.value,
                    "attempts": download_status.attempts,
                    "error": download_status.error
                })
            else:
                statuses.append({
                    "video_id": video_id,
                    "status": "queued"
                })
    
    return {
        "message": f"Queued {len(video_ids)} videos for download",
        "statuses": statuses
    }

@app.get("/api/youtube/download/status/{video_id}")
async def get_download_status(video_id: str):
    """
    Get download status for a specific video.
    
    Returns:
        Download status including progress, errors, etc.
    """
    # Check if cached
    cached_file = youtube_cache.get_cached_file(video_id)
    if cached_file:
        return {
            "video_id": video_id,
            "status": "completed",
            "cached": True,
            "size_mb": round(cached_file.stat().st_size / 1024 / 1024, 1)
        }
    
    # Check download status
    download_status = youtube_download_manager.get_download_status(video_id)
    if download_status:
        return {
            "video_id": video_id,
            "status": download_status.status.value,
            "cached": False,
            "attempts": download_status.attempts,
            "max_attempts": download_status.max_attempts,
            "error": download_status.error,
            "started_at": download_status.started_at.isoformat() if download_status.started_at else None,
            "completed_at": download_status.completed_at.isoformat() if download_status.completed_at else None
        }
    
    return {
        "video_id": video_id,
        "status": "not_found",
        "cached": False
    }

@app.get("/api/youtube/download/stats")
async def get_download_stats():
    """
    Get overall download statistics.
    
    Returns:
        Statistics about downloads (success rate, active downloads, etc.)
    """
    stats = youtube_download_manager.get_statistics()
    cache_stats = youtube_cache.get_cache_stats()
    
    return {
        "download_stats": stats,
        "cache_stats": cache_stats
    }

@app.get("/api/youtube/stream")
async def get_youtube_stream(url: str):
    """
    Extract audio stream URL from YouTube video/playlist using yt-dlp.
    Returns direct stream URLs for playback without embed restrictions.
    """
    try:
        import yt_dlp
        
        logger.info(f"🎬 [YOUTUBE/YT-DLP] ========== START ==========")
        logger.info(f"🎬 [YOUTUBE/YT-DLP] Received URL: {url}")
        
        # Check if this is a YouTube Mix/Radio playlist (RD prefix)
        # These are auto-generated and can't be accessed directly
        if 'list=RD' in url or 'list=RDMM' in url or 'list=RDAO' in url:
            logger.warning(f"🎬 [YOUTUBE/YT-DLP] Detected YouTube Mix playlist (RD/RDMM/RDAO)")
            
            # Try to extract the video ID from the Mix playlist ID
            # Format: RD{videoId} or RDMM{videoId}
            import re
            video_id_match = re.search(r'list=RD(?:MM|AO)?([a-zA-Z0-9_-]{11})', url)
            
            if video_id_match:
                video_id = video_id_match.group(1)
                fallback_url = f"https://www.youtube.com/watch?v={video_id}"
                logger.info(f"🎬 [YOUTUBE/YT-DLP] Extracted video ID: {video_id}")
                logger.info(f"🎬 [YOUTUBE/YT-DLP] Falling back to single video: {fallback_url}")
                url = fallback_url
            else:
                logger.error(f"🎬 [YOUTUBE/YT-DLP] Could not extract video ID from Mix playlist")
                raise HTTPException(
                    status_code=404, 
                    detail="YouTube Mix playlists are not supported. Please use a regular playlist or video URL."
                )
        
        # yt-dlp options for audio extraction
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': False,  # Show yt-dlp output for debugging
            'no_warnings': False,
            'extract_flat': False,  # Get full info for playlists
            'ignoreerrors': True,   # Continue on errors
            'logger': logger,  # Use our logger
        }
        
        logger.info(f"🎬 [YOUTUBE/YT-DLP] Calling yt-dlp.extract_info()...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            logger.info(f"🎬 [YOUTUBE/YT-DLP] Extract complete. Info type: {type(info)}")
            
            if not info:
                logger.error(f"🎬 [YOUTUBE/YT-DLP] yt-dlp returned None - video may be unavailable")
                raise HTTPException(
                    status_code=404, 
                    detail="Could not extract video information. The video may be private, deleted, or region-restricted."
                )
            
            # Handle playlists
            if 'entries' in info:
                logger.info(f"🎬 [YOUTUBE/YT-DLP] Type: PLAYLIST with {len(info.get('entries', []))} entries")
                tracks = []
                video_ids = []
                
                for idx, entry in enumerate(info['entries']):
                    if entry:
                        video_id = entry.get('id')
                        if video_id:
                            video_ids.append(video_id)
                            logger.info(f"🎬 [YOUTUBE/YT-DLP]   Track {idx+1}: {entry.get('title', 'Unknown')} (ID: {video_id})")
                            tracks.append({
                                'title': entry.get('title', 'Unknown'),
                                'duration': entry.get('duration', 0),
                                'url': f"https://www.youtube.com/watch?v={video_id}",
                                'video_id': video_id,
                                'thumbnail': entry.get('thumbnail'),
                            })
                
                # Queue all videos for download immediately (prioritize first track)
                if video_ids:
                    logger.info(f"🎬 [YOUTUBE/YT-DLP] Queuing {len(video_ids)} videos for download")
                    await youtube_download_manager.download_playlist(video_ids, current_index=0)
                
                logger.info(f"🎬 [YOUTUBE/YT-DLP] ✅ SUCCESS - Returning {len(tracks)} tracks")
                logger.info(f"🎬 [YOUTUBE/YT-DLP] ========== END ==========")
                return {
                    'found': True,
                    'type': 'playlist',
                    'title': info.get('title', 'Unknown Playlist'),
                    'tracks': tracks,
                    'track_count': len(tracks)
                }
            
            # Handle single video
            else:
                video_id = info.get('id')
                logger.info(f"🎬 [YOUTUBE/YT-DLP] Type: SINGLE VIDEO")
                logger.info(f"🎬 [YOUTUBE/YT-DLP] Title: {info.get('title', 'Unknown')}")
                logger.info(f"🎬 [YOUTUBE/YT-DLP] Duration: {info.get('duration', 0)}s")
                logger.info(f"🎬 [YOUTUBE/YT-DLP] Video ID: {video_id}")
                
                # Queue single video for download immediately
                if video_id:
                    logger.info(f"🎬 [YOUTUBE/YT-DLP] Queuing video for download: {video_id}")
                    await youtube_download_manager.download_video(video_id, priority=True)
                
                logger.info(f"🎬 [YOUTUBE/YT-DLP] ✅ SUCCESS")
                logger.info(f"🎬 [YOUTUBE/YT-DLP] ========== END ==========")
                return {
                    'found': True,
                    'type': 'video',
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'video_id': video_id,
                    'url': f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
                    'thumbnail': info.get('thumbnail'),
                }
        
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"🎬 [YOUTUBE/YT-DLP] ❌ DownloadError for URL {url}")
        logger.error(f"🎬 [YOUTUBE/YT-DLP] Error: {e}")
        logger.error(f"🎬 [YOUTUBE/YT-DLP] ========== END (ERROR) ==========")
        raise HTTPException(status_code=404, detail=f"Could not extract stream: {str(e)}")
    except Exception as e:
        logger.error(f"🎬 [YOUTUBE/YT-DLP] ❌ Unexpected error for URL {url}")
        logger.error(f"🎬 [YOUTUBE/YT-DLP] Error: {e}")
        import traceback
        logger.error(f"🎬 [YOUTUBE/YT-DLP] Traceback:\n{traceback.format_exc()}")
        logger.error(f"🎬 [YOUTUBE/YT-DLP] ========== END (ERROR) ==========")
        raise HTTPException(status_code=500, detail=str(e))

# Simple cache for Bandcamp track data to avoid rate limiting
bandcamp_tracks_cache = {}
BANDCAMP_CACHE_TTL = 3600  # 1 hour

@app.get("/api/bandcamp/tracks")
async def get_bandcamp_tracks(url: str):
    """
    Extract track URLs from a Bandcamp album page.
    Returns direct MP3 URLs for playback without cookie popups.
    Cached for 1 hour to avoid rate limiting.
    """
    try:
        from playwright.async_api import async_playwright
        from platform_verifier import PlatformVerifier
        import time
        
        # Check cache first
        cache_key = url
        if cache_key in bandcamp_tracks_cache:
            cached_data, cached_time = bandcamp_tracks_cache[cache_key]
            if time.time() - cached_time < BANDCAMP_CACHE_TTL:
                logger.info(f"🎵 [CACHE HIT] Returning cached tracks for: {url}")
                return cached_data
            else:
                logger.info(f"🎵 [CACHE EXPIRED] Re-fetching tracks for: {url}")
                del bandcamp_tracks_cache[cache_key]
        
        logger.info(f"🎵 [CACHE MISS] Extracting Bandcamp tracks from: {url}")
        
        # Launch browser and extract tracks
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Enable console logging from the page
            page.on("console", lambda msg: logger.info(f"Browser console: {msg.text}"))
            
            verifier = PlatformVerifier(page)
            track_data = await verifier.extract_bandcamp_tracks(url)
            
            await browser.close()
        
        logger.info(f"Track extraction result: found={track_data.get('found')}, tracks={len(track_data.get('tracks', []))}")
        
        if not track_data.get('found'):
            error_msg = track_data.get('error', 'Could not extract tracks from Bandcamp page')
            logger.error(f"❌ Track extraction failed: {error_msg}")
            raise HTTPException(status_code=404, detail=error_msg)
        
        # Cache the successful result
        bandcamp_tracks_cache[cache_key] = (track_data, time.time())
        logger.info(f"✓ Successfully extracted and cached {len(track_data['tracks'])} tracks")
        
        return track_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error extracting Bandcamp tracks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/verify-playable")
async def verify_playable_urls(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    min_similarity: int = Query(75, description="Minimum fuzzy match score (0-100)"),
    background_tasks: BackgroundTasks = None,
    token: str = Depends(verify_admin_token)
):
    """
    Verify playable URLs for albums in date range.
    This runs in the background and updates albums with embed URLs.
    """
    from batch_verifier import BatchVerifier
    
    async def run_verification():
        verifier = BatchVerifier(db, headless=True)
        try:
            await verifier.initialize()
            stats = await verifier.verify_date_range(start_date, end_date, min_similarity)
            logger.info(f"Verification complete: {stats}")
        except Exception as e:
            logger.error(f"Verification error: {e}")
        finally:
            await verifier.close()
    
    # Run in background
    if background_tasks:
        background_tasks.add_task(run_verification)
    else:
        # Fallback: run synchronously
        await run_verification()
    
    return {
        "message": "Playable URL verification started",
        "date_range": f"{start_date} to {end_date}",
        "min_similarity": min_similarity
    }

@app.get("/api/admin/test-youtube-search")
async def test_youtube_search(
    band_name: str = Query("AngelMaker", description="Band name to search"),
    album_name: str = Query("This Used to Be Heaven", description="Album name to search")
    # No auth required - diagnostic endpoint for troubleshooting
):
    """
    Detailed YouTube search diagnostic endpoint.
    Tests the complete YouTube search flow and returns detailed results.
    """
    import time
    import asyncio
    from fuzzywuzzy import fuzz
    
    diagnostic_log = []
    start_time = time.time()
    
    def log(message):
        diagnostic_log.append(f"[{time.time() - start_time:.2f}s] {message}")
        logger.info(message)
    
    try:
        log("🔧 Starting YouTube search diagnostic")
        log(f"   Band: {band_name}")
        log(f"   Album: {album_name}")
        
        # Step 1: Check Playwright availability
        log("1️⃣ Checking Playwright installation...")
        try:
            from playwright.async_api import async_playwright
            log("   ✓ Playwright module imported successfully")
        except ImportError as e:
            log(f"   ✗ Playwright import failed: {e}")
            raise
        
        # Step 2: Initialize scraper
        log("2️⃣ Initializing MetalArchivesScraper...")
        from scraper import MetalArchivesScraper
        from platform_verifier import PlatformVerifier
        
        scraper = MetalArchivesScraper(headless=True)
        try:
            await scraper.initialize()
            log("   ✓ Scraper initialized successfully")
            log(f"   Browser: Chromium (headless)")
        except Exception as e:
            log(f"   ✗ Scraper initialization failed: {e}")
            raise
        
        verifier = PlatformVerifier(scraper.page)
        log("   ✓ PlatformVerifier created")
        
        try:
            # Step 3: Construct search URL
            search_query = f"{band_name} {album_name} full album"
            search_url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}"
            log(f"3️⃣ Navigating to YouTube...")
            log(f"   URL: {search_url}")
            
            # Step 4: Navigate to YouTube
            try:
                await scraper.page.goto(search_url, wait_until='networkidle', timeout=30000)
                log("   ✓ Page loaded successfully")
                await asyncio.sleep(2)
            except Exception as e:
                log(f"   ✗ Navigation failed: {e}")
                raise
            
            # Step 5: Check page title
            try:
                page_title = await scraper.page.title()
                log(f"   Page title: {page_title}")
            except Exception as e:
                log(f"   ⚠️  Could not get page title: {e}")
            
            # Step 6: Extract search results
            log("4️⃣ Extracting search results...")
            try:
                results = await scraper.page.evaluate('''() => {
                    const items = [];
                    const videoElements = document.querySelectorAll('ytd-video-renderer, ytd-playlist-renderer');
                    
                    videoElements.forEach(el => {
                        const titleEl = el.querySelector('#video-title, h3 a');
                        const linkEl = el.querySelector('a#thumbnail, a#video-title');
                        
                        if (titleEl && linkEl) {
                            const title = titleEl.textContent?.trim() || titleEl.getAttribute('title') || '';
                            const href = linkEl.getAttribute('href') || '';
                            
                            if (title && href) {
                                items.push({
                                    title: title,
                                    url: href.startsWith('http') ? href : 'https://www.youtube.com' + href,
                                    isPlaylist: href.includes('list=')
                                });
                            }
                        }
                    });
                    
                    return items;
                }''')
                log(f"   ✓ Found {len(results)} search results")
            except Exception as e:
                log(f"   ✗ Failed to extract results: {e}")
                raise
            
            if not results:
                log("   ⚠️  No results found - possible bot detection or page structure change")
                
                # Get page content for debugging
                try:
                    content = await scraper.page.content()
                    if 'captcha' in content.lower():
                        log("   ⚠️  CAPTCHA detected in page content")
                    if 'unusual traffic' in content.lower():
                        log("   ⚠️  'Unusual traffic' message detected")
                    if 'consent' in content.lower():
                        log("   ⚠️  Cookie consent detected")
                except:
                    pass
            
            # Step 7: Fuzzy match results
            log("5️⃣ Performing fuzzy matching...")
            search_term = f"{band_name} {album_name}".lower()
            min_similarity = 90
            
            matches = []
            detailed_results = []
            
            for i, result in enumerate(results[:10], 1):
                title_lower = result['title'].lower()
                
                # Calculate similarity scores
                full_score = fuzz.token_sort_ratio(search_term, title_lower)
                album_score = fuzz.partial_ratio(album_name.lower(), title_lower)
                band_score = fuzz.partial_ratio(band_name.lower(), title_lower)
                
                # Boost score if "full album" is in title
                boost = 10 if 'full album' in title_lower else 0
                
                # Boost if both band and album are present
                if band_score > 70 and album_score > 70:
                    score = max(full_score, (album_score + band_score) // 2) + boost
                else:
                    score = max(full_score, album_score) + boost
                
                final_score = min(score, 100)
                
                match_status = "✓ MATCH" if final_score >= min_similarity else "✗ Below threshold"
                
                detailed_results.append({
                    "rank": i,
                    "title": result['title'],
                    "url": result['url'],
                    "is_playlist": result['isPlaylist'],
                    "scores": {
                        "final": final_score,
                        "full_match": full_score,
                        "album_match": album_score,
                        "band_match": band_score,
                        "boost": boost
                    },
                    "matched": final_score >= min_similarity
                })
                
                if final_score >= min_similarity:
                    matches.append({
                        'title': result['title'],
                        'url': result['url'],
                        'score': final_score,
                        'isPlaylist': result['isPlaylist']
                    })
                    log(f"   {match_status} [{final_score}%] {result['title'][:60]}")
            
            # Step 8: Return best match
            if matches:
                best_match = matches[0]
                log(f"6️⃣ ✓ SUCCESS! Best match found:")
                log(f"   Score: {best_match['score']}%")
                log(f"   Title: {best_match['title']}")
                log(f"   Type: {'Playlist' if best_match['isPlaylist'] else 'Video'}")
                
                # Call the actual search function to get formatted result
                final_result = await verifier.search_youtube_directly(
                    album_name=album_name,
                    band_name=band_name,
                    min_similarity=90
                )
                
                return {
                    "success": True,
                    "search_query": search_query,
                    "total_results": len(results),
                    "matches_found": len(matches),
                    "best_match": {
                        "title": best_match['title'],
                        "url": best_match['url'],
                        "score": best_match['score'],
                        "type": 'playlist' if best_match['isPlaylist'] else 'video'
                    },
                    "verification_result": final_result,
                    "detailed_results": detailed_results[:5],  # Top 5 results
                    "diagnostic_log": diagnostic_log,
                    "execution_time": f"{time.time() - start_time:.2f}s"
                }
            else:
                log(f"6️⃣ ✗ FAILED! No matches above {min_similarity}% threshold")
                log(f"   This could mean:")
                log(f"   - Album doesn't exist on YouTube")
                log(f"   - Search results are too different from album name")
                log(f"   - Bot detection is affecting results")
                
                return {
                    "success": False,
                    "search_query": search_query,
                    "total_results": len(results),
                    "matches_found": 0,
                    "reason": f"No matches above {min_similarity}% similarity threshold",
                    "detailed_results": detailed_results[:5],
                    "diagnostic_log": diagnostic_log,
                    "execution_time": f"{time.time() - start_time:.2f}s"
                }
                
        finally:
            await scraper.close()
            log("🔧 Scraper closed")
            
    except Exception as e:
        log(f"❌ CRITICAL ERROR: {e}")
        logger.error(f"YouTube search test error: {e}")
        import traceback
        error_trace = traceback.format_exc()
        log(f"Traceback:\n{error_trace}")
        
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": error_trace,
            "diagnostic_log": diagnostic_log,
            "execution_time": f"{time.time() - start_time:.2f}s"
        }

@app.delete("/api/admin/data/{date}")
async def delete_data_by_date(date: str, token: str = Depends(verify_admin_token)):
    """Delete all data for a specific date"""
    search_date = None
    
    try:
        # Try YYYY-MM-DD format first (database storage format)
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
            search_date = date  # Use as-is since it matches database format
        except ValueError:
            # Try DD-MM-YYYY format and convert to database format
            parsed_date = datetime.strptime(date, "%d-%m-%Y")
            search_date = parsed_date.strftime("%Y-%m-%d")  # Convert to database format
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD or DD-MM-YYYY")
    
    deleted_count = db.delete_albums_by_date(search_date)
    
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"No data found for date {date}")
    
    return {
        "message": f"Deleted {deleted_count} albums for {date}",
        "date": date,
        "deleted_albums": deleted_count
    }

@app.delete("/api/admin/data/range")
async def delete_data_by_range(request: DeleteRangeRequest, token: str = Depends(verify_admin_token)):
    """Delete all data within a date range"""
    try:
        # Validate date formats
        start_parsed = datetime.strptime(request.start_date, "%d-%m-%Y")
        end_parsed = datetime.strptime(request.end_date, "%d-%m-%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use DD-MM-YYYY")
    
    if start_parsed > end_parsed:
        raise HTTPException(status_code=400, detail="Start date must be before or equal to end date")
    
    deleted_count = db.delete_albums_by_date_range(request.start_date, request.end_date)
    
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"No data found in range {request.start_date} to {request.end_date}")
    
    return {
        "message": f"Deleted {deleted_count} albums from {request.start_date} to {request.end_date}",
        "start_date": request.start_date,
        "end_date": request.end_date,
        "deleted_albums": deleted_count
    }

@app.get("/api/admin/summary")
async def get_admin_summary(token: str = Depends(verify_admin_token)):
    """Get database summary for admin dashboard"""
    try:
        summary = db.get_data_summary()
        summary["scraping_status"] = scraping_status
        return summary
    except Exception as e:
        logger.error(f"Error fetching admin summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch admin summary")

# Settings endpoints
@app.get("/api/admin/settings/platform-links")
async def get_platform_link_settings(token: str = Depends(verify_admin_token)):
    """Get platform link visibility settings"""
    import config as app_config
    
    # Get settings from database or use defaults from config
    platforms = app_config.LINK_EXTRACTION.get('platforms', {})
    settings = {}
    
    for platform_name, platform_info in platforms.items():
        # Try to get from database first
        db_setting = db.get_setting(f'platform_link_visible_{platform_name}')
        if db_setting is not None:
            visible = db_setting
        else:
            # Use config default
            visible = platform_info.get('enabled', True)
        
        settings[platform_name] = {
            'visible': visible,
            'label': platform_name.capitalize(),
            'patterns': platform_info.get('patterns', [])
        }
    
    return {"settings": settings}

@app.put("/api/admin/settings/platform-links")
async def update_platform_link_settings(settings: dict, token: str = Depends(verify_admin_token)):
    """Update platform link visibility settings"""
    try:
        for platform_name, platform_data in settings.items():
            if 'visible' in platform_data:
                db.set_setting(
                    f'platform_link_visible_{platform_name}',
                    platform_data['visible'],
                    category='platform_links',
                    description=f'Visibility setting for {platform_name} links'
                )
        
        return {"message": "Settings updated successfully", "settings": settings}
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")

@app.get("/api/settings/platform-links")
async def get_public_platform_link_settings():
    """Get platform link visibility settings (public endpoint for frontend)"""
    import config as app_config
    
    platforms = app_config.LINK_EXTRACTION.get('platforms', {})
    settings = {}
    
    for platform_name, platform_info in platforms.items():
        # Try to get from database first
        db_setting = db.get_setting(f'platform_link_visible_{platform_name}')
        if db_setting is not None:
            visible = db_setting
        else:
            # Use config default
            visible = platform_info.get('enabled', True)
        
        settings[platform_name] = visible
    
    return {"settings": settings}

# YouTube Cache Management endpoints
@app.get("/api/admin/cache/stats")
async def get_cache_stats(token: str = Depends(verify_admin_token)):
    """Get YouTube cache statistics"""
    try:
        stats = youtube_cache.get_cache_stats()
        return {"stats": stats}
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache stats")

@app.post("/api/admin/cache/clear")
async def clear_cache(token: str = Depends(verify_admin_token)):
    """Clear entire YouTube cache"""
    try:
        youtube_cache.clear_cache()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

@app.get("/api/admin/settings/cache")
async def get_cache_settings(token: str = Depends(verify_admin_token)):
    """Get YouTube cache and download settings"""
    try:
        max_size_gb = db.get_setting('youtube_cache_max_size_gb')
        if max_size_gb is None:
            max_size_gb = config.YOUTUBE_CACHE_MAX_SIZE_GB
        
        parallel_downloads = db.get_setting('youtube_parallel_downloads')
        if parallel_downloads is None:
            parallel_downloads = config.YOUTUBE_PARALLEL_DOWNLOADS
        
        download_timeout = db.get_setting('youtube_download_timeout')
        if download_timeout is None:
            download_timeout = config.YOUTUBE_DOWNLOAD_TIMEOUT
        
        post_scrape_downloads = db.get_setting('youtube_post_scrape_downloads')
        if post_scrape_downloads is None:
            post_scrape_downloads = config.YOUTUBE_POST_SCRAPE_DOWNLOADS
        
        return {
            "youtube_cache_max_size_gb": float(max_size_gb),
            "youtube_parallel_downloads": int(parallel_downloads),
            "youtube_download_timeout": int(download_timeout),
            "youtube_post_scrape_downloads": int(post_scrape_downloads)
        }
    except Exception as e:
        logger.error(f"Error getting cache settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache settings")

@app.put("/api/admin/settings/cache")
async def update_cache_settings(settings: dict, token: str = Depends(verify_admin_token)):
    """Update YouTube cache and download settings"""
    try:
        if 'youtube_cache_max_size_gb' in settings:
            new_size = float(settings['youtube_cache_max_size_gb'])
            
            # Validate size (must be positive, reasonable limit of 100GB)
            if new_size <= 0 or new_size > 100:
                raise HTTPException(status_code=400, detail="Cache size must be between 0 and 100 GB")
            
            # Save to database
            db.set_setting(
                'youtube_cache_max_size_gb',
                new_size,
                category='cache',
                description='Maximum YouTube cache size in gigabytes'
            )
            
            # Update cache manager
            youtube_cache.update_max_size(new_size)
            
            logger.info(f"📦 [CACHE] Settings updated: max_size={new_size} GB")
        
        if 'youtube_parallel_downloads' in settings:
            new_parallel = int(settings['youtube_parallel_downloads'])
            
            # Validate (must be between 1 and 10)
            if new_parallel < 1 or new_parallel > 10:
                raise HTTPException(status_code=400, detail="Parallel downloads must be between 1 and 10")
            
            # Save to database
            db.set_setting(
                'youtube_parallel_downloads',
                new_parallel,
                category='cache',
                description='Maximum number of parallel YouTube downloads'
            )
            
            # Update download manager
            youtube_download_manager.update_max_parallel(new_parallel)
            
            logger.info(f"🔧 [DOWNLOAD-MGR] Settings updated: max_parallel={new_parallel}")
        
        if 'youtube_download_timeout' in settings:
            new_timeout = int(settings['youtube_download_timeout'])
            
            # Validate (must be between 60 and 600 seconds)
            if new_timeout < 60 or new_timeout > 600:
                raise HTTPException(status_code=400, detail="Download timeout must be between 60 and 600 seconds")
            
            # Save to database
            db.set_setting(
                'youtube_download_timeout',
                new_timeout,
                category='cache',
                description='Timeout for individual YouTube downloads in seconds'
            )
            
            # Note: timeout change requires restart to take effect
            logger.info(f"🔧 [DOWNLOAD-MGR] Settings updated: timeout={new_timeout}s (requires restart)")
        
        if 'youtube_post_scrape_downloads' in settings:
            new_post_scrape = int(settings['youtube_post_scrape_downloads'])
            
            # Validate (must be between 1 and 10)
            if new_post_scrape < 1 or new_post_scrape > 10:
                raise HTTPException(status_code=400, detail="Post-scrape parallel downloads must be between 1 and 10")
            
            # Save to database
            db.set_setting(
                'youtube_post_scrape_downloads',
                new_post_scrape,
                category='cache',
                description='Parallel downloads after scraping completes (1-10)'
            )
            
            logger.info(f"🔧 [DOWNLOAD-MGR] Settings updated: post_scrape_downloads={new_post_scrape}")
        
        return {"message": "Cache settings updated successfully", "settings": settings}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cache settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update cache settings")

# Player Settings endpoints
@app.get("/api/admin/settings/player")
async def get_player_settings():
    """Get player service settings (public endpoint)"""
    try:
        bandcamp_enabled = db.get_setting('player_bandcamp_enabled')
        youtube_enabled = db.get_setting('player_youtube_enabled')
        
        # Default to True if not set
        if bandcamp_enabled is None:
            bandcamp_enabled = True
        if youtube_enabled is None:
            youtube_enabled = True
        
        logger.info(f"📖 [PLAYER] Settings requested - Bandcamp: {bandcamp_enabled}, YouTube: {youtube_enabled}")
        
        return {
            "bandcamp_enabled": bool(bandcamp_enabled),
            "youtube_enabled": bool(youtube_enabled)
        }
    except Exception as e:
        logger.error(f"Error getting player settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get player settings")

@app.put("/api/admin/settings/player")
async def update_player_settings(settings: dict, token: str = Depends(verify_admin_token)):
    """Update player service settings"""
    try:
        if 'bandcamp_enabled' in settings:
            db.set_setting(
                'player_bandcamp_enabled',
                bool(settings['bandcamp_enabled']),
                category='player',
                description='Enable/disable Bandcamp player'
            )
            logger.info(f"🎵 [PLAYER] Bandcamp enabled: {settings['bandcamp_enabled']}")
        
        if 'youtube_enabled' in settings:
            db.set_setting(
                'player_youtube_enabled',
                bool(settings['youtube_enabled']),
                category='player',
                description='Enable/disable YouTube player'
            )
            logger.info(f"🎬 [PLAYER] YouTube enabled: {settings['youtube_enabled']}")
        
        return {"message": "Player settings updated successfully", "settings": settings}
    except Exception as e:
        logger.error(f"Error updating player settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update player settings")

# Authentication endpoints
@app.get("/api/auth/status")
async def get_auth_status():
    """Get authentication status (public endpoint)"""
    return auth_manager.get_auth_status()

@app.post("/api/auth/setup", response_model=AuthResponse)
async def setup_admin_password(request: SetupRequest):
    """Set up admin password for first-time use"""
    try:
        if not auth_manager.is_first_time_setup():
            raise HTTPException(status_code=409, detail="Admin password already set")
        
        auth_manager.set_admin_password(request.password)
        token = auth_manager.generate_token(expires_hours=24)
        
        return AuthResponse(
            success=True,
            token=token,
            message="Admin password set successfully",
            expires_hours=24
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Setup error: {e}")
        raise HTTPException(status_code=500, detail="Setup failed")

@app.post("/api/auth/login", response_model=AuthResponse)
async def admin_login(request: LoginRequest):
    """Admin login endpoint"""
    try:
        if auth_manager.is_first_time_setup():
            raise HTTPException(status_code=409, detail="First-time setup required")
        
        if auth_manager.verify_password(request.password):
            expires_hours = 168 if request.remember_me else 24  # 7 days or 24 hours
            token = auth_manager.generate_token(expires_hours=expires_hours)
            
            return AuthResponse(
                success=True,
                token=token,
                message="Login successful",
                expires_hours=expires_hours
            )
        else:
            raise HTTPException(status_code=401, detail="Invalid password")
    
    except ValueError as e:
        # Handle account locked or other auth errors
        raise HTTPException(status_code=423, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.post("/api/auth/verify")
async def verify_token_endpoint(token: str = Depends(verify_admin_token)):
    """Verify if token is valid (protected endpoint)"""
    return {"valid": True, "message": "Token is valid"}

# ============================================================================
# PLAYLIST ENDPOINTS
# ============================================================================

@app.get("/api/playlists")
async def get_playlists():
    """Get all playlists."""
    try:
        playlists = db.get_all_playlists()
        return {"playlists": playlists}
    except Exception as e:
        logger.error(f"Error fetching playlists: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch playlists")

@app.get("/api/playlists/{playlist_id}")
async def get_playlist(playlist_id: int):
    """Get playlist details with items."""
    try:
        playlist = db.get_playlist(playlist_id)
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")
        return playlist
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching playlist {playlist_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch playlist")

@app.post("/api/playlists")
async def create_playlist(request: PlaylistCreate):
    """Create new playlist."""
    try:
        playlist_id = db.create_playlist(
            name=request.name,
            description=request.description,
            is_public=request.is_public
        )
        return {"id": playlist_id, "name": request.name, "message": "Playlist created successfully"}
    except Exception as e:
        logger.error(f"Error creating playlist: {e}")
        raise HTTPException(status_code=500, detail="Failed to create playlist")

@app.put("/api/playlists/{playlist_id}")
async def update_playlist(playlist_id: int, request: PlaylistUpdate):
    """Update playlist metadata."""
    try:
        success = db.update_playlist(
            playlist_id=playlist_id,
            name=request.name,
            description=request.description,
            is_public=request.is_public
        )
        if not success:
            raise HTTPException(status_code=404, detail="Playlist not found")
        return {"success": True, "message": "Playlist updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating playlist: {e}")
        raise HTTPException(status_code=500, detail="Failed to update playlist")

@app.delete("/api/playlists/{playlist_id}")
async def delete_playlist(playlist_id: int):
    """Delete playlist."""
    try:
        success = db.delete_playlist(playlist_id)
        if not success:
            raise HTTPException(status_code=404, detail="Playlist not found")
        return {"success": True, "message": "Playlist deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting playlist: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete playlist")

@app.post("/api/playlists/{playlist_id}/items")
async def add_playlist_item(
    playlist_id: int, 
    request: PlaylistItemCreate,
    background_tasks: BackgroundTasks
):
    """
    Add item to playlist with verification.
    Verifies that the platform link contains the album using fuzzy matching.
    """
    try:
        # Check if playlist exists
        playlist = db.get_playlist(playlist_id)
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")
        
        # Get album details
        album = db.get_album_by_id(request.album_id)
        if not album:
            raise HTTPException(status_code=404, detail="Album not found")
        
        # Get the platform URL
        platform_url = album.get(f'{request.platform}_url')
        if not platform_url or platform_url == 'N/A' or platform_url == '':
            raise HTTPException(
                status_code=400, 
                detail=f"No {request.platform} link available for this album"
            )
        
        # Initialize scraper for verification
        scraper = MetalArchivesScraper(headless=True)
        await scraper.initialize()
        
        try:
            # Create verifier
            verifier = PlatformVerifier(scraper.page)
            
            # Verify based on platform
            if request.platform == 'youtube':
                result = await verifier.verify_youtube_album(
                    youtube_url=platform_url,
                    album_name=album['album_name'],
                    band_name=album['band_name'],
                    min_similarity=75  # Configurable threshold
                )
            elif request.platform == 'bandcamp':
                result = await verifier.verify_bandcamp_album(
                    bandcamp_url=platform_url,
                    album_name=album['album_name'],
                    album_type=album.get('type', 'album'),
                    min_similarity=75
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Platform '{request.platform}' not supported for playback. Only 'youtube' and 'bandcamp' are supported."
                )
            
            # Check if album was found
            if not result.get('found'):
                error_msg = result.get('error', 'Album not found on platform')
                raise HTTPException(
                    status_code=404,
                    detail=f"Album not found on {request.platform}. {error_msg}"
                )
            
            # Add to playlist with verified URL
            item_id = db.add_playlist_item_verified(
                playlist_id=playlist_id,
                album_id=request.album_id,
                platform=request.platform,
                playable_url=result['embed_url'],
                verification_status='verified',
                verification_score=result['match_score'],
                verified_title=result['title'],
                embed_type=result.get('type', 'video'),
                track_number=request.track_number
            )
            
            return {
                "id": item_id,
                "verified": True,
                "match_score": result['match_score'],
                "found_title": result['title'],
                "embed_url": result['embed_url'],
                "message": f"Added to playlist (Match: {result['match_score']}%)"
            }
            
        finally:
            await scraper.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding playlist item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/playlists/{playlist_id}/items/{item_id}")
async def delete_playlist_item(playlist_id: int, item_id: int):
    """Remove item from playlist."""
    try:
        success = db.delete_playlist_item(playlist_id, item_id)
        if not success:
            raise HTTPException(status_code=404, detail="Playlist item not found")
        return {"success": True, "message": "Item removed from playlist"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting playlist item: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete item")

@app.put("/api/playlists/{playlist_id}/reorder")
async def reorder_playlist(playlist_id: int, request: ReorderRequest):
    """Reorder playlist items."""
    try:
        success = db.reorder_playlist_items(playlist_id, request.item_ids)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to reorder items")
        return {"success": True, "message": "Playlist reordered successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reordering playlist: {e}")
        raise HTTPException(status_code=500, detail="Failed to reorder playlist")

@app.get("/api/albums/{album_id}/playable-links")
async def get_playable_links(album_id: str):
    """Get all playable links for an album."""
    try:
        album = db.get_album_by_id(album_id)
        if not album:
            raise HTTPException(status_code=404, detail="Album not found")
        
        links = {}
        
        # Check YouTube
        if album.get('youtube_url') and album['youtube_url'] != 'N/A':
            links['youtube'] = {
                'available': True,
                'url': album['youtube_url']
            }
        else:
            links['youtube'] = {'available': False}
        
        # Check Bandcamp
        if album.get('bandcamp_url') and album['bandcamp_url'] != 'N/A':
            links['bandcamp'] = {
                'available': True,
                'url': album['bandcamp_url']
            }
        else:
            links['bandcamp'] = {'available': False}
        
        return {
            "album_id": album_id,
            "album_name": album['album_name'],
            "band_name": album['band_name'],
            "playable_links": links
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting playable links: {e}")
        raise HTTPException(status_code=500, detail="Failed to get playable links")

@app.get("/api/playlist/dynamic")
async def get_dynamic_playlist(
    period_type: str = Query(..., description="day, week, or month"),
    period_key: str = Query(..., description="Date or period identifier"),
    genres: Optional[str] = Query(None, description="Comma-separated genre filters"),
    search: Optional[str] = Query(None, description="Search query"),
    shuffle: bool = Query(False, description="Shuffle playlist order")
):
    """
    Generate dynamic playlist for a period with filters.
    Returns albums with verified playable URLs ready for sidebar player.
    """
    logger.info(f"🎵 Dynamic playlist request: {period_type} = {period_key}")
    logger.info(f"   Filters: genres={genres}, search={search}, shuffle={shuffle}")
    
    try:
        # Parse genre filters
        genre_filters = [g.strip() for g in genres.split(',')] if genres else None
        
        # Calculate date range based on period type
        if period_type == 'day':
            albums = db.get_albums_for_dynamic_playlist(
                release_date=period_key,
                genre_filters=genre_filters,
                search_query=search,
                only_playable=True
            )
        elif period_type == 'week':
            # Period key format: "2024-W01"
            from datetime import datetime, timedelta
            year, week = period_key.split('-W')
            # Calculate start and end of week
            first_day = datetime.strptime(f'{year}-W{week}-1', '%Y-W%W-%w')
            last_day = first_day + timedelta(days=6)
            
            albums = db.get_albums_for_dynamic_playlist(
                start_date=first_day.strftime('%Y-%m-%d'),
                end_date=last_day.strftime('%Y-%m-%d'),
                genre_filters=genre_filters,
                search_query=search,
                only_playable=True
            )
        elif period_type == 'month':
            # Period key format: "2024-01"
            from datetime import datetime
            from calendar import monthrange
            year, month = map(int, period_key.split('-'))
            last_day = monthrange(year, month)[1]
            
            albums = db.get_albums_for_dynamic_playlist(
                start_date=f'{year}-{month:02d}-01',
                end_date=f'{year}-{month:02d}-{last_day:02d}',
                genre_filters=genre_filters,
                search_query=search,
                only_playable=True
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid period_type. Must be day, week, or month")
        
        # Get player settings to filter by enabled platforms
        bandcamp_enabled = db.get_setting('player_bandcamp_enabled')
        youtube_enabled = db.get_setting('player_youtube_enabled')
        
        # Default to True if not set
        if bandcamp_enabled is None:
            bandcamp_enabled = True
        if youtube_enabled is None:
            youtube_enabled = True
        
        logger.info(f"   Player settings: Bandcamp={bandcamp_enabled}, YouTube={youtube_enabled}")
        
        # Shuffle if requested
        if shuffle:
            import random
            random.shuffle(albums)
        
        # Transform to playable format
        playlist_items = []
        skipped_albums = 0
        for album in albums:
            item = {
                'album_id': album['album_id'],
                'title': album['album_name'],
                'artist': album['band_name'],
                'type': album.get('type', 'Full-length'),
                'release_date': album['release_date'],
                'genre': album.get('genre'),
                'cover_art': album.get('cover_art'),
                'cover_path': album.get('cover_path'),
                'album_url': album.get('album_url'),
                'platforms': {}
            }
            
            # Add YouTube embed if available AND enabled
            if album.get('youtube_embed_url') and youtube_enabled:
                item['platforms']['youtube'] = {
                    'embed_url': album['youtube_embed_url'],
                    'verified_title': album.get('youtube_verified_title'),
                    'verification_score': album.get('youtube_verification_score'),
                    'embed_type': album.get('youtube_embed_type', 'video')
                }
            
            # Add Bandcamp embed if available AND enabled
            if album.get('bandcamp_embed_url') and bandcamp_enabled:
                item['platforms']['bandcamp'] = {
                    'embed_url': album['bandcamp_embed_url'],
                    'verified_title': album.get('bandcamp_verified_title'),
                    'verification_score': album.get('bandcamp_verification_score')
                }
            
            # Only include if at least one ENABLED platform is available
            if item['platforms']:
                playlist_items.append(item)
            else:
                skipped_albums += 1
        
        if skipped_albums > 0:
            logger.info(f"   ⏭️  Skipped {skipped_albums} albums (no enabled platforms available)")
        
        logger.info(f"   ✓ Returning {len(playlist_items)} playable items out of {len(albums)} total albums")
        
        return {
            'period_type': period_type,
            'period_key': period_key,
            'total_albums': len(playlist_items),
            'filters': {
                'genres': genre_filters,
                'search': search,
                'shuffle': shuffle
            },
            'items': playlist_items
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating dynamic playlist: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate playlist: {str(e)}")

# Serve React frontend (will be created next)
@app.get("/")
async def serve_frontend():
    """Serve the React frontend"""
    frontend_path = Path(__file__).parent / "frontend" / "build" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    else:
        return {"message": "Metal Albums API", "frontend": "not_built", "api_docs": "/docs", "admin_endpoints": ["/api/admin/scrape", "/api/admin/scrape/status", "/api/admin/summary"]}

# Mount static files for React build
frontend_build_path = Path(__file__).parent / "frontend" / "build"
if frontend_build_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_build_path / "static")), name="static")

# Mount covers directory for album cover images
covers_path = Path(__file__).parent / "covers"
if covers_path.exists():
    app.mount("/covers", StaticFiles(directory=str(covers_path)), name="covers")

class WebServer:
    """Web server wrapper for integration with orchestrator"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
    
    def start(self):
        """Start the web server in a separate thread"""
        def run_server():
            config = uvicorn.Config(
                app, 
                host=self.host, 
                port=self.port, 
                log_level="info",
                access_log=False
            )
            self.server = uvicorn.Server(config)
            asyncio.run(self.server.serve())
        
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()
        logger.info(f"🌐 Web server starting at http://{self.host}:{self.port}")
    
    def stop(self):
        """Stop the web server"""
        if self.server:
            self.server.should_exit = True
        logger.info("🌐 Web server stopped")

if __name__ == "__main__":
    # Run server directly
    uvicorn.run(app, host="0.0.0.0", port=8000)
