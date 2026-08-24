<template>
  <div class="tickets-management">
    <h2>工单管理</h2>

    <!-- 筛选区域 -->
    <div class="filter-bar">
      <div class="filter-left">
        <el-select v-model="filterStatus" placeholder="状态" class="filter-select" clearable @change="handleFilter">
          <el-option label="待处理" value="open" />
          <el-option label="处理中" value="in_progress" />
          <el-option label="等待回复" value="waiting" />
          <el-option label="已解决" value="resolved" />
          <el-option label="已关闭" value="closed" />
        </el-select>
        <el-select v-model="filterPriority" placeholder="优先级" class="filter-select" clearable @change="handleFilter">
          <el-option label="紧急" value="P0" />
          <el-option label="高" value="P1" />
          <el-option label="中" value="P2" />
          <el-option label="低" value="P3" />
        </el-select>
      </div>
    </div>

    <!-- 工单表格 -->
    <el-table :data="store.tickets" v-loading="store.loading">
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
      <el-table-column prop="requester.username" label="客户" />
      <el-table-column label="负责人" width="120">
        <template #default="{ row }">
          {{ row.assignee?.username || '未分配' }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link @click="router.push(`/admin/tickets/${row.id}`)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="store.pagination.total"
      layout="total, prev, pager, next"
      @change="handleFilter"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTicketsStore } from '@/stores'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityTag from '@/components/PriorityTag.vue'

const router = useRouter()
const store = useTicketsStore()
const currentPage = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')
const filterPriority = ref('')

const handleFilter = () => {
  const params = { page: currentPage.value, page_size: pageSize.value }
  if (filterStatus.value) params.status = filterStatus.value
  if (filterPriority.value) params.priority = filterPriority.value
  store.fetchTickets(params)
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN')
}

onMounted(handleFilter)
</script>

<style scoped>
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.filter-left {
  display: flex;
  gap: 12px;
}
.filter-select {
  width: 140px;
}
</style>
