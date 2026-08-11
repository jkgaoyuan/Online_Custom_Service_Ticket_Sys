import { defineStore } from 'pinia'
import { ref } from 'vue'
import { adminApi } from '@/api/admin'
import { ElMessage } from 'element-plus'

export const useUsersStore = defineStore('users', () => {
  const users = ref([])
  const loading = ref(false)
  const pagination = ref({ total: 0, page: 1, page_size: 20 })
  const filters = ref({ role: '', is_active: '' })

  const fetchUsers = async (params = {}) => {
    loading.value = true
    try {
      const query = {
        page: pagination.value.page,
        page_size: pagination.value.page_size,
        ...params,
      }
      if (filters.value.role) query.role = filters.value.role
      if (filters.value.is_active !== '' && filters.value.is_active !== null && filters.value.is_active !== undefined) {
        query.is_active = filters.value.is_active
      }
      const { data } = await adminApi.listUsers(query)
      users.value = data.items
      pagination.value = { total: data.total, page: data.page, page_size: data.page_size }
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '加载用户列表失败')
    } finally {
      loading.value = false
    }
  }

  const updateUser = async (userId, data) => {
    try {
      const { data: res } = await adminApi.updateUser(userId, data)
      ElMessage.success('用户更新成功')
      return res
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '更新用户失败')
      throw error
    }
  }

  const resetPassword = async (userId) => {
    try {
      const { data: res } = await adminApi.resetPassword(userId)
      ElMessage.success('密码重置成功')
      return res
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '重置密码失败')
      throw error
    }
  }

  return {
    users, loading, pagination, filters,
    fetchUsers, updateUser, resetPassword,
  }
})
