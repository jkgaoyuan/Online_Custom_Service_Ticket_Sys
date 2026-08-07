<template>
  <div>
    <h2>客服工作台</h2>
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
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link @click="router.push(`/agent/tickets/${row.id}`)">处理</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :total="store.pagination.total" :page-size="20" @change="load" />
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
const page = ref(1)
const load = () => store.fetchTickets({ page: page.value, page_size: 20 })
onMounted(load)
</script>
