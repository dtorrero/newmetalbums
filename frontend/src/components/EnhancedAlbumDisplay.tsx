import React, { useState, useEffect, useCallback } from 'react';
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
  IconButton,
  Drawer,
  Checkbox,
  FormControlLabel,
  FormGroup,
  TextField,
  InputAdornment,
  useMediaQuery,
  useTheme,
  Fab,
  Grid,
  Skeleton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Badge,
  Dialog,
  DialogContent,
  DialogTitle,
} from '@mui/material';
import {
  ArrowBack,
  OpenInNew,
  LocationOn,
  DateRange,
  Album as AlbumIcon,
  FilterList,
  Search,
  Clear,
  ExpandMore,
  Close,
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { Pagination } from '@mui/material';
import { api } from '../api/client';
import { AlbumWithGenres } from '../types';
import { groupGenres, albumMatchesGenreGroups, GenreGroup, GenreHierarchy } from '../utils/genreGrouping';
import PlatformLinks from './PlatformLinks';

interface GenreFilter {
  genre: string;
  selected: boolean;
  count: number;
  color: string;
}

const EnhancedAlbumDisplay: React.FC = () => {
  const { date, periodType, periodKey } = useParams<{ date?: string; periodType?: string; periodKey?: string }>();
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const [albums, setAlbums] = useState<AlbumWithGenres[]>([]);
  const [filteredAlbums, setFilteredAlbums] = useState<AlbumWithGenres[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [genreHierarchy, setGenreHierarchy] = useState<GenreHierarchy | null>(null);
  const [selectedGenreGroups, setSelectedGenreGroups] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchInput, setSearchInput] = useState(''); // Separate input state for debouncing
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [pageTitle, setPageTitle] = useState<string>('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalAlbums, setTotalAlbums] = useState(0);
  const [periodInfo, setPeriodInfo] = useState<{ start_date: string; end_date: string } | null>(null);
  const [imageDialog, setImageDialog] = useState<{
    open: boolean;
    imageUrl: string;
    albumName: string;
    bandName: string;
  }>({
    open: false,
    imageUrl: '',
    albumName: '',
    bandName: ''
  });

  // Generate color for genre
  const generateGenreColor = (genre: string): string => {
    const colors = ['#f44336', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', '#2196f3', '#00bcd4', '#009688', '#4caf50', '#ff9800'];
    let hash = 0;
    for (let i = 0; i < genre.length; i++) {
      hash = genre.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  };

  // Format period title for display
  const formatPeriodTitle = (): string => {
    if (!periodInfo) return periodKey || '';
    
    const startDate = new Date(periodInfo.start_date);
    const endDate = new Date(periodInfo.end_date);
    
    if (periodType === 'day') {
      return `Albums Released on ${startDate.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })}`;
    } else if (periodType === 'week') {
      const startStr = startDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const endStr = endDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      return `Albums Released: Week of ${startStr} - ${endStr}`;
    } else if (periodType === 'month') {
      return `Albums Released: ${startDate.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
      })}`;
    }
    return periodKey || '';
  };

  // Fetch albums and build genre hierarchy
  useEffect(() => {
    const fetchAlbums = async () => {
      if (!date && !periodKey) return;
      
      try {
        setLoading(true);
        let response;
        
        if (periodType && periodKey) {
          // Fetch period data with pagination AND filtering
          const periodResponse = await api.getAlbumsByPeriod(
            periodType as 'day' | 'week' | 'month',
            periodKey,
            page,
            50,
            selectedGenreGroups.length > 0 ? selectedGenreGroups : undefined,
            searchQuery || undefined
          );
          response = { albums: periodResponse.albums };
          setTotalPages(periodResponse.total_pages);
          setTotalAlbums(periodResponse.total);
          setPeriodInfo({ start_date: periodResponse.start_date, end_date: periodResponse.end_date });
        } else if (date) {
          // Fetch single date data (no pagination, client-side filtering)
          response = await api.getAlbumsByDate(date);
          setTotalAlbums(response.albums.length);
        } else {
          return;
        }
        
        setAlbums(response.albums);
        
        // Build genre map from raw genre strings
        const genreMap = new Map<string, number>();
        response.albums.forEach(album => {
          if (album.genre) {
            const genres = album.genre.split(/[\/,;]/).map(g => g.trim());
            genres.forEach(genre => {
              if (genre) genreMap.set(genre, (genreMap.get(genre) || 0) + 1);
            });
          }
        });

        // Create smart genre hierarchy
        const hierarchy = groupGenres(genreMap);
        setGenreHierarchy(hierarchy);
        
        // For single dates, filter client-side; for periods, already filtered by backend
        if (date) {
          setFilteredAlbums(response.albums);
        } else {
          // Backend already filtered, just set the albums
          setFilteredAlbums(response.albums);
        }
      } catch (err) {
        setError('Failed to load albums for this period.');
      } finally {
        setLoading(false);
      }
    };

    fetchAlbums();
  }, [date, periodType, periodKey, page, selectedGenreGroups, searchQuery]);

  // Filter albums using smart genre groups (ONLY for single dates, not periods)
  const filterAlbums = useCallback(() => {
    // For periods, filtering is done on backend, so skip client-side filtering
    if (periodType && periodKey) {
      setFilteredAlbums(albums);
      return;
    }
    
    // For single dates, do client-side filtering
    let filtered = albums;

    // Filter by selected genre groups
    if (selectedGenreGroups.length > 0) {
      filtered = filtered.filter(album => {
        if (!album.genre) return false;
        return albumMatchesGenreGroups(album.genre, selectedGenreGroups);
      });
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(album =>
        album.album_name.toLowerCase().includes(query) ||
        album.band_name.toLowerCase().includes(query) ||
        (album.genre && album.genre.toLowerCase().includes(query))
      );
    }

    setFilteredAlbums(filtered);
  }, [albums, selectedGenreGroups, searchQuery, periodType, periodKey]);

  useEffect(() => {
    // Only run client-side filtering for single dates
    if (date) {
      filterAlbums();
    }
  }, [filterAlbums, date]);
  
  // Debounce search input (only for periods with backend filtering)
  useEffect(() => {
    if (periodType && periodKey) {
      const timer = setTimeout(() => {
        setSearchQuery(searchInput);
      }, 500); // 500ms debounce
      
      return () => clearTimeout(timer);
    } else {
      // For single dates, update immediately (client-side filtering is fast)
      setSearchQuery(searchInput);
    }
  }, [searchInput, periodType, periodKey]);
  
  // Reset to page 1 when filters change (for periods only)
  useEffect(() => {
    if (periodType && periodKey && page !== 1) {
      setPage(1);
    }
  }, [selectedGenreGroups, searchQuery]);

  const getCoverImageUrl = (album: AlbumWithGenres) => {
    if (album.cover_path && album.cover_path !== 'N/A') {
      const baseUrl = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000';
      return `${baseUrl}/${album.cover_path}`;
    }
    return album.cover_art && album.cover_art !== 'N/A' ? album.cover_art : null;
  };

  const handleImageClick = (album: AlbumWithGenres) => {
    const imageUrl = getCoverImageUrl(album);
    if (imageUrl) {
      setImageDialog({
        open: true,
        imageUrl,
        albumName: album.album_name,
        bandName: album.band_name
      });
    }
  };

  const handleCloseImageDialog = () => {
    setImageDialog({
      open: false,
      imageUrl: '',
      albumName: '',
      bandName: ''
    });
  };

  const selectedGenreCount = selectedGenreGroups.length;
  const totalGenreGroups = genreHierarchy?.mainGenres.length || 0;

  if (loading) {
    return (
      <Container maxWidth="xl">
        <Box py={4}>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: '1fr',
                sm: 'repeat(2, 1fr)',
                md: 'repeat(3, 1fr)',
                lg: 'repeat(4, 1fr)',
              },
              gap: 3,
            }}
          >
            {[...Array(8)].map((_, index) => (
              <Card key={index}>
                <Skeleton variant="rectangular" height={200} />
                <CardContent>
                  <Skeleton variant="text" height={30} />
                  <Skeleton variant="text" height={20} />
                </CardContent>
              </Card>
            ))}
          </Box>
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl">
        <Box py={4}>
          <Button startIcon={<ArrowBack />} onClick={() => navigate('/')} sx={{ mb: 2 }}>
            Back to Dates
          </Button>
          <Alert severity="error">{error}</Alert>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl">
      <Box py={4}>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Button startIcon={<ArrowBack />} onClick={() => navigate('/')} variant="outlined">
            Back to Dates
          </Button>
          <Button
            startIcon={<FilterList />}
            onClick={() => setFilterDrawerOpen(true)}
            variant="contained"
            color="secondary"
          >
            Filter ({selectedGenreCount}/{totalGenreGroups})
          </Button>
        </Box>

        <Typography variant="h4" component="h1" gutterBottom>
          🤘 {periodType && periodInfo ? formatPeriodTitle() : `Albums Released on ${date}`}
        </Typography>
        
        <Typography variant="h6" color="text.secondary" sx={{ mb: 4 }}>
          {filteredAlbums.length} of {albums.length} albums
          {totalPages > 1 && ` (Page ${page} of ${totalPages}, ${totalAlbums} total)`}
        </Typography>

        {/* Pagination Top */}
        {totalPages > 1 && (
          <Box display="flex" justifyContent="center" mb={3}>
            <Pagination 
              count={totalPages} 
              page={page} 
              onChange={(_event, value) => {
                setPage(value);
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              color="primary"
              size="large"
              showFirstButton
              showLastButton
            />
          </Box>
        )}

        {/* Albums Grid */}
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: {
              xs: '1fr',
              sm: 'repeat(2, 1fr)',
              md: 'repeat(3, 1fr)',
              lg: 'repeat(4, 1fr)',
            },
            gap: 3,
          }}
        >
          {filteredAlbums.map((album) => (
            <Card 
              key={album.id}
              elevation={3} 
              sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                '&:hover': { transform: 'translateY(-4px)' }
              }}
            >
                {/* Cover */}
                <Box 
                  sx={{ 
                    position: 'relative', 
                    paddingTop: '100%',
                    cursor: getCoverImageUrl(album) ? 'pointer' : 'default',
                    '&:hover': getCoverImageUrl(album) ? {
                      '& .cover-overlay': {
                        opacity: 1
                      }
                    } : {}
                  }}
                  onClick={() => handleImageClick(album)}
                >
                  {getCoverImageUrl(album) ? (
                    <>
                      <CardMedia
                        component="img"
                        sx={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          width: '100%',
                          height: '100%',
                          objectFit: 'cover',
                        }}
                        image={getCoverImageUrl(album) || ''}
                        alt={`${album.album_name} cover`}
                      />
                      <Box
                        className="cover-overlay"
                        sx={{
                          position: 'absolute',
                          top: 0,
                          left: 0,
                          width: '100%',
                          height: '100%',
                          backgroundColor: 'rgba(0, 0, 0, 0.3)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          opacity: 0,
                          transition: 'opacity 0.2s ease-in-out',
                        }}
                      >
                        <Typography variant="body2" color="white" sx={{ fontWeight: 'bold' }}>
                          Click to enlarge
                        </Typography>
                      </Box>
                    </>
                  ) : (
                    <Box sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      bgcolor: 'grey.800',
                    }}>
                      <AlbumIcon sx={{ fontSize: 60, color: 'grey.500' }} />
                    </Box>
                  )}
                </Box>

                {/* Details */}
                <CardContent sx={{ flex: 1 }}>
                  <Typography variant="h6" component="h3" gutterBottom noWrap>
                    {album.album_name}
                  </Typography>
                  <Typography variant="subtitle2" color="primary" gutterBottom noWrap>
                    {album.band_name}
                  </Typography>

                  {/* Genre chips */}
                  {album.genre && (
                    <Box display="flex" flexWrap="wrap" gap={0.5} mb={1}>
                      {album.genre.split(/[\/,;]/).slice(0, 2).map((genre, index) => (
                        <Chip
                          key={index}
                          label={genre.trim()}
                          size="small"
                          sx={{
                            fontSize: '0.7rem',
                            backgroundColor: generateGenreColor(genre.trim()),
                            color: 'white',
                          }}
                        />
                      ))}
                    </Box>
                  )}

                  <Box display="flex" gap={0.5} mb={2}>
                    <Chip icon={<DateRange />} label={album.type} size="small" />
                    {album.country_of_origin && (
                      <Chip icon={<LocationOn />} label={album.country_of_origin} size="small" />
                    )}
                  </Box>

                  {/* Links */}
                  <Box display="flex" gap={1} flexWrap="wrap" alignItems="center">
                    {album.album_url && (
                      <Button 
                        size="small" 
                        startIcon={<OpenInNew />} 
                        href={album.album_url} 
                        target="_blank"
                        variant="outlined"
                      >
                        Metal Archives
                      </Button>
                    )}
                    <PlatformLinks album={album} size="small" />
                  </Box>
                </CardContent>
              </Card>
          ))}
        </Box>

        {/* Pagination Bottom */}
        {totalPages > 1 && (
          <Box display="flex" justifyContent="center" mt={4}>
            <Pagination 
              count={totalPages} 
              page={page} 
              onChange={(_event, value) => {
                setPage(value);
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              color="primary"
              size="large"
              showFirstButton
              showLastButton
            />
          </Box>
        )}

        {/* Filter Drawer */}
        <Drawer
          anchor={isMobile ? "bottom" : "right"}
          open={filterDrawerOpen}
          onClose={() => setFilterDrawerOpen(false)}
          PaperProps={{
            sx: {
              ...(isMobile && {
                borderTopLeftRadius: 16,
                borderTopRightRadius: 16,
                maxHeight: '80vh',
              })
            }
          }}
        >
          <Box sx={{ 
            width: isMobile ? '100vw' : 350, 
            maxWidth: isMobile ? '100vw' : 350,
            p: isMobile ? 2 : 3,
            height: isMobile ? 'auto' : 'auto'
          }}>
            {/* Header with close button for mobile */}
            <Box 
              display="flex" 
              justifyContent="space-between" 
              alignItems="center" 
              mb={2}
              sx={{
                ...(isMobile && {
                  position: 'sticky',
                  top: 0,
                  backgroundColor: 'background.paper',
                  zIndex: 1,
                  pb: 1,
                  borderBottom: 1,
                  borderColor: 'divider'
                })
              }}
            >
              <Typography variant="h6">Filter Albums</Typography>
              {isMobile && (
                <IconButton 
                  onClick={() => setFilterDrawerOpen(false)}
                  size="small"
                >
                  <Close />
                </IconButton>
              )}
            </Box>
            
            <TextField
              fullWidth
              placeholder="Search..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              InputProps={{
                startAdornment: <InputAdornment position="start"><Search /></InputAdornment>,
              }}
              sx={{ 
                mb: 3,
                ...(isMobile && {
                  position: 'sticky',
                  top: isMobile ? '60px' : 0,
                  backgroundColor: 'background.paper',
                  zIndex: 1
                })
              }}
            />

            <Typography variant="subtitle1" mb={2}>
              Genre Groups ({selectedGenreCount}/{totalGenreGroups})
            </Typography>

            {genreHierarchy && (
              <Box sx={{ 
                maxHeight: isMobile ? '60vh' : 400, 
                overflow: 'auto',
                pb: isMobile ? 2 : 0
              }}>
                {/* Main Genre Groups */}
                <Accordion defaultExpanded>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography variant="subtitle2">
                      Main Genres ({genreHierarchy.mainGenres.length})
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <FormGroup>
                      {genreHierarchy.mainGenres.map((group) => (
                        <FormControlLabel
                          key={group.name}
                          control={
                            <Checkbox
                              checked={selectedGenreGroups.includes(group.name)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedGenreGroups(prev => [...prev, group.name]);
                                } else {
                                  setSelectedGenreGroups(prev => prev.filter(g => g !== group.name));
                                }
                              }}
                            />
                          }
                          label={
                            <Box display="flex" alignItems="center" gap={1}>
                              <Badge
                                badgeContent={group.count}
                                color="primary"
                                sx={{
                                  '& .MuiBadge-badge': {
                                    backgroundColor: group.color,
                                    color: 'white'
                                  }
                                }}
                              >
                                <Typography variant="body2">{group.name}</Typography>
                              </Badge>
                              {group.subgenres.length > 1 && (
                                <Typography variant="caption" color="text.secondary">
                                  (+{group.subgenres.length - 1} variants)
                                </Typography>
                              )}
                            </Box>
                          }
                        />
                      ))}
                    </FormGroup>
                  </AccordionDetails>
                </Accordion>

                {/* Quick Actions */}
                <Box 
                  mt={2} 
                  display="flex" 
                  gap={1} 
                  flexWrap="wrap"
                  sx={{
                    position: isMobile ? 'sticky' : 'static',
                    bottom: isMobile ? 0 : 'auto',
                    backgroundColor: isMobile ? 'background.paper' : 'transparent',
                    pt: isMobile ? 2 : 0,
                    pb: isMobile ? 1 : 0,
                    borderTop: isMobile ? 1 : 0,
                    borderColor: 'divider'
                  }}
                >
                  <Button
                    size={isMobile ? "medium" : "small"}
                    onClick={() => setSelectedGenreGroups([])}
                    startIcon={<Clear />}
                    fullWidth={isMobile}
                  >
                    Clear All
                  </Button>
                  <Button
                    size={isMobile ? "medium" : "small"}
                    onClick={() => setSelectedGenreGroups(genreHierarchy.mainGenres.map(g => g.name))}
                    fullWidth={isMobile}
                  >
                    Select All
                  </Button>
                </Box>
              </Box>
            )}
          </Box>
        </Drawer>

        {/* Mobile Filter FAB */}
        {isMobile && (
          <Fab
            color="secondary"
            sx={{ position: 'fixed', bottom: 16, right: 16 }}
            onClick={() => setFilterDrawerOpen(true)}
          >
            <FilterList />
          </Fab>
        )}

        {/* Image Dialog */}
        <Dialog
          open={imageDialog.open}
          onClose={handleCloseImageDialog}
          maxWidth="md"
          fullWidth
          PaperProps={{
            sx: {
              backgroundColor: 'rgba(0, 0, 0, 0.9)',
              backdropFilter: 'blur(10px)',
            }
          }}
        >
          <DialogTitle sx={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            color: 'white',
            pb: 1
          }}>
            <Box>
              <Typography variant="h6" component="div" noWrap>
                {imageDialog.albumName}
              </Typography>
              <Typography variant="subtitle2" color="grey.300">
                {imageDialog.bandName}
              </Typography>
            </Box>
            <IconButton
              onClick={handleCloseImageDialog}
              sx={{ color: 'white' }}
              size="large"
            >
              <Close />
            </IconButton>
          </DialogTitle>
          <DialogContent sx={{ p: 0, display: 'flex', justifyContent: 'center' }}>
            <Box
              component="img"
              src={imageDialog.imageUrl}
              alt={`${imageDialog.albumName} cover`}
              sx={{
                maxWidth: '100%',
                maxHeight: '70vh',
                objectFit: 'contain',
                cursor: 'pointer'
              }}
              onClick={handleCloseImageDialog}
            />
          </DialogContent>
        </Dialog>
      </Box>
    </Container>
  );
};

export default EnhancedAlbumDisplay;
