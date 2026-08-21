import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { useAuthStore } from './index'
import { listNotifications, markRead as apiMarkRead, markAllRead as apiMarkAllRead } from '@/api/notifications'

export const useNotificationsStore = defineStore('notifications', () => {
  const notifications = ref([])
  const unreadCount = ref(0)
  const eventSource = ref(null)
  const abortController = ref(null)

  const authStore = useAuthStore()

  function handleEvent(event) {
    if (event.type === 'new_notification') {
      unreadCount.value += 1
      notifications.value.unshift(event.data)
    }
  }

  async function connectSSE() {
    if (eventSource.value) {
      disconnectSSE()
    }
    const token = authStore.token
    if (!token) return

    const controller = new AbortController()
    abortController.value = controller

    try {
      const response = await fetch('/api/v1/sse/connect', {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'text/event-stream',
        },
        signal: controller.signal,
      })

      if (!response.ok || !response.body) {
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      eventSource.value = { reader, controller }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let currentData = null
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            currentData = line.slice(6)
          } else if (line === '' && currentData !== null) {
            try {
              const parsed = JSON.parse(currentData)
              handleEvent(parsed)
            } catch {
              // ignore malformed JSON
            }
            currentData = null
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('SSE error:', err)
      }
    } finally {
      eventSource.value = null
      abortController.value = null
    }
  }

  function disconnectSSE() {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
    eventSource.value = null
  }

  async function fetchNotifications() {
    const { data } = await listNotifications()
    notifications.value = data.items || []
    unreadCount.value = data.unread_count || 0
  }

  async function markRead(id) {
    await apiMarkRead(id)
    const idx = notifications.value.findIndex((n) => n.id === id)
    if (idx !== -1 && !notifications.value[idx].is_read) {
      notifications.value[idx].is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  }

  async function markAllRead() {
    await apiMarkAllRead()
    notifications.value.forEach((n) => {
      n.is_read = true
    })
    unreadCount.value = 0
  }

  // Auto connect/disconnect based on auth token
  watch(
    () => authStore.token,
    (newToken) => {
      if (newToken) {
        connectSSE()
      } else {
        disconnectSSE()
      }
    },
    { immediate: true }
  )

  return {
    notifications,
    unreadCount,
    eventSource,
    connectSSE,
    disconnectSSE,
    fetchNotifications,
    markRead,
    markAllRead,
  }
})
