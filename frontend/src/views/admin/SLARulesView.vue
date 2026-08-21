<template>
  <div class="sla-rules-management">
    <h2>SLA 规则</h2>

    <el-tabs v-model="activeTab">
      <!-- Tab1: SLA 规则 -->
      <el-tab-pane label="SLA规则" name="rules">
        <el-table :data="slaStore.rules" v-loading="slaStore.loading">
          <el-table-column prop="category_name" label="分类" />
          <el-table-column prop="first_resp_hours" label="首次响应时限（小时）" />
          <el-table-column prop="resolution_hours" label="解决时限（小时）" />
          <el-table-column prop="updated_at" label="更新时间">
            <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab2: 超时工单 -->
      <el-tab-pane label="超时工单" name="overdue">
        <el-table :data="slaStore.overdueTickets" v-loading="slaStore.loading">
          <el-table-column prop="ticket_no" label="工单编号" />
          <el-table-column prop="title" label="标题" />
          <el-table-column prop="assignee_name" label="负责人" />
          <el-table-column prop="due_time" label="截止时间">
            <template #default="{ row }">{{ formatDate(row.due_time) }}</template>
          </el-table-column>
          <el-table-column prop="breach_type" label="超时类型">
            <template #default="{ row }">
              <el-tag :type="breachTagType(row.breach_type)">{{ breachLabel(row.breach_type) }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useSlaStore } from '@/stores/sla'

const slaStore = useSlaStore()
const activeTab = ref('rules')

function formatDate(d) {
  return d ? new Date(d).toLocaleString() : '-'
}

function breachTagType(type) {
  const map = { first_response: 'warning', resolution: 'danger' }
  return map[type] || 'info'
}

function breachLabel(type) {
  const map = { first_response: '首次响应超时', resolution: '解决超时' }
  return map[type] || type
}

async function loadTabData() {
  if (activeTab.value === 'rules') {
    await slaStore.fetchRules()
  } else {
    await slaStore.fetchOverdue()
  }
}

watch(activeTab, loadTabData)

onMounted(loadTabData)
</script>

<style scoped>
.sla-rules-management { padding: 24px; }
</style>
