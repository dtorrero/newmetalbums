#!/usr/bin/env python3
"""
Platform Link Verification and Album Matching
Verifies that band platform links actually contain the specific album using fuzzy matching
"""

import re
import asyncio
from typing import Optional, Dict, List
from playwright.async_api import Page
from fuzzywuzzy import fuzz
import logging

logger = logging.getLogger(__name__)

class PlatformVerifier:
    """Verify and extract album-specific URLs from band platform pages."""
    
    def __init__(self, page: Page):
        self.page = page
        
    async def verify_youtube_album(
        self, 
        youtube_url: str, 
        album_name: str, 
        band_name: str,
        min_similarity: int = 75
    ) -> Dict[str, any]:
        """
        Verify if album exists on band's YouTube channel.
        
        Args:
            youtube_url: Band's YouTube channel URL
            album_name: Album name to search for
            band_name: Band name for better matching
            min_similarity: Minimum fuzzy match score (0-100)
        
        Returns:
            {
                'found': bool,
                'video_url': str,  # Specific video/playlist URL
                'embed_url': str,  # Embeddable URL
                'match_score': int,  # Fuzzy match score (0-100)
                'title': str,  # Actual title found
                'type': str  # 'video' or 'playlist'
            }
        """
        try:
            logger.info(f"Verifying YouTube album: {album_name} by {band_name}")
            
            # Navigate to the channel
            await self.page.goto(youtube_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # Strategy 1: Check Videos tab
            videos = await self._search_youtube_videos(album_name, band_name, min_similarity)
            
            if videos:
                best_match = videos[0]
                video_id = self._extract_youtube_video_id(best_match['url'])
                
                if video_id:
                    return {
                        'found': True,
                        'video_url': best_match['url'],
                        'embed_url': f"https://www.youtube-nocookie.com/embed/{video_id}",
                        'match_score': best_match['score'],
                        'title': best_match['title'],
                        'type': 'video'
                    }
            
            # Strategy 2: Check Playlists tab (for full albums)
            playlists = await self._search_youtube_playlists(album_name, min_similarity)
            
            if playlists:
                best_match = playlists[0]
                playlist_id = self._extract_youtube_playlist_id(best_match['url'])
                
                if playlist_id:
                    return {
                        'found': True,
                        'video_url': best_match['url'],
                        'embed_url': f"https://www.youtube-nocookie.com/embed/videoseries?list={playlist_id}",
                        'match_score': best_match['score'],
                        'title': best_match['title'],
                        'type': 'playlist'
                    }
            
            logger.warning(f"Album not found on YouTube: {album_name}")
            return {'found': False, 'match_score': 0}
            
        except Exception as e:
            logger.error(f"Error verifying YouTube album: {e}")
            return {'found': False, 'error': str(e), 'match_score': 0}
    
    async def _search_youtube_videos(
        self, 
        album_name: str, 
        band_name: str,
        min_similarity: int
    ) -> List[Dict]:
        """Search for album in YouTube channel videos."""
        try:
            # Try to click on Videos tab
            try:
                await self.page.click('text=Videos', timeout=5000)
                await asyncio.sleep(2)
            except Exception as e:
                logger.debug(f"Could not click Videos tab: {e}")
            
            # Scroll to load more videos
            for _ in range(3):
                await self.page.evaluate('window.scrollBy(0, 1000)')
                await asyncio.sleep(0.5)
            
            # Extract all video titles and URLs
            videos = await self.page.evaluate('''() => {
                const videoElements = document.querySelectorAll('ytd-grid-video-renderer, ytd-video-renderer, ytd-rich-item-renderer');
                const results = [];
                
                videoElements.forEach(el => {
                    const titleEl = el.querySelector('#video-title, #video-title-link');
                    if (titleEl) {
                        const title = titleEl.textContent?.trim() || titleEl.getAttribute('title') || '';
                        const url = titleEl.href || titleEl.getAttribute('href') || '';
                        
                        if (title && url) {
                            results.push({
                                title: title,
                                url: url.startsWith('http') ? url : 'https://www.youtube.com' + url
                            });
                        }
                    }
                });
                
                return results;
            }''')
            
            # Fuzzy match against album name
            matches = []
            search_term = f"{band_name} {album_name}".lower()
            
            for video in videos:
                title_lower = video['title'].lower()
                
                # Calculate similarity scores
                full_score = fuzz.token_sort_ratio(search_term, title_lower)
                album_score = fuzz.partial_ratio(album_name.lower(), title_lower)
                band_score = fuzz.partial_ratio(band_name.lower(), title_lower)
                
                # Boost score if both band and album are present
                if band_score > 70 and album_score > 70:
                    score = max(full_score, (album_score + band_score) // 2)
                else:
                    score = max(full_score, album_score)
                
                if score >= min_similarity:
                    matches.append({
                        'title': video['title'],
                        'url': video['url'],
                        'score': score
                    })
            
            # Sort by score (best match first)
            matches.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"Found {len(matches)} video matches for '{album_name}'")
            return matches
            
        except Exception as e:
            logger.error(f"Error searching YouTube videos: {e}")
            return []
    
    async def _search_youtube_playlists(self, album_name: str, min_similarity: int) -> List[Dict]:
        """Search for album in YouTube channel playlists."""
        try:
            # Try to click on Playlists tab
            try:
                await self.page.click('text=Playlists', timeout=5000)
                await asyncio.sleep(2)
            except Exception as e:
                logger.debug(f"Could not click Playlists tab: {e}")
                return []
            
            # Extract all playlist titles and URLs
            playlists = await self.page.evaluate('''() => {
                const playlistElements = document.querySelectorAll('ytd-grid-playlist-renderer, ytd-playlist-renderer');
                const results = [];
                
                playlistElements.forEach(el => {
                    const titleEl = el.querySelector('#video-title, a#video-title');
                    if (titleEl) {
                        const title = titleEl.textContent?.trim() || titleEl.getAttribute('title') || '';
                        const url = titleEl.href || titleEl.getAttribute('href') || '';
                        
                        if (title && url) {
                            results.push({
                                title: title,
                                url: url.startsWith('http') ? url : 'https://www.youtube.com' + url
                            });
                        }
                    }
                });
                
                return results;
            }''')
            
            # Fuzzy match against album name
            matches = []
            
            for playlist in playlists:
                score = fuzz.token_sort_ratio(album_name.lower(), playlist['title'].lower())
                
                if score >= min_similarity:
                    matches.append({
                        'title': playlist['title'],
                        'url': playlist['url'],
                        'score': score
                    })
            
            matches.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"Found {len(matches)} playlist matches for '{album_name}'")
            return matches
            
        except Exception as e:
            logger.error(f"Error searching YouTube playlists: {e}")
            return []
    
    async def verify_bandcamp_album(
        self, 
        bandcamp_url: str, 
        album_name: str,
        album_type: str = "album",
        min_similarity: int = 75
    ) -> Dict[str, any]:
        """
        Verify if album exists on band's Bandcamp page.
        
        Args:
            bandcamp_url: Band's Bandcamp page URL
            album_name: Album name to search for
            album_type: Type of release (album, single, EP, etc.)
            min_similarity: Minimum fuzzy match score (0-100)
        
        Returns:
            {
                'found': bool,
                'album_url': str,  # Specific album URL
                'embed_url': str,  # Embeddable URL (if available)
                'embed_code': str,  # Full embed HTML code
                'match_score': int,
                'title': str
            }
        """
        try:
            logger.info(f"Verifying Bandcamp album: {album_name}")
            
            # Navigate to band's Bandcamp page
            await self.page.goto(bandcamp_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # Extract all albums/releases from the page
            releases = await self.page.evaluate('''() => {
                const results = [];
                
                // Check music grid (main discography)
                const musicGrid = document.querySelectorAll('.music-grid-item, .featured-item');
                musicGrid.forEach(item => {
                    const titleEl = item.querySelector('.title, p.title');
                    const linkEl = item.querySelector('a');
                    
                    if (titleEl && linkEl) {
                        results.push({
                            title: titleEl.textContent.trim(),
                            url: linkEl.href
                        });
                    }
                });
                
                // Also check track list (for singles)
                const tracks = document.querySelectorAll('.track_row_view');
                tracks.forEach(track => {
                    const titleEl = track.querySelector('.track-title');
                    const linkEl = track.querySelector('a');
                    
                    if (titleEl && linkEl) {
                        results.push({
                            title: titleEl.textContent.trim(),
                            url: linkEl.href
                        });
                    }
                });
                
                return results;
            }''')
            
            # Fuzzy match against album name
            matches = []
            
            for release in releases:
                score = fuzz.token_sort_ratio(album_name.lower(), release['title'].lower())
                
                if score >= min_similarity:
                    matches.append({
                        'title': release['title'],
                        'url': release['url'],
                        'score': score
                    })
            
            if not matches:
                logger.warning(f"Album not found on Bandcamp: {album_name}")
                return {'found': False, 'match_score': 0}
            
            # Get best match
            best_match = max(matches, key=lambda x: x['score'])
            
            # Navigate to the specific album page to get embed code
            await self.page.goto(best_match['url'], wait_until='networkidle', timeout=30000)
            await asyncio.sleep(1)
            
            # Try to extract embed code
            embed_info = await self._extract_bandcamp_embed(best_match['url'])
            
            return {
                'found': True,
                'album_url': best_match['url'],
                'embed_url': embed_info.get('embed_url', best_match['url']),
                'embed_code': embed_info.get('embed_code', ''),
                'match_score': best_match['score'],
                'title': best_match['title']
            }
            
        except Exception as e:
            logger.error(f"Error verifying Bandcamp album: {e}")
            return {'found': False, 'error': str(e), 'match_score': 0}
    
    async def _extract_bandcamp_embed(self, album_url: str) -> Dict[str, str]:
        """Extract Bandcamp embed code from album page."""
        try:
            # Look for share/embed button and click it
            try:
                await self.page.click('button:has-text("Share"), a:has-text("Share")', timeout=3000)
                await asyncio.sleep(1)
            except:
                logger.debug("No Share/Embed button found")
            
            # Try to extract embed code from the page
            embed_code = await self.page.evaluate('''() => {
                // Look for embed code in share dialog
                const embedInput = document.querySelector('input[value*="EmbeddedPlayer"], textarea[value*="EmbeddedPlayer"]');
                if (embedInput) {
                    return embedInput.value;
                }
                
                // Alternative: look for data attributes
                const albumData = document.querySelector('[data-embed]');
                if (albumData) {
                    return albumData.getAttribute('data-embed');
                }
                
                return null;
            }''')
            
            if embed_code:
                # Extract album ID from embed code
                album_id_match = re.search(r'album=(\d+)', embed_code)
                if album_id_match:
                    album_id = album_id_match.group(1)
                    embed_url = f"https://bandcamp.com/EmbeddedPlayer/album={album_id}/size=large/bgcol=ffffff/linkcol=0687f5/tracklist=false/artwork=small/transparent=true/"
                    
                    return {
                        'embed_code': embed_code,
                        'embed_url': embed_url
                    }
            
            # Fallback: use iframe with album URL
            return {
                'embed_url': album_url,
                'embed_code': f'<iframe src="{album_url}" width="350" height="470"></iframe>'
            }
            
        except Exception as e:
            logger.error(f"Error extracting Bandcamp embed: {e}")
            return {'embed_url': album_url}
    
    def _extract_youtube_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
            r'youtube\.com\/embed\/([^&\n?#]+)',
            r'youtube\.com\/v\/([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_youtube_playlist_id(self, url: str) -> Optional[str]:
        """Extract playlist ID from YouTube URL."""
        match = re.search(r'list=([^&\n?#]+)', url)
        return match.group(1) if match else None
    
    async def extract_bandcamp_tracks(self, album_url: str) -> Dict[str, any]:
        """
        Extract individual track URLs and metadata from a Bandcamp album page.
        This allows direct playback without cookie popups.
        
        Returns:
            {
                'album_id': str,
                'album_title': str,
                'artist': str,
                'tracks': [
                    {
                        'title': str,
                        'duration': int,  # seconds
                        'track_num': int,
                        'file_mp3': str,  # Direct MP3 URL
                    }
                ]
            }
        """
        try:
            logger.info(f"Extracting Bandcamp tracks from: {album_url}")
            
            # Navigate to album page
            await self.page.goto(album_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # Extract track data from the page's JavaScript data
            track_data = await self.page.evaluate('''() => {
                // Bandcamp embeds track data in TralbumData JavaScript object
                if (typeof TralbumData !== 'undefined' && TralbumData.trackinfo) {
                    console.log('Found TralbumData with', TralbumData.trackinfo.length, 'tracks');
                    return {
                        album_id: TralbumData.id || TralbumData.album_id,
                        album_title: TralbumData.current?.title || TralbumData.album_title,
                        artist: TralbumData.artist,
                        tracks: TralbumData.trackinfo
                    };
                }
                
                // Fallback: try to find it in script tags
                console.log('TralbumData not found in window, searching scripts...');
                const scripts = document.querySelectorAll('script[type="application/ld+json"], script:not([src])');
                
                for (const script of scripts) {
                    const text = script.textContent || script.innerText;
                    
                    // Look for TralbumData assignment
                    if (text.includes('TralbumData') || text.includes('trackinfo')) {
                        console.log('Found potential TralbumData in script');
                        
                        // Try multiple regex patterns
                        const patterns = [
                            /var TralbumData\s*=\s*(\{[\s\S]*?\});/,
                            /TralbumData\s*=\s*(\{[\s\S]*?\});/,
                            /"@type":\s*"MusicAlbum"[\s\S]*?"track":\s*(\[[\s\S]*?\])/
                        ];
                        
                        for (const pattern of patterns) {
                            const match = text.match(pattern);
                            if (match) {
                                try {
                                    let data;
                                    if (pattern.source.includes('MusicAlbum')) {
                                        // JSON-LD format
                                        const jsonLd = JSON.parse(script.textContent);
                                        if (jsonLd.track) {
                                            return {
                                                album_id: null,
                                                album_title: jsonLd.name,
                                                artist: jsonLd.byArtist?.name,
                                                tracks: jsonLd.track.map((t, i) => ({
                                                    title: t.name,
                                                    duration: t.duration || 0,
                                                    track_num: i + 1,
                                                    file: {}
                                                }))
                                            };
                                        }
                                    } else {
                                        // TralbumData format
                                        data = eval('(' + match[1] + ')');
                                        if (data.trackinfo) {
                                            console.log('Successfully parsed TralbumData');
                                            return {
                                                album_id: data.id || data.album_id,
                                                album_title: data.current?.title || data.album_title,
                                                artist: data.artist,
                                                tracks: data.trackinfo
                                            };
                                        }
                                    }
                                } catch (e) {
                                    console.error('Failed to parse data:', e);
                                }
                            }
                        }
                    }
                }
                
                console.error('Could not find track data');
                return null;
            }''')
            
            if not track_data or not track_data.get('tracks'):
                logger.warning(f"No track data found on Bandcamp page: {album_url}")
                return {'found': False, 'error': 'No track data found'}
            
            # Process tracks
            tracks = []
            for track in track_data['tracks']:
                if track.get('file'):  # Has audio file
                    tracks.append({
                        'title': track.get('title', ''),
                        'duration': track.get('duration', 0),
                        'track_num': track.get('track_num', 0),
                        'file_mp3': track['file'].get('mp3-128', ''),  # 128kbps MP3
                    })
            
            logger.info(f"✓ Extracted {len(tracks)} tracks from Bandcamp")
            
            return {
                'found': True,
                'album_id': track_data.get('album_id'),
                'album_title': track_data.get('album_title', ''),
                'artist': track_data.get('artist', ''),
                'tracks': tracks,
                'album_url': album_url
            }
            
        except Exception as e:
            logger.error(f"Error extracting Bandcamp tracks: {e}")
            return {'found': False, 'error': str(e)}
