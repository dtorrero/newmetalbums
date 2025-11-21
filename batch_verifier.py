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
    
    async def restart_browser(self):
        """Restart the browser connection after an error."""
        logger.info("Restarting browser...")
        try:
            if self.scraper:
                await self.scraper.close()
        except Exception as e:
            logger.warning(f"Error closing old browser: {e}")
        
        # Reinitialize
        self.scraper = MetalArchivesScraper(headless=self.headless)
        await self.scraper.initialize()
        self.verifier = PlatformVerifier(self.scraper.page)
        logger.info("Browser restarted successfully")
    
    async def close(self):
        """Close scraper."""
        if self.scraper:
            try:
                await self.scraper.close()
                logger.info("Batch verifier closed")
            except Exception as e:
                logger.warning(f"Error closing batch verifier: {e}")
    
    async def verify_album(self, album: Dict, min_similarity: int = 75, max_retries: int = 2) -> Dict:
        """
        Verify a single album's playable URLs with retry logic.
        
        Args:
            album: Album dictionary with metadata
            min_similarity: Minimum fuzzy match score
            max_retries: Number of retries on connection errors
        
        Returns:
            {
                'album_id': str,
                'youtube': {...} or None,
                'bandcamp': {...} or None,
                'success': bool,
                'error': str or None
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
            'success': False,
            'error': None
        }
        
        for attempt in range(max_retries + 1):
            try:
                # NOTE: We no longer depend on Metal Archives related links for
                # YouTube or Bandcamp. Instead we always perform our own
                # full-text searches using album and band names.

                # Verify YouTube via global search with strict 90%+ similarity
                try:
                    youtube_result = await self.verifier.search_youtube_directly(
                        album_name=album_name,
                        band_name=band_name,
                        min_similarity=90,
                    )
                    if youtube_result.get('found'):
                        result['youtube'] = youtube_result
                        logger.info(f"  ✓ YouTube verified (score: {youtube_result['match_score']})")
                    else:
                        logger.warning("  ✗ YouTube not found with ≥90% similarity")
                except Exception as e:
                    error_msg = str(e)
                    if 'Target page, context or browser has been closed' in error_msg or 'Connection closed' in error_msg:
                        raise  # Re-raise connection errors to trigger retry
                    logger.error(f"  ✗ YouTube verification error: {e}")

                # Verify Bandcamp via global Bandcamp search (albums only) with 90%+ similarity
                try:
                    bandcamp_result = await self.verifier.verify_bandcamp_from_search(
                        album_name=album_name,
                        band_name=band_name,
                        min_similarity=90,
                    )
                    if bandcamp_result.get('found'):
                        result['bandcamp'] = bandcamp_result
                        logger.info(f"  ✓ Bandcamp verified (score: {bandcamp_result['match_score']})")
                    else:
                        logger.warning("  ✗ Bandcamp not found with ≥90% similarity")
                except Exception as e:
                    error_msg = str(e)
                    if 'Target page, context or browser has been closed' in error_msg or 'Connection closed' in error_msg:
                        raise  # Re-raise connection errors to trigger retry
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
                
                # Success - break retry loop
                break
                
            except Exception as e:
                error_msg = str(e)
                is_connection_error = (
                    'Target page, context or browser has been closed' in error_msg or
                    'Connection closed' in error_msg or
                    'AttributeError' in str(type(e)) or
                    '_object' in error_msg
                )
                
                if is_connection_error and attempt < max_retries:
                    logger.warning(f"  ⚠️  Connection error (attempt {attempt + 1}/{max_retries + 1}), restarting browser...")
                    try:
                        await self.restart_browser()
                        await asyncio.sleep(2)
                    except Exception as restart_error:
                        logger.error(f"  ✗ Browser restart failed: {restart_error}")
                        result['error'] = f"Browser restart failed: {restart_error}"
                        break
                else:
                    logger.error(f"Error verifying album {album_id}: {e}")
                    result['error'] = str(e)
                    break
        
        return result
    
    async def verify_albums_batch(
        self,
        albums: List[Dict],
        min_similarity: int = 75,
        delay_between: float = 2.0,
        restart_every: int = 50
    ) -> Dict:
        """
        Verify multiple albums with delay between requests.
        
        Args:
            albums: List of album dictionaries
            min_similarity: Minimum fuzzy match score
            delay_between: Seconds to wait between albums
            restart_every: Restart browser every N albums to prevent connection issues
        
        Returns:
            {
                'total': int,
                'verified': int,
                'youtube_count': int,
                'bandcamp_count': int,
                'failed': int,
                'errors': int,
                'results': List[Dict]
            }
        """
        stats = {
            'total': len(albums),
            'verified': 0,
            'youtube_count': 0,
            'bandcamp_count': 0,
            'failed': 0,
            'errors': 0,
            'results': []
        }
        
        for i, album in enumerate(albums, 1):
            logger.info(f"[{i}/{len(albums)}] Processing album...")
            
            # Preventive browser restart every N albums
            if i > 1 and i % restart_every == 0:
                logger.info(f"Preventive browser restart after {restart_every} albums...")
                try:
                    await self.restart_browser()
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Preventive restart failed: {e}")
            
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
                if result.get('error'):
                    stats['errors'] += 1
            
            # Show progress
            if i % 10 == 0 or i == len(albums):
                logger.info(f"Progress: {i}/{len(albums)} albums processed, {stats['verified']} verified")
            
            # Delay between requests to avoid rate limiting
            if i < len(albums):
                await asyncio.sleep(delay_between)
        
        logger.info(f"Batch verification complete: {stats['verified']}/{stats['total']} verified, {stats['errors']} errors")
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
