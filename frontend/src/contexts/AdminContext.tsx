import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { checkAuthStatus, isAuthenticated, getToken, AuthStatus } from '../utils/auth';

interface AdminContextType {
  showAdminButton: boolean;
  isAuthenticated: boolean;
  isFirstTimeSetup: boolean;
  loading: boolean;
  error: string | null;
  refreshAdminStatus: () => Promise<void>;
}

const AdminContext = createContext<AdminContextType | undefined>(undefined);

interface AdminProviderProps {
  children: ReactNode;
}

export const AdminProvider: React.FC<AdminProviderProps> = ({ children }) => {
  const [state, setState] = useState({
    showAdminButton: false,
    isAuthenticated: false,
    isFirstTimeSetup: false,
    loading: true,
    error: null as string | null,
  });

  const refreshAdminStatus = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    refreshAdminStatus();
  }, [refreshAdminStatus]);

  const contextValue: AdminContextType = {
    ...state,
    refreshAdminStatus,
  };

  return (
    <AdminContext.Provider value={contextValue}>
      {children}
    </AdminContext.Provider>
  );
};

export const useAdminContext = (): AdminContextType => {
  const context = useContext(AdminContext);
  if (context === undefined) {
    throw new Error('useAdminContext must be used within an AdminProvider');
  }
  return context;
};
