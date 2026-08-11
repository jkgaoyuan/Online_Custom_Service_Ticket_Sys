import api from './index'

export const adminApi = {
  listUsers: (params = {}) => api.get('/admin/users', { params }),
}
