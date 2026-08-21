import { defineStore } from 'pinia'
import { ref } from 'vue'
import { slaApi } from '@/api/sla'

export const useSlaStore = defineStore('sla', () => {
  const rules = ref([])
  const overdueTickets = ref([])
  const loading = ref(false)

  async function fetchRules() {
    loading.value = true
    try {
      const { data } = await slaApi.getRules()
      rules.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchOverdue() {
    loading.value = true
    try {
      const { data } = await slaApi.getOverdue()
      overdueTickets.value = data
    } finally {
      loading.value = false
    }
  }

  return {
    rules,
    overdueTickets,
    loading,
    fetchRules,
    fetchOverdue,
  }
})
