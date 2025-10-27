import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Drawer,
  IconButton,
  Typography,
  LinearProgress,
  Stack,
  Chip,
  Tooltip,
  Card,
  CardMedia,
  CardContent,
  Divider,
  Button,
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  SkipNext,
  SkipPrevious,
  Shuffle,
  Close,
  MusicNote,
  OpenInNew,
} from '@mui/icons-material';
import { PlaylistItem, PlayerState } from '../types/playlist';
import PlatformLinks from './PlatformLinks';
import { BandcampPlayer } from './BandcampPlayer';
import { YouTubePlayer } from './YouTubePlayer';

interface SidebarPlayerProps {
  open: boolean;
  onClose: () => void;
  playlist: PlaylistItem[];
  initialIndex?: number;
}

const SIDEBAR_WIDTH = 400;

export const SidebarPlayer: React.FC<SidebarPlayerProps> = ({
  open,
  onClose,
  playlist,
  initialIndex = 0,
}) => {
  const [playerState, setPlayerState] = useState<PlayerState>({
    isPlaying: false,
    currentIndex: initialIndex,
    currentPlatform: null,
    volume: 80,
    shuffle: false,
    repeat: 'none',
  });

  // User's platform preference (stored in localStorage)
  const [platformPreference, setPlatformPreference] = useState<'bandcamp' | 'youtube'>(() => {
    const saved = localStorage.getItem('player_platform_preference');
    return (saved as 'bandcamp' | 'youtube') || 'bandcamp'; // Default to Bandcamp
  });

  const youtubeRef = useRef<HTMLIFrameElement>(null);
  const bandcampRef = useRef<HTMLIFrameElement>(null);

  const currentItem = playlist[playerState.currentIndex];

  // Determine which platform to show based on user preference
  useEffect(() => {
    if (!currentItem) return;

    // Try user's preferred platform first, fallback to the other
    let selectedPlatform: 'youtube' | 'bandcamp' | null = null;
    
    if (platformPreference === 'bandcamp') {
      if (currentItem.platforms.bandcamp) {
        selectedPlatform = 'bandcamp';
      } else if (currentItem.platforms.youtube) {
        selectedPlatform = 'youtube';
      }
    } else {
      if (currentItem.platforms.youtube) {
        selectedPlatform = 'youtube';
      } else if (currentItem.platforms.bandcamp) {
        selectedPlatform = 'bandcamp';
      }
    }

    setPlayerState(prev => ({ ...prev, currentPlatform: selectedPlatform, isPlaying: false }));
  }, [currentItem, platformPreference]);
  
  // Auto-play YouTube when play button is clicked
  useEffect(() => {
    if (playerState.isPlaying && playerState.currentPlatform === 'youtube' && youtubeRef.current) {
      youtubeRef.current.contentWindow?.postMessage(
        JSON.stringify({ event: 'command', func: 'playVideo', args: [] }),
        '*'
      );
    } else if (!playerState.isPlaying && playerState.currentPlatform === 'youtube' && youtubeRef.current) {
      youtubeRef.current.contentWindow?.postMessage(
        JSON.stringify({ event: 'command', func: 'pauseVideo', args: [] }),
        '*'
      );
    }
  }, [playerState.isPlaying]);

  const handlePlayPause = () => {
    const newPlayingState = !playerState.isPlaying;
    setPlayerState(prev => ({ ...prev, isPlaying: newPlayingState }));
    
    // Control iframe playback via postMessage
    if (playerState.currentPlatform === 'youtube' && youtubeRef.current) {
      const command = newPlayingState ? 'playVideo' : 'pauseVideo';
      youtubeRef.current.contentWindow?.postMessage(
        JSON.stringify({ event: 'command', func: command, args: [] }),
        '*'
      );
    }
    
    // For Bandcamp, we can't control it programmatically due to CORS
    // User needs to click play on the embed itself
  };

  const handleNext = () => {
    let nextIndex = playerState.currentIndex + 1;
    if (nextIndex >= playlist.length) {
      nextIndex = 0; // Loop to start
    }
    setPlayerState(prev => ({ ...prev, currentIndex: nextIndex }));
  };

  const handleAlbumEnd = () => {
    // Called when the last track of an album finishes
    console.log('Album finished, advancing to next album');
    handleNext();
  };

  const handlePrevious = () => {
    let prevIndex = playerState.currentIndex - 1;
    if (prevIndex < 0) {
      prevIndex = playlist.length - 1; // Loop to end
    }
    setPlayerState(prev => ({ ...prev, currentIndex: prevIndex }));
  };

  const handleShuffle = () => {
    setPlayerState(prev => ({ ...prev, shuffle: !prev.shuffle }));
  };

  const handlePlatformChange = (platform: 'bandcamp' | 'youtube') => {
    setPlatformPreference(platform);
    localStorage.setItem('player_platform_preference', platform);
    
    // Switch platform if available
    if (currentItem.platforms[platform]) {
      setPlayerState(prev => ({ ...prev, currentPlatform: platform, isPlaying: false }));
    }
  };

  if (!currentItem) {
    return null;
  }

  const currentEmbed = playerState.currentPlatform 
    ? currentItem.platforms[playerState.currentPlatform]
    : null;

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      variant="persistent"
      sx={{
        width: SIDEBAR_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: SIDEBAR_WIDTH,
          boxSizing: 'border-box',
          bgcolor: 'background.paper',
          borderLeft: '1px solid',
          borderColor: 'divider',
        },
      }}
    >
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <MusicNote /> Now Playing
          </Typography>
          <IconButton onClick={onClose} size="small">
            <Close />
          </IconButton>
        </Box>

        <Divider />

        {/* Album Cover - At Top */}
        <Box sx={{ position: 'relative', width: '100%', bgcolor: 'black' }}>
          {(currentItem.cover_path || currentItem.cover_art) ? (
            <CardMedia
              component="img"
              sx={{ 
                width: '100%',
                height: '300px',
                objectFit: 'cover'
              }}
              image={currentItem.cover_path ? `http://127.0.0.1:8000/${currentItem.cover_path}` : currentItem.cover_art}
              alt={currentItem.title}
            />
          ) : (
            <Box sx={{ 
              width: '100%', 
              height: '300px', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              bgcolor: 'grey.900'
            }}>
              <MusicNote sx={{ fontSize: 80, color: 'grey.700' }} />
            </Box>
          )}
          
          {/* Overlay with track info */}
          <Box
            sx={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              background: 'linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.7) 70%, transparent 100%)',
              p: 2,
            }}
          >
            <Typography variant="h6" sx={{ color: 'white', fontWeight: 'bold' }} noWrap>
              {currentItem.title}
            </Typography>
            <Typography variant="body2" sx={{ color: 'grey.300' }} noWrap>
              {currentItem.artist}
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
              <Chip label={currentItem.type} size="small" sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }} />
              {currentEmbed && (
                <Chip 
                  label={playerState.currentPlatform?.toUpperCase()} 
                  size="small" 
                  color="primary"
                />
              )}
            </Stack>
          </Box>
        </Box>

        {/* Platform Selection */}
        {currentItem.platforms.youtube && currentItem.platforms.bandcamp && (
          <Box sx={{ px: 2, pt: 2 }}>
            <Stack direction="row" spacing={1} justifyContent="center">
              <Button
                variant={platformPreference === 'bandcamp' ? 'contained' : 'outlined'}
                size="small"
                onClick={() => handlePlatformChange('bandcamp')}
                disabled={!currentItem.platforms.bandcamp}
              >
                Bandcamp
              </Button>
              <Button
                variant={platformPreference === 'youtube' ? 'contained' : 'outlined'}
                size="small"
                onClick={() => handlePlatformChange('youtube')}
                disabled={!currentItem.platforms.youtube}
              >
                YouTube
              </Button>
            </Stack>
          </Box>
        )}

        {/* Embed Players */}
        <Box sx={{ px: 2, py: 2 }}>
          {currentItem.platforms.youtube && playerState.currentPlatform === 'youtube' && (
            <Box sx={{ width: '100%', mb: 2 }}>
              {/* Custom YouTube Player using yt-dlp - No embed restrictions! */}
              <YouTubePlayer
                youtubeUrl={currentItem.platforms.youtube.video_url || currentItem.platforms.youtube.embed_url}
                albumTitle={currentItem.title}
                artist={currentItem.artist}
                onAlbumEnd={handleAlbumEnd}
              />
              
              {/* Fallback link */}
              <Button
                variant="text"
                size="small"
                fullWidth
                startIcon={<OpenInNew />}
                href={currentItem.platforms.youtube.video_url || currentItem.platforms.youtube.embed_url}
                target="_blank"
                rel="noopener noreferrer"
                sx={{ mt: 1, fontSize: '0.75rem' }}
              >
                Open in YouTube
              </Button>
            </Box>
          )}

          {currentItem.platforms.bandcamp && playerState.currentPlatform === 'bandcamp' && (
            <Box sx={{ width: '100%', mb: 2 }}>
              {/* Custom Bandcamp Player - No cookie popups! */}
              <BandcampPlayer
                bandcampUrl={currentItem.platforms.bandcamp.embed_url}
                albumTitle={currentItem.title}
                artist={currentItem.artist}
                onAlbumEnd={handleAlbumEnd}
              />
              
              {/* Fallback link */}
              <Button
                variant="text"
                size="small"
                fullWidth
                startIcon={<OpenInNew />}
                href={currentItem.platforms.bandcamp.embed_url}
                target="_blank"
                rel="noopener noreferrer"
                sx={{ mt: 1, fontSize: '0.75rem' }}
              >
                Open in Bandcamp
              </Button>
            </Box>
          )}
        </Box>

        {/* Album Navigation Controls */}
        <Box sx={{ p: 2, bgcolor: 'background.default' }}>
          <Typography variant="caption" color="text.secondary" align="center" display="block" sx={{ mb: 1 }}>
            Album {playerState.currentIndex + 1} of {playlist.length}
          </Typography>
          
          <Stack direction="row" spacing={2} justifyContent="center" alignItems="center">
            <Button
              variant="outlined"
              startIcon={<SkipPrevious />}
              onClick={handlePrevious}
              disabled={playlist.length <= 1}
              size="large"
            >
              Previous Album
            </Button>
            
            <Button
              variant="outlined"
              endIcon={<SkipNext />}
              onClick={handleNext}
              disabled={playlist.length <= 1}
              size="large"
            >
              Next Album
            </Button>
          </Stack>
          
          <LinearProgress 
            variant="determinate" 
            value={(playerState.currentIndex / playlist.length) * 100} 
            sx={{ mt: 2, borderRadius: 1 }}
          />
        </Box>

        {/* Platform Toggle (if both available) */}
        {currentItem.platforms.youtube && currentItem.platforms.bandcamp && (
          <Box sx={{ px: 2, pb: 2 }}>
            <Stack direction="row" spacing={1} justifyContent="center">
              <Chip
                label="YouTube"
                onClick={() => setPlayerState(prev => ({ ...prev, currentPlatform: 'youtube' }))}
                color={playerState.currentPlatform === 'youtube' ? 'primary' : 'default'}
                variant={playerState.currentPlatform === 'youtube' ? 'filled' : 'outlined'}
              />
              <Chip
                label="Bandcamp"
                onClick={() => setPlayerState(prev => ({ ...prev, currentPlatform: 'bandcamp' }))}
                color={playerState.currentPlatform === 'bandcamp' ? 'primary' : 'default'}
                variant={playerState.currentPlatform === 'bandcamp' ? 'filled' : 'outlined'}
              />
            </Stack>
          </Box>
        )}
      </Box>
    </Drawer>
  );
};

export default SidebarPlayer;
