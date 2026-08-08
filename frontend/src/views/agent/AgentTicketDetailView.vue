<template>
  <div v-if="store.currentTicket">
    <h2>{{ store.currentTicket.title }}</h2>
    <el-descriptions border>
      <el-descriptions-item label="工单号">{{ store.currentTicket.ticket_no }}</el-descriptions-item>
      <el-descriptions-item label="状态"><StatusBadge :status="store.currentTicket.status" /></el-descriptions-item>
      <el-descriptions-item label="优先级"><PriorityTag :priority="store.currentTicket.priority" /></el-descriptions-item>
      <el-descriptions-item label="客户">{{ store.currentTicket.requester?.username }}</el-descriptions-item>
    </el-descriptions>
    <el-divider />
    <h3>描述</h3>
    <p>{{ store.currentTicket.description }}</p>
    <el-divider />
    <h3>回复记录</h3>
    <el-timeline>
      <el-timeline-item v-for="reply in store.replies" :key="reply.id" :timestamp="reply.created_at">
        <el-tag v-if="reply.is_internal" type="warning" size="small">内部</el-tag>
        {{ reply.content }}
      </el-timeline-item>
    </el-timeline>
    <el-divider />
    <h3>回复</h3>
    <ReplyBox :ticketId="store.currentTicket.id" @replied="handleReply" />
    <el-divider />
    <h3>分派</h3>
    <el-button-group v-if="store.currentTicket.status === 'open'">
      <el-button @click="loadSuggestions">建议分配</el-button>
      <el-button type="primary" @click="handleAutoAssign">自动分派</el-button>
    </el-button-group>
    <AssignSuggestionList v-if="suggestions.length" :suggestions="suggestions" @assign="handleManualAssign" />
    <el-divider />
    <h3>操作</h3>
    <el-button-group>
      <el-button v-if="store.currentTicket.status === 'in_progress'" @click="changeStatus('resolved')">标记已解决</el-button>
      <el-button v-if="store.currentTicket.status === 'resolved'" @click="changeStatus('closed')">关闭工单</el-button>
      <el-button v-if="store.currentTicket.status === 'in_progress'" @click="changeStatus('waiting')">等待客户</el-button>
    </el-button-group>
  </div>
</template>

<script setup>
import { onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useTicketsStore } from '@/stores'
import { useDispatchStore } from '@/stores/dispatch'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityTag from '@/components/PriorityTag.vue'
import ReplyBox from '@/components/ReplyBox.vue'
import AssignSuggestionList from '@/components/AssignSuggestionList.vue'
import { ElMessage } from 'element-plus'
const route = useRoute()
const store = useTicketsStore()
const dispatchStore = useDispatchStore()
const suggestions = computed(() => dispatchStore.suggestions)

onMounted(() => {
  store.fetchTicket(route.params.id)
  store.fetchReplies(route.params.id)
})

const handleReply = async (payload) => {
  await store.replyTicket(store.currentTicket.id, payload)
  await store.fetchReplies(store.currentTicket.id)
  await store.fetchTicket(store.currentTicket.id)
  ElMessage.success('回复成功')
}

const changeStatus = async (status) => {
  await store.updateStatus(store.currentTicket.id, status)
  ElMessage.success('状态更新成功')
}

const loadSuggestions = async () => {
  await dispatchStore.fetchSuggestions(store.currentTicket.id)
}

const handleAutoAssign = async () => {
  const result = await dispatchStore.autoAssign(store.currentTicket.id)
  if (result.assigned) {
    ElMessage.success('自动分派成功')
    await store.fetchTicket(store.currentTicket.id)
  } else {
    ElMessage.warning('暂无可分配的客服')
  }
}

const handleManualAssign = async (agentId) => {
  await dispatchStore.manualAssign(store.currentTicket.id, agentId)
  ElMessage.success('手动分派成功')
  await store.fetchTicket(store.currentTicket.id)
}
</script>
