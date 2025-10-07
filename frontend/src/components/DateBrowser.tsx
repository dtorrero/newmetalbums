import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActionArea,
  Chip,
  CircularProgress,
  Alert,
  Container,
  Button,
  Fab,
  useMediaQuery,
  useTheme,
  ToggleButtonGroup,
  ToggleButton,
} from '@mui/material';
import { CalendarToday, Album, Settings, Today, DateRange, CalendarMonth } from '@mui/icons-material';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { PeriodInfo } from '../types';
import { useAdminContext } from '../contexts/AdminContext';

const DateBrowser: React.FC = () => {
  const [periods, setPeriods] = useState<PeriodInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'day' | 'week' | 'month'>('day');
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { showAdminButton } = useAdminContext();

  useEffect(() => {
    const fetchPeriods = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await api.getDatesGrouped(viewMode);
        setPeriods(response.periods);
      } catch (err) {
        console.error('Error fetching periods:', err);
        setError('Failed to load release dates. Please check if the backend is running.');
      } finally {
        setLoading(false);
      }
    };

    fetchPeriods();
  }, [viewMode]);

  const handlePeriodClick = (period: PeriodInfo) => {
    // Navigate to period view with type and key
    navigate(`/period/${period.period_type}/${encodeURIComponent(period.period_key)}`);
  };

  const handleViewModeChange = (_event: React.MouseEvent<HTMLElement>, newMode: 'day' | 'week' | 'month' | null) => {
    if (newMode !== null) {
      setViewMode(newMode);
    }
  };

  const formatPeriodLabel = (period: PeriodInfo, mobile: boolean = false): string => {
    try {
      const startDate = new Date(period.start_date);
      const endDate = new Date(period.end_date);
      
      if (period.period_type === 'day') {
        if (mobile) {
          return startDate.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
          });
        } else {
          return startDate.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          });
        }
      } else if (period.period_type === 'week') {
        const startStr = startDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        const endStr = endDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        return mobile ? `${startStr} - ${endStr}` : `Week of ${startStr} - ${endStr}`;
      } else if (period.period_type === 'month') {
        return startDate.toLocaleDateString('en-US', {
          year: 'numeric',
          month: mobile ? 'short' : 'long',
        });
      }
      return period.period_key;
    } catch {
      return period.period_key;
    }
  };

  const getGenreChips = (genres: string) => {
    if (!genres) return [];
    return genres
      .split(',')
      .map(g => g.trim())
      .filter(g => g.length > 0)
      .slice(0, 3); // Show max 3 genres
  };

  if (loading) {
    return (
      <Container maxWidth="lg">
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight="400px"
        >
          <CircularProgress size={60} />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg">
        <Box mt={4}>
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box py={isMobile ? 2 : 4}>
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          mb: 3,
          flexDirection: isMobile ? 'column' : 'row',
          gap: isMobile ? 2 : 0
        }}>
          <Typography 
            variant={isMobile ? "h5" : "h4"} 
            component="h1" 
            align={showAdminButton ? (isMobile ? "center" : "left") : "center"}
            sx={{ 
              fontWeight: 'bold',
              color: 'primary.main',
              order: showAdminButton ? (isMobile ? 2 : 1) : 1,
              width: showAdminButton ? 'auto' : '100%'
            }}
          >
            🤘 Browse new metal album releases by date
          </Typography>
          {showAdminButton && (
            <Button
              component={Link}
              to="/admin"
              startIcon={!isMobile ? <Settings /> : undefined}
              variant="outlined"
              color="secondary"
              size={isMobile ? "small" : "medium"}
              sx={{
                order: isMobile ? 1 : 2,
                alignSelf: isMobile ? 'flex-end' : 'auto',
                minWidth: isMobile ? 'auto' : undefined,
                px: isMobile ? 1.5 : 2
              }}
            >
              {isMobile ? <Settings /> : 'Admin'}
            </Button>
          )}
        </Box>

        {/* View Mode Toggle */}
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={handleViewModeChange}
            aria-label="view mode"
            size={isMobile ? "small" : "medium"}
          >
            <ToggleButton value="day" aria-label="day view">
              <Today sx={{ mr: isMobile ? 0 : 1 }} />
              {!isMobile && 'Day'}
            </ToggleButton>
            <ToggleButton value="week" aria-label="week view">
              <DateRange sx={{ mr: isMobile ? 0 : 1 }} />
              {!isMobile && 'Week'}
            </ToggleButton>
            <ToggleButton value="month" aria-label="month view">
              <CalendarMonth sx={{ mr: isMobile ? 0 : 1 }} />
              {!isMobile && 'Month'}
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {periods.length === 0 ? (
          <Alert severity="info">
            No release dates found. The database might be empty.
          </Alert>
        ) : (
          <Box
            display="grid"
            gridTemplateColumns={{
              xs: '1fr',
              sm: 'repeat(2, 1fr)',
              md: 'repeat(3, 1fr)',
            }}
            gap={isMobile ? 2 : 3}
          >
            {periods.map((period) => (
              <Card
                key={period.period_key}
                elevation={2}
                sx={{
                  height: '100%',
                  transition: 'all 0.3s ease-in-out',
                  '&:hover': {
                    elevation: 8,
                    transform: 'translateY(-4px)',
                  },
                }}
              >
                <CardActionArea
                  onClick={() => handlePeriodClick(period)}
                  sx={{ height: '100%', p: 0 }}
                >
                  <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <Box display="flex" alignItems="center" mb={2}>
                      <CalendarToday color="primary" sx={{ mr: 1 }} />
                      <Typography 
                        variant={isMobile ? "subtitle1" : "h6"} 
                        component="h2" 
                        sx={{
                          fontWeight: 'bold',
                          fontSize: isMobile ? '1rem' : '1.25rem',
                          lineHeight: 1.2
                        }}
                      >
                        {formatPeriodLabel(period, isMobile)}
                      </Typography>
                    </Box>

                    <Box display="flex" alignItems="center" mb={2}>
                      <Album color="secondary" sx={{ mr: 1 }} />
                      <Typography variant="body1" color="text.secondary">
                        {period.album_count} album{period.album_count !== 1 ? 's' : ''}
                        {period.period_type !== 'day' && ` across ${period.dates_count} date${period.dates_count !== 1 ? 's' : ''}`}
                      </Typography>
                    </Box>

                    <Box flexGrow={1}>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        Top Genres:
                      </Typography>
                      <Box display="flex" flexWrap="wrap" gap={0.5}>
                        {getGenreChips(period.genres).map((genre, index) => (
                          <Chip
                            key={index}
                            label={genre}
                            size="small"
                            variant="outlined"
                            color="primary"
                          />
                        ))}
                        {getGenreChips(period.genres).length === 0 && (
                          <Typography variant="body2" color="text.disabled">
                            Various
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  </CardContent>
                </CardActionArea>
              </Card>
            ))}
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default DateBrowser;
