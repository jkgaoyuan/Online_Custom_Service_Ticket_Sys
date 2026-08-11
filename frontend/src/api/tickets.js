import api from './index'

export const ticketApi = {
  create: (data) => api.post('/tickets', data),
  list: (params) => api.get('/tickets', { params }),
  get: (id) => api.get(`/tickets/${id}`),
  reply: (id, data) => api.post(`/tickets/${id}/replies`, data),
  updateStatus: (id, status) => api.post(`/tickets/${id}/status`, { status }),
  assign: (id, assigneeId) => api.post(`/tickets/${id}/assign`, { assignee_id: assigneeId }),
  submitSatisfaction: (id, data) => api.post(`/tickets/${id}/satisfaction`, data),
  transfer: (id, data) => api.post(`/tickets/${id}/transfer`, data),
  assist: (id, data) => api.post(`/tickets/${id}/assist`, data),
}

export const replyApi = {
  list: (ticketId) => api.get(`/tickets/${ticketId}/replies`),
}
