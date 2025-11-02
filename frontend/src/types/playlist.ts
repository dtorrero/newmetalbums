/**
 * TypeScript interfaces for playlist system
 */

export interface PlatformEmbed {
  embed_url: string;
  video_url?: string; // Original video/playlist URL (for YouTube)
  verified_title?: string;
  verification_score?: number;
  embed_type?: string; // 'video' or 'playlist' for YouTube
}

export interface PlaylistItem {
  album_id: string;
  title: string;
  artist: string;
  type: string;
  release_date: string;
  genre?: string;
  cover_art?: string;
  cover_path?: string;
  album_url?: string;
  platforms: {
    youtube?: PlatformEmbed;
    bandcamp?: PlatformEmbed;
  };
}

export interface DynamicPlaylist {
  period_type: 'day' | 'week' | 'month';
  period_key: string;
  total_albums: number;
  filters: {
    genres?: string[];
    search?: string;
    shuffle: boolean;
  };
  items: PlaylistItem[];
}

export interface PlayerState {
  isPlaying: boolean;
  currentIndex: number;
  currentPlatform: 'youtube' | 'bandcamp' | null;
  volume: number;
  shuffle: boolean;
  repeat: 'none' | 'one' | 'all';
}
