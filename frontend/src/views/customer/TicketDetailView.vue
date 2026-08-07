<template>
  <div v-if="store.currentTicket">
    <h2>{{ store.currentTicket.title }}</h2>
    <el-descriptions border>
      <el-descriptions-item label="工单号">{{ store.currentTicket.ticket_no }}</el-descriptions-item>
      <el-descriptions-item label="状态"><StatusBadge :status="store.currentTicket.status" /></el-descriptions-item>
      <el-descriptions-item label="优先级"><PriorityTag :priority="store.currentTicket.priority" /></el-descriptions-item>
      <el-descriptions-item label="创建时间">{{ store.currentTicket.created_at }}</el-descriptions-item>
    </el-descriptions>
    <el-divider />
    <h3>描述</h3>
    <p>{{ store.currentTicket.description }}</p>
    <el-divider />
    <h3>回复记录</h3>
    <el-timeline>
      <el-timeline-item v-for="reply in store.replies" :key="reply.id" :timestamp="reply.created_at">
        {{ reply.content }}
      </el-timeline-item>
    </el-timeline>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTicketsStore } from '@/stores'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityTag from '@/components/PriorityTag.vue'
const route = useRoute()
const store = useTicketsStore()
onMounted(() => {
  store.fetchTicket(route.params.id)
  store.fetchReplies(route.params.id)
})
</script>
