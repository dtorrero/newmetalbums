import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Typography,
  Box,
  Button,
  TextField,
  Card,
  CardContent,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  FormControlLabel,
  Switch
} from '@mui/material';
import {
  PlayArrow,
  Delete,
  Refresh,
  Home,
  Schedule,
  Storage,
  Warning,
  Logout
} from '@mui/icons-material';
import { Link } from 'react-router-dom';
import { authFetch, logout } from '../utils/auth';

interface ScrapeStatus {
  is_running: boolean;
  current_date: string | null;
  progress: number;
  total: number;
  status_message: string;
  error: string | null;
  start_time: string | null;
  end_time: string | null;
}

interface AdminSummary {
  total_albums: number;
  total_tracks: number;
  dates_count: number;
  dates_data: Array<{
    release_date: string;
    count: number;
  }>;
  database_size_bytes: number;
  scraping_status: ScrapeStatus;
}

const AdminPanel: React.FC = () => {
  const [scrapeDate, setScrapeDate] = useState(() => {
    const today = new Date();
    const dd = String(today.getDate()).padStart(2, '0');
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const yyyy = today.getFullYear();
    return `${dd}-${mm}-${yyyy}`;
  });
  const [downloadCovers, setDownloadCovers] = useState(true);
  const [scrapeStatus, setScrapeStatus] = useState<ScrapeStatus | null>(null);
  const [adminSummary, setAdminSummary] = useState<AdminSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' as 'success' | 'error' | 'info' });
  const [deleteDialog, setDeleteDialog] = useState({ open: false, date: '', type: 'single' as 'single' | 'range' });
  const [forceDialog, setForceDialog] = useState({ open: false, message: '', albumCount: 0 });

  const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000';

  const showSnackbar = (message: string, severity: 'success' | 'error' | 'info' = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const fetchScrapeStatus = useCallback(async () => {
    try {
      const response = await authFetch(`${API_BASE}/api/admin/scrape/status`);
      const data = await response.json();
      setScrapeStatus(data);
    } catch (error) {
      console.error('Error fetching scrape status:', error);
    }
  }, [API_BASE]);

  const fetchAdminSummary = useCallback(async () => {
    try {
      const response = await authFetch(`${API_BASE}/api/admin/summary`);
      const data = await response.json();
      setAdminSummary(data);
    } catch (error) {
      console.error('Error fetching admin summary:', error);
      showSnackbar('Failed to fetch admin summary', 'error');
    }
  }, [API_BASE]);

  const handleScrape = async (forceRescrape = false) => {
    setLoading(true);
    try {
      const response = await authFetch(`${API_BASE}/api/admin/scrape`, {
        method: 'POST',
        body: JSON.stringify({
          date: scrapeDate,
          download_covers: downloadCovers,
          force_rescrape: forceRescrape,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        showSnackbar(data.message, 'success');
        fetchScrapeStatus();
      } else if (response.status === 409 && !forceRescrape) {
        // Handle existing data conflict
        const error = await response.json();
        const message = error.detail || 'Data already exists';
        
        // Extract album count from message (format: "Data already exists for DD-MM-YYYY (X albums)...")
        const countMatch = message.match(/\((\d+) albums?\)/);
        const albumCount = countMatch ? parseInt(countMatch[1]) : 0;
        
        setForceDialog({
          open: true,
          message: message,
          albumCount: albumCount
        });
      } else {
        const error = await response.json();
        showSnackbar(error.detail || 'Scraping failed', 'error');
      }
    } catch (error) {
      showSnackbar('Network error occurred', 'error');
    }
    setLoading(false);
  };

  const handleForceRescrape = () => {
    setForceDialog({ open: false, message: '', albumCount: 0 });
    handleScrape(true);
  };

  const handleDeleteDate = async (date: string) => {
    try {
      const response = await authFetch(`${API_BASE}/api/admin/data/${date}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        const data = await response.json();
        showSnackbar(data.message, 'success');
        fetchAdminSummary();
      } else {
        const error = await response.json();
        showSnackbar(error.detail || 'Delete failed', 'error');
      }
    } catch (error) {
      showSnackbar('Network error occurred', 'error');
    }
    setDeleteDialog({ open: false, date: '', type: 'single' });
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    try {
      // Database stores dates in YYYY-MM-DD format
      const [year, month, day] = dateString.split('-');
      return new Date(parseInt(year), parseInt(month) - 1, parseInt(day)).toLocaleDateString();
    } catch {
      return dateString;
    }
  };

  useEffect(() => {
    fetchScrapeStatus();
    fetchAdminSummary();
    
    // Poll scrape status every 2 seconds when scraping is running
    const interval = setInterval(() => {
      if (scrapeStatus?.is_running) {
        fetchScrapeStatus();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [fetchScrapeStatus, fetchAdminSummary, scrapeStatus?.is_running]);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="h3" component="h1" sx={{ flexGrow: 1 }}>
          🔧 Admin Panel
        </Typography>
        <Button
          onClick={logout}
          startIcon={<Logout />}
          variant="outlined"
          color="secondary"
          sx={{ mr: 1 }}
        >
          Logout
        </Button>
        <Button
          component={Link}
          to="/"
          startIcon={<Home />}
          variant="outlined"
        >
          Back to Albums
        </Button>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3, mb: 3 }}>
        {/* Scraping Section */}
        <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Schedule /> Manual Scraping
              </Typography>
              
              <Box sx={{ mb: 3 }}>
                <TextField
                  fullWidth
                  label="Scrape Date (DD-MM-YYYY)"
                  value={scrapeDate}
                  onChange={(e) => setScrapeDate(e.target.value)}
                  placeholder="13-09-2025"
                  disabled={scrapeStatus?.is_running}
                  sx={{ mb: 2 }}
                />
                
                <FormControlLabel
                  control={
                    <Switch
                      checked={downloadCovers}
                      onChange={(e) => setDownloadCovers(e.target.checked)}
                      disabled={scrapeStatus?.is_running}
                    />
                  }
                  label="Download Album Covers"
                />
              </Box>

              <Button
                fullWidth
                variant="contained"
                startIcon={<PlayArrow />}
                onClick={() => handleScrape()}
                disabled={loading || scrapeStatus?.is_running}
                sx={{ mb: 2 }}
              >
                {scrapeStatus?.is_running ? 'Scraping...' : 'Start Scraping'}
              </Button>

              {/* Scraping Status */}
              {scrapeStatus && (
                <Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Chip
                      label={scrapeStatus.is_running ? 'Running' : 'Idle'}
                      color={scrapeStatus.is_running ? 'primary' : 'default'}
                      size="small"
                    />
                    {scrapeStatus.current_date && (
                      <Chip label={`Date: ${scrapeStatus.current_date}`} size="small" />
                    )}
                  </Box>
                  
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {scrapeStatus.status_message}
                  </Typography>
                  
                  {scrapeStatus.is_running && scrapeStatus.total > 0 && (
                    <LinearProgress
                      variant="determinate"
                      value={(scrapeStatus.progress / scrapeStatus.total) * 100}
                      sx={{ mb: 1 }}
                    />
                  )}
                  
                  {scrapeStatus.error && (
                    <Alert severity="error" sx={{ mt: 1 }}>
                      {scrapeStatus.error}
                    </Alert>
                  )}
                </Box>
              )}
            </CardContent>
          </Card>

        {/* Database Summary */}
        <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Storage /> Database Summary
              </Typography>
              
              {adminSummary && (
                <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                  <Box>
                    <Typography variant="h4" color="primary">
                      {adminSummary.total_albums.toLocaleString()}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Albums
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="h4" color="secondary">
                      {adminSummary.total_tracks.toLocaleString()}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Tracks
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="h4" color="info.main">
                      {adminSummary.dates_count}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Release Dates
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="h6" color="text.primary">
                      {formatBytes(adminSummary.database_size_bytes)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Database Size
                    </Typography>
                  </Box>
                </Box>
              )}
              
              <Button
                fullWidth
                variant="outlined"
                startIcon={<Refresh />}
                onClick={fetchAdminSummary}
                sx={{ mt: 2 }}
              >
                Refresh Summary
              </Button>
            </CardContent>
          </Card>
      </Box>

      {/* Data Management */}
      <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Delete /> Data Management
              </Typography>
              
              {adminSummary?.dates_data && adminSummary.dates_data.length > 0 ? (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Release Date</TableCell>
                        <TableCell align="right">Albums</TableCell>
                        <TableCell align="right">Formatted Date</TableCell>
                        <TableCell align="right">Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {adminSummary.dates_data.slice(0, 10).map((dateData) => (
                        <TableRow key={dateData.release_date}>
                          <TableCell>{dateData.release_date}</TableCell>
                          <TableCell align="right">{dateData.count}</TableCell>
                          <TableCell align="right">{formatDate(dateData.release_date)}</TableCell>
                          <TableCell align="right">
                            <IconButton
                              color="error"
                              onClick={() => setDeleteDialog({ 
                                open: true, 
                                date: dateData.release_date, 
                                type: 'single' 
                              })}
                              size="small"
                            >
                              <Delete />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Alert severity="info">No data found in database</Alert>
              )}
            </CardContent>
          </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, date: '', type: 'single' })}>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Warning color="error" />
          Confirm Delete
        </DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete all data for {deleteDialog.date}? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, date: '', type: 'single' })}>
            Cancel
          </Button>
          <Button 
            color="error" 
            variant="contained"
            onClick={() => handleDeleteDate(deleteDialog.date)}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Force Rescrape Confirmation Dialog */}
      <Dialog open={forceDialog.open} onClose={() => setForceDialog({ open: false, message: '', albumCount: 0 })}>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Warning color="warning" />
          Data Already Exists
        </DialogTitle>
        <DialogContent>
          <Typography sx={{ mb: 2 }}>
            Data already exists for {scrapeDate} with {forceDialog.albumCount} albums.
          </Typography>
          <Typography>
            Do you want to overwrite the existing data? This will replace all current albums for this date.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setForceDialog({ open: false, message: '', albumCount: 0 })}>
            Cancel
          </Button>
          <Button 
            color="warning" 
            variant="contained"
            onClick={handleForceRescrape}
          >
            Overwrite Data
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default AdminPanel;
