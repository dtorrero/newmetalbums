import React, { useState, useEffect, useRef, useCallback } from 'react';
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
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  SkipNext,
  SkipPrevious,
  VolumeUp,
} from '@mui/icons-material';

interface BandcampTrack {
  title: string;
  duration: number;
  track_num: number;
  file_mp3: string;
}

interface BandcampPlayerProps {
  bandcampUrl: string;
  albumTitle?: string;
  artist?: string;
  onAlbumEnd?: () => void;
  hasUserInteractedRef?: React.RefObject<boolean>;
}

export const BandcampPlayer: React.FC<BandcampPlayerProps> = ({
  bandcampUrl,
  albumTitle,
  artist,
  onAlbumEnd,
  hasUserInteractedRef: externalHasUserInteractedRef,
}) => {
  const [tracks, setTracks] = useState<BandcampTrack[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentTrackIndex, setCurrentTrackIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [trackLoading, setTrackLoading] = useState(false);

  const audioRef = useRef<HTMLAudioElement>(null);
  const isPlayingRef = useRef(isPlaying); // Keep ref in sync for event handlers
  const fallbackTimerRef = useRef<NodeJS.Timeout | null>(null);
  
  // Keep ref in sync with state
  useEffect(() => {
    isPlayingRef.current = isPlaying;
    console.log('🎵 isPlaying state changed:', isPlaying);
  }, [isPlaying]);

  // Fetch tracks from backend
  useEffect(() => {
    const fetchTracks = async () => {
      try {
        setLoading(true);
        setError(null);
        setCurrentTrackIndex(0);  // Reset to first track when album changes
        
        // Preserve play state from parent's ref (shared across albums)
        if (externalHasUserInteractedRef?.current) {
          console.log('🎵 User was playing, preserving play state');
          setIsPlaying(true);
        }
        
        setCurrentTime(0);
        setDuration(0);
        const baseUrl = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000';
        const response = await fetch(
          `${baseUrl}/api/bandcamp/tracks?url=${encodeURIComponent(bandcampUrl)}`
        );
        
        if (!response.ok) {
          throw new Error('Failed to load tracks');
        }
        
        const data = await response.json();
        
        if (!data.tracks || data.tracks.length === 0) {
          throw new Error('No tracks found');
        }
        
        setTracks(data.tracks);
      } catch (err) {
        console.error('Error fetching Bandcamp tracks:', err);
        setError('Could not load tracks. Please try opening in Bandcamp.');
      } finally {
        setLoading(false);
      }
    };

    fetchTracks();
    
    // Cleanup: stop audio when album changes or component unmounts
    return () => {
      // Capture the current audio element at cleanup time
      const audio = audioRef.current;
      if (audio) {
        console.log('🎵 Cleaning up old album audio');
        // Pause first
        audio.pause();
        // Remove src to stop loading - this will trigger an error event but we ignore it
        audio.removeAttribute('src');
        audio.load();
      }
    };
  }, [bandcampUrl]);

  const handleNext = useCallback(() => {
    setCurrentTrackIndex(prev => {
      if (prev < tracks.length - 1) {
        // Go to next track
        return prev + 1;
      } else {
        // Last track - notify parent to go to next album
        // Defer to avoid updating parent during render
        if (onAlbumEnd) {
          setTimeout(() => {
            console.log('🎵 Album finished, calling onAlbumEnd');
            onAlbumEnd();
          }, 0);
        }
        // Don't change track index - parent will load new album
        return prev;
      }
    });
  }, [tracks.length, onAlbumEnd]);

  // Audio event handlers - set up once, never remove
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
      console.log('🎵 Track ended, advancing...');
      handleNext();
    };
    
    const handleLoadedData = () => {
      console.log('🎵 Track data loaded | isPlayingRef:', isPlayingRef.current);
      setTrackLoading(false);
      
      // Cancel fallback timer since loadeddata fired
      if (fallbackTimerRef.current) {
        console.log('🎵 Canceling fallback timer (loadeddata fired)');
        clearTimeout(fallbackTimerRef.current);
        fallbackTimerRef.current = null;
      }
      
      // Auto-play if we should be playing
      if (isPlayingRef.current) {
        console.log('🎵 Attempting auto-play...');
        audio.play()
          .then(() => {
            console.log('✅ Auto-play successful');
          })
          .catch(err => {
            console.error('❌ Auto-play failed:', err);
            setIsPlaying(false);
          });
      } else {
        console.log('⏸️ Not auto-playing (isPlaying is false)');
      }
    };
    
    const handlePlaying = () => {
      console.log('🎵 Playing');
      setTrackLoading(false);
    };
    
    const handleWaiting = () => {
      console.log('🎵 Buffering...');
      setTrackLoading(true);
    };
    
    const handleError = (e: Event) => {
      console.error('🎵 Audio error:', e);
      // Don't reset isPlaying - error might be from cleanup or network issue
      // User can manually pause if needed
      setTrackLoading(false);
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('durationchange', handleDurationChange);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('loadeddata', handleLoadedData);
    audio.addEventListener('playing', handlePlaying);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('waiting', handleWaiting);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('durationchange', handleDurationChange);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('loadeddata', handleLoadedData);
      audio.removeEventListener('playing', handlePlaying);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('waiting', handleWaiting);
      audio.removeEventListener('error', handleError);
    };
  }, [handleNext]);

  // Load track when index changes
  useEffect(() => {
    if (tracks.length > 0 && audioRef.current) {
      const track = tracks[currentTrackIndex];
      if (track && track.file_mp3) {
        console.log('🎵 Loading track:', track.title, '| isPlaying:', isPlaying);
        const audio = audioRef.current;
        
        // Reset state for new track
        setCurrentTime(0);
        setDuration(0);
        setTrackLoading(true);
        
        // Load the new track
        audio.src = track.file_mp3;
        audio.load();
        console.log('🎵 Track load initiated, waiting for loadeddata event...');
        
        // Fallback: if loadeddata doesn't fire, try to play after a short delay
        if (isPlaying) {
          fallbackTimerRef.current = setTimeout(() => {
            console.log('🎵 Fallback: loadeddata timeout, attempting play...');
            if (audio.readyState >= 2) { // HAVE_CURRENT_DATA or better
              setTrackLoading(false);
              audio.play().catch(err => {
                console.error('Fallback play failed:', err);
                setIsPlaying(false);
              });
            }
            fallbackTimerRef.current = null;
          }, 2000);
          
          return () => {
            if (fallbackTimerRef.current) {
              clearTimeout(fallbackTimerRef.current);
              fallbackTimerRef.current = null;
            }
          };
        }
      } else {
        // No valid track - clear loading state
        console.warn('⚠️ No valid track to load');
        setTrackLoading(false);
      }
    } else if (tracks.length === 0 && !loading) {
      // No tracks available and not loading - clear loading state
      setTrackLoading(false);
    }
  }, [currentTrackIndex, tracks, loading]);

  const handlePlayPause = async () => {
    if (!audioRef.current) return;
    
    if (isPlaying) {
      // Pause
      audioRef.current.pause();
      setIsPlaying(false);
      if (externalHasUserInteractedRef) {
        externalHasUserInteractedRef.current = false;
      }
    } else {
      // Play
      setIsPlaying(true);
      // Mark that user has started playback (for parent to track)
      if (externalHasUserInteractedRef) {
        externalHasUserInteractedRef.current = true;
      }
      try {
        await audioRef.current.play();
      } catch (err) {
        console.error('Play error:', err);
        setIsPlaying(false);
      }
    }
  };

  const handlePrevious = () => {
    if (currentTrackIndex > 0) {
      setCurrentTrackIndex(currentTrackIndex - 1);
    } else {
      setCurrentTrackIndex(tracks.length - 1); // Loop to end
    }
  };

  const handleTrackSelect = (index: number) => {
    setCurrentTrackIndex(index);
    // If we're playing, the new track will auto-play via canplaythrough event
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
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 4 }}>
        <CircularProgress />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Loading tracks from Bandcamp...
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
        No tracks available for this album.
      </Alert>
    );
  }

  const currentTrack = tracks[currentTrackIndex];
  
  // Safety check
  if (!currentTrack) {
    return (
      <Alert severity="warning" sx={{ m: 2 }}>
        Invalid track index. Please try again.
      </Alert>
    );
  }

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
            label={`Track ${currentTrack.track_num}`} 
            size="small" 
            sx={{ bgcolor: 'rgba(255,255,255,0.1)' }}
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
            bgcolor: 'primary.main',
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
            bgcolor: 'primary.main',
            color: 'white',
            '&:hover': { bgcolor: 'primary.dark' },
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

      {/* Track List */}
      <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
        <Typography variant="caption" color="text.secondary" sx={{ px: 2, pb: 1 }}>
          Track List ({tracks.length} tracks):
        </Typography>
        <List dense>
          {tracks.map((track, index) => (
            <ListItem key={index} disablePadding>
              <ListItemButton
                selected={index === currentTrackIndex}
                onClick={() => handleTrackSelect(index)}
                sx={{
                  '&.Mui-selected': {
                    bgcolor: 'primary.dark',
                    '&:hover': { bgcolor: 'primary.main' }
                  }
                }}
              >
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 20 }}>
                        {track.track_num}.
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
    </Box>
  );
};

export default BandcampPlayer;
