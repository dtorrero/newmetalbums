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
    def __init__(self, db_path: str = "data/albums.db"):
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
                youtube_url TEXT,
                spotify_url TEXT,
                discogs_url TEXT,
                lastfm_url TEXT,
                soundcloud_url TEXT,
                tidal_url TEXT,
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
        
        # Parsed genres table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parsed_genres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                album_id TEXT NOT NULL,
                genre_name TEXT NOT NULL,
                genre_type TEXT NOT NULL, -- 'main', 'modifier', 'related'
                confidence REAL NOT NULL,
                period TEXT, -- 'early', 'mid', 'later', NULL
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (album_id) REFERENCES albums (album_id)
            )
        ''')
        
        # Genre taxonomy table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS genre_taxonomy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                genre_name TEXT UNIQUE NOT NULL,
                normalized_name TEXT NOT NULL,
                parent_genre TEXT,
                genre_category TEXT, -- 'base', 'modifier', 'style'
                aliases TEXT, -- JSON array of alternative names
                color_hex TEXT, -- For UI theming
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Genre statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS genre_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                genre_name TEXT NOT NULL,
                album_count INTEGER NOT NULL,
                date_range_start DATE,
                date_range_end DATE,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_albums_release_date ON albums(release_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_albums_band_name ON albums(band_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_albums_genre ON albums(genre)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracks_album_id ON tracks(album_id)')
        
        # Create indexes for new genre tables
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parsed_genres_album_id ON parsed_genres(album_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parsed_genres_genre_name ON parsed_genres(genre_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parsed_genres_genre_type ON parsed_genres(genre_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_genre_taxonomy_name ON genre_taxonomy(genre_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_genre_taxonomy_category ON genre_taxonomy(genre_category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_genre_stats_name ON genre_stats(genre_name)')
        
        # Settings table for user preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
                    bandcamp_url, youtube_url, spotify_url, discogs_url, lastfm_url,
                    soundcloud_url, tidal_url, country_of_origin, location, genre, themes,
                    current_label, years_active, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                album_data.get('youtube_url', ''),
                album_data.get('spotify_url', ''),
                album_data.get('discogs_url', ''),
                album_data.get('lastfm_url', ''),
                album_data.get('soundcloud_url', ''),
                album_data.get('tidal_url', ''),
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
    
    def delete_albums_by_date(self, release_date: str) -> int:
        """Delete all albums for a specific release date"""
        cursor = self.connection.cursor()
        
        # First get album IDs to delete tracks
        cursor.execute("SELECT album_id FROM albums WHERE release_date = ?", (release_date,))
        album_ids = [row['album_id'] for row in cursor.fetchall()]
        
        if not album_ids:
            return 0
        
        # Delete tracks for these albums
        placeholders = ','.join(['?' for _ in album_ids])
        cursor.execute(f"DELETE FROM tracks WHERE album_id IN ({placeholders})", album_ids)
        tracks_deleted = cursor.rowcount
        
        # Delete albums
        cursor.execute("DELETE FROM albums WHERE release_date = ?", (release_date,))
        albums_deleted = cursor.rowcount
        
        self.connection.commit()
        logger.info(f"Deleted {albums_deleted} albums and {tracks_deleted} tracks for date {release_date}")
        return albums_deleted
    
    def delete_albums_by_date_range(self, start_date: str, end_date: str) -> int:
        """Delete all albums within a date range (inclusive)"""
        cursor = self.connection.cursor()
        
        # First get album IDs to delete tracks
        cursor.execute("""
            SELECT album_id FROM albums 
            WHERE release_date >= ? AND release_date <= ?
        """, (start_date, end_date))
        album_ids = [row['album_id'] for row in cursor.fetchall()]
        
        if not album_ids:
            return 0
        
        # Delete tracks for these albums
        placeholders = ','.join(['?' for _ in album_ids])
        cursor.execute(f"DELETE FROM tracks WHERE album_id IN ({placeholders})", album_ids)
        tracks_deleted = cursor.rowcount
        
        # Delete albums
        cursor.execute("""
            DELETE FROM albums 
            WHERE release_date >= ? AND release_date <= ?
        """, (start_date, end_date))
        albums_deleted = cursor.rowcount
        
        self.connection.commit()
        logger.info(f"Deleted {albums_deleted} albums and {tracks_deleted} tracks for date range {start_date} to {end_date}")
        return albums_deleted
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of data in database for admin purposes"""
        cursor = self.connection.cursor()
        
        # Total counts
        cursor.execute("SELECT COUNT(*) as total FROM albums")
        total_albums = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM tracks")
        total_tracks = cursor.fetchone()['total']
        
        # Data by date
        cursor.execute("""
            SELECT release_date, COUNT(*) as count 
            FROM albums 
            WHERE release_date IS NOT NULL AND release_date != ''
            GROUP BY release_date 
            ORDER BY release_date DESC
        """)
        dates_data = [dict(row) for row in cursor.fetchall()]
        
        # Database size (approximate)
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        db_size = cursor.fetchone()['size']
        
        return {
            "total_albums": total_albums,
            "total_tracks": total_tracks,
            "dates_count": len(dates_data),
            "dates_data": dates_data,
            "database_size_bytes": db_size
        }
    
    def check_date_exists(self, release_date: str) -> bool:
        """Check if data exists for a specific date"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM albums WHERE release_date = ?", (release_date,))
        return cursor.fetchone()['count'] > 0
    
    def get_albums_count_by_date(self, release_date: str) -> int:
        """Get count of albums for a specific date"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM albums WHERE release_date = ?", (release_date,))
        return cursor.fetchone()['count']
    
    def get_dates_grouped(self, view_mode: str = 'day') -> List[Dict[str, Any]]:
        """Get dates grouped by day, week, or month with aggregated stats"""
        cursor = self.connection.cursor()
        
        if view_mode == 'day':
            # Same as get_available_dates but with period info
            cursor.execute('''
                SELECT 
                    release_date as period_key,
                    release_date as start_date,
                    release_date as end_date,
                    'day' as period_type,
                    COUNT(*) as album_count,
                    COUNT(DISTINCT release_date) as dates_count,
                    GROUP_CONCAT(DISTINCT genre) as genres
                FROM albums 
                WHERE release_date IS NOT NULL AND release_date != ''
                GROUP BY release_date 
                ORDER BY release_date DESC
            ''')
        elif view_mode == 'week':
            # Group by ISO week (YYYY-Www format)
            cursor.execute('''
                SELECT 
                    strftime('%Y-W%W', release_date) as period_key,
                    MIN(release_date) as start_date,
                    MAX(release_date) as end_date,
                    'week' as period_type,
                    COUNT(*) as album_count,
                    COUNT(DISTINCT release_date) as dates_count,
                    GROUP_CONCAT(DISTINCT genre) as genres
                FROM albums 
                WHERE release_date IS NOT NULL AND release_date != ''
                GROUP BY strftime('%Y-W%W', release_date)
                ORDER BY period_key DESC
            ''')
        elif view_mode == 'month':
            # Group by month (YYYY-MM format)
            cursor.execute('''
                SELECT 
                    strftime('%Y-%m', release_date) as period_key,
                    MIN(release_date) as start_date,
                    MAX(release_date) as end_date,
                    'month' as period_type,
                    COUNT(*) as album_count,
                    COUNT(DISTINCT release_date) as dates_count,
                    GROUP_CONCAT(DISTINCT genre) as genres
                FROM albums 
                WHERE release_date IS NOT NULL AND release_date != ''
                GROUP BY strftime('%Y-%m', release_date)
                ORDER BY period_key DESC
            ''')
        else:
            raise ValueError(f"Invalid view_mode: {view_mode}")
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_albums_by_period(self, period_type: str, period_key: str, 
                            limit: int = 50, offset: int = 0,
                            genre_filters: List[str] = None,
                            search_query: str = None) -> Dict[str, Any]:
        """Get albums for a specific period (day/week/month) with pagination and filtering"""
        cursor = self.connection.cursor()
        
        # Determine date range based on period type
        if period_type == 'day':
            start_date = end_date = period_key
        elif period_type == 'week':
            # Parse YYYY-Www format and get date range
            # SQLite doesn't have great week support, so we'll use the dates directly
            cursor.execute('''
                SELECT MIN(release_date) as start, MAX(release_date) as end
                FROM albums
                WHERE strftime('%Y-W%W', release_date) = ?
            ''', (period_key,))
            row = cursor.fetchone()
            if not row or not row['start']:
                return {"albums": [], "total": 0, "period_key": period_key, "has_more": False}
            start_date = row['start']
            end_date = row['end']
        elif period_type == 'month':
            # Parse YYYY-MM format
            cursor.execute('''
                SELECT MIN(release_date) as start, MAX(release_date) as end
                FROM albums
                WHERE strftime('%Y-%m', release_date) = ?
            ''', (period_key,))
            row = cursor.fetchone()
            if not row or not row['start']:
                return {"albums": [], "total": 0, "period_key": period_key, "has_more": False}
            start_date = row['start']
            end_date = row['end']
        else:
            raise ValueError(f"Invalid period_type: {period_type}")
        
        # Build WHERE clause with filters
        where_conditions = ['release_date >= ?', 'release_date <= ?']
        params = [start_date, end_date]
        
        # Add genre filters
        if genre_filters and len(genre_filters) > 0:
            # Create OR conditions for each genre filter
            genre_conditions = []
            for genre in genre_filters:
                genre_conditions.append('genre LIKE ?')
                params.append(f'%{genre}%')
            where_conditions.append(f"({' OR '.join(genre_conditions)})")
        
        # Add search query
        if search_query and search_query.strip():
            search_conditions = '(album_name LIKE ? OR band_name LIKE ? OR genre LIKE ?)'
            where_conditions.append(search_conditions)
            search_param = f'%{search_query.strip()}%'
            params.extend([search_param, search_param, search_param])
        
        where_clause = ' AND '.join(where_conditions)
        
        # Get total count for pagination (with filters)
        count_query = f'SELECT COUNT(*) as total FROM albums WHERE {where_clause}'
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # Get paginated albums (with filters)
        query = f'''
            SELECT * FROM albums 
            WHERE {where_clause}
            ORDER BY release_date DESC, band_name, album_name
            LIMIT ? OFFSET ?
        '''
        cursor.execute(query, params + [limit, offset])
        
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
        
        return {
            "albums": albums,
            "total": total,
            "period_key": period_key,
            "period_type": period_type,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(albums)) < total
        }
    
    # Genre-related methods
    
    def insert_parsed_genres(self, album_id: str, parsed_genres: List[Dict[str, Any]]) -> bool:
        """Insert parsed genres for an album"""
        cursor = self.connection.cursor()
        
        try:
            # Delete existing parsed genres for this album
            cursor.execute('DELETE FROM parsed_genres WHERE album_id = ?', (album_id,))
            
            # Insert new parsed genres
            for genre_data in parsed_genres:
                cursor.execute('''
                    INSERT INTO parsed_genres (album_id, genre_name, genre_type, confidence, period)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    album_id,
                    genre_data.get('genre_name', ''),
                    genre_data.get('genre_type', 'main'),
                    genre_data.get('confidence', 1.0),
                    genre_data.get('period')
                ))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error inserting parsed genres for album {album_id}: {e}")
            self.connection.rollback()
            return False
    
    def get_parsed_genres_by_album(self, album_id: str) -> List[Dict[str, Any]]:
        """Get parsed genres for a specific album"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT genre_name, genre_type, confidence, period
            FROM parsed_genres 
            WHERE album_id = ?
            ORDER BY confidence DESC, genre_type
        ''', (album_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_all_genres(self, category: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all genres from taxonomy with optional filtering"""
        cursor = self.connection.cursor()
        
        if category:
            cursor.execute('''
                SELECT gt.*, COALESCE(gs.album_count, 0) as album_count
                FROM genre_taxonomy gt
                LEFT JOIN genre_stats gs ON gt.genre_name = gs.genre_name
                WHERE gt.genre_category = ?
                ORDER BY gs.album_count DESC, gt.genre_name
                LIMIT ?
            ''', (category, limit))
        else:
            cursor.execute('''
                SELECT gt.*, COALESCE(gs.album_count, 0) as album_count
                FROM genre_taxonomy gt
                LEFT JOIN genre_stats gs ON gt.genre_name = gs.genre_name
                ORDER BY gs.album_count DESC, gt.genre_name
                LIMIT ?
            ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_genres(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search genres with fuzzy matching"""
        cursor = self.connection.cursor()
        
        # Use LIKE for fuzzy matching
        search_pattern = f"%{query}%"
        cursor.execute('''
            SELECT gt.*, COALESCE(gs.album_count, 0) as album_count
            FROM genre_taxonomy gt
            LEFT JOIN genre_stats gs ON gt.genre_name = gs.genre_name
            WHERE gt.genre_name LIKE ? OR gt.normalized_name LIKE ? OR gt.aliases LIKE ?
            ORDER BY 
                CASE 
                    WHEN gt.genre_name = ? THEN 1
                    WHEN gt.genre_name LIKE ? THEN 2
                    ELSE 3
                END,
                gs.album_count DESC
            LIMIT ?
        ''', (search_pattern, search_pattern, search_pattern, query, f"{query}%", limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_albums_by_genre(self, genre_name: str, date: str = None, date_from: str = None, 
                           date_to: str = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get albums filtered by genre with optional date filtering"""
        cursor = self.connection.cursor()
        
        # Build the query based on filters
        base_query = '''
            SELECT DISTINCT a.*
            FROM albums a
            JOIN parsed_genres pg ON a.album_id = pg.album_id
            WHERE pg.genre_name = ?
        '''
        params = [genre_name]
        
        if date:
            base_query += ' AND a.release_date = ?'
            params.append(date)
        elif date_from and date_to:
            base_query += ' AND a.release_date BETWEEN ? AND ?'
            params.extend([date_from, date_to])
        elif date_from:
            base_query += ' AND a.release_date >= ?'
            params.append(date_from)
        elif date_to:
            base_query += ' AND a.release_date <= ?'
            params.append(date_to)
        
        base_query += ' ORDER BY a.release_date DESC, a.band_name, a.album_name LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(base_query, params)
        albums = [dict(row) for row in cursor.fetchall()]
        
        # Add parsed genres for each album
        for album in albums:
            album['parsed_genres'] = self.get_parsed_genres_by_album(album['album_id'])
        
        return albums
    
    def get_genre_statistics(self) -> Dict[str, Any]:
        """Get comprehensive genre statistics"""
        cursor = self.connection.cursor()
        
        # Total genre counts
        cursor.execute('SELECT COUNT(*) as total FROM genre_taxonomy')
        total_genres = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(DISTINCT genre_name) as total FROM parsed_genres')
        total_parsed_genres = cursor.fetchone()['total']
        
        # Top genres
        cursor.execute('''
            SELECT gs.genre_name, gs.album_count
            FROM genre_stats gs
            ORDER BY gs.album_count DESC
            LIMIT 10
        ''')
        top_genres = [dict(row) for row in cursor.fetchall()]
        
        # Genre distribution by type
        cursor.execute('''
            SELECT genre_type, COUNT(*) as count
            FROM parsed_genres
            GROUP BY genre_type
        ''')
        type_distribution = {row['genre_type']: row['count'] for row in cursor.fetchall()}
        
        # Temporal distribution
        cursor.execute('''
            SELECT period, COUNT(*) as count
            FROM parsed_genres
            WHERE period IS NOT NULL
            GROUP BY period
        ''')
        temporal_distribution = {row['period']: row['count'] for row in cursor.fetchall()}
        
        return {
            'total_genres': total_genres,
            'total_parsed_genres': total_parsed_genres,
            'top_genres': top_genres,
            'type_distribution': type_distribution,
            'temporal_distribution': temporal_distribution
        }
    
    def upsert_genre_taxonomy(self, genre_name: str, normalized_name: str, 
                             category: str, parent_genre: str = None, 
                             aliases: List[str] = None, color_hex: str = None) -> bool:
        """Insert or update genre taxonomy entry"""
        cursor = self.connection.cursor()
        
        try:
            aliases_json = json.dumps(aliases or [])
            cursor.execute('''
                INSERT OR REPLACE INTO genre_taxonomy 
                (genre_name, normalized_name, parent_genre, genre_category, aliases, color_hex)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (genre_name, normalized_name, parent_genre, category, aliases_json, color_hex))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error upserting genre taxonomy for {genre_name}: {e}")
            self.connection.rollback()
            return False
    
    def update_genre_statistics(self) -> bool:
        """Update genre statistics table with current data"""
        cursor = self.connection.cursor()
        
        try:
            # Clear existing stats
            cursor.execute('DELETE FROM genre_stats')
            
            # Calculate new stats
            cursor.execute('''
                INSERT INTO genre_stats (genre_name, album_count, date_range_start, date_range_end)
                SELECT 
                    pg.genre_name,
                    COUNT(DISTINCT pg.album_id) as album_count,
                    MIN(a.release_date) as date_range_start,
                    MAX(a.release_date) as date_range_end
                FROM parsed_genres pg
                JOIN albums a ON pg.album_id = a.album_id
                WHERE a.release_date IS NOT NULL AND a.release_date != ''
                GROUP BY pg.genre_name
            ''')
            
            self.connection.commit()
            logger.info("Genre statistics updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating genre statistics: {e}")
            self.connection.rollback()
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        if result:
            return json.loads(result['value'])
        return default
    
    def set_setting(self, key: str, value: Any, category: str = 'general', description: str = None) -> bool:
        """Set a setting value"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, category, description, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (key, json.dumps(value), category, description))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            return False
    
    def get_settings_by_category(self, category: str) -> Dict[str, Any]:
        """Get all settings in a category"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT key, value, description FROM settings WHERE category = ?', (category,))
        results = cursor.fetchall()
        return {
            row['key']: {
                'value': json.loads(row['value']),
                'description': row['description']
            }
            for row in results
        }

def ingest_json_files(db: AlbumsDatabase, json_pattern: str = "data/albums_*.json"):
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
