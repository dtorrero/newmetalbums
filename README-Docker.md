# Docker Setup for New Metal Albums

This document explains how to run the entire New Metal Albums project using Docker Compose.

## Quick Start

### Production Mode
```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d --build
```

The application will be available at:
- **Frontend**: http://localhost (port 80)
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Development Mode
```bash
# Start with development overrides (hot reloading)
docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build
```

## Services

### Backend (FastAPI)
- **Container**: `newmetalbums-backend`
- **Port**: 8000
- **Features**:
  - Metal Archives scraper with Playwright
  - SQLite database management
  - Admin panel for manual scraping
  - Album cover serving
  - Health checks

### Frontend (React)
- **Container**: `newmetalbums-frontend`
- **Port**: 80 (production) / 3000 (development)
- **Features**:
  - Material-UI interface
  - Mobile-responsive design
  - Album browsing by date
  - Search functionality
  - Admin panel

## Data Persistence

The following directories are mounted as volumes:
- `./data/` - SQLite database and JSON files
- `./covers/` - Downloaded album cover images

## Commands

```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# Build and start
docker-compose up --build

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart a service
docker-compose restart backend

# Execute commands in running container
docker-compose exec backend python scraper.py --help
docker-compose exec backend bash
```

## Development

For development with hot reloading:

1. **Backend Development**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.override.yml up backend
   ```

2. **Frontend Development** (alternative):
   ```bash
   # Start only backend in Docker
   docker-compose up backend
   
   # Run frontend locally with hot reloading
   cd frontend
   npm start
   ```

## Environment Variables

### Backend
- `PYTHONUNBUFFERED=1` - Python output buffering
- `ENVIRONMENT` - Set to `development` or `production`

### Frontend
- `REACT_APP_API_URL` - Backend API URL (default: http://localhost:8000)

## Troubleshooting

### Backend Issues
```bash
# Check backend health
curl http://localhost:8000/api/health

# View backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

### Frontend Issues
```bash
# Check if frontend is serving files
curl http://localhost

# View frontend logs
docker-compose logs frontend

# Rebuild frontend
docker-compose up --build frontend
```

### Database Issues
```bash
# Access backend container
docker-compose exec backend bash

# Check database
python -c "from db_manager import AlbumsDatabase; db = AlbumsDatabase(); print(db.get_stats())"
```

### Playwright Issues
If scraping fails, Playwright browsers might need reinstalling:
```bash
docker-compose exec backend playwright install chromium
docker-compose exec backend playwright install-deps chromium
```

## Production Deployment

For production deployment:

1. **Set environment variables**:
   ```bash
   export ENVIRONMENT=production
   ```

2. **Use production compose file**:
   ```bash
   docker-compose -f docker-compose.yml up -d --build
   ```

3. **Configure reverse proxy** (optional):
   - Set up nginx or Apache to proxy to port 80
   - Configure SSL certificates
   - Set up domain name

## File Structure

```
newmetalbums/
├── docker-compose.yml              # Main compose file
├── docker-compose.override.yml     # Development overrides
├── Dockerfile.backend              # Backend container
├── frontend/
│   ├── Dockerfile                  # Frontend container
│   └── nginx.conf                  # Nginx configuration
├── data/                           # Database files (mounted)
├── covers/                         # Album covers (mounted)
└── README-Docker.md               # This file
```
