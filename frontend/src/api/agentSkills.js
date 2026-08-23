import api from './index'

export const agentSkillApi = {
  list: () => api.get('/admin/agent-skills'),
  create: (data) => api.post('/admin/agent-skills', data),
  update: (id, data) => api.put(`/admin/agent-skills/${id}`, data),
  delete: (id) => api.delete(`/admin/agent-skills/${id}`),
}
