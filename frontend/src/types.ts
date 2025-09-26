// Type definitions for the Metal Albums API

export interface Album {
  id: number;
  album_id: string;
  album_name: string;
  album_url: string;
  band_name: string;
  band_id: string;
  band_url: string;
  release_date: string;
  release_date_raw: string;
  type: string;
  cover_art: string;
  cover_path: string;
  bandcamp_url: string;
  country_of_origin: string;
  location: string;
  genre: string;
  themes: string;
  current_label: string;
  years_active: string;
  details: any;
  tracklist: Track[];
  created_at: string;
}

export interface Track {
  track_number: string;
  track_name: string;
  track_length: string;
  lyrics_url: string;
}

export interface DateInfo {
  release_date: string;
  album_count: number;
  genres: string;
}

export interface ApiResponse<T> {
  data?: T;
  total?: number;
  date?: string;
  query?: string;
}

export interface DatesResponse {
  dates: DateInfo[];
  total: number;
}

export interface AlbumsResponse {
  albums: Album[];
  total: number;
  date: string;
}

export interface SearchResponse {
  albums: Album[];
  total: number;
  query: string;
}

export interface StatsResponse {
  total_albums: number;
  total_tracks: number;
  top_genres: { genre: string; count: number }[];
  top_countries: { country: string; count: number }[];
  recent_dates: { release_date: string; count: number }[];
}

// Genre-related types
export interface ParsedGenre {
  genre_name: string;
  genre_type: 'main' | 'modifier' | 'related';
  confidence: number;
  period?: string;
}

export interface Genre {
  id: number;
  genre_name: string;
  normalized_name: string;
  parent_genre?: string;
  genre_category: 'base' | 'modifier' | 'style';
  aliases: string[];
  color_hex?: string;
  album_count: number;
  created_at: string;
}

export interface GenreResponse {
  genres: Genre[];
  total: number;
  category?: string;
  include_stats: boolean;
}

export interface GenreSearchResponse {
  genres: Genre[];
  total: number;
  query: string;
  suggestions: string[];
}

export interface AlbumWithGenres extends Album {
  parsed_genres?: ParsedGenre[];
}

export interface AlbumsWithGenresResponse {
  albums: AlbumWithGenres[];
  total: number;
  limit: number;
  offset: number;
  genre: string;
  filters: {
    date?: string;
    date_from?: string;
    date_to?: string;
  };
}
