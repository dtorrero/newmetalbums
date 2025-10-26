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
  thumbnail?: string;
}

interface YouTubePlayerProps {
  youtubeUrl: string;
  albumTitle?: string;
  artist?: string;
}

export const YouTubePlayer: React.FC<YouTubePlayerProps> = ({
  youtubeUrl,
  albumTitle,
  artist,
}) => {
  const [tracks, setTracks] = useState<YouTubeTrack[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentTrackIndex, setCurrentTrackIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [downloadProgress, setDownloadProgress] = useState<string | null>(null);
  
  const audioRef = useRef<HTMLAudioElement>(null);

  // Fetch stream URLs from backend
  useEffect(() => {
    const fetchStream = async () => {
      try {
        setLoading(true);
        setError(null);
        setCurrentTrackIndex(0);
        setIsPlaying(false);
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
          throw new Error('Failed to load YouTube stream');
        }
        
        const data = await response.json();
        console.log('🎬 [YOUTUBE] Backend response:', data);
        
        if (data.found) {
          if (data.type === 'playlist' && data.tracks && data.tracks.length > 0) {
            console.log('🎬 [YOUTUBE] Playlist with', data.tracks.length, 'tracks');
            // Extract video IDs and use cached audio endpoint
            const cachedTracks = data.tracks.map((track: any) => {
              // Extract video ID from the original URL
              const videoIdMatch = urlToFetch.match(/[?&]v=([^&]+)/);
              const videoId = videoIdMatch ? videoIdMatch[1] : null;
              
              return {
                ...track,
                stream_url: videoId ? 
                  `${baseUrl}/api/youtube/audio/${videoId}` : 
                  null
              };
            });
            setTracks(cachedTracks);
          } else if (data.type === 'video') {
            // Single video - extract video ID and use cached audio endpoint
            console.log('🎬 [YOUTUBE] Single video');
            
            // Extract video ID from URL
            const videoIdMatch = urlToFetch.match(/[?&]v=([^&]+)/);
            const videoId = videoIdMatch ? videoIdMatch[1] : null;
            
            if (videoId) {
              const cachedUrl = `${baseUrl}/api/youtube/audio/${videoId}`;
              console.log('🎬 [YOUTUBE] Cached audio URL:', cachedUrl);
              
              setTracks([{
                title: data.title,
                duration: data.duration,
                stream_url: cachedUrl,
                thumbnail: data.thumbnail,
              }]);
            } else {
              console.error('🎬 [YOUTUBE] Could not extract video ID from URL');
              setError('Could not extract video ID');
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
  }, [youtubeUrl]);

  const handleNext = () => {
    if (currentTrackIndex < tracks.length - 1) {
      setCurrentTrackIndex(currentTrackIndex + 1);
    } else {
      setCurrentTrackIndex(0); // Loop back to start
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

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('durationchange', handleDurationChange);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('durationchange', handleDurationChange);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
    };
  }, [currentTrackIndex, tracks.length]);

  // Load track when index changes
  useEffect(() => {
    if (tracks.length > 0 && audioRef.current) {
      const track = tracks[currentTrackIndex];
      console.log('🎬 [YOUTUBE] Loading track:', track?.title);
      console.log('🎬 [YOUTUBE] Stream URL:', track?.stream_url?.substring(0, 100) + '...');
      
      if (track && track.stream_url) {
        audioRef.current.src = track.stream_url;
        audioRef.current.load();
        console.log('🎬 [YOUTUBE] Audio element src set, calling load()');
        
        // Auto-play when track changes
        audioRef.current.play()
          .then(() => {
            console.log('🎬 [YOUTUBE] ✅ Playback started successfully');
            setIsPlaying(true);
          })
          .catch(err => {
            console.error('🎬 [YOUTUBE] ❌ Playback error:', err);
            console.error('🎬 [YOUTUBE] Error name:', err.name);
            console.error('🎬 [YOUTUBE] Error message:', err.message);
            setIsPlaying(false);
          });
      } else {
        console.error('🎬 [YOUTUBE] ❌ No stream URL available for track');
      }
    }
  }, [currentTrackIndex, tracks]);

  const handlePlayPause = async () => {
    if (!audioRef.current) return;
    
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      try {
        await audioRef.current.play();
        setIsPlaying(true);
      } catch (err) {
        console.error('Playback error:', err);
        setIsPlaying(false);
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
        {downloadProgress ? (
          <Typography variant="caption" color="text.secondary" align="center">
            {downloadProgress}
          </Typography>
        ) : (
          <Typography variant="caption" color="text.secondary">
            Loading YouTube stream...
          </Typography>
        )}
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
          sx={{
            bgcolor: '#FF0000',
            color: 'white',
            '&:hover': { bgcolor: '#CC0000' },
            width: 56,
            height: 56,
          }}
        >
          {isPlaying ? <Pause /> : <PlayArrow />}
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
    </Box>
  );
};

export default YouTubePlayer;
