<template>
  <div>
    <h2>客服工作台</h2>

    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-bottom: 20px;">
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <el-icon class="stat-icon" :style="{ color: '#e6a23c' }">
              <Tickets />
            </el-icon>
            <div>
              <div class="stat-value">{{ stats.open }}</div>
              <div class="stat-label">待处理工单</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <el-icon class="stat-icon" :style="{ color: '#409eff' }">
              <Loading />
            </el-icon>
            <div>
              <div class="stat-value">{{ stats.in_progress }}</div>
              <div class="stat-label">处理中工单</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <el-icon class="stat-icon" :style="{ color: '#67c23a' }">
              <CircleCheck />
            </el-icon>
            <div>
              <div class="stat-value">{{ stats.resolved }}</div>
              <div class="stat-label">今日已解决</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <el-icon class="stat-icon" :style="{ color: '#909399' }">
              <Timer />
            </el-icon>
            <div>
              <div class="stat-value">{{ stats.waiting }}</div>
              <div class="stat-label">等待客户</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷操作 -->
    <el-button-group style="margin-bottom: 20px;">
      <el-button @click="router.push('/agent/tickets')">查看全部工单</el-button>
      <el-button @click="router.push('/agent/tickets?status=open')">处理 open 工单</el-button>
    </el-button-group>

    <!-- 最近工单 -->
    <h3>最近工单</h3>
    <el-table :data="recentTickets" v-loading="store.loading" style="margin-top: 12px;">
      <el-table-column prop="ticket_no" label="工单号" width="160" />
      <el-table-column prop="title" label="标题" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <StatusBadge :status="row.status" />
        </template>
      </el-table-column>
      <el-table-column label="优先级" width="80">
        <template #default="{ row }">
          <PriorityTag :priority="row.priority" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link @click="router.push(`/agent/tickets/${row.id}`)">处理</el-button>
          <el-button v-if="row.status === 'open'" link type="primary" @click="claim(row)">接单</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'
import { useTicketsStore } from '@/stores'
import { useAuthStore } from '@/stores'
import { ticketApi } from '@/api/tickets'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityTag from '@/components/PriorityTag.vue'
import { Tickets, Loading, CircleCheck, Timer } from '@element-plus/icons-vue'

const router = useRouter()
const store = useTicketsStore()
const authStore = useAuthStore()

const stats = ref({
  open: 0,
  in_progress: 0,
  resolved: 0,
  waiting: 0,
})

const recentTickets = ref([])
let abortController = null

const loadStats = async () => {
  try {
    const { data } = await ticketApi.getAgentStats()
    stats.value = data
  } catch (e) {
    // ignore
  }
}

const loadRecent = async () => {
  await store.fetchTickets({ page_size: 5 })
  recentTickets.value = store.tickets
}

const claim = async (row) => {
  await store.updateStatus(row.id, 'in_progress')
  await Promise.all([loadStats(), loadRecent()])
}

const connectSSE = () => {
  if (!authStore.token) return
  abortController = new AbortController()
  fetch('/api/v1/sse/connect', {
    headers: { Authorization: `Bearer ${authStore.token}` },
    signal: abortController.signal,
  }).then(async (response) => {
    if (!response.body) return
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const payload = JSON.parse(line.slice(6))
            if (payload.type === 'ticket_assigned') {
              ElNotification({
                title: '新工单分配',
                message: `工单 ${payload.data.ticket_no}：${payload.data.title}`,
                type: 'warning',
              })
              loadRecent()
            } else if (payload.type === 'stats_update') {
              loadStats()
            }
          } catch (e) {
            // ignore parse error
          }
        }
      }
    }
  }).catch(() => {
    // connection closed or error
  })
}

onMounted(() => {
  loadStats()
  loadRecent()
  connectSSE()
})

onUnmounted(() => {
  if (abortController) {
    abortController.abort()
  }
})
</script>

<style scoped>
.stat-card {
  display: flex;
  align-items: center;
}
.stat-icon {
  font-size: 32px;
  margin-right: 12px;
}
.stat-value {
  font-size: 24px;
  font-weight: bold;
}
.stat-label {
  color: #999;
  font-size: 12px;
}
</style>
