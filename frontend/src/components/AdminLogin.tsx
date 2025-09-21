import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  TextField,
  Alert,
  CircularProgress,
  FormControlLabel,
  Checkbox,
  Divider
} from '@mui/material';
import {
  Security,
  VpnKey,
  AdminPanelSettings
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { checkAuthStatus, setupPassword, login, isAuthenticated, AuthStatus } from '../utils/auth';

const AdminLogin: React.FC = () => {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    // Check if already authenticated
    if (isAuthenticated()) {
      navigate('/admin');
      return;
    }

    // Check auth status
    checkAuthStatus().then(setAuthStatus).catch(console.error);
  }, [navigate]);

  const handleSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      const response = await setupPassword(password);
      if (response.success) {
        setSuccess('Admin password set successfully! Redirecting...');
        setTimeout(() => navigate('/admin'), 1500);
      } else {
        setError(response.message || 'Setup failed');
      }
    } catch (error) {
      setError('Network error occurred');
    }
    setLoading(false);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!password) {
      setError('Please enter your password');
      return;
    }

    setLoading(true);
    try {
      const response = await login(password, rememberMe);
      if (response.success) {
        setSuccess('Login successful! Redirecting...');
        setTimeout(() => navigate('/admin'), 1000);
      } else {
        setError(response.message || 'Login failed');
      }
    } catch (error) {
      setError('Network error occurred');
    }
    setLoading(false);
  };

  if (!authStatus) {
    return (
      <Container maxWidth="sm" sx={{ py: 8 }}>
        <Box display="flex" justifyContent="center">
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  const isSetup = authStatus.setup_required;

  return (
    <Container maxWidth="sm" sx={{ py: 8 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <AdminPanelSettings sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
          <Typography variant="h4" component="h1" gutterBottom>
            {isSetup ? 'Admin Setup' : 'Admin Login'}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {isSetup 
              ? 'Set up your admin password to secure the admin panel'
              : 'Enter your password to access the admin panel'
            }
          </Typography>
        </Box>

        {authStatus.locked && (
          <Alert severity="error" sx={{ mb: 3 }}>
            Account is temporarily locked due to too many failed login attempts. Please try again later.
          </Alert>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 3 }}>
            {success}
          </Alert>
        )}

        <form onSubmit={isSetup ? handleSetup : handleLogin}>
          <TextField
            fullWidth
            type="password"
            label={isSetup ? 'New Admin Password' : 'Admin Password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading || authStatus.locked}
            sx={{ mb: 3 }}
            InputProps={{
              startAdornment: <VpnKey sx={{ mr: 1, color: 'text.secondary' }} />
            }}
            helperText={isSetup ? 'Must be at least 8 characters long' : ''}
          />

          {isSetup && (
            <TextField
              fullWidth
              type="password"
              label="Confirm Password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={loading}
              sx={{ mb: 3 }}
              InputProps={{
                startAdornment: <Security sx={{ mr: 1, color: 'text.secondary' }} />
              }}
            />
          )}

          {!isSetup && (
            <FormControlLabel
              control={
                <Checkbox
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  disabled={loading}
                />
              }
              label="Remember me for 7 days"
              sx={{ mb: 2 }}
            />
          )}

          <Button
            type="submit"
            fullWidth
            variant="contained"
            size="large"
            disabled={loading || authStatus.locked}
            sx={{ mb: 3 }}
          >
            {loading ? (
              <CircularProgress size={24} />
            ) : (
              isSetup ? 'Set Up Admin Password' : 'Login to Admin Panel'
            )}
          </Button>
        </form>

        <Divider sx={{ my: 3 }} />

        <Box sx={{ textAlign: 'center' }}>
          <Button
            variant="text"
            onClick={() => navigate('/')}
            sx={{ color: 'text.secondary' }}
          >
            ← Back to Albums
          </Button>
        </Box>

        {authStatus.last_login && !isSetup && (
          <Box sx={{ mt: 3, textAlign: 'center' }}>
            <Typography variant="caption" color="text.secondary">
              Last login: {new Date(authStatus.last_login).toLocaleString()}
            </Typography>
          </Box>
        )}
      </Paper>
    </Container>
  );
};

export default AdminLogin;
