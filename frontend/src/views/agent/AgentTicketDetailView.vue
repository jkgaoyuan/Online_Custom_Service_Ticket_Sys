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
      <el-button v-if="canCollaborate" @click="openTransferDialog">转交工单</el-button>
      <el-button v-if="canCollaborate" @click="openAssistDialog">请求协助</el-button>
    </el-button-group>

    <!-- 转交对话框 -->
    <el-dialog v-model="transferDialogVisible" title="转交工单" width="500px">
      <el-form label-width="80px">
        <el-form-item label="目标客服">
          <el-select v-model="transferForm.to_user_id" placeholder="选择客服" style="width: 100%">
            <el-option v-for="agent in availableAgents" :key="agent.id" :label="agent.username" :value="agent.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="transferForm.reason" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="请输入转交原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="transferDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitTransfer">确认</el-button>
      </template>
    </el-dialog>

    <!-- 协助对话框 -->
    <el-dialog v-model="assistDialogVisible" title="请求协助" width="500px">
      <el-form label-width="80px">
        <el-form-item label="协助客服">
          <el-select v-model="assistForm.to_user_id" placeholder="选择客服" style="width: 100%">
            <el-option v-for="agent in availableAgents" :key="agent.id" :label="agent.username" :value="agent.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="assistForm.reason" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="请输入协助说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assistDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitAssist">确认</el-button>
      </template>
    </el-dialog>

    <!-- 协作历史 -->
    <template v-if="store.currentTicket.collaborations?.length">
      <el-divider />
      <h3>协作历史</h3>
      <el-timeline>
        <el-timeline-item v-for="collab in store.currentTicket.collaborations" :key="collab.id" :timestamp="collab.created_at">
          <span v-if="collab.type === 'transfer'">🔄 转交</span>
          <span v-else>🤝 协助</span>
          {{ collab.from_user?.username || '系统' }} → {{ collab.to_user.username }}
          <el-tag v-if="collab.reason" size="small" type="info">{{ collab.reason }}</el-tag>
        </el-timeline-item>
      </el-timeline>
    </template>
  </div>
</template>

<script setup>
import { onMounted, computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useTicketsStore } from '@/stores'
import { useAuthStore } from '@/stores'
import { useDispatchStore } from '@/stores/dispatch'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityTag from '@/components/PriorityTag.vue'
import ReplyBox from '@/components/ReplyBox.vue'
import AssignSuggestionList from '@/components/AssignSuggestionList.vue'
import { adminApi } from '@/api/admin'
import { ElMessage } from 'element-plus'

const route = useRoute()
const store = useTicketsStore()
const authStore = useAuthStore()
const dispatchStore = useDispatchStore()
const suggestions = computed(() => dispatchStore.suggestions)

const canCollaborate = computed(() => ['agent', 'supervisor', 'admin'].includes(authStore.userRole))

const transferDialogVisible = ref(false)
const assistDialogVisible = ref(false)
const submitting = ref(false)
const availableAgents = ref([])

const transferForm = ref({ to_user_id: null, reason: '' })
const assistForm = ref({ to_user_id: null, reason: '' })

onMounted(() => {
  store.fetchTicket(route.params.id)
  store.fetchReplies(route.params.id)
})

const loadAvailableAgents = async () => {
  try {
    const { data } = await adminApi.listUsers({ role: 'agent' })
    availableAgents.value = data
  } catch (error) {
    ElMessage.error('加载客服列表失败')
  }
}

const openTransferDialog = async () => {
  transferForm.value = { to_user_id: null, reason: '' }
  await loadAvailableAgents()
  transferDialogVisible.value = true
}

const openAssistDialog = async () => {
  assistForm.value = { to_user_id: null, reason: '' }
  await loadAvailableAgents()
  assistDialogVisible.value = true
}

const submitTransfer = async () => {
  if (!transferForm.value.to_user_id) {
    ElMessage.warning('请选择目标客服')
    return
  }
  submitting.value = true
  try {
    await store.transferTicket(store.currentTicket.id, {
      to_user_id: transferForm.value.to_user_id,
      reason: transferForm.value.reason,
    })
    ElMessage.success('转交成功')
    transferDialogVisible.value = false
    await store.fetchTicket(store.currentTicket.id)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '转交失败')
  } finally {
    submitting.value = false
  }
}

const submitAssist = async () => {
  if (!assistForm.value.to_user_id) {
    ElMessage.warning('请选择协助客服')
    return
  }
  submitting.value = true
  try {
    await store.assistTicket(store.currentTicket.id, {
      to_user_id: assistForm.value.to_user_id,
      reason: assistForm.value.reason,
    })
    ElMessage.success('协助请求已发送')
    assistDialogVisible.value = false
    await store.fetchTicket(store.currentTicket.id)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '请求协助失败')
  } finally {
    submitting.value = false
  }
}

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
