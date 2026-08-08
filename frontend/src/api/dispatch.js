import api from './index'

export const dispatchApi = {
  suggest: (ticketId) => api.post(`/tickets/${ticketId}/suggest-assignees`),
  autoAssign: (ticketId) => api.post(`/tickets/${ticketId}/auto-assign`),
  assign: (ticketId, assigneeId) => api.post(`/tickets/${ticketId}/assign`, { assignee_id: assigneeId }),
}
