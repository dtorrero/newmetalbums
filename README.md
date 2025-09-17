# Metal Albums Database

A complete system for scraping, storing, and browsing metal album releases from Metal Archives with a modern web interface and automated Docker deployment.

## 🎯 Features

- **Metal Archives Scraper**: Automated scraping with Playwright browser automation
- **Database Storage**: SQLite database with proper indexing and relationships  
- **REST API**: FastAPI backend with search, filtering, and statistics
- **Modern Web Interface**: React + Material UI responsive frontend
- **Admin Panel**: Manual scraping control and data management
- **Cover Art**: Automatic album cover downloading and serving
- **Docker Support**: Multi-architecture containers (AMD64/ARM64)
- **GitHub Actions**: Automated builds and releases

## 🐳 Quick Start with Docker (Recommended)

### Using Pre-built Images

Create a `docker-compose.yml` file and copy this content:

```yaml
version: '3.8'

services:
  backend:
    image: ghcr.io/dtorrero/newmetalbums-backend:latest
    container_name: newmetalbums-backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./covers:/app/covers
    environment:
      - PYTHONUNBUFFERED=1
      - ENVIRONMENT=production
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/api/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    image: ghcr.io/dtorrero/newmetalbums-frontend:latest
    container_name: newmetalbums-frontend
    ports:
      - "80:80"
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
    environment:
      - REACT_APP_API_URL=http://localhost:8000
```

Then start the application:

```bash
docker-compose up -d
```

### Building Locally

```bash
# Clone the repository
git clone https://github.com/dtorrero/newmetalbums.git
cd newmetalbums

# Start with Docker Compose
docker-compose up --build
```

**Access the application:**
- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🛠️ Development Setup

### Local Development

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Install frontend dependencies
cd frontend && npm install

# Start development servers
python start_dev.py
```

## 📱 Using the Web Interface

### Admin Panel
1. Navigate to http://localhost/admin
2. Select a date to scrape
3. Click "Start Scraping" to fetch new albums
4. Monitor progress and view results

### Browse Albums
1. Visit http://localhost
2. Use the date picker to browse releases by date
3. Click album covers for full-size view
4. Search and filter albums

## 🔧 Manual Scraping (CLI)

```bash
# Scrape albums for a specific date
python scraper.py 2025-08-31 --output albums.json

# Different date example
python scraper.py 2025-12-25 --output christmas_albums.json
```

### CLI Arguments
- `date`: Release date to search (YYYY-MM-DD format)
- `--output`: Output JSON file path (default: albums.json)

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

## 🐳 Docker Deployment

### Multi-Architecture Support
Images are automatically built for:
- **linux/amd64**: Intel/AMD processors
- **linux/arm64**: Apple Silicon, ARM servers, Raspberry Pi

### Production Deployment
```bash
# Using pre-built images (recommended)
docker-compose -f docker-compose.production.yml up -d

# Building locally
docker-compose up --build
```

### Environment Variables
- `ENVIRONMENT`: Set to `production` or `development`
- `PYTHONUNBUFFERED`: Python output buffering (default: 1)
- `REACT_APP_API_URL`: Frontend API URL (default: http://localhost:8000)

## 📁 Project Structure

```
newmetalbums/
├── backend/
│   ├── scraper.py          # Metal Archives scraper
│   ├── web_server.py       # FastAPI backend
│   ├── db_manager.py       # Database operations
│   ├── models.py           # Data models
│   └── config.py           # Configuration
├── frontend/               # React application
│   ├── src/
│   │   ├── components/     # React components
│   │   └── api/           # API client
│   ├── public/            # Static assets
│   └── Dockerfile         # Frontend container
├── .github/workflows/     # GitHub Actions
├── data/                  # SQLite database
├── covers/               # Album cover images
└── docker-compose.yml    # Local development
```

## 🚀 GitHub Actions

Automated builds trigger on:
- **Push to main**: Builds latest images
- **Tagged releases**: Creates versioned releases
- **Pull requests**: Builds for testing

Images are published to GitHub Container Registry with vulnerability scanning.

## 📖 Documentation

- **[Docker Setup](README-Docker.md)**: Detailed Docker instructions
- **[GitHub Actions](README-GitHub-Actions.md)**: CI/CD setup guide

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details
