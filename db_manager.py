#!/usr/bin/env python3
"""
Database Manager for Metal Albums
Handles SQLite database creation and JSON data ingestion
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import glob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlbumsDatabase:
    def __init__(self, db_path: str = "albums.db"):
        self.db_path = db_path
        self.connection = None
    
    def connect(self):
        """Connect to SQLite database"""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row  # Enable dict-like access
        return self.connection
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
    
    def create_tables(self):
        """Create database tables"""
        cursor = self.connection.cursor()
        
        # Albums table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS albums (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                album_id TEXT UNIQUE NOT NULL,
                album_name TEXT NOT NULL,
                album_url TEXT,
                band_name TEXT NOT NULL,
                band_id TEXT,
                band_url TEXT,
                release_date DATE NOT NULL,
                release_date_raw TEXT,
                type TEXT,
                cover_art TEXT,
                cover_path TEXT,
                bandcamp_url TEXT,
                country_of_origin TEXT,
                location TEXT,
                genre TEXT,
                themes TEXT,
                current_label TEXT,
                years_active TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tracks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                album_id TEXT NOT NULL,
                track_number TEXT NOT NULL,
                track_name TEXT NOT NULL,
                track_length TEXT,
                lyrics_url TEXT,
                FOREIGN KEY (album_id) REFERENCES albums (album_id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_albums_release_date ON albums(release_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_albums_band_name ON albums(band_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_albums_genre ON albums(genre)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_album_id ON tracks(album_id)')
        
        self.connection.commit()
        logger.info("Database tables created successfully")
    
    def insert_album(self, album_data: Dict[str, Any]) -> bool:
        """Insert album data into database"""
        cursor = self.connection.cursor()
        
        try:
            # Extract release date from top-level field (not from details)
            release_date = album_data.get('release_date', '')
            release_date_raw = album_data.get('release_date_raw', '')
            
            # Extract band details (these come from band page scraping)
            country_of_origin = album_data.get('country_of_origin', '')
            location = album_data.get('location', '')
            genre = album_data.get('genre', '')
            themes = album_data.get('themes', '')
            current_label = album_data.get('current_label', '')
            years_active = album_data.get('years_active', '')
            
            # Insert album
            cursor.execute('''
                INSERT OR REPLACE INTO albums (
                    album_id, album_name, album_url, band_name, band_id, band_url,
                    release_date, release_date_raw, type, cover_art, cover_path,
                    bandcamp_url, country_of_origin, location, genre, themes,
                    current_label, years_active, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                album_data.get('album_id', ''),
                album_data.get('album_name', ''),
                album_data.get('album_url', ''),
                album_data.get('band_name', ''),
                album_data.get('band_id', ''),
                album_data.get('band_url', ''),
                release_date,
                release_date_raw,
                album_data.get('type', ''),
                album_data.get('cover_art', ''),
                album_data.get('cover_path', ''),
                album_data.get('bandcamp_url', ''),
                country_of_origin,
                location,
                genre,
                themes,
                current_label,
                years_active,
                json.dumps(album_data.get('details', {}))
            ))
            
            # Insert tracks
            album_id = album_data.get('album_id', '')
            if album_id:
                # Delete existing tracks for this album
                cursor.execute('DELETE FROM tracks WHERE album_id = ?', (album_id,))
                
                # Insert new tracks
                for track in album_data.get('tracklist', []):
                    cursor.execute('''
                        INSERT INTO tracks (album_id, track_number, track_name, track_length, lyrics_url)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        album_id,
                        track.get('number', ''),
                        track.get('name', ''),
                        track.get('length', ''),
                        track.get('lyrics_url', '')
                    ))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error inserting album {album_data.get('album_name', 'Unknown')}: {e}")
            self.connection.rollback()
            return False
    
    def get_available_dates(self) -> List[Dict[str, Any]]:
        """Get all available release dates with album counts"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT 
                release_date,
                COUNT(*) as album_count,
                GROUP_CONCAT(DISTINCT genre) as genres
            FROM albums 
            WHERE release_date IS NOT NULL AND release_date != ''
            GROUP BY release_date 
            ORDER BY release_date DESC
        ''')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_albums_by_date(self, release_date: str) -> List[Dict[str, Any]]:
        """Get all albums for a specific release date"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT * FROM albums 
            WHERE release_date = ? 
            ORDER BY band_name, album_name
        ''', (release_date,))
        
        albums = [dict(row) for row in cursor.fetchall()]
        
        # Add tracks for each album
        for album in albums:
            cursor.execute('''
                SELECT track_number, track_name, track_length, lyrics_url
                FROM tracks 
                WHERE album_id = ? 
                ORDER BY CAST(track_number AS INTEGER)
            ''', (album['album_id'],))
            
            album['tracklist'] = [dict(row) for row in cursor.fetchall()]
            
            # Parse details JSON
            if album['details']:
                try:
                    album['details'] = json.loads(album['details'])
                except:
                    album['details'] = {}
        
        return albums

def ingest_json_files(db: AlbumsDatabase, json_pattern: str = "albums_*.json"):
    """Ingest all JSON files matching pattern into database"""
    json_files = glob.glob(json_pattern)
    
    if not json_files:
        logger.warning(f"No JSON files found matching pattern: {json_pattern}")
        return
    
    total_albums = 0
    successful_inserts = 0
    
    for json_file in json_files:
        logger.info(f"Processing {json_file}...")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                albums_data = json.load(f)
            
            if not isinstance(albums_data, list):
                logger.error(f"Expected list in {json_file}, got {type(albums_data)}")
                continue
            
            for album_data in albums_data:
                total_albums += 1
                if db.insert_album(album_data):
                    successful_inserts += 1
                    
        except Exception as e:
            logger.error(f"Error processing {json_file}: {e}")
    
    logger.info(f"Ingestion complete: {successful_inserts}/{total_albums} albums inserted successfully")

def main():
    """Main function to set up database and ingest data"""
    db = AlbumsDatabase()
    
    try:
        db.connect()
        db.create_tables()
        
        # Ingest JSON files
        ingest_json_files(db)
        
        # Show summary
        dates = db.get_available_dates()
        logger.info(f"Database now contains albums for {len(dates)} different release dates")
        
        for date_info in dates[:5]:  # Show first 5 dates
            logger.info(f"  {date_info['release_date']}: {date_info['album_count']} albums")
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
