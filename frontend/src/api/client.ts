// API client for Metal Albums backend

import axios from 'axios';
import { 
  DatesResponse, 
  AlbumsResponse, 
  SearchResponse, 
  StatsResponse,
  GenreResponse,
  GenreSearchResponse,
  AlbumsWithGenresResponse,
  PeriodsResponse,
  PeriodAlbumsResponse
} from '../types';
import { DynamicPlaylist } from '../types/playlist';

// Auth-related types
export interface AuthStatus {
  setup_required: boolean;
  locked: boolean;
  last_login: string | null;
  created_at?: string;
}

export interface AuthResponse {
  success: boolean;
  token?: string;
  message: string;
}

export interface LoginRequest {
  password: string;
  remember_me?: boolean;
}

export interface SetupRequest {
  password: string;
}

// Get API base URL - in production (Docker), nginx proxies everything, so use relative URLs
const API_BASE_URL = (process.env.NODE_ENV === 'production' || process.env.REACT_APP_API_URL === '')
  ? '' // Use relative URLs - nginx will proxy to backend
  : 'http://127.0.0.1:8000'; // Development mode - direct backend access

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for debugging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const api = {
  // Get all available dates with album counts
  getDates: async (): Promise<DatesResponse> => {
    const response = await apiClient.get<DatesResponse>('/api/dates');
    return response.data;
  },

  // Get dates grouped by day, week, or month
  getDatesGrouped: async (view: 'day' | 'week' | 'month' = 'day'): Promise<PeriodsResponse> => {
    const response = await apiClient.get<PeriodsResponse>('/api/dates/grouped', {
      params: { view }
    });
    return response.data;
  },

  // Get albums for a specific date
  getAlbumsByDate: async (date: string): Promise<AlbumsResponse> => {
    const response = await apiClient.get<AlbumsResponse>(`/api/albums/${date}`);
    return response.data;
  },

  // Get albums for a specific period (day/week/month) with pagination and filtering
  getAlbumsByPeriod: async (
    periodType: 'day' | 'week' | 'month',
    periodKey: string,
    page: number = 1,
    limit: number = 50,
    genreFilters?: string[],
    searchQuery?: string
  ): Promise<PeriodAlbumsResponse> => {
    const params: any = { page, limit };
    
    // Add genre filters as comma-separated string
    if (genreFilters && genreFilters.length > 0) {
      params.genres = genreFilters.join(',');
    }
    
    // Add search query
    if (searchQuery && searchQuery.trim()) {
      params.search = searchQuery.trim();
    }
    
    const response = await apiClient.get<PeriodAlbumsResponse>(
      `/api/albums/period/${periodType}/${encodeURIComponent(periodKey)}`,
      { params }
    );
    return response.data;
  },

  // Search albums with optional filters
  searchAlbums: async (params: {
    q?: string;
    genre?: string;
    country?: string;
    limit?: number;
  }): Promise<SearchResponse> => {
    const response = await apiClient.get<SearchResponse>('/api/search', { params });
    return response.data;
  },

  // Get database statistics
  getStats: async (): Promise<StatsResponse> => {
    const response = await apiClient.get<StatsResponse>('/api/stats');
    return response.data;
  },

  // Health check
  healthCheck: async (): Promise<{ status: string; message: string }> => {
    const response = await apiClient.get('/api/health');
    return response.data;
  },

  // Genre-related endpoints
  getGenres: async (params?: {
    category?: string;
    limit?: number;
    include_stats?: boolean;
  }): Promise<GenreResponse> => {
    const response = await apiClient.get<GenreResponse>('/api/genres', { params });
    return response.data;
  },

  searchGenres: async (query: string, limit?: number): Promise<GenreSearchResponse> => {
    const response = await apiClient.get<GenreSearchResponse>('/api/genres/search', {
      params: { q: query, limit }
    });
    return response.data;
  },

  getAlbumsByGenre: async (
    genreName: string,
    params?: {
      date?: string;
      date_from?: string;
      date_to?: string;
      limit?: number;
      offset?: number;
    }
  ): Promise<AlbumsWithGenresResponse> => {
    const response = await apiClient.get<AlbumsWithGenresResponse>(
      `/api/albums/by-genre/${encodeURIComponent(genreName)}`,
      { params }
    );
    return response.data;
  },

  // Authentication endpoints
  getAuthStatus: async (): Promise<AuthStatus> => {
    const response = await apiClient.get<AuthStatus>('/api/auth/status');
    return response.data;
  },

  setupAdmin: async (password: string): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/api/auth/setup', { password });
    return response.data;
  },

  login: async (password: string, remember_me: boolean = false): Promise<AuthResponse> => {
    const response = await apiClient.post<AuthResponse>('/api/auth/login', { password, remember_me });
    return response.data;
  },

  verifyToken: async (token: string): Promise<{ valid: boolean; message: string }> => {
    const response = await apiClient.post('/api/auth/verify', {}, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  // Settings endpoints
  getPlatformLinkSettings: async (): Promise<{ settings: { [key: string]: boolean } }> => {
    const response = await apiClient.get('/api/settings/platform-links');
    return response.data;
  },

  // Playlist endpoints
  getDynamicPlaylist: async (
    periodType: 'day' | 'week' | 'month',
    periodKey: string,
    options?: {
      genres?: string[];
      search?: string;
      shuffle?: boolean;
    }
  ): Promise<DynamicPlaylist> => {
    const params: any = {
      period_type: periodType,
      period_key: periodKey,
    };
    
    if (options?.genres && options.genres.length > 0) {
      params.genres = options.genres.join(',');
    }
    
    if (options?.search) {
      params.search = options.search;
    }
    
    if (options?.shuffle) {
      params.shuffle = true;
    }
    
    const response = await apiClient.get<DynamicPlaylist>('/api/playlist/dynamic', { params });
    return response.data;
  },

  // Expose raw axios client for advanced usage
  raw: apiClient,
};

export default api;
