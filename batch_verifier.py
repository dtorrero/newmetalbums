#!/usr/bin/env python3
"""
Batch Verification for Album Playable URLs
Verifies YouTube and Bandcamp links for multiple albums efficiently
"""

import asyncio
import logging
from typing import List, Dict
from db_manager import AlbumsDatabase
from scraper import MetalArchivesScraper
from platform_verifier import PlatformVerifier

logger = logging.getLogger(__name__)

class BatchVerifier:
    """Batch verify playable URLs for albums."""
    
    def __init__(self, db: AlbumsDatabase, headless: bool = True):
        self.db = db
        self.headless = headless
        self.scraper = None
        self.verifier = None
    
    async def initialize(self):
        """Initialize scraper and verifier."""
        self.scraper = MetalArchivesScraper(headless=self.headless)
        await self.scraper.initialize()
        self.verifier = PlatformVerifier(self.scraper.page)
        logger.info("Batch verifier initialized")
    
    async def close(self):
        """Close scraper."""
        if self.scraper:
            await self.scraper.close()
            logger.info("Batch verifier closed")
    
    async def verify_album(self, album: Dict, min_similarity: int = 75) -> Dict:
        """
        Verify a single album's playable URLs.
        
        Returns:
            {
                'album_id': str,
                'youtube': {...} or None,
                'bandcamp': {...} or None,
                'success': bool
            }
        """
        album_id = album['album_id']
        album_name = album['album_name']
        band_name = album['band_name']
        
        logger.info(f"Verifying: {band_name} - {album_name}")
        
        result = {
            'album_id': album_id,
            'youtube': None,
            'bandcamp': None,
            'success': False
        }
        
        try:
            # Verify YouTube
            youtube_url = album.get('youtube_url')
            if youtube_url and youtube_url != 'N/A' and youtube_url.strip():
                try:
                    youtube_result = await self.verifier.verify_youtube_album(
                        youtube_url=youtube_url,
                        album_name=album_name,
                        band_name=band_name,
                        min_similarity=min_similarity
                    )
                    if youtube_result.get('found'):
                        result['youtube'] = youtube_result
                        logger.info(f"  ✓ YouTube verified (score: {youtube_result['match_score']})")
                    else:
                        logger.warning(f"  ✗ YouTube not found")
                except Exception as e:
                    logger.error(f"  ✗ YouTube verification error: {e}")
            
            # Verify Bandcamp
            bandcamp_url = album.get('bandcamp_url')
            if bandcamp_url and bandcamp_url != 'N/A' and bandcamp_url.strip():
                try:
                    bandcamp_result = await self.verifier.verify_bandcamp_album(
                        bandcamp_url=bandcamp_url,
                        album_name=album_name,
                        album_type=album.get('type', 'album'),
                        min_similarity=min_similarity
                    )
                    if bandcamp_result.get('found'):
                        result['bandcamp'] = bandcamp_result
                        logger.info(f"  ✓ Bandcamp verified (score: {bandcamp_result['match_score']})")
                    else:
                        logger.warning(f"  ✗ Bandcamp not found")
                except Exception as e:
                    logger.error(f"  ✗ Bandcamp verification error: {e}")
            
            # Mark as success if at least one platform verified
            result['success'] = result['youtube'] is not None or result['bandcamp'] is not None
            
            # Update database
            if result['success']:
                self.db.update_album_playable_urls(
                    album_id=album_id,
                    youtube_result=result['youtube'],
                    bandcamp_result=result['bandcamp']
                )
                logger.info(f"  ✓ Database updated")
            
        except Exception as e:
            logger.error(f"Error verifying album {album_id}: {e}")
        
        return result
    
    async def verify_albums_batch(
        self,
        albums: List[Dict],
        min_similarity: int = 75,
        delay_between: float = 2.0
    ) -> Dict:
        """
        Verify multiple albums with delay between requests.
        
        Args:
            albums: List of album dictionaries
            min_similarity: Minimum fuzzy match score
            delay_between: Seconds to wait between albums
        
        Returns:
            {
                'total': int,
                'verified': int,
                'youtube_count': int,
                'bandcamp_count': int,
                'failed': int,
                'results': List[Dict]
            }
        """
        stats = {
            'total': len(albums),
            'verified': 0,
            'youtube_count': 0,
            'bandcamp_count': 0,
            'failed': 0,
            'results': []
        }
        
        for i, album in enumerate(albums, 1):
            logger.info(f"[{i}/{len(albums)}] Processing album...")
            
            result = await self.verify_album(album, min_similarity)
            stats['results'].append(result)
            
            if result['success']:
                stats['verified'] += 1
                if result['youtube']:
                    stats['youtube_count'] += 1
                if result['bandcamp']:
                    stats['bandcamp_count'] += 1
            else:
                stats['failed'] += 1
            
            # Delay between requests to avoid rate limiting
            if i < len(albums):
                await asyncio.sleep(delay_between)
        
        logger.info(f"Batch verification complete: {stats['verified']}/{stats['total']} verified")
        return stats
    
    async def verify_date_range(
        self,
        start_date: str,
        end_date: str,
        min_similarity: int = 75
    ) -> Dict:
        """Verify all albums in a date range."""
        # Get albums without verified playable URLs
        cursor = self.db.connection.cursor()
        cursor.execute('''
            SELECT 
                album_id, album_name, band_name, type,
                youtube_url, bandcamp_url
            FROM albums
            WHERE release_date BETWEEN ? AND ?
            AND (playable_verified = 0 OR playable_verified IS NULL)
            AND (youtube_url IS NOT NULL OR bandcamp_url IS NOT NULL)
        ''', (start_date, end_date))
        
        albums = [dict(row) for row in cursor.fetchall()]
        
        if not albums:
            logger.info(f"No albums to verify for {start_date} to {end_date}")
            return {'total': 0, 'verified': 0}
        
        logger.info(f"Found {len(albums)} albums to verify")
        return await self.verify_albums_batch(albums, min_similarity)


async def verify_albums_for_date(
    date_str: str,
    db: AlbumsDatabase,
    headless: bool = True,
    min_similarity: int = 75
) -> Dict:
    """
    Convenience function to verify all albums for a specific date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        db: Database instance
        headless: Run browser in headless mode
        min_similarity: Minimum fuzzy match score
    
    Returns:
        Verification statistics
    """
    verifier = BatchVerifier(db, headless=headless)
    
    try:
        await verifier.initialize()
        return await verifier.verify_date_range(date_str, date_str, min_similarity)
    finally:
        await verifier.close()
