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
  Dialog,
  DialogContent,
  IconButton,
} from '@mui/material';
import {
  ArrowBack,
  OpenInNew,
  MusicNote,
  LocationOn,
  Label,
  DateRange,
  Album as AlbumIcon,
  Close,
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
  const [imageDialog, setImageDialog] = useState<{ open: boolean; imageUrl: string; albumName: string }>({ 
    open: false, 
    imageUrl: '', 
    albumName: '' 
  });

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
    // First try local cover file if available
    if (album.cover_path && album.cover_path !== 'N/A') {
      const baseUrl = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000';
      // cover_path already includes 'covers/' prefix, so just add base URL
      return `${baseUrl}/${album.cover_path}`;
    }
    // Fallback to album_id.jpg if cover_path not available
    if (album.album_id) {
      const baseUrl = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000';
      return `${baseUrl}/covers/${album.album_id}.jpg`;
    }
    // Final fallback to external cover URL
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
              <Card key={album.id} elevation={3} sx={{ display: 'flex', minHeight: 340 }}>
                  {/* Album Cover */}
                  <Box sx={{ width: 320, flexShrink: 0, position: 'relative' }}>
                    <Box
                      sx={{
                        width: 320,
                        height: 320,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        bgcolor: 'grey.800',
                        border: '1px solid',
                        borderColor: 'grey.700',
                      }}
                    >
                      {getCoverImageUrl(album) ? (
                        <CardMedia
                          component="img"
                          sx={{ 
                            width: '100%', 
                            height: '100%', 
                            objectFit: 'contain',
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            cursor: 'pointer',
                            transition: 'transform 0.2s ease-in-out',
                            '&:hover': {
                              transform: 'scale(1.02)'
                            }
                          }}
                          image={getCoverImageUrl(album) || ''}
                          alt={`${album.album_name} cover`}
                          onClick={() => setImageDialog({ 
                            open: true, 
                            imageUrl: getCoverImageUrl(album) || '', 
                            albumName: album.album_name 
                          })}
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            target.style.display = 'none';
                          }}
                        />
                      ) : (
                        <AlbumIcon sx={{ fontSize: 80, color: 'grey.500' }} />
                      )}
                    </Box>
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

        {/* Image Dialog */}
        <Dialog
          open={imageDialog.open}
          onClose={() => setImageDialog({ open: false, imageUrl: '', albumName: '' })}
          maxWidth="lg"
          fullWidth
          sx={{
            '& .MuiDialog-paper': {
              backgroundColor: 'rgba(0, 0, 0, 0.9)',
              boxShadow: 'none',
            }
          }}
        >
          <DialogContent sx={{ p: 0, position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <IconButton
              onClick={() => setImageDialog({ open: false, imageUrl: '', albumName: '' })}
              sx={{
                position: 'absolute',
                top: 16,
                right: 16,
                color: 'white',
                backgroundColor: 'rgba(0, 0, 0, 0.5)',
                zIndex: 1,
                '&:hover': {
                  backgroundColor: 'rgba(0, 0, 0, 0.7)'
                }
              }}
            >
              <Close />
            </IconButton>
            <Box
              component="img"
              src={imageDialog.imageUrl}
              alt={`${imageDialog.albumName} cover - full size`}
              sx={{
                maxWidth: '100%',
                maxHeight: '90vh',
                objectFit: 'contain',
                display: 'block'
              }}
              onClick={() => setImageDialog({ open: false, imageUrl: '', albumName: '' })}
            />
          </DialogContent>
        </Dialog>
      </Box>
    </Container>
  );
};

export default AlbumDisplay;
