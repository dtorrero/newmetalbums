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
} from '@mui/material';
import { Save, Refresh, ArrowBack } from '@mui/icons-material';
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

      <Box mt={3}>
        <Alert severity="info">
          <Typography variant="body2">
            <strong>Note:</strong> Changes will take effect immediately for all users. Previously
            scraped data will retain all platform links in the database, but only enabled platforms
            will be displayed in the user interface.
          </Typography>
        </Alert>
      </Box>
    </Container>
  );
};

export default Settings;
