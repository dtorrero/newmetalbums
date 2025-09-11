#!/usr/bin/env python3
"""
FastAPI Web Server for Metal Albums Database
Serves API endpoints and static frontend files
"""

import asyncio
import threading
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import uvicorn
import logging
from pathlib import Path
from db_manager import AlbumsDatabase

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

# Serve React frontend (will be created next)
@app.get("/")
async def serve_frontend():
    """Serve the React frontend"""
    frontend_path = Path(__file__).parent / "frontend" / "build" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    else:
        return {"message": "Metal Albums API", "frontend": "not_built", "api_docs": "/docs"}

# Mount static files for React build
frontend_build_path = Path(__file__).parent / "frontend" / "build"
if frontend_build_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_build_path / "static")), name="static")

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
