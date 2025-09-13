#!/usr/bin/env python3
"""
FastAPI Web Server for Metal Albums Database
Serves API endpoints and static frontend files
"""

import asyncio
import threading
import json
from datetime import datetime, date
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import uvicorn
import logging
from pathlib import Path
from db_manager import AlbumsDatabase, ingest_json_files
from scraper import MetalArchivesScraper
from models import Album

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Metal Albums API",
    description="API for browsing metal album releases",
    version="1.0.0"
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global database instance
db = AlbumsDatabase()

# Global scraping status
scraping_status = {
    "is_running": False,
    "current_date": None,
    "progress": 0,
    "total": 0,
    "status_message": "Idle",
    "error": None,
    "start_time": None,
    "end_time": None
}

# Pydantic models for admin endpoints
class ScrapeRequest(BaseModel):
    date: str  # Format: DD-MM-YYYY
    download_covers: bool = True
    
class DeleteDateRequest(BaseModel):
    date: str  # Format: DD-MM-YYYY or YYYY-MM-DD
    
class DeleteRangeRequest(BaseModel):
    start_date: str
    end_date: str

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    db.connect()
    logger.info("🗄️ Database connected")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    db.close()
    logger.info("🗄️ Database disconnected")

@app.get("/api/dates")
async def get_available_dates():
    """Get all available release dates with album counts"""
    try:
        dates = db.get_available_dates()
        return {"dates": dates, "total": len(dates)}
    except Exception as e:
        logger.error(f"Error fetching dates: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dates")

@app.get("/api/albums/{release_date}")
async def get_albums_by_date(release_date: str):
    """Get all albums for a specific release date"""
    try:
        albums = db.get_albums_by_date(release_date)
        return {"albums": albums, "total": len(albums), "date": release_date}
    except Exception as e:
        logger.error(f"Error fetching albums for {release_date}: {e}")
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
# ADMIN ENDPOINTS
# ============================================================================

async def run_scraper_task(scrape_date: str, download_covers: bool = True):
    """Background task to run the scraper"""
    global scraping_status
    
    try:
        scraping_status.update({
            "is_running": True,
            "current_date": scrape_date,
            "progress": 0,
            "total": 0,
            "status_message": "Initializing scraper...",
            "error": None,
            "start_time": datetime.now().isoformat(),
            "end_time": None
        })
        
        # Initialize scraper
        scraper = MetalArchivesScraper(headless=True)
        await scraper.initialize()
        
        scraping_status["status_message"] = f"Scraping albums for {scrape_date}..."
        
        # Run the scraper
        date_obj = datetime.strptime(scrape_date, "%d-%m-%Y").date()
        albums_data = await scraper.search_albums_by_date(date_obj)
        
        # Convert to Album objects if needed
        albums = []
        for album_data in albums_data:
            album = Album.from_scraped_data(album_data)
            if download_covers:
                await scraper.download_cover(album_data)
            albums.append(album)
        
        scraping_status.update({
            "progress": len(albums),
            "total": len(albums),
            "status_message": f"Scraped {len(albums)} albums, saving to database..."
        })
        
        # Save to JSON file - flatten band data for database compatibility
        json_filename = f"data/albums_{scrape_date}.json"
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
        
        scraping_status.update({
            "is_running": False,
            "status_message": f"Successfully scraped and saved {len(albums)} albums for {scrape_date}",
            "end_time": datetime.now().isoformat()
        })
        
        await scraper.close()
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        scraping_status.update({
            "is_running": False,
            "error": str(e),
            "status_message": f"Scraping failed: {str(e)}",
            "end_time": datetime.now().isoformat()
        })
        
        # Cleanup scraper if it was initialized
        try:
            await scraper.close()
        except:
            pass

@app.post("/api/admin/scrape")
async def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Trigger manual scraping for a specific date"""
    if scraping_status["is_running"]:
        raise HTTPException(status_code=409, detail="Scraping is already in progress")
    
    # Validate date format
    try:
        datetime.strptime(request.date, "%d-%m-%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use DD-MM-YYYY")
    
    # Check if data already exists for this date
    if db.check_date_exists(request.date):
        raise HTTPException(
            status_code=409, 
            detail=f"Data already exists for {request.date}. Delete existing data first if you want to re-scrape."
        )
    
    # Start background scraping task
    background_tasks.add_task(run_scraper_task, request.date, request.download_covers)
    
    return {
        "message": f"Scraping started for {request.date}",
        "date": request.date,
        "download_covers": request.download_covers
    }

@app.get("/api/admin/scrape/status")
async def get_scrape_status():
    """Get current scraping status"""
    return scraping_status

@app.delete("/api/admin/data/{date}")
async def delete_data_by_date(date: str):
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
async def delete_data_by_range(request: DeleteRangeRequest):
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
async def get_admin_summary():
    """Get database summary for admin dashboard"""
    try:
        summary = db.get_data_summary()
        summary["scraping_status"] = scraping_status
        return summary
    except Exception as e:
        logger.error(f"Error fetching admin summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch admin summary")

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
    uvicorn.run(app, host="127.0.0.1", port=8000)
