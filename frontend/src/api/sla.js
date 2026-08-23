import api from './index'

export const slaApi = {
  getRules: () => api.get('/admin/sla/rules'),
  getOverdue: () => api.get('/admin/sla/overdue'),
}
