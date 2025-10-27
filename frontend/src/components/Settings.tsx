import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Switch,
  FormControlLabel,
  FormGroup,
  Button,
  Alert,
  CircularProgress,
  Divider,
  Container,
  TextField,
  InputAdornment,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { Save, Refresh, ArrowBack, Storage, Delete, Info } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { authFetch } from '../utils/auth';

interface PlatformSetting {
  visible: boolean;
  label: string;
  patterns: string[];
}

interface PlatformSettings {
  [key: string]: PlatformSetting;
}

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

const PLATFORM_ICONS: { [key: string]: string } = {
  bandcamp: '🎵',
  youtube: '▶️',
  spotify: '🎧',
  discogs: '💿',
  lastfm: '📻',
  soundcloud: '☁️',
  tidal: '🌊',
};

const Settings: React.FC = () => {
  const navigate = useNavigate();
  const [settings, setSettings] = useState<PlatformSettings>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Cache settings state
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [cacheSettings, setCacheSettings] = useState<CacheSettings>({ youtube_cache_max_size_gb: 5.0 });
  const [originalCacheSettings, setOriginalCacheSettings] = useState<CacheSettings>({ youtube_cache_max_size_gb: 5.0 });
  const [clearCacheDialog, setClearCacheDialog] = useState(false);

  // Get API base URL - in production, nginx proxies everything, so use relative URLs
  const getApiBase = () => {
    if (process.env.NODE_ENV === 'production' || process.env.REACT_APP_API_URL === '') {
      return ''; // Use relative URLs - nginx will proxy to backend
    }
    return 'http://127.0.0.1:8000'; // Development mode - direct backend access
  };
  
  const API_BASE = getApiBase();

  useEffect(() => {
    loadSettings();
    loadCacheSettings();
    loadCacheStats();
    
    // Refresh cache stats every 30 seconds
    const interval = setInterval(loadCacheStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await authFetch(`${API_BASE}/api/admin/settings/platform-links`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error('Non-JSON response:', text);
        throw new Error('Server returned non-JSON response. Check console for details.');
      }
      
      const data = await response.json();
      
      if (!data.settings) {
        throw new Error('Invalid response format: missing settings');
      }
      
      setSettings(data.settings);
    } catch (err: any) {
      console.error('Error loading settings:', err);
      setError(err.message || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = (platform: string) => {
    setSettings(prev => ({
      ...prev,
      [platform]: {
        ...prev[platform],
        visible: !prev[platform].visible
      }
    }));
    // Clear success message when making changes
    setSuccess(null);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      
      const settingsToSave: { [key: string]: { visible: boolean } } = {};
      
      Object.entries(settings).forEach(([platform, data]) => {
        settingsToSave[platform] = { visible: data.visible };
      });

      const response = await authFetch(`${API_BASE}/api/admin/settings/platform-links`, {
        method: 'PUT',
        body: JSON.stringify(settingsToSave)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save settings');
      }
      
      setSuccess('Settings saved successfully!');
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const loadCacheStats = async () => {
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

  const loadCacheSettings = async () => {
    try {
      const response = await authFetch(`${API_BASE}/api/admin/settings/cache`);
      if (response.ok) {
        const data = await response.json();
        setCacheSettings(data);
        setOriginalCacheSettings(data);
      }
    } catch (error) {
      console.error('Error fetching cache settings:', error);
    }
  };

  const handleSaveCacheSettings = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      
      const response = await authFetch(`${API_BASE}/api/admin/settings/cache`, {
        method: 'PUT',
        body: JSON.stringify(cacheSettings),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save cache settings');
      }
      
      setOriginalCacheSettings(cacheSettings);
      setSuccess('Cache settings saved successfully!');
      await loadCacheStats();
      
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save cache settings');
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
        setSuccess('Cache cleared successfully!');
        setClearCacheDialog(false);
        await loadCacheStats();
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError('Failed to clear cache');
      }
    } catch (error) {
      console.error('Error clearing cache:', error);
      setError('Failed to clear cache');
    }
  };

  const handleCacheSizeChange = (value: string) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue) && numValue >= 0 && numValue <= 100) {
      setCacheSettings({ ...cacheSettings, youtube_cache_max_size_gb: numValue });
      setSuccess(null);
    }
  };

  const hasCacheChanges = cacheSettings.youtube_cache_max_size_gb !== originalCacheSettings.youtube_cache_max_size_gb;

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center" gap={2}>
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate('/admin')}
            variant="outlined"
          >
            Back to Admin
          </Button>
          <Typography variant="h4" component="h1">
            Platform Link Settings
          </Typography>
        </Box>
        <Button
          startIcon={<Refresh />}
          onClick={loadSettings}
          disabled={saving}
        >
          Reload
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Platform Link Visibility
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Control which music platform links are displayed on album pages. Disabled platforms
            will still be scraped but won't be shown to users.
          </Typography>

          <Divider sx={{ my: 2 }} />

          <FormGroup>
            {Object.entries(settings).map(([platform, data]) => (
              <Box key={platform} sx={{ mb: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={data.visible}
                      onChange={() => handleToggle(platform)}
                      color="primary"
                    />
                  }
                  label={
                    <Box display="flex" alignItems="center" gap={1}>
                      <span style={{ fontSize: '1.5rem' }}>
                        {PLATFORM_ICONS[platform] || '🔗'}
                      </span>
                      <Typography variant="body1">
                        {data.label}
                      </Typography>
                    </Box>
                  }
                />
                <Box ml={7} mt={0.5}>
                  <Typography variant="caption" color="text.secondary">
                    Patterns: {data.patterns.join(', ')}
                  </Typography>
                </Box>
              </Box>
            ))}
          </FormGroup>

          <Divider sx={{ my: 3 }} />

          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="body2" color="text.secondary">
              {Object.values(settings).filter(s => s.visible).length} of {Object.keys(settings).length} platforms enabled
            </Typography>
            <Button
              variant="contained"
              startIcon={<Save />}
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* YouTube Cache Settings */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Box display="flex" alignItems="center" mb={2}>
            <Storage sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="h6">YouTube Cache Settings</Typography>
          </Box>
          <Divider sx={{ mb: 3 }} />

          <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3, mb: 3 }}>
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

          <Alert severity="info" icon={<Info />} sx={{ mb: 3 }}>
            <Typography variant="body2">
              <strong>How it works:</strong> The cache uses LRU (Least Recently Used) eviction. 
              When the cache is full, the oldest accessed files are automatically deleted to make room for new downloads.
              Frequently played songs stay in cache longer.
            </Typography>
          </Alert>

          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Box display="flex" gap={2}>
              <Button
                variant="contained"
                startIcon={<Save />}
                onClick={handleSaveCacheSettings}
                disabled={!hasCacheChanges || saving}
              >
                {saving ? 'Saving...' : 'Save Cache Settings'}
              </Button>
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={loadCacheStats}
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
        </CardContent>
      </Card>

      <Box mt={3}>
        <Alert severity="info">
          <Typography variant="body2">
            <strong>Note:</strong> Changes will take effect immediately for all users. Previously
            scraped data will retain all platform links in the database, but only enabled platforms
            will be displayed in the user interface.
          </Typography>
        </Alert>
      </Box>

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
    </Container>
  );
};

export default Settings;
