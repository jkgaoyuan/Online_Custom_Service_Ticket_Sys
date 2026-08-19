<template>
  <div class="reports-page" v-loading="store.loading">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <el-date-picker
        v-model="store.dateRange"
        type="daterange"
        value-format="YYYY-MM-DD"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        :disabled="store.activeTab === 'overview' || store.loading"
        @change="refreshData"
      />
      <div class="export-buttons">
        <el-button
          :loading="store.exporting"
          :disabled="store.exporting"
          @click="handleExport('xlsx')"
        >
          导出 Excel
        </el-button>
        <el-button
          :loading="store.exporting"
          :disabled="store.exporting"
          @click="handleExport('csv')"
        >
          导出 CSV
        </el-button>
      </div>
    </div>

    <!-- 导出状态提示 -->
    <el-alert
      v-if="store.exportTask?.status === 'pending'"
      title="导出任务处理中..."
      type="info"
      :closable="false"
      show-icon
      class="export-alert"
    />
    <el-alert
      v-if="store.exportTask?.status === 'completed' && store.exportTask?.downloadUrl"
      title="导出完成"
      type="success"
      :closable="true"
      show-icon
      class="export-alert"
    >
      <template #default>
        <span>导出完成，<el-link type="primary" @click="downloadFile">点击下载</el-link></span>
      </template>
    </el-alert>

    <!-- Tab 内容 -->
    <el-tabs v-model="store.activeTab" @tab-change="refreshData">
      <el-tab-pane label="综合概览" name="overview">
        <OverviewPanel v-if="store.activeTab === 'overview'" />
      </el-tab-pane>
      <el-tab-pane label="客服绩效" name="agent_performance">
        <AgentPerformanceTable v-if="store.activeTab === 'agent_performance'" />
      </el-tab-pane>
      <el-tab-pane label="分类分布" name="category_distribution">
        <CategoryDistributionChart v-if="store.activeTab === 'category_distribution'" />
      </el-tab-pane>
      <el-tab-pane label="时段趋势" name="trend">
        <TrendChart v-if="store.activeTab === 'trend'" />
      </el-tab-pane>
      <el-tab-pane label="满意度" name="satisfaction">
        <SatisfactionPanel v-if="store.activeTab === 'satisfaction'" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useReportsStore } from '@/stores'
import { ElMessage } from 'element-plus'
import api from '@/api'
import OverviewPanel from '@/components/reports/OverviewPanel.vue'
import AgentPerformanceTable from '@/components/reports/AgentPerformanceTable.vue'
import CategoryDistributionChart from '@/components/reports/CategoryDistributionChart.vue'
import TrendChart from '@/components/reports/TrendChart.vue'
import SatisfactionPanel from '@/components/reports/SatisfactionPanel.vue'

const store = useReportsStore()

onMounted(() => {
  store.fetchCurrentTab()
})

const refreshData = () => {
  store.fetchCurrentTab()
}

const handleExport = async (format) => {
  try {
    const taskId = await store.submitExport(format)
    let attempts = 0
    const maxAttempts = 30
    const interval = setInterval(async () => {
      attempts++
      try {
        const data = await store.pollExportStatus(taskId)
        if (data.status === 'completed') {
          clearInterval(interval)
        } else if (data.status === 'failed') {
          clearInterval(interval)
          ElMessage.error('导出失败，请重试')
          store.exportTask = null
        } else if (attempts >= maxAttempts) {
          clearInterval(interval)
          ElMessage.error('导出超时，请重试')
          store.exportTask = null
        }
      } catch {
        clearInterval(interval)
        ElMessage.error('导出失败，请重试')
        store.exportTask = null
      }
    }, 2000)
  } catch {
    ElMessage.error('导出失败，请重试')
  }
}

const downloadFile = async () => {
  const url = store.exportTask?.downloadUrl
  if (!url) return
  try {
    const res = await api.get(url.replace(/^\/api\/v1/, ''), { responseType: 'blob' })
    const downloadUrl = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = downloadUrl
    const format = store.exportFormat || 'xlsx'
    a.download = `report_${store.exportTask.taskId}.${format}`
    a.click()
    setTimeout(() => URL.revokeObjectURL(downloadUrl), 100)
  } catch {
    ElMessage.error('下载失败')
  }
}
</script>

<style scoped>
.reports-page {
  padding: 20px;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.export-buttons {
  display: flex;
  gap: 10px;
}
.export-alert {
  margin-bottom: 16px;
}
</style>
