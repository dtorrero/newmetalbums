import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import DateBrowser from './components/DateBrowser';
import AlbumDisplay from './components/AlbumDisplay';
import EnhancedAlbumDisplay from './components/EnhancedAlbumDisplay';
import AdminPanel from './components/AdminPanel';
import AdminLogin from './components/AdminLogin';
import Settings from './components/Settings';
import ProtectedRoute from './components/ProtectedRoute';
import { AdminProvider } from './contexts/AdminContext';

// Create a dark theme for the metal aesthetic
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#ff6b35', // Orange-red for metal aesthetic
    },
    secondary: {
      main: '#ffd23f', // Golden yellow
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
    },
  },
  typography: {
    h3: {
      fontWeight: 700,
    },
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 500,
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AdminProvider>
        <Router>
          <Routes>
            <Route path="/" element={<DateBrowser />} />
            <Route path="/date/:date" element={<EnhancedAlbumDisplay />} />
            <Route path="/date-old/:date" element={<AlbumDisplay />} />
            <Route path="/period/:periodType/:periodKey" element={<EnhancedAlbumDisplay />} />
            <Route path="/admin/login" element={<AdminLogin />} />
            <Route 
              path="/admin" 
              element={
                <ProtectedRoute>
                  <AdminPanel />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/admin/settings" 
              element={
                <ProtectedRoute>
                  <Settings />
                </ProtectedRoute>
              } 
            />
          </Routes>
        </Router>
      </AdminProvider>
    </ThemeProvider>
  );
}

export default App;
