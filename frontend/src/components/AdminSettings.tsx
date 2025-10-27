import React, { useState, useEffect } from 'react';
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
  LinearProgress,
  Divider,
  Grid,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  InputAdornment,
} from '@mui/material';
import {
  Save,
  Refresh,
  Delete,
  Storage,
  Info,
  Home,
  Logout,
} from '@mui/icons-material';
import { Link, useNavigate } from 'react-router-dom';
import { authFetch, logout } from '../utils/auth';

interface CacheStats {
  total_size_bytes: number;
  total_size_mb: number;
  total_size_gb: number;
  max_size_bytes: number;
  max_size_gb: number;
  usage_percent: number;
  file_count: number;
  available_bytes: number;
  available_gb: number;
}

interface CacheSettings {
  youtube_cache_max_size_gb: number;
}

const AdminSettings: React.FC = () => {
  const navigate = useNavigate();
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [cacheSettings, setCacheSettings] = useState<CacheSettings>({ youtube_cache_max_size_gb: 5.0 });
  const [originalSettings, setOriginalSettings] = useState<CacheSettings>({ youtube_cache_max_size_gb: 5.0 });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' as 'success' | 'error' | 'info' });
  const [clearCacheDialog, setClearCacheDialog] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000';

  const showSnackbar = (message: string, severity: 'success' | 'error' | 'info' = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const fetchCacheStats = async () => {
    try {
      const response = await authFetch(`${API_BASE}/api/admin/cache/stats`);
      if (response.ok) {
        const data = await response.json();
        setCacheStats(data.stats);
      }
    } catch (error) {
      console.error('Error fetching cache stats:', error);
    }
  };

  const fetchCacheSettings = async () => {
    setLoading(true);
    try {
      const response = await authFetch(`${API_BASE}/api/admin/settings/cache`);
      if (response.ok) {
        const data = await response.json();
        setCacheSettings(data);
        setOriginalSettings(data);
        setHasUnsavedChanges(false);
      }
    } catch (error) {
      console.error('Error fetching cache settings:', error);
      showSnackbar('Failed to load settings', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      const response = await authFetch(`${API_BASE}/api/admin/settings/cache`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cacheSettings),
      });

      if (response.ok) {
        setOriginalSettings(cacheSettings);
        setHasUnsavedChanges(false);
        showSnackbar('Settings saved successfully', 'success');
        // Refresh stats to show new limits
        await fetchCacheStats();
      } else {
        const error = await response.json();
        showSnackbar(error.detail || 'Failed to save settings', 'error');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      showSnackbar('Failed to save settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleClearCache = async () => {
    try {
      const response = await authFetch(`${API_BASE}/api/admin/cache/clear`, {
        method: 'POST',
      });

      if (response.ok) {
        showSnackbar('Cache cleared successfully', 'success');
        setClearCacheDialog(false);
        await fetchCacheStats();
      } else {
        showSnackbar('Failed to clear cache', 'error');
      }
    } catch (error) {
      console.error('Error clearing cache:', error);
      showSnackbar('Failed to clear cache', 'error');
    }
  };

  const handleCacheSizeChange = (value: string) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue) && numValue >= 0 && numValue <= 100) {
      setCacheSettings({ ...cacheSettings, youtube_cache_max_size_gb: numValue });
      setHasUnsavedChanges(numValue !== originalSettings.youtube_cache_max_size_gb);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/admin/login');
  };

  useEffect(() => {
    fetchCacheSettings();
    fetchCacheStats();
    
    // Refresh stats every 30 seconds
    const interval = setInterval(fetchCacheStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Settings
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            component={Link}
            to="/admin"
            startIcon={<Home />}
            variant="outlined"
          >
            Admin Panel
          </Button>
          <Button
            onClick={handleLogout}
            startIcon={<Logout />}
            variant="outlined"
            color="error"
          >
            Logout
          </Button>
        </Box>
      </Box>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* YouTube Cache Settings */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Storage sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="h6">YouTube Cache Settings</Typography>
          </Box>
          <Divider sx={{ mb: 3 }} />

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* Cache Size Setting */}
            <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
              <Box sx={{ flex: 1 }}>
              <TextField
                label="Maximum Cache Size"
                type="number"
                value={cacheSettings.youtube_cache_max_size_gb}
                onChange={(e) => handleCacheSizeChange(e.target.value)}
                fullWidth
                inputProps={{ min: 0.1, max: 100, step: 0.5 }}
                InputProps={{
                  endAdornment: <InputAdornment position="end">GB</InputAdornment>,
                }}
                helperText="Set maximum cache size (0.1 - 100 GB). Supports decimals like 2.5"
              />
              </Box>

              {/* Cache Statistics */}
              {cacheStats && (
                <Box sx={{ flex: 1 }}>
                <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Current Usage
                  </Typography>
                  <Typography variant="h5" gutterBottom>
                    {cacheStats.total_size_gb.toFixed(2)} GB / {cacheStats.max_size_gb.toFixed(2)} GB
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min(cacheStats.usage_percent, 100)}
                    sx={{ mb: 1, height: 8, borderRadius: 1 }}
                    color={cacheStats.usage_percent > 90 ? 'error' : cacheStats.usage_percent > 70 ? 'warning' : 'primary'}
                  />
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      {cacheStats.file_count} files
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {cacheStats.usage_percent.toFixed(1)}% used
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Available: {cacheStats.available_gb.toFixed(2)} GB
                  </Typography>
                </Box>
                </Box>
              )}
            </Box>

            {/* Info Box */}
            <Box>
              <Alert severity="info" icon={<Info />}>
                <Typography variant="body2">
                  <strong>How it works:</strong> The cache uses LRU (Least Recently Used) eviction. 
                  When the cache is full, the oldest accessed files are automatically deleted to make room for new downloads.
                  Frequently played songs stay in cache longer.
                </Typography>
              </Alert>
            </Box>

            {/* Action Buttons */}
            <Box>
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'space-between' }}>
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <Button
                    variant="contained"
                    startIcon={<Save />}
                    onClick={handleSaveSettings}
                    disabled={!hasUnsavedChanges || saving}
                  >
                    {saving ? 'Saving...' : 'Save Settings'}
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<Refresh />}
                    onClick={fetchCacheStats}
                  >
                    Refresh Stats
                  </Button>
                </Box>
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<Delete />}
                  onClick={() => setClearCacheDialog(true)}
                >
                  Clear Cache
                </Button>
              </Box>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Future Settings Sections - Placeholder */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            More Settings Coming Soon
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Additional settings will be added here:
          </Typography>
          <Box component="ul" sx={{ mt: 1 }}>
            <Typography component="li" variant="body2" color="text.secondary">
              Automatic scraping schedule
            </Typography>
            <Typography component="li" variant="body2" color="text.secondary">
              Verification settings (similarity threshold, delay)
            </Typography>
            <Typography component="li" variant="body2" color="text.secondary">
              Platform link visibility preferences
            </Typography>
            <Typography component="li" variant="body2" color="text.secondary">
              Database maintenance options
            </Typography>
          </Box>
        </CardContent>
      </Card>

      {/* Clear Cache Confirmation Dialog */}
      <Dialog open={clearCacheDialog} onClose={() => setClearCacheDialog(false)}>
        <DialogTitle>Clear YouTube Cache?</DialogTitle>
        <DialogContent>
          <Typography>
            This will delete all cached YouTube audio files ({cacheStats?.file_count || 0} files, {cacheStats?.total_size_gb.toFixed(2) || 0} GB).
            Songs will need to be re-downloaded when played again.
          </Typography>
          <Typography sx={{ mt: 2 }} color="warning.main">
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setClearCacheDialog(false)}>Cancel</Button>
          <Button onClick={handleClearCache} color="error" variant="contained">
            Clear Cache
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default AdminSettings;
