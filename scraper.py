#!/usr/bin/env python3
"""
Improved Metal Archives Album Scraper

A robust Python script to scrape album and band information from Metal Archives
for a specific release date using Playwright for better reliability.
"""

import asyncio
import time
import random
import logging
import re
import json
import argparse
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, date
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from urllib.parse import urljoin, quote_plus, urlencode

import config
from models import Album, Band, BandLink

# Set up logging
logging.basicConfig(
    level=logging.INFO if not config.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Regular expressions for extracting IDs
BAND_ID_PATTERN = re.compile(r'bands/.*?/(\d+)')
ALBUM_ID_PATTERN = re.compile(r'albums/.*?/(\d+)')


class MetalArchivesScraper:
    """Improved Metal Archives scraper using Playwright for better reliability."""
    
    def __init__(self, headless: bool = True):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.headless = headless
        self.user_agents = config.USER_AGENTS
        self.last_request_time = time.time()
        self.request_count = 0

    async def initialize(self) -> None:
        """Initialize the Playwright browser with optimized settings."""
        try:
            self.playwright = await async_playwright().start()
            
            # Launch Chromium browser with realistic settings
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--single-process',
                    '--disable-gpu'
                ]
            )
            
            # Create browser context with random user agent
            user_agent = random.choice(self.user_agents)
            self.context = await self.browser.new_context(
                user_agent=user_agent,
                viewport={'width': random.randint(1200, 1920), 'height': random.randint(800, 1080)},
                locale='en-US',
                timezone_id='Europe/Madrid',
                ignore_https_errors=False,
                java_script_enabled=True
            )
            
            # Set extra HTTP headers
            await self.context.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # Create new page
            self.page = await self.context.new_page()
            
            logger.info("Browser initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            raise

    async def close(self) -> None:
        """Close the browser and clean up resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")

    async def _random_delay(self, min_delay: float = 1.0, max_delay: float = 3.0) -> None:
        """Add a random delay between actions to appear more human-like."""
        delay = random.uniform(min_delay, max_delay)
        if config.DEBUG:
            logger.debug(f"Waiting for {delay:.2f} seconds...")
        await asyncio.sleep(delay)

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        now = time.time()
        elapsed = now - self.last_request_time
        
        # Add jitter to make requests seem more natural
        jitter = random.uniform(0.8, 1.2)
        delay = max(0, (config.REQUEST_DELAY * jitter) - elapsed)
        
        if delay > 0:
            await asyncio.sleep(delay)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
        # Add longer delay every 10 requests to avoid detection
        if self.request_count % 10 == 0:
            await asyncio.sleep(random.uniform(3, 6))

    async def _check_cloudflare_challenge(self) -> bool:
        """Check if Cloudflare challenge is present on the page."""
        if not self.page:
            return False
            
        try:
            # Check for common Cloudflare challenge elements
            cf_selectors = [
                "div#cf-challenge-running",
                ".cf-browser-verification",
                "[data-ray]",
                ".challenge-running"
            ]
            
            for selector in cf_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    return True
                    
            # Check page title for Cloudflare indicators
            title = await self.page.title()
            if "just a moment" in title.lower() or "cloudflare" in title.lower():
                return True
                
            return False
            
        except Exception as e:
            logger.debug(f"Error checking for Cloudflare challenge: {str(e)}")
            return False

    async def _solve_cloudflare_challenge(self) -> bool:
        """Attempt to solve Cloudflare's anti-bot challenge."""
        if not self.page:
            return False
            
        try:
            logger.info("Attempting to solve Cloudflare challenge...")
            
            # Wait for challenge to appear and then disappear
            max_wait = 30  # seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                if not await self._check_cloudflare_challenge():
                    logger.info("Cloudflare challenge solved automatically!")
                    return True
                    
                await asyncio.sleep(1)
            
            logger.warning("Cloudflare challenge not solved within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Error solving Cloudflare challenge: {str(e)}")
            return False

    async def _navigate_to_url(self, url: str, params: Optional[Dict] = None, retry: int = 0) -> Optional[str]:
        """Navigate to a URL using Playwright with retry logic."""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")
            
        if params:
            query_string = urlencode(params, doseq=True)
            url = f"{url}?{query_string}"
            
        try:
            logger.debug(f"Navigating to: {url}")
            
            # Apply rate limiting
            await self._rate_limit()
            
            # Navigate to the page
            response = await self.page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=config.REQUEST_TIMEOUT * 1000
            )
            
            # Check for Cloudflare challenge
            if await self._check_cloudflare_challenge():
                logger.warning("Cloudflare challenge detected. Solving...")
                if await self._solve_cloudflare_challenge():
                    return await self.page.content()
                else:
                    logger.error("Failed to solve Cloudflare challenge")
                    return None
            
            # Check for rate limiting
            if response and response.status == 429:
                retry_after = int(response.headers.get('retry-after', 30))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                await asyncio.sleep(retry_after)
                return await self._navigate_to_url(url, params, retry + 1)
                
            # Wait for the page to be fully loaded
            await self.page.wait_for_load_state("networkidle", timeout=30000)
            
            return await self.page.content()
            
        except Exception as e:
            logger.error(f"Error navigating to {url}: {str(e)}")
            if retry < config.MAX_RETRIES:
                wait_time = min(config.RETRY_DELAY * (2 ** retry), 300)
                logger.info(f"Retrying in {wait_time} seconds (attempt {retry + 1}/{config.MAX_RETRIES})")
                await asyncio.sleep(wait_time)
                return await self._navigate_to_url(url, params, retry + 1)
            logger.error(f"Max retries exceeded for {url}")
            return None

    async def _extract_json_response(self) -> Optional[Dict]:
        """Extract JSON response from the current page."""
        if not self.page:
            return None
            
        try:
            # Wait for content to load
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            
            # Extract JSON from page
            json_text = await self.page.evaluate('''
                () => {
                    // Method 1: Look for <pre> tag (most common)
                    const pre = document.querySelector('pre');
                    if (pre && pre.textContent) {
                        return pre.textContent;
                    }
                    
                    // Method 2: Look for JSON in page body
                    const body = document.body.textContent;
                    if (body && body.trim().startsWith('{')) {
                        return body.trim();
                    }
                    
                    return null;
                }
            ''')
            
            if not json_text:
                logger.error("Could not find JSON data in the response")
                return None
                
            response_data = json.loads(json_text)
            
            if 'aaData' not in response_data:
                logger.error(f"Unexpected response format: {list(response_data.keys())}")
                return None
                
            return response_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error extracting JSON response: {str(e)}")
            return None

    async def _get_albums_for_month(self, year: int, month: int, target_date: str) -> List[Dict]:
        """Get albums for a specific month and year, filtering by target date."""
        logger.info(f"Searching for albums in {year}-{month:02d}")
        
        albums = []
        start = 0
        page_count = 0
        
        while True:
            # Prepare search parameters
            params = {
                'sEcho': '1',
                'iColumns': '4',
                'sColumns': ',,,',
                'iDisplayStart': str(start),
                'iDisplayLength': str(config.PAGE_SIZE),
                'sSearch': '',
                'bRegex': 'false',
                'iSortCol_0': '2',
                'sSortDir_0': 'asc',
                'iSortingCols': '1',
                'bSortable_0': 'false',
                'bSortable_1': 'true',
                'bSortable_2': 'true',
                'bSortable_3': 'false',
                'releaseYearFrom': str(year),
                'releaseMonthFrom': str(month),
                'releaseYearTo': str(year),
                'releaseMonthTo': str(month)
            }
            
            logger.info(f"Fetching page {page_count + 1}, albums {start + 1} to {start + config.PAGE_SIZE}...")
            
            try:
                content = await self._navigate_to_url(config.SEARCH_URL, params)
                if not content:
                    logger.error("Failed to get content from the page")
                    break
                
                # Extract JSON data from the response
                json_data = await self._extract_json_response()
                if not json_data:
                    logger.error("Failed to extract JSON data")
                    break
                    
                data = json_data.get('aaData', [])
                if not data:
                    logger.info("No more albums found")
                    break
                    
                # Process album data and filter by date immediately
                processed_count = 0
                for album_data in data:
                    try:
                        # Parse basic album data without enrichment
                        album = await self._parse_album_data_basic(album_data)
                        if album and album.get('release_date') == target_date:
                            # Only enrich data for albums matching target date
                            if album.get('album_url'):
                                await self._enrich_album_data(album)
                            albums.append(album)
                            processed_count += 1
                    except Exception as e:
                        logger.error(f"Error parsing album data: {e}")
                        continue
                
                logger.info(f"Found {processed_count} matching albums from page {page_count + 1}")
                
                # Check if we've reached the end
                if len(data) < config.PAGE_SIZE:
                    logger.info("Reached end of results")
                    break
                    
                start += len(data)
                page_count += 1
                
                # Delay between pages
                await self._random_delay(2.0, 4.0)
                
            except Exception as e:
                logger.error(f"Error fetching albums page {page_count + 1}: {str(e)}")
                break
                
        logger.info(f"Found {len(albums)} albums for target date {target_date}")
        return albums

    async def search_albums_by_date(self, target_date: date) -> List[Dict]:
        """Search for albums released on a specific date."""
        logger.info(f"Searching for albums released on {target_date}")
        
        target_date_str = target_date.strftime('%Y-%m-%d')
        # Get albums for the month, filtering by target date immediately
        target_albums = await self._get_albums_for_month(target_date.year, target_date.month, target_date_str)
        
        logger.info(f"Found {len(target_albums)} albums for {target_date}")
        return target_albums

    async def _parse_album_data_basic(self, album_data: List[str]) -> Optional[Dict]:
        """Parse basic album data from the API response without enrichment."""
        try:
            if len(album_data) < 4:
                logger.warning(f"Insufficient album data: {album_data}")
                return None
                
            # Extract data from the table row (Band, Album, Type, Date)
            band_cell = BeautifulSoup(album_data[0], 'html.parser')
            album_cell = BeautifulSoup(album_data[1], 'html.parser')
            
            # Extract band information
            band_link = band_cell.find('a')
            band_name = band_cell.get_text(strip=True)
            band_url = band_link['href'] if band_link else ''
            band_id = self._extract_id_from_url(band_url, BAND_ID_PATTERN) if band_url else ''
            
            # Extract album information
            album_link = album_cell.find('a')
            album_name = album_cell.get_text(strip=True)
            album_url = album_link['href'] if album_link else ''
            album_id = self._extract_id_from_url(album_url, ALBUM_ID_PATTERN) if album_url else ''
            
            # Extract type and release date
            album_type = album_data[2].strip()
            release_date_raw = album_data[3].strip()
            
            # Parse the release date to standardized format
            release_date = self._parse_release_date(release_date_raw)
            
            # Create album dictionary (basic data only)
            album = {
                'band_name': band_name,
                'band_id': band_id,
                'band_url': urljoin(config.BASE_URL, band_url) if band_url else '',
                'album_name': album_name,
                'album_id': album_id,
                'album_url': urljoin(config.BASE_URL, album_url) if album_url else '',
                'release_date': release_date,
                'release_date_raw': release_date_raw,
                'type': album_type,
                'cover_art': None,
                'cover_path': None,
                'bandcamp_url': None,
                'tracklist': [],
                'details': {}
            }
            
            return album
            
        except Exception as e:
            logger.error(f"Error parsing album data: {str(e)}")
            logger.debug(f"Album data: {album_data}")
            return None

    async def _parse_album_data(self, album_data: List[str]) -> Optional[Dict]:
        """Parse album data from the API response with enrichment."""
        album = await self._parse_album_data_basic(album_data)
        if album and album.get('album_url'):
            await self._enrich_album_data(album)
        return album

    def _extract_id_from_url(self, url: str, pattern: re.Pattern) -> str:
        """Extract ID from URL using regex pattern."""
        if not url:
            return ''
        match = pattern.search(url)
        return match.group(1) if match else ''

    def _parse_release_date(self, date_str: str) -> str:
        """Parse release date from Metal Archives format to YYYY-MM-DD format."""
        try:
            # Extract date from HTML comment if present
            # Format: "August 31st, 2025 <!-- 2025-08-31 -->"
            if '<!--' in date_str and '-->' in date_str:
                comment_start = date_str.find('<!--') + 4
                comment_end = date_str.find('-->')
                iso_date = date_str[comment_start:comment_end].strip()
                if iso_date and len(iso_date) == 10:  # YYYY-MM-DD format
                    return iso_date
            
            # Fallback: try to parse the human-readable date
            # Remove HTML tags and extra whitespace
            clean_date = re.sub(r'<[^>]+>', '', date_str).strip()
            
            # Try to parse dates like "August 31st, 2025"
            import re
            from datetime import datetime
            
            # Remove ordinal suffixes (st, nd, rd, th)
            clean_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', clean_date)
            
            try:
                parsed_date = datetime.strptime(clean_date, '%B %d, %Y')
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                # Try other common formats
                for fmt in ['%B %d %Y', '%d %B %Y', '%Y-%m-%d']:
                    try:
                        parsed_date = datetime.strptime(clean_date, fmt)
                        return parsed_date.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
            
            logger.warning(f"Could not parse date: {date_str}")
            return clean_date
            
        except Exception as e:
            logger.error(f"Error parsing date '{date_str}': {str(e)}")
            return date_str

    async def _enrich_album_data(self, album: Dict) -> None:
        """Enrich album data with additional details from the album page."""
        if not album.get('album_url'):
            return
            
        try:
            logger.debug(f"Enriching data for album: {album['album_name']}")
            
            # Navigate to the album page
            content = await self._navigate_to_url(album['album_url'])
            if not content:
                logger.warning(f"Failed to load album page: {album['album_url']}")
                return
            
            # Extract cover art URL
            cover_art = await self.page.evaluate('''() => {
                // Try multiple selectors for cover art
                let img = document.querySelector('a.image img');
                if (!img) img = document.querySelector('img.album_img');
                if (!img) img = document.querySelector('img[src*="albums"]');
                if (!img) img = document.querySelector('#album_img img');
                if (!img) img = document.querySelector('.album_img');
                if (!img) {
                    // Look for any image in the album info area
                    const albumInfo = document.querySelector('#album_info');
                    if (albumInfo) {
                        img = albumInfo.querySelector('img');
                    }
                }
                
                console.log('Found cover image:', img ? img.src : 'none');
                return img ? img.src : null;
            }''')
            
            if cover_art:
                album['cover_art'] = cover_art
                # Download the cover
                cover_path = await self.download_cover(album)
                if cover_path:
                    album['cover_path'] = cover_path
                
                # Navigate back to the album page after downloading cover
                await self._navigate_to_url(album['album_url'])
            
            # Extract album details
            details = await self.page.evaluate('''() => {
                const info = {};
                const dl = document.querySelector('div#album_info dl');
                
                if (dl) {
                    const dts = dl.querySelectorAll('dt');
                    const dds = dl.querySelectorAll('dd');
                    
                    dts.forEach((dt, i) => {
                        if (dds[i]) {
                            const key = dt.textContent.trim().toLowerCase().replace(/[^a-z0-9]/g, '_');
                            const value = dds[i].textContent.trim();
                            if (key && value) {
                                info[key] = value;
                            }
                        }
                    });
                }
                
                return info;
            }''')
            
            album['details'] = details or {}
            
            # Extract tracklist from Songs tab
            tracklist = await self._extract_tracklist()
            album['tracklist'] = tracklist or []
            
            # Extract band details and Bandcamp link from band page
            if album.get('band_url'):
                # Extract band details
                band_details = await self._extract_band_details(album['band_url'])
                album.update(band_details)
                
                # Extract Bandcamp link
                bandcamp_url = await self._extract_bandcamp_link(album['band_url'])
                if bandcamp_url:
                    album['bandcamp_url'] = bandcamp_url
            
        except Exception as e:
            logger.error(f"Error enriching album data for {album['album_name']}: {str(e)}")

    async def _extract_tracklist(self) -> List[Dict[str, str]]:
        """Extract tracklist from the Songs tab of the album page."""
        try:
            # Wait for page to be fully loaded
            await asyncio.sleep(3)
            
            # Try to activate Songs tab if present, but don't fail if not found
            try:
                songs_tab_clicked = await self.page.evaluate('''() => {
                    // Look for Songs tab and click it
                    const tabElements = document.querySelectorAll('a.ui-tabs-anchor, a[href*="songs"], *');
                    for (let element of tabElements) {
                        const text = element.textContent?.trim().toLowerCase();
                        if (text === 'songs' && element.click) {
                            element.click();
                            return true;
                        }
                    }
                    return false;
                }''')
                
                if songs_tab_clicked:
                    logger.debug("Clicked on Songs tab")
                    await asyncio.sleep(2)
                else:
                    logger.debug("No Songs tab found, trying direct extraction")
            except Exception as e:
                logger.debug(f"Tab clicking failed: {e}, trying direct extraction")
            
            
            
            # Extract tracklist data
            tracks = await self.page.evaluate('''() => {
                const tracks = [];
                
                // Look for the standard Metal Archives tracklist table
                const trackTable = document.querySelector('table.table_lyrics');
                
                if (trackTable) {
                    const rows = trackTable.querySelectorAll('tr');
                    
                    rows.forEach((row, index) => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 2) {
                            const trackNum = cells[0]?.textContent?.trim() || '';
                            const trackName = cells[1]?.textContent?.trim() || '';
                            const trackLength = cells[2]?.textContent?.trim() || '';
                            
                            // Skip rows with "(loading lyrics...)" or empty track numbers
                            if (trackName.includes('(loading lyrics...)') || !trackNum) {
                                return;
                            }
                            
                            // Validate track number (should be a number followed by optional dot)
                            if (trackNum.match(/^\d+\.?$/)) {
                                const track = {
                                    number: trackNum.replace('.', ''),
                                    name: trackName,
                                    length: trackLength || ''
                                };
                                
                                // Check for lyrics link
                                const lyricsLink = cells[1]?.querySelector('a[href*="lyrics"]');
                                if (lyricsLink) {
                                    track.lyrics_url = lyricsLink.href;
                                }
                                
                                tracks.push(track);
                            }
                        }
                    });
                }
                
                // If no tracks found in table, try alternative methods
                if (tracks.length === 0) {
                    // Look for track listings in page content
                    const allText = document.body.textContent;
                    const lines = allText.split('\\n');
                    
                    lines.forEach(line => {
                        const trimmed = line.trim();
                        // Match patterns like "1. Song Name" or "1. Song Name 04:24"
                        const match = trimmed.match(/^(\d+)\.?\s+(.+?)(?:\s+(\d{1,2}:\d{2}))?$/);
                        if (match) {
                            const [, num, name, duration] = match;
                            const trackNum = parseInt(num);
                            
                            // Only add if it's a reasonable track and we don't already have it
                            if (trackNum > 0 && trackNum <= 20 && 
                                !tracks.find(t => t.number === num) &&
                                name.length > 1 && name.length < 100 &&
                                !name.includes('(loading lyrics...)')) {
                                tracks.push({
                                    number: num,
                                    name: name.trim(),
                                    length: duration || ''
                                });
                            }
                        }
                    });
                    
                    // Sort by track number
                    tracks.sort((a, b) => parseInt(a.number) - parseInt(b.number));
                }
                
                return tracks;
            }''')
            
            logger.debug(f"Extracted {len(tracks)} tracks from tracklist")
            return tracks
            
        except Exception as e:
            logger.error(f"Error extracting tracklist: {str(e)}")
            return []

    async def _extract_band_details(self, band_url: str) -> Dict[str, str]:
        """Extract band details from band page."""
        try:
            logger.debug(f"Extracting band details from: {band_url}")
            
            # Navigate to the band page
            content = await self._navigate_to_url(band_url)
            if not content:
                logger.warning(f"Failed to load band page: {band_url}")
                return {}
            
            # Extract band information from the band_info section
            band_details = await self.page.evaluate('''() => {
                const info = {};
                const bandInfoDiv = document.querySelector('#band_info');
                
                if (bandInfoDiv) {
                    const dts = bandInfoDiv.querySelectorAll('dt');
                    const dds = bandInfoDiv.querySelectorAll('dd');
                    
                    dts.forEach((dt, i) => {
                        if (dds[i]) {
                            const key = dt.textContent.trim().toLowerCase();
                            const value = dds[i].textContent.trim();
                            
                            // Map the keys to our expected field names
                            if (key.includes('country of origin')) {
                                info['country_of_origin'] = value;
                            } else if (key.includes('location')) {
                                info['location'] = value;
                            } else if (key.includes('genre')) {
                                info['genre'] = value;
                            } else if (key.includes('themes')) {
                                info['themes'] = value;
                            } else if (key.includes('current label')) {
                                info['current_label'] = value;
                            } else if (key.includes('years active')) {
                                info['years_active'] = value;
                            }
                        }
                    });
                }
                
                return info;
            }''')
            
            logger.debug(f"Extracted band details: {band_details}")
            return band_details or {}
            
        except Exception as e:
            logger.error(f"Error extracting band details from {band_url}: {str(e)}")
            return {}

    async def _extract_bandcamp_link(self, band_url: str) -> Optional[str]:
        """Extract Bandcamp link from band page Related Links AJAX endpoint."""
        try:
            logger.debug(f"Extracting Bandcamp link from: {band_url}")
            
            # Extract band ID from URL
            band_id = self._extract_id_from_url(band_url, BAND_ID_PATTERN)
            if not band_id:
                logger.warning(f"Could not extract band ID from: {band_url}")
                return None
            
            # Construct Related Links AJAX URL
            links_url = f"https://www.metal-archives.com/link/ajax-list/type/band/id/{band_id}"
            logger.debug(f"Fetching Related Links from: {links_url}")
            
            # Navigate to the AJAX endpoint
            content = await self._navigate_to_url(links_url)
            if not content:
                logger.warning(f"Failed to load Related Links: {links_url}")
                return None
            
            # Extract Bandcamp URL from the AJAX response
            bandcamp_url = await self.page.evaluate('''() => {
                console.log('Searching for Bandcamp links in AJAX response...');
                
                // Look for any bandcamp.com links
                const bandcampLinks = document.querySelectorAll('a[href*="bandcamp.com"]');
                console.log('Found', bandcampLinks.length, 'bandcamp.com links');
                
                if (bandcampLinks.length > 0) {
                    const link = bandcampLinks[0];
                    console.log('Found Bandcamp link:', link.href, 'Text:', link.textContent);
                    return link.href;
                }
                
                return null;
            }''')
            
            if bandcamp_url:
                logger.info(f"Found Bandcamp link: {bandcamp_url}")
                return bandcamp_url
            else:
                logger.debug("No Bandcamp link found in Related Links")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting Bandcamp link: {str(e)}")
            return None

    async def download_cover(self, album: Dict, covers_dir: Path = None) -> Optional[str]:
        """Download album cover art."""
        if not album.get('cover_art'):
            return None
            
        if covers_dir is None:
            covers_dir = config.COVERS_DIR
            
        try:
            # Ensure covers directory exists
            covers_dir.mkdir(parents=True, exist_ok=True)
            
            cover_url = album['cover_art']
            album_id = album.get('album_id', 'unknown')
            
            # Create filename
            filename = f"{album_id}.jpg"
            filepath = covers_dir / filename
            
            # Download the image using requests-like approach with Playwright
            logger.debug(f"Downloading cover: {cover_url}")
            
            # Navigate to the image URL and get the response
            response = await self.page.goto(cover_url)
            if response and response.status == 200:
                # Get the image data
                image_data = await response.body()
                
                # Write to file
                with open(filepath, 'wb') as f:
                    f.write(image_data)
                
                logger.info(f"Downloaded cover: {filepath}")
                return str(filepath)
            else:
                logger.warning(f"Failed to download cover, status: {response.status if response else 'No response'}")
                return None
            
        except Exception as e:
            logger.error(f"Error downloading cover for {album['album_name']}: {str(e)}")
            return None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


