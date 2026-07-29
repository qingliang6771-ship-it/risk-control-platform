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
  getModels: () => api.get('/report/models'),
  generateReport: (query, context = null, model = null) =>
    api.post('/report/generate', { query, context, model }),
  chatStream: async (query, sessionId = null, history = null, model = null) => {
    const token = localStorage.getItem('token');
    const response = await fetch('/api/report/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query, session_id: sessionId, history, model }),
    });
    return response;
  },

  // Session APIs
  listSessions: () => api.get('/report/sessions'),
  createSession: (title = '新对话', projectId = '105') =>
    api.post('/report/sessions', { title, project_id: projectId }),
  getSession: (sessionId) => api.get(`/report/sessions/${sessionId}`),
  updateSession: (sessionId, data) => api.put(`/report/sessions/${sessionId}`, data),
  deleteSession: (sessionId) => api.delete(`/report/sessions/${sessionId}`),
  // Legacy history
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

// Ban (封禁管理) APIs
export const banAPI = {
  getOptions: () => api.get('/bans/options'),
  list: (params = {}) => api.get('/bans', { params }),
  create: (data) => api.post('/bans', data),
  batchUpload: (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return api.post('/bans/batch', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  fetchFundInfo: (data) => api.post('/bans/fund-info', data),
  downloadTemplate: () => api.get('/bans/template', { responseType: 'blob' }),
};

// Admin (权限管理) APIs
export const adminAPI = {

  listModules: () => api.get('/admin/modules'),
  listUsers: (q = '') => api.get('/admin/users', { params: { q } }),
  addUser: (data) => api.post('/admin/users', data),
  updatePermissions: (userId, data) =>
    api.put(`/admin/users/${userId}/permissions`, data),
};

export default api;

