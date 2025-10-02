from pathlib import Path
import random

# Base URL for Metal Archives
BASE_URL = "https://www.metal-archives.com"

# API Endpoints
SEARCH_URL = f"{BASE_URL}/search/ajax-advanced/searching/albums"
ALBUM_DETAILS_URL = f"{BASE_URL}/albums/detail/id"
BAND_LINKS_URL = f"{BASE_URL}/band/links/id"

# Browser settings
HEADLESS = True

# Common user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.46',
]

# Base headers
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
    'DNT': '1',
    'User-Agent': random.choice(USER_AGENTS),
}

# Directory to store downloaded covers
COVERS_DIR = Path("covers")
COVERS_DIR.mkdir(exist_ok=True, parents=True)

# Request settings
REQUEST_TIMEOUT = 45  # seconds
REQUEST_DELAY = 3.0  # base delay between requests (will have random jitter added)
PAGE_SIZE = 200  # Reduced from 500 to be more conservative
MAX_RETRIES = 7  # Increased max retries
RETRY_DELAY = 10  # Base delay between retries (will use exponential backoff)

# Cloudflare settings
CLOUDFLARE_MAX_WAIT = 30  # Max seconds to wait for Cloudflare challenge
CLOUDFLARE_RETRIES = 3  # Number of times to retry Cloudflare challenge

# Debug mode (set to True for more verbose output)
DEBUG = True

# Link extraction settings
LINK_EXTRACTION = {
    'enabled': True,
    'platforms': {
        'bandcamp': {
            'enabled': True,
            'priority': 1,
            'patterns': ['bandcamp.com'],
            'field_name': 'bandcamp_url'  # For backward compatibility
        },
        'youtube': {
            'enabled': True,
            'priority': 2,
            'patterns': ['youtube.com', 'youtu.be']
        },
        'spotify': {
            'enabled': True,
            'priority': 3,
            'patterns': ['spotify.com', 'open.spotify.com']
        },
        'discogs': {
            'enabled': True,
            'priority': 4,
            'patterns': ['discogs.com']
        },
        'lastfm': {
            'enabled': True,
            'priority': 5,
            'patterns': ['last.fm', 'lastfm.com', 'www.last.fm']
        },
        'soundcloud': {
            'enabled': True,
            'priority': 6,
            'patterns': ['soundcloud.com']
        },
        'tidal': {
            'enabled': True,
            'priority': 7,
            'patterns': ['tidal.com', 'listen.tidal.com']
        }
    }
}
