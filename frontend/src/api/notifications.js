import api from './index'

export const listNotifications = (limit = 50) => api.get('/notifications', { params: { limit } })
export const markRead = (id) => api.post(`/notifications/${id}/read`)
export const markAllRead = () => api.post('/notifications/read-all')
