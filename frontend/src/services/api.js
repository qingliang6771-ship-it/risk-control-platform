import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
});

// Request interceptor - add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth APIs
export const authAPI = {
  getLarkLoginUrl: () => api.get('/auth/lark/login'),
  getMe: () => api.get('/auth/me'),
};

// Report APIs
export const reportAPI = {
  generateReport: (query, context = null) =>
    api.post('/report/generate', { query, context }),
  chatStream: async (query, history = null) => {
    const token = localStorage.getItem('token');
    const response = await fetch('/api/report/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query, history }),
    });
    return response;
  },
  getHistory: (limit = 50) => api.get(`/report/history?limit=${limit}`),
  deleteHistory: (logId) => api.delete(`/report/history/${logId}`),
};

// Risk APIs
export const riskAPI = {
  getRiskScore: (userId) => api.get(`/risk/score/${userId}`),
  getFraudDetection: (userId) => api.get(`/risk/fraud/${userId}`),
  getCreditAssessment: (userId) => api.get(`/risk/credit/${userId}`),
  getBehaviorAnalysis: (userId) => api.get(`/risk/behavior/${userId}`),
  getDeviceFingerprint: (userId) => api.get(`/risk/device/${userId}`),
  getAllModels: (userId) => api.post('/risk/all', { user_id: userId }),
};

export default api;
