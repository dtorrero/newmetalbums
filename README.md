# Metal Archives Album Scraper

A robust Python script to scrape album and band information from Metal Archives for a specific release date using Playwright for improved reliability.

## Features

- 🎯 **Smart Date Filtering**: Search for albums released on a specific date with optimized performance
- 📀 **Complete Album Data**: Extract detailed album information including tracklists and metadata
- 🎨 **Automatic Cover Downloads**: Download album cover art to local storage
- 🎵 **Bandcamp Integration**: Extract Bandcamp links from band pages for music discovery
- 🏷️ **Rich Metadata**: Extract comprehensive information (genre, label, format, catalog ID, etc.)
- 🤖 **Anti-Detection**: Human-like browsing patterns with rate limiting and jitter
- ⚡ **High Performance**: Async/await with optimized filtering (only enriches matching albums)
- 🛡️ **Robust Error Handling**: Retry logic with exponential backoff
- 📊 **Data Validation**: Structured data models with Pydantic validation

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:

```bash
playwright install firefox
```

## Usage

Run the scraper with a date in YYYY-MM-DD format:

```bash
python scraper.py 2025-08-31 --output albums.json
```

### Examples

```bash
# Scrape albums released on August 31st, 2025
python scraper.py 2025-08-31 --output albums.json

# Scrape albums from a different date
python scraper.py 2025-12-25 --output christmas_albums.json
```

### Arguments

- `date`: The release date to search for (required, format: YYYY-MM-DD)
- `--output`: Output JSON file path (default: albums.json)

### Performance

The scraper is optimized for efficiency:
- **Smart filtering**: Only processes albums matching the target date
- **Automatic cover downloads**: Downloads covers during enrichment
- **Bandcamp extraction**: Fetches Bandcamp links via AJAX endpoints
- **Rate limiting**: Respects Metal Archives with delays and jitter

## Output Format

The script generates a JSON file containing an array of album objects with comprehensive data:

```json
{
  "band_name": "Example Band",
  "band_id": "3540123456",
  "band_url": "https://www.metal-archives.com/bands/Example_Band/3540123456",
  "album_name": "Example Album",
  "album_id": "1234567",
  "album_url": "https://www.metal-archives.com/albums/Example_Band/Example_Album/1234567",
  "release_date": "2025-08-31",
  "release_date_raw": "August 31st, 2025 <!-- 2025-08-31 -->",
  "type": "Full-length",
  "cover_art": "https://www.metal-archives.com/images/1/2/3/4/1234567.jpg",
  "cover_path": "covers/1234567.jpg",
  "bandcamp_url": "https://exampleband.bandcamp.com/",
  "tracklist": [
    {
      "number": "1.",
      "name": "Track Name",
      "length": "04:32"
    }
  ],
  "details": {
    "type_": "Full-length",
    "release_date_": "August 31st, 2025",
    "catalog_id_": "LABEL001",
    "version_desc__": "Limited edition"
  }
}
```

### Key Features

- **Complete Album Data**: Title, URL, release date, type, tracklist
- **Band Information**: Name, URL, Metal Archives ID
- **Cover Art**: Both URL and local file path
- **Bandcamp Links**: Direct links to Bandcamp pages when available
- **Rich Metadata**: Catalog IDs, version descriptions, and more

## File Structure

```
newmetalbums/
├── scraper.py          # Main scraper script
├── models.py           # Data models with Pydantic validation
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── albums.json         # Output file with scraped data
└── covers/            # Downloaded album covers
    ├── 1234567.jpg
    └── 7654321.jpg
```

## Dependencies

- **playwright**: Browser automation for reliable scraping
- **beautifulsoup4**: HTML parsing and extraction
- **pydantic**: Data validation and modeling
- **asyncio**: Asynchronous programming support

## License

MIT
