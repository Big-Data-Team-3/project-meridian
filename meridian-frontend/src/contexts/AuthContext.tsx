'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import type { User, AuthState, LoginCredentials, RegisterCredentials } from '@/types';
import { apiClient } from '@/lib/api';
import { storage, STORAGE_KEYS } from '@/lib/storage';

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for stored user and token on mount
    const restoreAuth = () => {
      try {
        const storedUser = storage.get<User>(STORAGE_KEYS.USER);
        const token = storage.get<string>(STORAGE_KEYS.TOKEN);
        
        if (storedUser && token) {
          console.log('🔄 Restoring authentication from storage');
          apiClient.setToken(token);
          setUser(storedUser);
          setIsAuthenticated(true);
          console.log('✅ Authentication restored:', { email: storedUser.email, hasToken: !!token });
        } else {
          console.log('ℹ️ No stored authentication found');
          setIsAuthenticated(false);
        }
      } catch (error) {
        console.error('❌ Error restoring authentication:', error);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    restoreAuth();
  }, []);

  const login = useCallback(async (credentials: LoginCredentials): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await apiClient.login(credentials);
      if (response.error || !response.data) {
        throw new Error(response.error || 'Login failed');
      }
      const { user, token } = response.data;
      apiClient.setToken(token);
      storage.set(STORAGE_KEYS.USER, user);
      storage.set(STORAGE_KEYS.TOKEN, token);
      setUser(user);
      setIsAuthenticated(true);
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(async (credentials: RegisterCredentials): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await apiClient.register(credentials);
      if (response.error || !response.data) {
        throw new Error(response.error || 'Registration failed');
      }
      const { user, token } = response.data;
      apiClient.setToken(token);
      storage.set(STORAGE_KEYS.USER, user);
      storage.set(STORAGE_KEYS.TOKEN, token);
      setUser(user);
      setIsAuthenticated(true);
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    try {
      await apiClient.logout();
    } catch (error) {
      // Continue with logout even if API call fails
      console.error('Logout error:', error);
    } finally {
      apiClient.setToken(null);
      storage.clear();
      setUser(null);
      setIsAuthenticated(false);
      setIsLoading(false);
    }
  }, []);

  const loginWithGoogle = useCallback(async (credential: string): Promise<void> => {
    console.log('🔵 Step 5: AuthContext - loginWithGoogle called');
    setIsLoading(true);
    try {
      const response = await apiClient.loginWithGoogle(credential);
      console.log('🔵 Step 6: AuthContext - Received API response');
      
      if (response.error || !response.data) {
        console.error('❌ AuthContext Error:', {
          error: response.error,
          hasData: !!response.data,
          status: response.status,
        });
        throw new Error(response.error || 'Google login failed');
      }
      
      const { user, token } = response.data;
      console.log('🔵 Step 7: AuthContext - Extracting user and token');
      console.log('   User:', { id: user?.id, email: user?.email, name: user?.name });
      console.log('   Token length:', token?.length || 0);
      
      apiClient.setToken(token);
      storage.set(STORAGE_KEYS.USER, user);
      storage.set(STORAGE_KEYS.TOKEN, token);
      setUser(user);
      setIsAuthenticated(true);
      
      console.log('✅ Step 8: AuthContext - Authentication complete');
      console.log('   User stored in state and localStorage');
    } catch (error) {
      console.error('❌ AuthContext - Error in loginWithGoogle:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshUser = useCallback(async (): Promise<void> => {
    // Placeholder for future user refresh logic
    // For now, just re-read from storage
    const storedUser = storage.get<User>(STORAGE_KEYS.USER);
    if (storedUser) {
      setUser(storedUser);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        isLoading,
        login,
        register,
        loginWithGoogle,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

