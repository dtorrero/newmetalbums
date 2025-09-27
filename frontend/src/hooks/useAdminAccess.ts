import { useState, useEffect } from 'react';
import { checkAuthStatus, isAuthenticated, getToken, AuthStatus } from '../utils/auth';

interface AdminAccessState {
  showAdminButton: boolean;
  isAuthenticated: boolean;
  isFirstTimeSetup: boolean;
  loading: boolean;
  error: string | null;
}

/**
 * Custom hook to manage admin button visibility
 * Shows admin button only if:
 * 1. First time setup (no admin password set)
 * 2. User is authenticated as admin (has valid token)
 */
export const useAdminAccess = (): AdminAccessState => {
  const [state, setState] = useState<AdminAccessState>({
    showAdminButton: false,
    isAuthenticated: false,
    isFirstTimeSetup: false,
    loading: true,
    error: null,
  });

  useEffect(() => {
    const checkAdminAccess = async () => {
      try {
        setState(prev => ({ ...prev, loading: true, error: null }));

        // Check authentication status from backend
        const authStatus: AuthStatus = await checkAuthStatus();
        const isFirstTime = authStatus.setup_required;

        // Check if user has valid admin token using existing auth system
        const userIsAuthenticated = isAuthenticated() && getToken() !== null;

        // Show admin button if first time setup OR user is authenticated
        const showAdminButton = isFirstTime || userIsAuthenticated;

        setState({
          showAdminButton,
          isAuthenticated: userIsAuthenticated,
          isFirstTimeSetup: isFirstTime,
          loading: false,
          error: null,
        });

      } catch (error) {
        console.error('Error checking admin access:', error);
        setState(prev => ({
          ...prev,
          loading: false,
          error: 'Failed to check admin access',
        }));
      }
    };

    checkAdminAccess();
  }, []);

  return state;
};

// Re-export auth utilities for convenience
export { setToken as setAdminToken, clearToken as clearAdminToken, getToken as getAdminToken } from '../utils/auth';
