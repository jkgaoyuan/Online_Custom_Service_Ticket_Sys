import api from './index'

export const slaApi = {
  getRules: () => api.get('/sla/rules'),
  getOverdue: () => api.get('/sla/overdue'),
}
