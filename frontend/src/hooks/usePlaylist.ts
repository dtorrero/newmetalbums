import { useState, useCallback } from 'react';
import api from '../api/client';
import { DynamicPlaylist, PlaylistItem } from '../types/playlist';

export const usePlaylist = () => {
  const [playlist, setPlaylist] = useState<PlaylistItem[]>([]);
  const [isPlayerOpen, setIsPlayerOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPlaylist = useCallback(async (
    periodType: 'day' | 'week' | 'month',
    periodKey: string,
    options?: {
      genres?: string[];
      search?: string;
      shuffle?: boolean;
    }
  ) => {
    setLoading(true);
    setError(null);

    try {
      const data = await api.getDynamicPlaylist(periodType, periodKey, options);
      
      if (data.items.length === 0) {
        setError('No playable albums found for this period. Albums need to be verified first.');
        return;
      }

      setPlaylist(data.items);
      setIsPlayerOpen(true);
    } catch (err: any) {
      console.error('Failed to load playlist:', err);
      setError(err.response?.data?.detail || 'Failed to load playlist');
    } finally {
      setLoading(false);
    }
  }, []);

  const closePlayer = useCallback(() => {
    setIsPlayerOpen(false);
  }, []);

  const clearPlaylist = useCallback(() => {
    setPlaylist([]);
    setIsPlayerOpen(false);
    setError(null);
  }, []);

  return {
    playlist,
    isPlayerOpen,
    loading,
    error,
    loadPlaylist,
    closePlayer,
    clearPlaylist,
  };
};

export default usePlaylist;
