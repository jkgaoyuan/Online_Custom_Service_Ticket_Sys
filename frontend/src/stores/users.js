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
      const { data } = await adminApi.listUsers({
        page: pagination.value.page,
        page_size: pagination.value.page_size,
        ...filters.value,
        ...params,
      })
      users.value = data.items
      pagination.value = { total: data.total, page: data.page, page_size: data.page_size }
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '加载用户列表失败')
    } finally {
      loading.value = false
    }
  }

  const updateUser = async (userId, data) => {
    const { data: res } = await adminApi.updateUser(userId, data)
    ElMessage.success('用户更新成功')
    return res
  }

  const resetPassword = async (userId) => {
    const { data: res } = await adminApi.resetPassword(userId)
    ElMessage.success('密码重置成功')
    return res
  }

  return {
    users, loading, pagination, filters,
    fetchUsers, updateUser, resetPassword,
  }
})
