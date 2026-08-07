import api from './index'

export const categoryApi = {
  list: () => api.get('/categories'),
}
