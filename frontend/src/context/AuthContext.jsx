import React, { useState, useEffect } from 'react';
import { AuthContext } from './auth-context-def';
import {
  loginApi,
  registerApi,
  getCurrentUserApi,
  logoutApi,
  setAuthToken
} from '../services/api';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore session on app load
  useEffect(() => {
    let ignore = false;

    const restoreSession = async () => {
      try {
        const currentUser = await getCurrentUserApi();
        if (!ignore) {
          setUser(currentUser);
        }
      } catch {
        // Not authenticated or token expired - clear local token
        if (!ignore) {
          setUser(null);
          setAuthToken(null);
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    };

    restoreSession();

    return () => {
      ignore = true;
    };
  }, []);

  const login = async (email, password) => {
    const data = await loginApi({ email, password });
    if (data.access_token) {
      setAuthToken(data.access_token);
    }
    setUser(data.user);
    return data.user;
  };

  const register = async (fullName, email, password) => {
    await registerApi({ full_name: fullName, email, password });
    return await login(email, password);
  };

  const logout = async () => {
    try {
      await logoutApi();
    } catch {
      // Ignore API logout errors and clear local state regardless
    } finally {
      setAuthToken(null);
      setUser(null);
    }
  };

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthProvider;
