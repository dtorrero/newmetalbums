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

## 🚀 Quick Start

**Works on any platform: x64, ARM64, Raspberry Pi, etc.**

1. **Download and run:**
   ```bash
   curl -O https://raw.githubusercontent.com/dtorrero/newmetalbums/main/docker-compose.yml
   docker-compose up -d
   ```

2. **Access your application:**
   - **Web Interface**: http://localhost
   - **Admin Panel**: http://localhost/admin

3. **First-time setup:**
   - Visit the admin panel and set your password (8+ characters)
   - Start scraping metal album data

### 🛠️ Development

```bash
# Clone repository
git clone https://github.com/dtorrero/newmetalbums.git
cd newmetalbums

# Setup Python environment
python -m venv env
source env/bin/activate
pip install -r requirements.txt
playwright install chromium

# Start development servers
python start_dev.py
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://127.0.0.1:8000
- API Docs: http://127.0.0.1:8000/docs

### 🛠️ Management

```bash
# Update to latest version
docker-compose pull && docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📄 License

MIT License - see LICENSE file for details
