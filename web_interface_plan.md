# Material UI Web Interface Plan

## Architecture Overview

```
Backend (Python)                    Frontend (React + Material UI)
├── scraper.py                     ├── src/
├── daily_orchestrator.py          │   ├── components/
├── db_manager.py                   │   │   ├── DateBrowser/
├── web_server.py (API)             │   │   ├── AlbumGrid/
└── albums.db (SQLite)              │   │   ├── AlbumDetails/
                                    │   │   ├── SearchBar/
                                    │   │   └── Statistics/
                                    │   ├── pages/
                                    │   ├── hooks/
                                    │   └── utils/
                                    └── public/
```

## Technology Stack

### Frontend
- **React 18** - Modern React with hooks
- **Material UI v5** - Component library
- **React Router** - Client-side routing
- **Axios** - API communication
- **React Query** - Data fetching and caching
- **TypeScript** - Type safety

### Backend Integration
- **FastAPI** - Existing Python API
- **SQLite** - Existing database
- **CORS enabled** - For local development

## Component Structure

### 1. Layout Components
- **AppLayout** - Main layout with navigation
- **Header** - App title and search
- **Navigation** - Date browser, stats, search results
- **Footer** - Credits and links

### 2. Date Navigation
- **DateBrowser** - Grid of available dates
- **DateCard** - Individual date with album count
- **DatePicker** - Calendar-style date selection

### 3. Album Display
- **AlbumGrid** - Responsive grid of albums
- **AlbumCard** - Individual album preview
- **AlbumDetails** - Modal/drawer with full details
- **TrackList** - Album tracklist display

### 4. Search & Filters
- **SearchBar** - Global search input
- **FilterPanel** - Genre, country, type filters
- **SearchResults** - Search results display

### 5. Statistics
- **StatsOverview** - Key metrics
- **GenreChart** - Genre distribution
- **CountryChart** - Country distribution
- **Timeline** - Release timeline

## Pages/Routes

```
/ - Home (Date Browser)
/albums/:date - Albums for specific date
/album/:id - Album details
/search - Search results
/stats - Statistics dashboard
```

## Material UI Theme

### Color Palette
- **Primary**: Deep Orange (#FF6B35) - Metal theme
- **Secondary**: Dark Grey (#2D2D2D)
- **Background**: Dark theme with gradients
- **Surface**: Semi-transparent cards

### Typography
- **Headers**: Bold, modern fonts
- **Body**: Clean, readable fonts
- **Accent**: Metal-inspired styling

## API Integration

### Endpoints to Use
- `GET /api/dates` - Available dates
- `GET /api/albums/{date}` - Albums by date
- `GET /api/search` - Search albums
- `GET /api/stats` - Statistics

### Data Flow
1. React Query fetches data from FastAPI
2. Components render with Material UI
3. User interactions trigger new API calls
4. Loading states and error handling

## Mobile Responsiveness

### Breakpoints
- **xs**: 0-599px (Mobile)
- **sm**: 600-959px (Tablet)
- **md**: 960-1279px (Desktop)
- **lg**: 1280px+ (Large Desktop)

### Mobile Features
- Touch-friendly cards
- Swipe gestures
- Responsive grids
- Mobile-first design

## Development Phases

### Phase 1: Setup & Basic Structure
- Create React app with TypeScript
- Install Material UI and dependencies
- Set up routing and basic layout
- Connect to existing API

### Phase 2: Core Components
- Date browser with Material UI cards
- Album grid with responsive design
- Basic search functionality
- API integration with React Query

### Phase 3: Enhanced Features
- Album details modal
- Advanced search and filters
- Statistics dashboard
- Loading states and error handling

### Phase 4: Polish & Optimization
- Animations and transitions
- Performance optimization
- Mobile responsiveness
- Accessibility improvements

## File Structure

```
web-ui/
├── package.json
├── tsconfig.json
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── App.tsx
│   ├── index.tsx
│   ├── theme.ts
│   ├── api/
│   │   ├── client.ts
│   │   └── types.ts
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── AppLayout.tsx
│   │   │   ├── Header.tsx
│   │   │   └── Navigation.tsx
│   │   ├── DateBrowser/
│   │   │   ├── DateBrowser.tsx
│   │   │   ├── DateCard.tsx
│   │   │   └── DatePicker.tsx
│   │   ├── Albums/
│   │   │   ├── AlbumGrid.tsx
│   │   │   ├── AlbumCard.tsx
│   │   │   ├── AlbumDetails.tsx
│   │   │   └── TrackList.tsx
│   │   ├── Search/
│   │   │   ├── SearchBar.tsx
│   │   │   ├── FilterPanel.tsx
│   │   │   └── SearchResults.tsx
│   │   └── Stats/
│   │       ├── StatsOverview.tsx
│   │       ├── GenreChart.tsx
│   │       └── CountryChart.tsx
│   ├── pages/
│   │   ├── HomePage.tsx
│   │   ├── AlbumsPage.tsx
│   │   ├── AlbumDetailsPage.tsx
│   │   ├── SearchPage.tsx
│   │   └── StatsPage.tsx
│   ├── hooks/
│   │   ├── useAlbums.ts
│   │   ├── useDates.ts
│   │   ├── useSearch.ts
│   │   └── useStats.ts
│   └── utils/
│       ├── dateUtils.ts
│       ├── formatters.ts
│       └── constants.ts
└── README.md
```

## Next Steps

1. **Confirm architecture** - Review and approve this structure
2. **Create React project** - Set up the frontend project
3. **Implement basic layout** - Start with core components
4. **Connect to API** - Integrate with existing backend
5. **Iterate and improve** - Add features incrementally
