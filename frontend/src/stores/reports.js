import { defineStore } from 'pinia'
import { ref } from 'vue'
import { reportApi } from '@/api/reports'

export const useReportsStore = defineStore('reports', () => {
  const today = new Date()
  const sevenDaysAgo = new Date(today.getTime() - 6 * 24 * 60 * 60 * 1000)
  const dateRange = ref([
    sevenDaysAgo.toISOString().split('T')[0],
    today.toISOString().split('T')[0],
  ])

  const activeTab = ref('overview')
  const loading = ref(false)

  const overview = ref(null)
  const agentPerformance = ref([])
  const categoryDistribution = ref([])
  const trend = ref([])
  const satisfaction = ref(null)

  const exportTask = ref(null)
  const exporting = ref(false)

  const fetchCurrentTab = async () => {
    const tab = activeTab.value
    loading.value = true
    try {
      const [start, end] = dateRange.value
      const params = { start_date: start, end_date: end }

      if (tab === 'overview') {
        const { data } = await reportApi.overview()
        if (activeTab.value !== 'overview') return
        overview.value = data
      } else if (tab === 'agent_performance') {
        const { data } = await reportApi.agentPerformance(params)
        if (activeTab.value !== 'agent_performance') return
        agentPerformance.value = data
      } else if (tab === 'category_distribution') {
        const { data } = await reportApi.categoryDistribution(params)
        if (activeTab.value !== 'category_distribution') return
        categoryDistribution.value = data
      } else if (tab === 'trend') {
        const { data } = await reportApi.trend({ ...params, granularity: 'day' })
        if (activeTab.value !== 'trend') return
        trend.value = data
      } else if (tab === 'satisfaction') {
        const { data } = await reportApi.satisfaction(params)
        if (activeTab.value !== 'satisfaction') return
        satisfaction.value = data
      }
    } finally {
      loading.value = false
    }
  }

  const submitExport = async (format) => {
    exporting.value = true
    try {
      const [start, end] = dateRange.value
      const { data } = await reportApi.export({
        report_type: activeTab.value,
        format,
        start_date: start,
        end_date: end,
        filters: {},
      })
      exportTask.value = {
        taskId: data.task_id,
        status: data.status,
        downloadUrl: null,
      }
      return data.task_id
    } finally {
      exporting.value = false
    }
  }

  const pollExportStatus = async (taskId) => {
    const { data } = await reportApi.exportStatus(taskId)
    if (data.status === 'completed') {
      exportTask.value = {
        taskId: data.task_id,
        status: data.status,
        downloadUrl: data.download_url,
      }
    }
    return data
  }

  return {
    dateRange,
    activeTab,
    loading,
    overview,
    agentPerformance,
    categoryDistribution,
    trend,
    satisfaction,
    exportTask,
    exporting,
    fetchCurrentTab,
    submitExport,
    pollExportStatus,
  }
})
