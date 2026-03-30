import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const ENABLE_DEV_AUTH = process.env.REACT_APP_ENABLE_DEV_AUTH === 'true';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const checkAuth = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/auth/me`, {
        withCredentials: true
      });
      setUser(response.data);
      setError(null);
    } catch (err) {
      setUser(null);
      if (err.response?.status !== 401) {
        setError(err.response?.data?.detail || 'Authentication error');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Skip /me check when returning from OAuth callback — AuthCallback handles it
    if (window.location.pathname === '/auth/callback') {
      setLoading(false);
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const login = () => {
    if (ENABLE_DEV_AUTH) {
      window.location.href = `${BACKEND_URL}/api/dev/login`;
      return;
    }
    window.location.href = `${BACKEND_URL}/api/auth/google`;
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      setUser(null);
      window.location.href = '/';
    }
  };

  const updateUser = (userData) => {
    setUser(userData);
  };

  const value = {
    user,
    loading,
    error,
    login,
    logout,
    checkAuth,
    updateUser,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin' || user?.role === 'super_admin',
    isSuperAdmin: user?.role === 'super_admin',
    needsProfileSetup: user && (!user.phone || !user.accepted_terms)
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
