import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardMedia,
  Chip,
  CircularProgress,
  Alert,
  Container,
  Button,
  Link,
  Divider,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import {
  ArrowBack,
  OpenInNew,
  MusicNote,
  LocationOn,
  Label,
  DateRange,
  Album as AlbumIcon,
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Album } from '../types';

const AlbumDisplay: React.FC = () => {
  const { date } = useParams<{ date: string }>();
  const navigate = useNavigate();
  const [albums, setAlbums] = useState<Album[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAlbums = async () => {
      if (!date) return;
      
      try {
        setLoading(true);
        setError(null);
        const response = await api.getAlbumsByDate(date);
        setAlbums(response.albums);
      } catch (err) {
        console.error('Error fetching albums:', err);
        setError('Failed to load albums for this date.');
      } finally {
        setLoading(false);
      }
    };

    fetchAlbums();
  }, [date]);

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

  const getCoverImageUrl = (album: Album) => {
    if (album.cover_path && album.cover_path !== 'N/A') {
      return `http://127.0.0.1:8000/covers/${album.cover_path}`;
    }
    return album.cover_art && album.cover_art !== 'N/A' ? album.cover_art : null;
  };

  if (loading) {
    return (
      <Container maxWidth="lg">
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <CircularProgress size={60} />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg">
        <Box mt={4}>
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate('/')}
            sx={{ mb: 2 }}
          >
            Back to Dates
          </Button>
          <Alert severity="error">{error}</Alert>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box py={4}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate('/')}
          sx={{ mb: 3 }}
          variant="outlined"
        >
          Back to Dates
        </Button>

        <Typography variant="h4" component="h1" gutterBottom>
          🤘 Albums Released on {formatDate(date || '')}
        </Typography>
        
        <Typography variant="h6" color="text.secondary" sx={{ mb: 4 }}>
          {albums.length} album{albums.length !== 1 ? 's' : ''} found
        </Typography>

        {albums.length === 0 ? (
          <Alert severity="info">
            No albums found for this date.
          </Alert>
        ) : (
          <Box display="flex" flexDirection="column" gap={4}>
            {albums.map((album) => (
              <Card key={album.id} elevation={3} sx={{ display: 'flex', minHeight: 300 }}>
                  {/* Album Cover */}
                  <Box sx={{ width: 250, flexShrink: 0 }}>
                    {getCoverImageUrl(album) ? (
                      <CardMedia
                        component="img"
                        sx={{ width: 250, height: 250, objectFit: 'cover' }}
                        image={getCoverImageUrl(album) || ''}
                        alt={`${album.album_name} cover`}
                        onError={(e) => {
                          const target = e.target as HTMLImageElement;
                          target.style.display = 'none';
                        }}
                      />
                    ) : (
                      <Box
                        sx={{
                          width: 250,
                          height: 250,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          bgcolor: 'grey.200',
                        }}
                      >
                        <AlbumIcon sx={{ fontSize: 80, color: 'grey.400' }} />
                      </Box>
                    )}
                  </Box>

                  {/* Album Details */}
                  <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                    <Box>
                      <Typography variant="h5" component="h2" gutterBottom>
                        {album.album_name}
                      </Typography>
                      
                      <Typography variant="h6" color="primary" gutterBottom>
                        by {album.band_name}
                      </Typography>

                      <Box display="flex" flexWrap="wrap" gap={1} mb={2}>
                        <Chip
                          icon={<DateRange />}
                          label={album.type}
                          size="small"
                          color="secondary"
                        />
                        {album.country_of_origin && (
                          <Chip
                            icon={<LocationOn />}
                            label={album.country_of_origin}
                            size="small"
                            variant="outlined"
                          />
                        )}
                        {album.current_label && album.current_label !== 'N/A' && (
                          <Chip
                            icon={<Label />}
                            label={album.current_label}
                            size="small"
                            variant="outlined"
                          />
                        )}
                      </Box>

                      {album.genre && (
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          <strong>Genre:</strong> {album.genre}
                        </Typography>
                      )}

                      {album.themes && album.themes !== 'N/A' && (
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          <strong>Themes:</strong> {album.themes}
                        </Typography>
                      )}

                      {album.location && album.location !== 'N/A' && (
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          <strong>Location:</strong> {album.location}
                        </Typography>
                      )}
                    </Box>

                    <Box mt="auto">
                      <Divider sx={{ my: 2 }} />
                      
                      {/* Tracklist */}
                      {album.tracklist && album.tracklist.length > 0 && (
                        <Box mb={2}>
                          <Typography variant="subtitle2" gutterBottom>
                            <MusicNote sx={{ fontSize: 16, mr: 0.5, verticalAlign: 'middle' }} />
                            Tracklist ({album.tracklist.length} tracks)
                          </Typography>
                          <List dense sx={{ maxHeight: 150, overflow: 'auto' }}>
                            {album.tracklist.slice(0, 5).map((track, index) => (
                              <ListItem key={index} sx={{ py: 0.5 }}>
                                <ListItemText
                                  primary={`${track.track_number}. ${track.track_name}`}
                                  secondary={track.track_length}
                                  primaryTypographyProps={{ variant: 'body2' }}
                                  secondaryTypographyProps={{ variant: 'caption' }}
                                />
                              </ListItem>
                            ))}
                            {album.tracklist.length > 5 && (
                              <ListItem>
                                <ListItemText
                                  primary={`... and ${album.tracklist.length - 5} more tracks`}
                                  primaryTypographyProps={{ variant: 'body2', fontStyle: 'italic' }}
                                />
                              </ListItem>
                            )}
                          </List>
                        </Box>
                      )}

                      {/* Links */}
                      <Box display="flex" gap={1} flexWrap="wrap">
                        {album.album_url && (
                          <Button
                            size="small"
                            startIcon={<OpenInNew />}
                            href={album.album_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            Metal Archives
                          </Button>
                        )}
                        {album.bandcamp_url && album.bandcamp_url !== 'N/A' && (
                          <Button
                            size="small"
                            startIcon={<OpenInNew />}
                            href={album.bandcamp_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            color="secondary"
                          >
                            Bandcamp
                          </Button>
                        )}
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
            ))}
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default AlbumDisplay;
