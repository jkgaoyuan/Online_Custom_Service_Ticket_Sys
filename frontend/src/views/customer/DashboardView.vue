<template>
  <div class="customer-dashboard">
    <!-- 欢迎区域 -->
    <el-row style="margin-bottom: 20px;">
      <el-col :span="16">
        <h2>欢迎回来，{{ authStore.user?.username || '客户' }}</h2>
        <p class="subtitle">这里是您的服务概览，如需帮助可随时提交工单。</p>
      </el-col>
      <el-col :span="8" style="text-align: right;">
        <el-button type="primary" @click="router.push('/customer/tickets/new')">
          <el-icon><CirclePlus /></el-icon> 提交新工单
        </el-button>
      </el-col>
    </el-row>

    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-bottom: 24px;">
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <el-icon class="stat-icon" :style="{ color: '#409eff' }"><Tickets /></el-icon>
            <div>
              <div class="stat-value">{{ stats.total }}</div>
              <div class="stat-label">全部工单</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <el-icon class="stat-icon" :style="{ color: '#e6a23c' }"><Loading /></el-icon>
            <div>
              <div class="stat-value">{{ stats.pending }}</div>
              <div class="stat-label">处理中</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <el-icon class="stat-icon" :style="{ color: '#67c23a' }"><CircleCheck /></el-icon>
            <div>
              <div class="stat-value">{{ stats.closed }}</div>
              <div class="stat-label">已关闭</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <el-icon class="stat-icon" :style="{ color: '#f56c6c' }"><Star /></el-icon>
            <div>
              <div class="stat-value">{{ stats.pendingRating }}</div>
              <div class="stat-label">待评价</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近工单 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>最近工单</span>
          <el-button link @click="router.push('/customer/tickets')">查看全部</el-button>
        </div>
      </template>
      <el-table :data="recentTickets" v-loading="store.loading" style="width: 100%">
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
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link @click="router.push(`/customer/tickets/${row.id}`)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!store.loading && recentTickets.length === 0" description="暂无工单，点击上方按钮提交您的问题" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTicketsStore } from '@/stores'
import { useAuthStore } from '@/stores'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityTag from '@/components/PriorityTag.vue'
import { Tickets, Loading, CircleCheck, Star, CirclePlus } from '@element-plus/icons-vue'

const router = useRouter()
const store = useTicketsStore()
const authStore = useAuthStore()

const recentTickets = computed(() => store.tickets.slice(0, 5))

const stats = computed(() => {
  const all = store.tickets
  const pending = all.filter(t => ['open', 'in_progress', 'waiting'].includes(t.status))
  const closed = all.filter(t => ['resolved', 'closed'].includes(t.status))
  const pendingRating = all.filter(t => t.status === 'closed' && !t.satisfaction)
  return {
    total: all.length,
    pending: pending.length,
    closed: closed.length,
    pendingRating: pendingRating.length,
  }
})

onMounted(() => {
  store.fetchTickets({ page: 1, page_size: 5 })
})
</script>

<style scoped>
.subtitle {
  color: #909399;
  margin-top: 4px;
}
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
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
