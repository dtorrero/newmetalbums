from datetime import date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, Field

class BandLink(BaseModel):
    name: str
    url: str

class Track(BaseModel):
    number: str
    name: str
    length: str = ""

class Band(BaseModel):
    name: str
    url: str
    id: str = ""
    bandcamp_links: List[BandLink] = []
    country_of_origin: str = ""
    location: str = ""
    genre: str = ""
    themes: str = ""
    current_label: str = ""
    years_active: str = ""

class Album(BaseModel):
    title: str = Field(alias='album_name')
    url: str = Field(alias='album_url')
    id: str = Field(alias='album_id')
    release_date: str
    band: Band
    type: str = ""
    cover_art: Optional[str] = None
    cover_path: Optional[str] = None
    bandcamp_url: Optional[str] = None  # Kept for backward compatibility
    youtube_url: Optional[str] = None
    spotify_url: Optional[str] = None
    discogs_url: Optional[str] = None
    lastfm_url: Optional[str] = None
    soundcloud_url: Optional[str] = None
    tidal_url: Optional[str] = None
    tracklist: List[Track] = []
    details: Dict[str, Any] = {}
    
    class Config:
        populate_by_name = True
        
    @classmethod
    def from_scraped_data(cls, data: Dict[str, Any]) -> 'Album':
        """Create Album instance from scraped data dictionary."""
        band = Band(
            name=data.get('band_name', ''),
            url=data.get('band_url', ''),
            id=data.get('band_id', ''),
            country_of_origin=data.get('country_of_origin', ''),
            location=data.get('location', ''),
            genre=data.get('genre', ''),
            themes=data.get('themes', ''),
            current_label=data.get('current_label', ''),
            years_active=data.get('years_active', '')
        )
        
        tracks = [
            Track(
                number=track.get('number', ''),
                name=track.get('name', ''),
                length=track.get('length', '')
            )
            for track in data.get('tracklist', [])
        ]
        
        return cls(
            album_name=data.get('album_name', ''),
            album_url=data.get('album_url', ''),
            album_id=data.get('album_id', ''),
            release_date=data.get('release_date', ''),
            band=band,
            type=data.get('type', ''),
            cover_art=data.get('cover_art'),
            cover_path=data.get('cover_path'),
            bandcamp_url=data.get('bandcamp_url'),
            youtube_url=data.get('youtube_url'),
            spotify_url=data.get('spotify_url'),
            discogs_url=data.get('discogs_url'),
            lastfm_url=data.get('lastfm_url'),
            soundcloud_url=data.get('soundcloud_url'),
            tidal_url=data.get('tidal_url'),
            tracklist=tracks,
            details=data.get('details', {})
        )

# ============================================================================
# PLAYLIST MODELS
# ============================================================================

class PlaylistCreate(BaseModel):
    """Model for creating a new playlist."""
    name: str
    description: Optional[str] = None
    is_public: bool = True

class PlaylistUpdate(BaseModel):
    """Model for updating playlist metadata."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None

class PlaylistItemCreate(BaseModel):
    """Model for adding item to playlist."""
    album_id: str
    track_number: Optional[str] = None
    platform: str  # 'youtube' or 'bandcamp'

class PlaylistItemResponse(BaseModel):
    """Model for playlist item with album details."""
    id: int
    album_id: str
    album_name: str
    band_name: str
    track_number: Optional[str] = None
    track_name: Optional[str] = None
    platform: str
    playable_url: Optional[str] = None
    position: int
    cover_art: Optional[str] = None
    cover_path: Optional[str] = None
    verification_status: str
    verification_score: Optional[int] = None
    verified_title: Optional[str] = None
    embed_type: Optional[str] = None

class PlaylistResponse(BaseModel):
    """Model for playlist with metadata."""
    id: int
    name: str
    description: Optional[str] = None
    is_public: bool
    item_count: int
    created_at: str
    updated_at: str
    items: Optional[List[PlaylistItemResponse]] = None

class PlayableItem(BaseModel):
    """Optimized format for frontend player."""
    id: int
    title: str  # Track or album name
    artist: str  # Band name
    platform: str
    embed_url: str
    duration: Optional[str] = None
    cover_art: Optional[str] = None
    album_url: str  # Link to album page
    verification_score: Optional[int] = None

class PlayablePlaylist(BaseModel):
    """Playlist in playable format for frontend."""
    id: int
    name: str
    description: Optional[str] = None
    items: List[PlayableItem]

class ReorderRequest(BaseModel):
    """Model for reordering playlist items."""
    item_ids: List[int]
