import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

let authToken = localStorage.getItem('ujs_token') || null;

export const setAuthToken = (token) => {
  authToken = token;
  if (token) {
    localStorage.setItem('ujs_token', token);
  } else {
    localStorage.removeItem('ujs_token');
  }
};

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  withCredentials: true, // Send and receive HttpOnly cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach Authorization header if token exists
api.interceptors.request.use((config) => {
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

// Centralized response interceptor for consistent error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    let errorMessage = 'An unexpected error occurred.';
    
    if (error.response) {
      errorMessage = error.response.data?.detail || error.response.data?.message || `Server error (${error.response.status})`;
    } else if (error.request) {
      errorMessage = 'Backend server is unreachable. Please verify that the API server is running.';
    } else {
      errorMessage = error.message;
    }

    return Promise.reject({
      ...error,
      customMessage: errorMessage,
      status: error.response?.status,
    });
  }
);

// Health check endpoints
export const checkHealth = async () => {
  const response = await api.get('/api/health');
  return response.data;
};

export const checkDbHealth = async () => {
  const response = await api.get('/api/health/db');
  return response.data;
};

// Authentication endpoints
export const registerApi = async (userData) => {
  const response = await api.post('/api/auth/register', userData);
  return response.data;
};

export const loginApi = async (credentials) => {
  const response = await api.post('/api/auth/login', credentials);
  return response.data;
};

export const getCurrentUserApi = async () => {
  const response = await api.get('/api/auth/me');
  return response.data;
};

export const logoutApi = async () => {
  const response = await api.post('/api/auth/logout');
  return response.data;
};

// Profile endpoints
export const getProfileApi = async () => {
  const response = await api.get('/api/profile');
  return response.data;
};

export const updateProfileApi = async (profileData) => {
  const response = await api.put('/api/profile', profileData);
  return response.data;
};

export default api;
