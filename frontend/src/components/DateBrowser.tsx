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
} from '@mui/material';
import { CalendarToday, Album, Settings } from '@mui/icons-material';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { DateInfo } from '../types';

const DateBrowser: React.FC = () => {
  const [dates, setDates] = useState<DateInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDates = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await api.getDates();
        setDates(response.dates);
      } catch (err) {
        console.error('Error fetching dates:', err);
        setError('Failed to load release dates. Please check if the backend is running.');
      } finally {
        setLoading(false);
      }
    };

    fetchDates();
  }, []);

  const handleDateClick = (date: string) => {
    navigate(`/date/${date}`);
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return dateString;
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
      <Box py={4}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h3" component="h1">
            🤘 Metal Albums Database
          </Typography>
          <Button
            component={Link}
            to="/admin"
            startIcon={<Settings />}
            variant="outlined"
            color="secondary"
          >
            Admin
          </Button>
        </Box>
        <Typography variant="h6" color="text.secondary" align="center" sx={{ mb: 4 }}>
          Browse new metal album releases by date
        </Typography>

        {dates.length === 0 ? (
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
            gap={3}
          >
            {dates.map((dateInfo) => (
              <Card
                key={dateInfo.release_date}
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
                  onClick={() => handleDateClick(dateInfo.release_date)}
                  sx={{ height: '100%', p: 0 }}
                >
                  <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <Box display="flex" alignItems="center" mb={2}>
                      <CalendarToday color="primary" sx={{ mr: 1 }} />
                      <Typography variant="h6" component="h2" noWrap>
                        {formatDate(dateInfo.release_date)}
                      </Typography>
                    </Box>

                    <Box display="flex" alignItems="center" mb={2}>
                      <Album color="secondary" sx={{ mr: 1 }} />
                      <Typography variant="body1" color="text.secondary">
                        {dateInfo.album_count} album{dateInfo.album_count !== 1 ? 's' : ''}
                      </Typography>
                    </Box>

                    <Box flexGrow={1}>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        Top Genres:
                      </Typography>
                      <Box display="flex" flexWrap="wrap" gap={0.5}>
                        {getGenreChips(dateInfo.genres).map((genre, index) => (
                          <Chip
                            key={index}
                            label={genre}
                            size="small"
                            variant="outlined"
                            color="primary"
                          />
                        ))}
                        {getGenreChips(dateInfo.genres).length === 0 && (
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
