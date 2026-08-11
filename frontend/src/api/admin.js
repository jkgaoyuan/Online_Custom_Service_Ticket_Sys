import api from './index'

export const adminApi = {
  listUsers: (params = {}) => api.get('/admin/users', { params }),
  getUser: (userId) => api.get(`/admin/users/${userId}`),
  updateUser: (userId, data) => api.put(`/admin/users/${userId}`, data),
  resetPassword: (userId) => api.post(`/admin/users/${userId}/reset-password`),
}
