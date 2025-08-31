# Metal Archives Album Scraper

A robust Python script to scrape album and band information from Metal Archives for a specific release date using Playwright for improved reliability.

## Features

- 🎯 Search for albums released on a specific date
- 📀 Extract detailed album information including tracklists
- 🎨 Download album cover art
- 🏷️ Extract comprehensive metadata (genre, label, format, etc.)
- 🤖 Anti-detection measures with human-like browsing patterns
- ⚡ Async/await for better performance
- 🛡️ Robust error handling and retry logic
- 📊 Structured data models with Pydantic validation

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

### Improved Scraper (Recommended)

Run the improved script with a date in YYYY-MM-DD format:

```bash
python scraper_improved.py 2025-08-31 --output albums.json --download-covers
```

### Legacy Scraper

```bash
python scraper.py 2025-08-31 --output albums.json
```

### Arguments

- `date`: The release date to search for (required, format: YYYY-MM-DD)
- `--output`: Output JSON file path (default: albums.json)
- `--headless`: Run browser in headless mode (default: False for improved version)
- `--download-covers`: Download album cover art (improved version only)

## Output Format

The script generates a JSON file containing an array of album objects. Each album includes:

- Album details (title, URL, release date, genre, format, etc.)
- Band information (name, URL)
- Bandcamp links (if available)
- Cover image path (if downloaded)

## Notes

- The script includes rate limiting to be respectful to the Metal Archives server
- Covers are downloaded to a `covers` directory
- The script handles various edge cases and provides error messages for debugging

## Dependencies

- requests
- beautifulsoup4
- python-dateutil
- httpx
- lxml
- pydantic

## License

MIT
