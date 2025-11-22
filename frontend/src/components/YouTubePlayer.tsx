import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  CircularProgress,
  Alert,
  Chip,
  Snackbar,
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  SkipNext,
  SkipPrevious,
  VolumeUp,
} from '@mui/icons-material';

interface YouTubeTrack {
  title: string;
  duration: number;
  stream_url: string;
  video_id?: string;
  thumbnail?: string;
}

interface YouTubePlayerProps {
  youtubeUrl: string;
  albumTitle?: string;
  artist?: string;
  onAlbumEnd?: () => void;
  hasUserInteractedRef?: React.RefObject<boolean>;
}

export const YouTubePlayer: React.FC<YouTubePlayerProps> = ({
  youtubeUrl,
  albumTitle,
  artist,
  onAlbumEnd,
  hasUserInteractedRef: externalHasUserInteractedRef,
}) => {
  const [tracks, setTracks] = useState<YouTubeTrack[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentTrackIndex, setCurrentTrackIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [trackLoading, setTrackLoading] = useState(false);
  const [downloadNotification, setDownloadNotification] = useState<string | null>(null);
  const internalHasUserInteractedRef = useRef(false);  // Local fallback
  // Use external ref if provided, otherwise use internal
  const hasUserInteractedRef = externalHasUserInteractedRef || internalHasUserInteractedRef;
  
  const audioRef = useRef<HTMLAudioElement>(null);
  const isPlayingRef = useRef(isPlaying); // Keep ref in sync for event handlers
  const fallbackTimerRef = useRef<NodeJS.Timeout | null>(null);
  
  // Keep ref in sync with state
  useEffect(() => {
    isPlayingRef.current = isPlaying;
  }, [isPlaying]);

  // Fetch stream URLs from backend
  useEffect(() => {
    const fetchStream = async () => {
      try {
        setLoading(true);
        setError(null);
        setCurrentTrackIndex(0);
        
        // Preserve play state from parent's ref (shared across albums)
        if (externalHasUserInteractedRef?.current) {
          console.log('🎬 [YOUTUBE] User was playing, preserving play state');
          setIsPlaying(true);
        } else {
          setIsPlaying(false);
        }
        
        setCurrentTime(0);
        setDuration(0);
        
        // Convert embed URL to watch URL if needed
        let urlToFetch = youtubeUrl;
        console.log('🎬 [YOUTUBE] Original URL:', youtubeUrl);
        
        if (youtubeUrl.includes('/embed/videoseries') || youtubeUrl.includes('list=')) {
          // Convert playlist embed to playlist URL
          const playlistIdMatch = youtubeUrl.match(/list=([^&]+)/);
          if (playlistIdMatch) {
            urlToFetch = `https://www.youtube.com/playlist?list=${playlistIdMatch[1]}`;
            console.log('🎬 [YOUTUBE] Converted playlist embed to:', urlToFetch);
          }
        } else if (youtubeUrl.includes('/embed/')) {
          // Convert video embed URL to watch URL
          const videoIdMatch = youtubeUrl.match(/\/embed\/([^?]+)/);
          if (videoIdMatch) {
            urlToFetch = `https://www.youtube.com/watch?v=${videoIdMatch[1]}`;
            console.log('🎬 [YOUTUBE] Converted video embed to:', urlToFetch);
          }
        }
        
        console.log('🎬 [YOUTUBE] Fetching stream from backend:', urlToFetch);
        
        const baseUrl = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000';
        const response = await fetch(
          `${baseUrl}/api/youtube/stream?url=${encodeURIComponent(urlToFetch)}`
        );
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Failed to load YouTube stream' }));
          throw new Error(errorData.detail || 'Failed to load YouTube stream');
        }
        
        const data = await response.json();
        console.log('🎬 [YOUTUBE] Backend response:', data);
        
        if (data.found) {
          if (data.type === 'playlist' && data.tracks && data.tracks.length > 0) {
            console.log('🎬 [YOUTUBE] Playlist with', data.tracks.length, 'tracks');
            
            // Use video_id from backend response (already included in tracks)
            const cachedTracks = data.tracks.map((track: any) => {
              const videoId = track.video_id;
              
              return {
                ...track,
                stream_url: videoId ? `${baseUrl}/api/youtube/audio/${videoId}` : null
              };
            });
            
            setTracks(cachedTracks);
            
            // Note: Downloads are now automatically queued by the backend in /api/youtube/stream
            console.log('🎬 [YOUTUBE] Backend has queued', data.tracks.length, 'videos for download');
          } else if (data.type === 'video') {
            // Single video - use video_id from backend response
            console.log('🎬 [YOUTUBE] Single video');
            
            const videoId = data.video_id;
            
            if (videoId) {
              const cachedUrl = `${baseUrl}/api/youtube/audio/${videoId}`;
              console.log('🎬 [YOUTUBE] Video ID:', videoId);
              console.log('🎬 [YOUTUBE] Cached audio URL:', cachedUrl);
              
              setTracks([{
                title: data.title,
                duration: data.duration,
                stream_url: cachedUrl,
                video_id: videoId,
                thumbnail: data.thumbnail,
              }]);
              
              // Note: Download is now automatically queued by the backend in /api/youtube/stream
              console.log('🎬 [YOUTUBE] Backend has queued video for download:', videoId);
            } else {
              console.error('🎬 [YOUTUBE] No video ID in backend response');
              setError('Could not get video ID from backend');
            }
          } else {
            console.error('🎬 [YOUTUBE] No playable content in response:', data);
            setError('No playable content found');
          }
        } else {
          console.error('🎬 [YOUTUBE] Backend returned found=false');
          setError('Could not extract YouTube stream');
        }
      } catch (err) {
        console.error('Error fetching YouTube stream:', err);
        setError('Could not load YouTube stream. The video may be restricted or unavailable.');
      } finally {
        setLoading(false);
      }
    };

    fetchStream();
    
    // Cleanup: stop audio when album changes or component unmounts
    return () => {
      const audio = audioRef.current;
      if (audio) {
        console.log('🎬 [YOUTUBE] Cleaning up old album audio');
        audio.pause();
        audio.removeAttribute('src');
        audio.load();
      }
    };
  }, [youtubeUrl, externalHasUserInteractedRef]);

  const handleNext = () => {
    if (currentTrackIndex < tracks.length - 1) {
      setCurrentTrackIndex(currentTrackIndex + 1);
    } else {
      // Last track finished - notify parent to go to next album
      if (onAlbumEnd) {
        onAlbumEnd();
      } else {
        setCurrentTrackIndex(0); // Fallback: loop back to start
      }
    }
  };

  const handlePrevious = () => {
    if (currentTrackIndex > 0) {
      setCurrentTrackIndex(currentTrackIndex - 1);
    } else {
      setCurrentTrackIndex(tracks.length - 1);
    }
  };

  // Audio event handlers
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };
    const handleDurationChange = () => {
      const newDuration = audio.duration;
      if (!isNaN(newDuration) && isFinite(newDuration)) {
        setDuration(newDuration);
      }
    };
    const handleLoadedMetadata = () => {
      const newDuration = audio.duration;
      if (!isNaN(newDuration) && isFinite(newDuration)) {
        setDuration(newDuration);
      }
    };
    const handleEnded = () => {
      handleNext();
    };
    const handlePlay = () => {
      setIsPlaying(true);
    };
    const handlePause = () => {
      setIsPlaying(false);
    };
    const handleCanPlayThrough = () => {
      setTrackLoading(false);  // Track is ready
      console.log('🎬 [YOUTUBE] Track ready to play');
    };
    const handleWaiting = () => {
      setTrackLoading(true);  // Buffering
    };
    const handleError = (e: Event) => {
      console.error('🎬 [YOUTUBE] Audio error:', e);
      const currentTrack = tracks[currentTrackIndex];
      
      // Check if it's a 404 (file not available)
      if (audio.error) {
        console.error('🎬 [YOUTUBE] Error code:', audio.error.code, 'Message:', audio.error.message);
        
        if (audio.error.code === 4) { // MEDIA_ERR_SRC_NOT_SUPPORTED (includes 404)
          setDownloadNotification(
            `Audio file not ready yet. Downloading in background... (Track: ${currentTrack?.title || 'Unknown'})`
          );
          setTrackLoading(false);
          setIsPlaying(false);
          
          // Auto-retry after a delay
          setTimeout(() => {
            console.log('🎬 [YOUTUBE] Retrying track load...');
            if (audioRef.current && currentTrack?.stream_url) {
              audioRef.current.src = currentTrack.stream_url;
              audioRef.current.load();
            }
          }, 5000); // Retry after 5 seconds
        }
      }
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('durationchange', handleDurationChange);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('canplaythrough', handleCanPlayThrough);
    audio.addEventListener('waiting', handleWaiting);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('durationchange', handleDurationChange);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('canplaythrough', handleCanPlayThrough);
      audio.removeEventListener('waiting', handleWaiting);
      audio.removeEventListener('error', handleError);
    };
  }, [currentTrackIndex, tracks]);

  // Load track when index changes - SIMPLIFIED
  useEffect(() => {
    if (tracks.length > 0 && audioRef.current) {
      const track = tracks[currentTrackIndex];
      console.log('🎬 [YOUTUBE] Loading track:', track?.title);
      console.log('🎬 [YOUTUBE] Stream URL:', track?.stream_url?.substring(0, 100) + '...');
      
      if (track && track.stream_url) {
        setTrackLoading(true);
        const audio = audioRef.current;
        
        // Check if this is a cached download URL (contains /api/youtube/audio/)
        const isCachedDownload = track.stream_url.includes('/api/youtube/audio/');
        
        // If it's a cached download, check file size and show notification
        if (isCachedDownload) {
          const videoId = track.stream_url.split('/api/youtube/audio/')[1];
          const baseUrl = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000';
          
          // Get download info before loading audio
          fetch(`${baseUrl}/api/youtube/audio/${videoId}/info`)
            .then(response => response.json())
            .then(data => {
              if (!data.cached && data.size_mb > 20) {
                setDownloadNotification(
                  `Downloading large audio file (${data.size_mb}MB)... Estimated time: ${data.estimated_time}`
                );
              }
            })
            .catch(err => console.log('Could not check download size:', err));
        }
        
        // Use loadeddata event for more reliable autoplay
        const handleLoadedData = () => {
          console.log('🎬 [YOUTUBE] Track data loaded | isPlayingRef:', isPlayingRef.current);
          setTrackLoading(false);
          setDownloadNotification(null); // Clear notification when ready
          
          // Cancel fallback timer since loadeddata fired
          if (fallbackTimerRef.current) {
            console.log('🎬 [YOUTUBE] Canceling fallback timer (loadeddata fired)');
            clearTimeout(fallbackTimerRef.current);
            fallbackTimerRef.current = null;
          }
          
          // Auto-play if we should be playing (using ref for stable value)
          if (isPlayingRef.current) {
            console.log('🎬 [YOUTUBE] Attempting auto-play...');
            audio.play()
              .then(() => {
                console.log('🎬 [YOUTUBE] ✅ Auto-play successful');
                setIsPlaying(true);
              })
              .catch(err => {
                console.error('🎬 [YOUTUBE] ❌ Auto-play failed:', err);
                setIsPlaying(false);
              });
          } else {
            console.log('🎬 [YOUTUBE] ⏸️ Not auto-playing (isPlaying is false)');
          }
          
          // Remove listener after first use
          audio.removeEventListener('loadeddata', handleLoadedData);
        };
        
        audio.addEventListener('loadeddata', handleLoadedData);
        audio.src = track.stream_url;
        audio.load();
        console.log('🎬 [YOUTUBE] Audio element src set, calling load()');
        
        // Fallback: if loadeddata doesn't fire, try to play after a short delay
        if (isPlayingRef.current) {
          fallbackTimerRef.current = setTimeout(() => {
            console.log('🎬 [YOUTUBE] Fallback: loadeddata timeout, attempting play...');
            if (audio.readyState >= 2) { // HAVE_CURRENT_DATA or better
              setTrackLoading(false);
              audio.play().catch(err => {
                console.error('🎬 [YOUTUBE] Fallback play failed:', err);
                setIsPlaying(false);
              });
            }
            fallbackTimerRef.current = null;
          }, 3000); // 3 seconds for YouTube (larger files)
        }
        
        // Cleanup
        return () => {
          audio.removeEventListener('loadeddata', handleLoadedData);
          if (fallbackTimerRef.current) {
            clearTimeout(fallbackTimerRef.current);
            fallbackTimerRef.current = null;
          }
        };
      } else {
        console.error('🎬 [YOUTUBE] ❌ No stream URL available for track');
      }
    }
  }, [currentTrackIndex, tracks]);

  const handlePlayPause = async () => {
    if (!audioRef.current) return;
    
    if (isPlaying) {
      console.log('🎬 [YOUTUBE] Pausing');
      audioRef.current.pause();
      setIsPlaying(false);
      if (externalHasUserInteractedRef) {
        externalHasUserInteractedRef.current = false;
      }
    } else {
      console.log('🎬 [YOUTUBE] User clicked play');
      setIsPlaying(true);
      // Mark that user has started playback (for parent to track)
      if (externalHasUserInteractedRef) {
        externalHasUserInteractedRef.current = true;
      }
      setTrackLoading(true);
      try {
        await audioRef.current.play();
        console.log('🎬 [YOUTUBE] ✅ Playing');
        setTrackLoading(false);
      } catch (err) {
        console.error('🎬 [YOUTUBE] ❌ Play error:', err);
        setIsPlaying(false);
        setTrackLoading(false);
      }
    }
  };

  const handleTrackSelect = (index: number) => {
    setCurrentTrackIndex(index);
  };

  const handleSeek = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current) return;
    
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const percentage = x / rect.width;
    audioRef.current.currentTime = percentage * duration;
  };

  const formatTime = (seconds: number) => {
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', p: 4, gap: 2 }}>
        <CircularProgress />
        <Typography variant="caption" color="text.secondary">
          Loading YouTube audio...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  if (tracks.length === 0) {
    return (
      <Alert severity="info" sx={{ m: 2 }}>
        No tracks available.
      </Alert>
    );
  }

  const currentTrack = tracks[currentTrackIndex];

  return (
    <Box sx={{ width: '100%' }}>
      {/* Hidden audio element */}
      <audio ref={audioRef} preload="metadata" />

      {/* Current Track Info */}
      <Box sx={{ px: 2, py: 1, bgcolor: 'grey.900', borderRadius: 1, mb: 1 }}>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Now Playing:
        </Typography>
        <Typography variant="body1" fontWeight="bold" noWrap>
          {currentTrack.title}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
          <Chip 
            label="YouTube" 
            size="small" 
            color="error"
            sx={{ bgcolor: '#FF0000' }}
          />
          <Typography variant="caption" color="text.secondary">
            {formatTime(currentTime)} / {formatTime(duration)}
          </Typography>
        </Box>
      </Box>

      {/* Progress Bar */}
      <Box 
        sx={{ 
          width: '100%', 
          height: 6, 
          bgcolor: 'grey.800', 
          borderRadius: 1,
          cursor: 'pointer',
          mb: 2,
          '&:hover': { bgcolor: 'grey.700' }
        }}
        onClick={handleSeek}
      >
        <Box
          sx={{
            width: `${(currentTime / duration) * 100}%`,
            height: '100%',
            bgcolor: '#FF0000',
            borderRadius: 1,
            transition: 'width 0.1s linear',
          }}
        />
      </Box>

      {/* Playback Controls */}
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 1, mb: 2 }}>
        <IconButton onClick={handlePrevious} disabled={tracks.length <= 1}>
          <SkipPrevious />
        </IconButton>
        
        <IconButton
          onClick={handlePlayPause}
          disabled={trackLoading}
          sx={{
            bgcolor: '#FF0000',
            color: 'white',
            '&:hover': { bgcolor: '#CC0000' },
            '&.Mui-disabled': { bgcolor: '#666', color: '#999' },
            width: 56,
            height: 56,
          }}
        >
          {trackLoading ? <CircularProgress size={24} sx={{ color: 'white' }} /> : (isPlaying ? <Pause /> : <PlayArrow />)}
        </IconButton>
        
        <IconButton onClick={handleNext} disabled={tracks.length <= 1}>
          <SkipNext />
        </IconButton>
      </Box>

      {/* Track List (if playlist) */}
      {tracks.length > 1 && (
        <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
          <Typography variant="caption" color="text.secondary" sx={{ px: 2, pb: 1 }}>
            Playlist ({tracks.length} tracks):
          </Typography>
          <List dense>
            {tracks.map((track, index) => (
              <ListItem key={index} disablePadding>
                <ListItemButton
                  selected={index === currentTrackIndex}
                  onClick={() => handleTrackSelect(index)}
                  sx={{
                    '&.Mui-selected': {
                      bgcolor: 'rgba(255, 0, 0, 0.2)',
                      '&:hover': { bgcolor: 'rgba(255, 0, 0, 0.3)' }
                    }
                  }}
                >
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ minWidth: 20 }}>
                          {index + 1}.
                        </Typography>
                        <Typography variant="body2" noWrap>
                          {track.title}
                        </Typography>
                        {index === currentTrackIndex && isPlaying && (
                          <VolumeUp sx={{ fontSize: 16, ml: 'auto' }} />
                        )}
                      </Box>
                    }
                    secondary={formatTime(track.duration)}
                  />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Box>
      )}
      
      {/* Download Notification Snackbar */}
      <Snackbar
        open={!!downloadNotification}
        message={downloadNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        ContentProps={{
          sx: {
            bgcolor: 'info.main',
            color: 'white',
            fontWeight: 'bold',
          }
        }}
      />
    </Box>
  );
};

export default YouTubePlayer;
