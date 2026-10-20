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

export const uploadResumeApi = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/api/profile/resume', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const confirmSkillsApi = async (skills) => {
  const response = await api.post('/api/profile/confirm-skills', { skills });
  return response.data;
};

// Job Discovery & Records endpoints
export const getJobsApi = async (params = {}) => {
  const response = await api.get('/api/jobs', { params });
  return response.data;
};

export const getJobDetailsApi = async (jobId) => {
  const response = await api.get(`/api/jobs/${jobId}`);
  return response.data;
};

export const createJobApi = async (jobData) => {
  const response = await api.post('/api/jobs', jobData);
  return response.data;
};

export const importJobUrlApi = async (urlData) => {
  const response = await api.post('/api/jobs/import-url', urlData);
  return response.data;
};

export const updateJobApi = async (jobId, jobData) => {
  const response = await api.put(`/api/jobs/${jobId}`, jobData);
  return response.data;
};

export const deleteJobApi = async (jobId) => {
  const response = await api.delete(`/api/jobs/${jobId}`);
  return response.data;
};

// Explainable Job Matching endpoints
export const matchJobApi = async (jobId) => {
  const response = await api.post(`/api/jobs/${jobId}/match`);
  return response.data;
};

export const getRankedJobMatchesApi = async () => {
  const response = await api.get('/api/jobs/matches');
  return response.data;
};

// Verification Signals endpoints
export const verifyJobApi = async (jobId) => {
  const response = await api.post(`/api/jobs/${jobId}/verify`);
  return response.data;
};

export const getJobVerificationApi = async (jobId) => {
  const response = await api.get(`/api/jobs/${jobId}/verification`);
  return response.data;
};

// Application Tracking & Pipeline endpoints
export const getApplicationsApi = async (params = {}) => {
  const response = await api.get('/api/v1/applications', { params });
  return response.data;
};

export const getPipelineMetricsApi = async () => {
  const response = await api.get('/api/v1/applications/metrics');
  return response.data;
};

export const getApplicationDetailsApi = async (applicationId) => {
  const response = await api.get(`/api/v1/applications/${applicationId}`);
  return response.data;
};

export const createApplicationApi = async (data) => {
  const response = await api.post('/api/v1/applications', data);
  return response.data;
};

export const updateApplicationStageApi = async (applicationId, stageData) => {
  const response = await api.patch(`/api/v1/applications/${applicationId}/stage`, stageData);
  return response.data;
};

export const updateApplicationDetailsApi = async (applicationId, data) => {
  const response = await api.patch(`/api/v1/applications/${applicationId}`, data);
  return response.data;
};

export const deleteApplicationApi = async (applicationId) => {
  const response = await api.delete(`/api/v1/applications/${applicationId}`);
  return response.data;
};

export const trackJobApplyApi = async (jobId, data = {}) => {
  const response = await api.post(`/api/jobs/${jobId}/apply`, data);
  return response.data;
};

// Email Intelligence & Ingestion endpoints
export const getEmailsApi = async (params = {}) => {
  const response = await api.get('/api/v1/emails', { params });
  return response.data;
};

export const ingestEmailApi = async (data) => {
  const response = await api.post('/api/v1/emails/ingest', data);
  return response.data;
};

export const linkEmailToApplicationApi = async (emailId, applicationId) => {
  const response = await api.post(`/api/v1/emails/${emailId}/link-application`, {
    application_id: applicationId,
  });
  return response.data;
};

export default api;



