import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  IconButton,
  Slider,
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
}

export const BandcampPlayer: React.FC<BandcampPlayerProps> = ({
  bandcampUrl,
  albumTitle,
  artist,
  onAlbumEnd,
}) => {
  const [tracks, setTracks] = useState<BandcampTrack[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentTrackIndex, setCurrentTrackIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [trackLoading, setTrackLoading] = useState(false);
  const hasUserInteractedRef = useRef(false);  // Track if user has clicked play

  const audioRef = useRef<HTMLAudioElement>(null);

  // Fetch tracks from backend
  useEffect(() => {
    const fetchTracks = async () => {
      try {
        setLoading(true);
        setError(null);
        setCurrentTrackIndex(0);  // Reset to first track when album changes
        setIsPlaying(false);  // Reset play state
        setCurrentTime(0);
        setDuration(0);
        // Don't reset hasUserStartedPlaybackRef - preserve across albums
        const baseUrl = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000';
        const response = await fetch(
          `${baseUrl}/api/bandcamp/tracks?url=${encodeURIComponent(bandcampUrl)}`
        );
        
        if (!response.ok) {
          throw new Error('Failed to load tracks');
        }
        
        const data = await response.json();
        
        if (data.found && data.tracks && data.tracks.length > 0) {
          setTracks(data.tracks);
        } else {
          setError('No playable tracks found');
        }
      } catch (err) {
        console.error('Error fetching Bandcamp tracks:', err);
        setError('Could not load tracks. Please try opening in Bandcamp.');
      } finally {
        setLoading(false);
      }
    };

    fetchTracks();
  }, [bandcampUrl]);

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
        console.log('Duration loaded:', newDuration);
        setDuration(newDuration);
      }
    };
    const handleLoadedMetadata = () => {
      const newDuration = audio.duration;
      if (!isNaN(newDuration) && isFinite(newDuration)) {
        console.log('Metadata loaded, duration:', newDuration);
        setDuration(newDuration);
      }
    };
    const handleEnded = () => {
      console.log('Track ended, moving to next');
      handleNext();
    };
    const handlePlay = () => {
      console.log('Audio play event fired');
      setIsPlaying(true);
    };
    const handlePause = () => {
      console.log('Audio pause event fired');
      setIsPlaying(false);
    };
    const handleCanPlayThrough = () => {
      setTrackLoading(false);  // Track is ready
      console.log('Track ready to play');
    };
    const handleWaiting = () => {
      setTrackLoading(true);  // Buffering
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('durationchange', handleDurationChange);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('canplaythrough', handleCanPlayThrough);
    audio.addEventListener('waiting', handleWaiting);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('durationchange', handleDurationChange);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('canplaythrough', handleCanPlayThrough);
      audio.removeEventListener('waiting', handleWaiting);
    };
  }, [currentTrackIndex, tracks.length]);

  // Load track when index changes - SIMPLIFIED
  useEffect(() => {
    if (tracks.length > 0 && audioRef.current) {
      const track = tracks[currentTrackIndex];
      if (track && track.file_mp3) {
        console.log('🎵 [BANDCAMP] Loading track:', track.title);
        setTrackLoading(true);
        const audio = audioRef.current;
        
        // Simple approach: load and auto-play when ready (if user has interacted)
        const handleCanPlay = () => {
          console.log('🎵 [BANDCAMP] Track ready');
          setTrackLoading(false);
          
          // Only auto-play if user has clicked play before (browser autoplay policy)
          if (hasUserInteractedRef.current) {
            console.log('🎵 [BANDCAMP] Auto-playing...');
            audio.play()
              .then(() => {
                console.log('🎵 [BANDCAMP] ✅ Playing');
                setIsPlaying(true);
              })
              .catch(err => {
                console.error('🎵 [BANDCAMP] ❌ Play failed:', err);
                setIsPlaying(false);
              });
          } else {
            console.log('🎵 [BANDCAMP] Waiting for user to click play (first album)');
          }
          
          // Remove listener after first use
          audio.removeEventListener('canplaythrough', handleCanPlay);
        };
        
        audio.addEventListener('canplaythrough', handleCanPlay);
        audio.src = track.file_mp3;
        audio.load();
        
        // Cleanup
        return () => {
          audio.removeEventListener('canplaythrough', handleCanPlay);
        };
      }
    }
  }, [currentTrackIndex, tracks]);

  const handlePlayPause = async () => {
    if (!audioRef.current) return;
    
    if (isPlaying) {
      console.log('🎵 [BANDCAMP] Pausing');
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      console.log('🎵 [BANDCAMP] User clicked play');
      hasUserInteractedRef.current = true;  // Mark that user has interacted
      setTrackLoading(true);
      try {
        await audioRef.current.play();
        console.log('🎵 [BANDCAMP] ✅ Playing');
        setIsPlaying(true);
        setTrackLoading(false);
      } catch (err) {
        console.error('🎵 [BANDCAMP] ❌ Play error:', err);
        setIsPlaying(false);
        setTrackLoading(false);
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
    // isPlaying will be set by the audio 'play' event
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
