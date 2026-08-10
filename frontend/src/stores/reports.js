import { defineStore } from 'pinia'
import { ref } from 'vue'
import { reportApi } from '@/api/reports'

const formatDate = (d) => {
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export const useReportsStore = defineStore('reports', () => {
  const today = new Date()
  const sevenDaysAgo = new Date(today.getTime() - 6 * 24 * 60 * 60 * 1000)
  const dateRange = ref([
    formatDate(sevenDaysAgo),
    formatDate(today),
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
  const exportFormat = ref(null)

  const fetchCurrentTab = async () => {
    const targetTab = activeTab.value
    loading.value = true
    try {
      const [start, end] = dateRange.value
      const params = { start_date: start, end_date: end }

      if (targetTab === 'overview') {
        const { data } = await reportApi.overview()
        if (activeTab.value !== targetTab) return
        overview.value = data
      } else if (targetTab === 'agent_performance') {
        const { data } = await reportApi.agentPerformance(params)
        if (activeTab.value !== targetTab) return
        agentPerformance.value = data
      } else if (targetTab === 'category_distribution') {
        const { data } = await reportApi.categoryDistribution(params)
        if (activeTab.value !== targetTab) return
        categoryDistribution.value = data
      } else if (targetTab === 'trend') {
        const { data } = await reportApi.trend({ ...params, granularity: 'day' })
        if (activeTab.value !== targetTab) return
        trend.value = data
      } else if (targetTab === 'satisfaction') {
        const { data } = await reportApi.satisfaction(params)
        if (activeTab.value !== targetTab) return
        satisfaction.value = data
      }
    } catch (error) {
      console.error('Failed to fetch report:', error)
    } finally {
      if (activeTab.value === targetTab) {
        loading.value = false
      }
    }
  }

  const submitExport = async (format) => {
    if (exporting.value) return
    exporting.value = true
    exportFormat.value = format
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
    } catch (error) {
      console.error('Failed to submit export:', error)
    } finally {
      exporting.value = false
    }
  }

  const pollExportStatus = async (taskId) => {
    const { data } = await reportApi.exportStatus(taskId)
    exportTask.value = {
      taskId: data.task_id,
      status: data.status,
      downloadUrl: data.download_url || null,
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
    exportFormat,
    fetchCurrentTab,
    submitExport,
    pollExportStatus,
  }
})
