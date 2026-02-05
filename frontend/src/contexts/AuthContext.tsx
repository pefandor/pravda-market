/**
 * AuthContext - manages authentication state globally
 * Handles Telegram initData and provides auth methods
 */

import { createContext, useContext, useState, useEffect, ReactNode, FC } from 'react';
import { initData } from '@tma.js/sdk-react';

interface AuthContextType {
  isAuthenticated: boolean;
  initDataRaw: string | null;
  error: string | null;
  userId: number | null;
  username: string | null;
  firstName: string | null;
  isLoading: boolean;
  logout: () => void;
  refreshAuth: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: FC<AuthProviderProps> = ({ children }) => {
  const [initDataRaw, setInitDataRaw] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [userId, setUserId] = useState<number | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [firstName, setFirstName] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const extractAuthData = () => {
    try {
      setIsLoading(true);
      setError(null);

      // Get raw init data from Telegram SDK
      const rawData = initData.raw();

      if (!rawData || typeof rawData !== 'string') {
        // In development mode, allow unauthenticated access
        if (import.meta.env.DEV) {
          console.warn('⚠️ Development mode: No Telegram initData available');
          setInitDataRaw(null);
          setUserId(null);
          setUsername(null);
          setFirstName(null);
          setIsLoading(false);
          return;
        }

        // In production, auth is required
        throw new Error('Failed to retrieve Telegram authentication data');
      }

      setInitDataRaw(rawData);

      // Extract user data from initData
      const state = initData.state();
      if (state?.user) {
        setUserId(state.user.id);
        setUsername(state.user.username || null);
        setFirstName(state.user.first_name || null);
      }
    } catch (err) {
      console.error('Auth error:', err);
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    extractAuthData();
  }, []);

  const logout = () => {
    setInitDataRaw(null);
    setUserId(null);
    setUsername(null);
    setFirstName(null);
    setError(null);
  };

  const refreshAuth = () => {
    extractAuthData();
  };

  const value: AuthContextType = {
    isAuthenticated: !!initDataRaw,
    initDataRaw,
    error,
    userId,
    username,
    firstName,
    isLoading,
    logout,
    refreshAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

/**
 * Hook to use auth context
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
