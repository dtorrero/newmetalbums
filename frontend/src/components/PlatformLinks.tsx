import React, { useState, useEffect } from 'react';
import { Box, Button, Tooltip } from '@mui/material';
import { OpenInNew } from '@mui/icons-material';
import { Album } from '../types';
import { api } from '../api/client';

interface PlatformLinksProps {
  album: Album;
  size?: 'small' | 'medium' | 'large';
  orientation?: 'horizontal' | 'vertical';
}

interface PlatformConfig {
  key: keyof Album;
  label: string;
  color: 'primary' | 'secondary' | 'success' | 'error' | 'info' | 'warning';
  icon?: string; // Emoji icon
}

const PLATFORMS: PlatformConfig[] = [
  { key: 'bandcamp_url', label: 'Bandcamp', color: 'secondary', icon: '🎵' },
  { key: 'youtube_url', label: 'YouTube', color: 'error', icon: '▶️' },
  { key: 'spotify_url', label: 'Spotify', color: 'success', icon: '🎧' },
  { key: 'discogs_url', label: 'Discogs', color: 'info', icon: '💿' },
  { key: 'lastfm_url', label: 'Last.fm', color: 'error', icon: '📻' },
  { key: 'soundcloud_url', label: 'SoundCloud', color: 'warning', icon: '☁️' },
  { key: 'tidal_url', label: 'Tidal', color: 'primary', icon: '🌊' },
];

export const PlatformLinks: React.FC<PlatformLinksProps> = ({ 
  album, 
  size = 'small',
  orientation = 'horizontal' 
}) => {
  const [visibilitySettings, setVisibilitySettings] = useState<{ [key: string]: boolean }>({});
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await api.getPlatformLinkSettings();
        setVisibilitySettings(response.settings);
      } catch (error) {
        console.error('Failed to load platform link settings:', error);
        // Default to showing all if settings fail to load
        const defaultSettings: { [key: string]: boolean } = {};
        PLATFORMS.forEach(p => {
          const platformName = String(p.key).replace('_url', '');
          defaultSettings[platformName] = true;
        });
        setVisibilitySettings(defaultSettings);
      } finally {
        setLoaded(true);
      }
    };
    loadSettings();
  }, []);

  if (!loaded) {
    return null; // Don't show anything until settings are loaded
  }

  const availableLinks = PLATFORMS.filter(platform => {
    const url = album[platform.key];
    const platformName = String(platform.key).replace('_url', '');
    const isVisible = visibilitySettings[platformName] !== false; // Default to true if not set
    return url && url !== 'N/A' && url !== '' && isVisible;
  });

  if (availableLinks.length === 0) {
    return null;
  }

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: orientation === 'horizontal' ? 'row' : 'column',
        gap: 1,
        flexWrap: 'wrap',
        alignItems: orientation === 'horizontal' ? 'center' : 'stretch',
      }}
    >
      {availableLinks.map((platform) => {
        const url = album[platform.key] as string;
        return (
          <Tooltip key={platform.key} title={`Open on ${platform.label}`} arrow>
            <Button
              size={size}
              startIcon={platform.icon ? <span>{platform.icon}</span> : <OpenInNew />}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              color={platform.color}
              variant="outlined"
              sx={{
                minWidth: orientation === 'horizontal' ? 'auto' : '100%',
                textTransform: 'none',
                borderRadius: 2,
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: 2,
                },
                transition: 'all 0.2s ease-in-out',
              }}
            >
              {platform.label}
            </Button>
          </Tooltip>
        );
      })}
    </Box>
  );
};

export default PlatformLinks;
