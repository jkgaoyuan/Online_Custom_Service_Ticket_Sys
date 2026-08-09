import api from './index'

export const reportApi = {
  overview: () => api.get('/admin/reports/overview'),
  agentPerformance: (params) => api.get('/admin/reports/agent-performance', { params }),
  categoryDistribution: (params) => api.get('/admin/reports/category-distribution', { params }),
  trend: (params) => api.get('/admin/reports/trend', { params }),
  satisfaction: (params) => api.get('/admin/reports/satisfaction', { params }),
  export: (payload) => api.post('/admin/reports/export', payload),
  exportStatus: (taskId) => api.get(`/admin/reports/export/${taskId}`),
}
