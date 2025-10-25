import React from 'react';
import { Button, CircularProgress, Tooltip } from '@mui/material';
import { PlayArrow, QueueMusic } from '@mui/icons-material';

interface PlaylistButtonProps {
  periodType: 'day' | 'week' | 'month';
  periodKey: string;
  genres?: string[];
  search?: string;
  loading?: boolean;
  onClick: (periodType: 'day' | 'week' | 'month', periodKey: string, options?: any) => void;
  variant?: 'text' | 'outlined' | 'contained';
  size?: 'small' | 'medium' | 'large';
  fullWidth?: boolean;
}

export const PlaylistButton: React.FC<PlaylistButtonProps> = ({
  periodType,
  periodKey,
  genres,
  search,
  loading = false,
  onClick,
  variant = 'contained',
  size = 'medium',
  fullWidth = false,
}) => {
  const handleClick = () => {
    onClick(periodType, periodKey, {
      genres,
      search,
      shuffle: false,
    });
  };

  return (
    <Tooltip title="Play all albums from this period">
      <Button
        variant={variant}
        color="primary"
        size={size}
        fullWidth={fullWidth}
        startIcon={loading ? <CircularProgress size={20} /> : <PlayArrow />}
        endIcon={<QueueMusic />}
        onClick={handleClick}
        disabled={loading}
      >
        {loading ? 'Loading...' : 'Play All'}
      </Button>
    </Tooltip>
  );
};

export default PlaylistButton;
