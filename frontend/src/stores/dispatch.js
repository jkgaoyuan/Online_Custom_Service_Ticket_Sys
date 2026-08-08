import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dispatchApi } from '@/api/dispatch'

export const useDispatchStore = defineStore('dispatch', () => {
  const suggestions = ref([])
  const loading = ref(false)

  const fetchSuggestions = async (ticketId) => {
    loading.value = true
    try {
      const { data } = await dispatchApi.suggest(ticketId)
      suggestions.value = data
    } finally {
      loading.value = false
    }
  }

  const autoAssign = async (ticketId) => {
    const { data } = await dispatchApi.autoAssign(ticketId)
    return data
  }

  const manualAssign = async (ticketId, assigneeId) => {
    const { data } = await dispatchApi.assign(ticketId, assigneeId)
    return data
  }

  return { suggestions, loading, fetchSuggestions, autoAssign, manualAssign }
})