def parse_date(date_str: str) -> date:
    """Parse a date string into a date object."""
    try:
        return datetime.strptime(date_str, '%d-%m-%Y').date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected format: DD-MM-YYYY")


async def main():
    """Main function to run the improved scraper."""
    parser = argparse.ArgumentParser(description='Scrape Metal Archives for albums released on a specific date.')
    parser.add_argument('date', type=parse_date, help='Date in DD-MM-YYYY format')
    parser.add_argument('--output', '-o', type=str, default=None, help='Output JSON file (default: albums_DD-MM-YYYY.json)')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode (default: False)')
    parser.add_argument('--download-covers', action='store_true', help='Download album covers')
    parser.add_argument('--add-to-db', action='store_true', help='Add scraped data to database after creating JSON')
    args = parser.parse_args()
    
    # Generate default filename if no output specified
    if args.output is None:
        date_str = args.date.strftime('%d-%m-%Y')
        args.output = f'albums_{date_str}.json'
    
    # Ensure covers directory exists
    config.COVERS_DIR.mkdir(exist_ok=True, parents=True)
    
    async with MetalArchivesScraper(headless=args.headless) as scraper:
        try:
            # Search for albums on the target date
            albums = await scraper.search_albums_by_date(args.date)
            
            # Download covers if requested
            if args.download_covers:
                logger.info("Downloading album covers...")
                for album in albums:
                    cover_path = await scraper.download_cover(album)
                    if cover_path:
                        album['cover_path'] = cover_path
            
            # Save results to JSON
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(albums, f, indent=2, ensure_ascii=False, default=str)
                
            print(f"✅ Found {len(albums)} albums released on {args.date}")
            print(f"📁 Results saved to {args.output}")
            
            if args.download_covers:
                cover_count = sum(1 for album in albums if album.get('cover_path'))
                print(f"🖼️  Downloaded {cover_count} album covers")
            
            # Add to database if requested
            if args.add_to_db:
                try:
                    from db_manager import AlbumsDatabase
                    db = AlbumsDatabase()
                    db.connect()
                    db.create_tables()
                    
                    successful_inserts = 0
                    for album in albums:
                        if db.insert_album(album):
                            successful_inserts += 1
                    
                    db.close()
                    print(f"🗄️  Added {successful_inserts}/{len(albums)} albums to database")
                    
                except Exception as e:
                    logger.error(f"Database insertion failed: {str(e)}")
                    print(f"❌ Database insertion failed: {str(e)}")
                    # Don't fail the whole operation - JSON is already saved
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return 1
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user.")
        exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        exit(1)
