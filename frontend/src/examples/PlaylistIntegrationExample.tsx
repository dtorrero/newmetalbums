/**
 * Example: How to integrate the playlist system into existing views
 * 
 * This shows how to add the Play button to DayView, WeekView, or MonthView
 */

import React from 'react';
import { Box, Container, Typography, Alert } from '@mui/material';
import { usePlaylist } from '../hooks/usePlaylist';
import { PlaylistButton } from '../components/PlaylistButton';
import { SidebarPlayer } from '../components/SidebarPlayer';

// Example 1: Integration in DayView
export const DayViewWithPlaylist: React.FC<{ date: string }> = ({ date }) => {
  const { playlist, isPlayerOpen, loading, error, loadPlaylist, closePlayer } = usePlaylist();

  return (
    <Container>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Albums for {date}</Typography>
        
        <PlaylistButton
          periodType="day"
          periodKey={date}
          loading={loading}
          onClick={loadPlaylist}
        />
      </Box>

      {error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Your existing album grid/list here */}
      <Typography variant="body2" color="text.secondary">
        Album list would go here...
      </Typography>

      {/* Sidebar Player */}
      <SidebarPlayer
        open={isPlayerOpen}
        onClose={closePlayer}
        playlist={playlist}
      />
    </Container>
  );
};

// Example 2: Integration in WeekView with filters
export const WeekViewWithPlaylist: React.FC<{ 
  weekKey: string;
  selectedGenres: string[];
  searchQuery: string;
}> = ({ weekKey, selectedGenres, searchQuery }) => {
  const { playlist, isPlayerOpen, loading, error, loadPlaylist, closePlayer } = usePlaylist();

  return (
    <Container>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Week {weekKey}</Typography>
        
        <PlaylistButton
          periodType="week"
          periodKey={weekKey}
          genres={selectedGenres}
          search={searchQuery}
          loading={loading}
          onClick={loadPlaylist}
        />
      </Box>

      {error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Your existing album grid/list here */}

      {/* Sidebar Player */}
      <SidebarPlayer
        open={isPlayerOpen}
        onClose={closePlayer}
        playlist={playlist}
      />
    </Container>
  );
};

// Example 3: Integration in MonthView
export const MonthViewWithPlaylist: React.FC<{ monthKey: string }> = ({ monthKey }) => {
  const { playlist, isPlayerOpen, loading, error, loadPlaylist, closePlayer } = usePlaylist();

  return (
    <Container>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Month {monthKey}</Typography>
        
        <PlaylistButton
          periodType="month"
          periodKey={monthKey}
          loading={loading}
          onClick={loadPlaylist}
          variant="outlined"
        />
      </Box>

      {error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Your existing album grid/list here */}

      {/* Sidebar Player */}
      <SidebarPlayer
        open={isPlayerOpen}
        onClose={closePlayer}
        playlist={playlist}
      />
    </Container>
  );
};

/**
 * INTEGRATION STEPS:
 * 
 * 1. Import the hook and components:
 *    import { usePlaylist } from '../hooks/usePlaylist';
 *    import { PlaylistButton } from '../components/PlaylistButton';
 *    import { SidebarPlayer } from '../components/SidebarPlayer';
 * 
 * 2. Add the hook to your component:
 *    const { playlist, isPlayerOpen, loading, error, loadPlaylist, closePlayer } = usePlaylist();
 * 
 * 3. Add the PlaylistButton where you want it (usually in header):
 *    <PlaylistButton
 *      periodType="day"  // or "week" or "month"
 *      periodKey={yourDateOrPeriodKey}
 *      genres={yourGenreFilters}  // optional
 *      search={yourSearchQuery}   // optional
 *      loading={loading}
 *      onClick={loadPlaylist}
 *    />
 * 
 * 4. Add the SidebarPlayer at the end of your component:
 *    <SidebarPlayer
 *      open={isPlayerOpen}
 *      onClose={closePlayer}
 *      playlist={playlist}
 *    />
 * 
 * 5. Optionally show error messages:
 *    {error && <Alert severity="warning">{error}</Alert>}
 */
