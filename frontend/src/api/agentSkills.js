import api from './index'

export const agentSkillApi = {
  list: () => api.get('/agent-skills'),
  create: (data) => api.post('/agent-skills', data),
  update: (id, data) => api.put(`/agent-skills/${id}`, data),
  delete: (id) => api.delete(`/agent-skills/${id}`),
}
