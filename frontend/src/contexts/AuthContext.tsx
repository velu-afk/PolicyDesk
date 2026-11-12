import React, { createContext, useCallback, useEffect, useState } from 'react';
import { User } from '../types';
import {
  clearStoredAuth,
  getStoredToken,
  setStoredAuth,
  USER_STORAGE_KEY,
} from '../services/api';
import { authService } from '../services/authService';

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (name: string, email: string, password: string) => Promise<User>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const raw = localStorage.getItem(USER_STORAGE_KEY);
      return raw ? (JSON.parse(raw) as User) : null;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    clearStoredAuth();
    setUser(null);
  }, []);

  const refreshProfile = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const verifiedUser = await authService.getMe();
      setStoredAuth(token, verifiedUser);
      setUser(verifiedUser);
    } catch {
      clearStoredAuth();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshProfile();
    const handleUnauthorized = () => logout();
    window.addEventListener('policydesk:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('policydesk:unauthorized', handleUnauthorized);
    };
  }, [refreshProfile, logout]);

  const login = async (email: string, password: string): Promise<User> => {
    const response = await authService.login(email, password);
    setStoredAuth(response.access_token, response.user);
    setUser(response.user);
    return response.user;
  };

  const register = async (name: string, email: string, password: string): Promise<User> => {
    const response = await authService.register(name, email, password);
    setStoredAuth(response.access_token, response.user);
    setUser(response.user);
    return response.user;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: Boolean(user),
        isLoading,
        login,
        register,
        logout,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
