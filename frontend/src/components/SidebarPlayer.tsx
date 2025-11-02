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
  useTheme,
  useMediaQuery,
  Dialog,
  DialogTitle,
  DialogContent,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Paper,
  Collapse,
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
  QueueMusic,
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
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const [playerState, setPlayerState] = useState<PlayerState>({
    isPlaying: false,
    currentIndex: initialIndex,
    currentPlatform: null,
    volume: 80,
    shuffle: false,
    repeat: 'none',
  });

  // Playlist popup state
  const [playlistOpen, setPlaylistOpen] = useState(false);

  // User's platform preference (stored in localStorage)
  const [platformPreference, setPlatformPreference] = useState<'bandcamp' | 'youtube'>(() => {
    const saved = localStorage.getItem('player_platform_preference');
    return (saved as 'bandcamp' | 'youtube') || 'bandcamp'; // Default to Bandcamp
  });
  
  // Player settings from admin (which services are enabled)
  const [playerSettings, setPlayerSettings] = useState({
    bandcamp_enabled: true,
    youtube_enabled: true,
  });
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  
  // Shared user interaction state - passed to both players
  const hasUserInteractedRef = useRef(false);

  const youtubeRef = useRef<HTMLIFrameElement>(null);
  const bandcampRef = useRef<HTMLIFrameElement>(null);

  const currentItem = playlist[playerState.currentIndex];
  
  // Fetch player settings on mount
  useEffect(() => {
    const fetchPlayerSettings = async () => {
      try {
        const baseUrl = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000';
        console.log('🔧 Fetching player settings from:', `${baseUrl}/api/admin/settings/player`);
        const response = await fetch(`${baseUrl}/api/admin/settings/player`);
        console.log('🔧 Response status:', response.status);
        if (response.ok) {
          const data = await response.json();
          console.log('✅ Player settings loaded:', data);
          setPlayerSettings(data);
          setSettingsLoaded(true);
        } else {
          const errorText = await response.text();
          console.error('❌ Failed to fetch player settings. Status:', response.status, 'Error:', errorText);
          console.warn('⚠️ Using default settings (both enabled)');
          setSettingsLoaded(true);
        }
      } catch (error) {
        console.error('❌ Exception fetching player settings:', error);
        console.warn('⚠️ Using default settings (both enabled)');
        setSettingsLoaded(true);
      }
    };
    fetchPlayerSettings();
  }, []);

  // Determine which platform to show - ALWAYS prioritize Bandcamp over YouTube
  useEffect(() => {
    if (!currentItem || !settingsLoaded) return;

    // Priority: Bandcamp first (if available and enabled), then YouTube (if enabled)
    // This ensures better quality and no restrictions
    let selectedPlatform: 'youtube' | 'bandcamp' | null = null;
    
    console.log('Selecting platform with settings:', playerSettings);
    
    // ALWAYS try Bandcamp first
    if (currentItem.platforms.bandcamp && playerSettings.bandcamp_enabled) {
      selectedPlatform = 'bandcamp';
      console.log('Selected Bandcamp (priority)');
    } else if (currentItem.platforms.youtube && playerSettings.youtube_enabled) {
      selectedPlatform = 'youtube';
      console.log('Selected YouTube (fallback - no Bandcamp available)');
    } else {
      console.log('No enabled platform available');
    }

    setPlayerState(prev => ({ ...prev, currentPlatform: selectedPlatform, isPlaying: false }));
  }, [currentItem, playerSettings, settingsLoaded]);
  
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

  const handleTogglePlaylist = () => {
    setPlaylistOpen(prev => !prev);
  };

  const handleSelectAlbum = (index: number) => {
    setPlayerState(prev => ({ ...prev, currentIndex: index }));
    // Close playlist on mobile, keep open on desktop
    if (isMobile) {
      setPlaylistOpen(false);
    }
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
      variant={isMobile ? 'temporary' : 'persistent'}
      sx={{
        width: isMobile ? '100vw' : SIDEBAR_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: isMobile ? '100vw' : SIDEBAR_WIDTH,
          boxSizing: 'border-box',
          bgcolor: 'background.paper',
          borderLeft: '1px solid',
          borderColor: 'divider',
        },
      }}
    >
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Box sx={{ p: isMobile ? 1.5 : 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant={isMobile ? 'subtitle1' : 'h6'} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <MusicNote fontSize={isMobile ? 'small' : 'medium'} /> Now Playing
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
                height: isMobile ? '250px' : '300px',
                objectFit: 'cover'
              }}
              image={currentItem.cover_path ? `${process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000'}/${currentItem.cover_path}` : currentItem.cover_art}
              alt={currentItem.title}
            />
          ) : (
            <Box sx={{ 
              width: '100%', 
              height: isMobile ? '250px' : '300px', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              bgcolor: 'grey.900'
            }}>
              <MusicNote sx={{ fontSize: isMobile ? 60 : 80, color: 'grey.700' }} />
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
              p: isMobile ? 1.5 : 2,
            }}
          >
            <Typography variant={isMobile ? 'subtitle1' : 'h6'} sx={{ color: 'white', fontWeight: 'bold' }} noWrap>
              {currentItem.title}
            </Typography>
            <Typography variant={isMobile ? 'caption' : 'body2'} sx={{ color: 'grey.300' }} noWrap>
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

        {/* Platform Selection - Only show if both platforms available AND enabled */}
        {currentItem.platforms.youtube && currentItem.platforms.bandcamp && 
         playerSettings.youtube_enabled && playerSettings.bandcamp_enabled && (
          <Box sx={{ px: 2, pt: 2 }}>
            <Stack direction="row" spacing={1} justifyContent="center">
              <Button
                variant={platformPreference === 'bandcamp' ? 'contained' : 'outlined'}
                size="small"
                onClick={() => handlePlatformChange('bandcamp')}
                disabled={!currentItem.platforms.bandcamp || !playerSettings.bandcamp_enabled}
              >
                Bandcamp
              </Button>
              <Button
                variant={platformPreference === 'youtube' ? 'contained' : 'outlined'}
                size="small"
                onClick={() => handlePlatformChange('youtube')}
                disabled={!currentItem.platforms.youtube || !playerSettings.youtube_enabled}
              >
                YouTube
              </Button>
            </Stack>
          </Box>
        )}

        {/* Embed Players */}
        <Box sx={{ px: 2, py: 2 }}>
          {currentItem.platforms.youtube && playerState.currentPlatform === 'youtube' && playerSettings.youtube_enabled && (
            <Box sx={{ width: '100%', mb: 2 }}>
              {/* Custom YouTube Player using yt-dlp - No embed restrictions! */}
              <YouTubePlayer
                youtubeUrl={currentItem.platforms.youtube.video_url || currentItem.platforms.youtube.embed_url}
                albumTitle={currentItem.title}
                artist={currentItem.artist}
                onAlbumEnd={handleAlbumEnd}
                hasUserInteractedRef={hasUserInteractedRef}
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

          {currentItem.platforms.bandcamp && playerState.currentPlatform === 'bandcamp' && playerSettings.bandcamp_enabled && (
            <Box sx={{ width: '100%', mb: 2 }}>
              {/* Custom Bandcamp Player - No cookie popups! */}
              <BandcampPlayer
                bandcampUrl={currentItem.platforms.bandcamp.embed_url}
                albumTitle={currentItem.title}
                artist={currentItem.artist}
                onAlbumEnd={handleAlbumEnd}
                hasUserInteractedRef={hasUserInteractedRef}
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
        <Box sx={{ p: isMobile ? 1.5 : 2, bgcolor: 'background.default' }}>
          <Typography variant="caption" color="text.secondary" align="center" display="block" sx={{ mb: 1 }}>
            Album {playerState.currentIndex + 1} of {playlist.length}
          </Typography>
          
          <Stack direction="row" spacing={isMobile ? 1 : 2} justifyContent="center" alignItems="center">
            {isMobile ? (
              <>
                <IconButton
                  color="primary"
                  onClick={handlePrevious}
                  disabled={playlist.length <= 1}
                  size="large"
                  sx={{ border: '1px solid', borderColor: 'primary.main' }}
                >
                  <SkipPrevious />
                </IconButton>
                
                <IconButton
                  color="primary"
                  onClick={handleTogglePlaylist}
                  size="large"
                  sx={{ 
                    border: '1px solid', 
                    borderColor: 'primary.main',
                    bgcolor: playlistOpen ? 'primary.main' : 'transparent',
                    '&:hover': {
                      bgcolor: playlistOpen ? 'primary.dark' : 'rgba(255, 255, 255, 0.08)',
                    }
                  }}
                >
                  <QueueMusic />
                </IconButton>
                
                <IconButton
                  color="primary"
                  onClick={handleNext}
                  disabled={playlist.length <= 1}
                  size="large"
                  sx={{ border: '1px solid', borderColor: 'primary.main' }}
                >
                  <SkipNext />
                </IconButton>
              </>
            ) : (
              <>
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
                  variant={playlistOpen ? 'contained' : 'outlined'}
                  startIcon={<QueueMusic />}
                  onClick={handleTogglePlaylist}
                  size="large"
                >
                  Playlist
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
              </>
            )}
          </Stack>
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

      {/* Playlist Popup - Mobile (Dialog) */}
      {isMobile && (
        <Dialog
          open={playlistOpen}
          onClose={() => setPlaylistOpen(false)}
          fullWidth
          maxWidth="sm"
          PaperProps={{
            sx: {
              position: 'fixed',
              top: 0,
              m: 0,
              maxHeight: '70vh',
            }
          }}
        >
          <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">Playlist ({playlist.length} albums)</Typography>
            <IconButton onClick={() => setPlaylistOpen(false)} size="small">
              <Close />
            </IconButton>
          </DialogTitle>
          <DialogContent sx={{ p: 0 }}>
            <List sx={{ py: 0 }}>
              {playlist.map((item, index) => {
                const isCurrentlyPlaying = index === playerState.currentIndex;
                const availablePlatform = item.platforms.bandcamp ? 'bandcamp' : item.platforms.youtube ? 'youtube' : null;
                
                return (
                  <ListItem
                    key={`${item.album_id}-${index}`}
                    disablePadding
                    sx={{
                      bgcolor: isCurrentlyPlaying ? 'action.selected' : 'transparent',
                      borderLeft: isCurrentlyPlaying ? '4px solid' : '4px solid transparent',
                      borderColor: 'primary.main',
                    }}
                  >
                    <ListItemButton onClick={() => handleSelectAlbum(index)}>
                      <ListItemAvatar>
                        <Avatar
                          variant="rounded"
                          src={item.cover_path ? `${process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000'}/${item.cover_path}` : item.cover_art}
                          alt={item.title}
                        >
                          <MusicNote />
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Typography variant="body2" noWrap sx={{ flex: 1, fontWeight: isCurrentlyPlaying ? 'bold' : 'normal' }}>
                              {item.title}
                            </Typography>
                            {availablePlatform && (
                              <Box
                                component="img"
                                src={`/${availablePlatform === 'youtube' ? 'Youtube.svg' : 'Bandcamp.svg'}`}
                                alt={availablePlatform}
                                sx={{ width: 16, height: 16, opacity: 0.7 }}
                              />
                            )}
                          </Box>
                        }
                        secondary={
                          <Typography variant="caption" color="text.secondary" noWrap>
                            {item.artist}
                          </Typography>
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                );
              })}
            </List>
          </DialogContent>
        </Dialog>
      )}

      {/* Playlist Popup - Desktop (Collapsible Panel) */}
      {!isMobile && (
        <Collapse in={playlistOpen} orientation="horizontal">
          <Paper
            elevation={3}
            sx={{
              position: 'fixed',
              right: SIDEBAR_WIDTH,
              top: 0,
              bottom: 0,
              width: 350,
              bgcolor: 'background.paper',
              borderRight: '1px solid',
              borderColor: 'divider',
              display: 'flex',
              flexDirection: 'column',
              zIndex: 1200,
            }}
          >
            <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid', borderColor: 'divider' }}>
              <Typography variant="h6">Playlist ({playlist.length})</Typography>
              <IconButton onClick={() => setPlaylistOpen(false)} size="small">
                <Close />
              </IconButton>
            </Box>
            <List sx={{ flex: 1, overflow: 'auto', py: 0 }}>
              {playlist.map((item, index) => {
                const isCurrentlyPlaying = index === playerState.currentIndex;
                const availablePlatform = item.platforms.bandcamp ? 'bandcamp' : item.platforms.youtube ? 'youtube' : null;
                
                return (
                  <ListItem
                    key={`${item.album_id}-${index}`}
                    disablePadding
                    sx={{
                      bgcolor: isCurrentlyPlaying ? 'action.selected' : 'transparent',
                      borderLeft: isCurrentlyPlaying ? '4px solid' : '4px solid transparent',
                      borderColor: 'primary.main',
                    }}
                  >
                    <Tooltip 
                      title={item.genre || 'Genre not available'} 
                      placement="left"
                      arrow
                      enterDelay={500}
                    >
                      <ListItemButton onClick={() => handleSelectAlbum(index)}>
                        <ListItemAvatar>
                          <Avatar
                            variant="rounded"
                            src={item.cover_path ? `${process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000'}/${item.cover_path}` : item.cover_art}
                            alt={item.title}
                          >
                            <MusicNote />
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <Typography variant="body2" noWrap sx={{ flex: 1, fontWeight: isCurrentlyPlaying ? 'bold' : 'normal' }}>
                                {item.title}
                              </Typography>
                              {availablePlatform && (
                                <Box
                                  component="img"
                                  src={`/${availablePlatform === 'youtube' ? 'Youtube.svg' : 'Bandcamp.svg'}`}
                                  alt={availablePlatform}
                                  sx={{ width: 18, height: 18, opacity: 0.7 }}
                                />
                              )}
                            </Box>
                          }
                          secondary={
                            <Typography variant="caption" color="text.secondary" noWrap>
                              {item.artist}
                            </Typography>
                          }
                        />
                      </ListItemButton>
                    </Tooltip>
                  </ListItem>
                );
              })}
            </List>
          </Paper>
        </Collapse>
      )}
    </Drawer>
  );
};

export default SidebarPlayer;
