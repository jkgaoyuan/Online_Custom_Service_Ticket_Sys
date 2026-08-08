import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, getMe } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)
  const userRole = computed(() => user.value?.role || null)

  const setAuth = (newToken, newUser) => {
    token.value = newToken
    user.value = newUser
    localStorage.setItem('token', newToken)
    localStorage.setItem('user', JSON.stringify(newUser))
  }

  const clearAuth = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  const login = async (credentials) => {
    const { data } = await apiLogin(credentials)
    setAuth(data.access_token, data.user)
    return data
  }

  const logout = () => {
    clearAuth()
    window.location.href = '/login'
  }

  const initAuth = async () => {
    if (token.value && !user.value) {
      try {
        const { data } = await getMe()
        user.value = data
      } catch {
        clearAuth()
      }
    }
  }

  return {
    token,
    user,
    isLoggedIn,
    userRole,
    setAuth,
    clearAuth,
    login,
    logout,
    initAuth,
  }
})

export { useTicketsStore } from './tickets'
export { useDispatchStore } from './dispatch'