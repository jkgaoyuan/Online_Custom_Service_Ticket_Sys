import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useUsersStore = defineStore('users', () => {
  const users = ref([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchUsers(params = {}) {
    loading.value = true
    try {
      const response = await api.get('/admin/users', { params })
      users.value = response.data.items
      total.value = response.data.total
    } finally {
      loading.value = false
    }
  }

  async function updateUser(userId, data) {
    const response = await api.put(`/admin/users/${userId}`, data)
    return response.data
  }

  async function resetPassword(userId) {
    const response = await api.post(`/admin/users/${userId}/reset-password`)
    return response.data
  }

  async function createUser(data) {
    const response = await api.post('/auth/users', data)
    return response.data
  }

  return { users, total, loading, fetchUsers, updateUser, resetPassword, createUser }
})
