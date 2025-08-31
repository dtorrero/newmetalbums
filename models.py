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

class Album(BaseModel):
    title: str = Field(alias='album_name')
    url: str = Field(alias='album_url')
    id: str = Field(alias='album_id')
    release_date: str
    band: Band
    type: str = ""
    cover_art: Optional[str] = None
    cover_path: Optional[str] = None
    bandcamp_url: Optional[str] = None
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
            id=data.get('band_id', '')
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
            tracklist=tracks,
            details=data.get('details', {})
        )
