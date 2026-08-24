<template>
  <div v-if="ticketsStore.currentTicket">
    <h2>{{ ticketsStore.currentTicket.title }}</h2>
    <el-descriptions border>
      <el-descriptions-item label="工单号">{{ ticketsStore.currentTicket.ticket_no }}</el-descriptions-item>
      <el-descriptions-item label="状态"><StatusBadge :status="ticketsStore.currentTicket.status" /></el-descriptions-item>
      <el-descriptions-item label="优先级"><PriorityTag :priority="ticketsStore.currentTicket.priority" /></el-descriptions-item>
      <el-descriptions-item label="创建时间">{{ ticketsStore.currentTicket.created_at }}</el-descriptions-item>
    </el-descriptions>
    <el-divider />
    <h3>描述</h3>
    <p>{{ ticketsStore.currentTicket.description }}</p>
    <el-divider />
    <h3>回复记录</h3>
    <el-timeline>
      <el-timeline-item v-for="reply in ticketsStore.replies" :key="reply.id" :timestamp="reply.created_at">
        <div class="reply-header">
          <span :class="reply.author?.role === 'customer' ? 'customer-badge' : 'agent-badge'">
            {{ reply.author?.username || '未知用户' }}
          </span>
          <el-tag v-if="reply.is_internal" type="warning" size="small">内部</el-tag>
        </div>
        <div class="reply-content">{{ reply.content }}</div>
      </el-timeline-item>
    </el-timeline>

    <!-- 回复框 -->
    <el-divider />
    <div v-if="ticketsStore.currentTicket.status !== 'closed'">
      <h3>补充回复</h3>
      <ReplyBox
        :ticketId="ticketsStore.currentTicket.id"
        :showInternal="false"
        @replied="handleReply"
      />
    </div>

    <!-- 关闭工单 -->
    <el-divider v-if="ticketsStore.currentTicket.status === 'resolved'" />
    <div v-if="ticketsStore.currentTicket.status === 'resolved'">
      <el-button type="danger" @click="closeTicket">关闭工单</el-button>
    </div>

    <!-- 评价区域 -->
    <el-divider />
    <div v-if="ticketsStore.currentTicket.status === 'closed'" class="satisfaction-section">
      <!-- 未评价：邀请卡片 -->
      <el-card v-if="!ticketsStore.currentTicket.satisfaction" class="satisfaction-card">
        <template #header>
          <span>请评价本次服务</span>
        </template>
        <div class="rating-buttons">
          <el-button
            v-for="opt in ratingOptions"
            :key="opt.value"
            :type="selectedRating === opt.value ? 'primary' : 'default'"
            size="large"
            @click="selectedRating = opt.value"
          >
            {{ opt.icon }} {{ opt.label }}
          </el-button>
        </div>
        <el-input
          v-if="selectedRating"
          v-model="satisfactionNote"
          type="textarea"
          :rows="3"
          placeholder="您的反馈对我们很重要（选填，最多500字）"
          maxlength="500"
          show-word-limit
          class="note-input"
        />
        <el-button
          v-if="selectedRating"
          type="primary"
          @click="submitSatisfaction"
          :loading="submitting"
        >
          提交评价
        </el-button>
      </el-card>

      <!-- 已评价：展示卡片 -->
      <el-card v-else class="satisfaction-card">
        <template #header>
          <span>您的评价</span>
        </template>
        <div class="rating-display">
          <span class="rating-icon">{{ getRatingIcon(ticketsStore.currentTicket.satisfaction) }}</span>
          <span class="rating-label">{{ getRatingLabel(ticketsStore.currentTicket.satisfaction) }}</span>
        </div>
        <p v-if="ticketsStore.currentTicket.satisfaction_note" class="rating-note">{{ ticketsStore.currentTicket.satisfaction_note }}</p>
        <p class="rating-time">评价时间：{{ ticketsStore.currentTicket.satisfaction_at }}</p>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTicketsStore } from '@/stores'
import { ElMessage } from 'element-plus'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityTag from '@/components/PriorityTag.vue'
import ReplyBox from '@/components/ReplyBox.vue'

const route = useRoute()
const ticketsStore = useTicketsStore()

onMounted(() => {
  ticketsStore.fetchTicket(route.params.id)
  ticketsStore.fetchReplies(route.params.id)
})

const selectedRating = ref('')
const satisfactionNote = ref('')
const submitting = ref(false)

const ratingOptions = [
  { value: 'satisfied', label: '满意', icon: '😊' },
  { value: 'neutral', label: '一般', icon: '😐' },
  { value: 'dissatisfied', label: '不满意', icon: '😞' },
]

const getRatingIcon = (rating) => ratingOptions.find(o => o.value === rating)?.icon || ''
const getRatingLabel = (rating) => ratingOptions.find(o => o.value === rating)?.label || ''

const submitSatisfaction = async () => {
  submitting.value = true
  try {
    await ticketsStore.submitSatisfaction(route.params.id, {
      rating: selectedRating.value,
      note: satisfactionNote.value,
    })
    ElMessage.success('评价提交成功，感谢您的反馈！')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

const handleReply = async (payload) => {
  try {
    await ticketsStore.replyTicket(route.params.id, payload)
    await ticketsStore.fetchReplies(route.params.id)
    ElMessage.success('回复成功')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '回复失败')
  }
}

const closeTicket = async () => {
  try {
    await ticketsStore.updateStatus(route.params.id, 'closed')
    await ticketsStore.fetchTicket(route.params.id)
    ElMessage.success('工单已关闭')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '关闭工单失败')
  }
}
</script>

<style scoped>
.satisfaction-section { margin-top: 24px; }
.satisfaction-card { margin-top: 16px; }
.rating-buttons { display: flex; gap: 12px; margin-bottom: 16px; }
.note-input { margin-bottom: 16px; }
.rating-display { display: flex; align-items: center; gap: 8px; font-size: 18px; }
.rating-icon { font-size: 24px; }
.rating-note { color: #666; margin-top: 8px; }
.rating-time { color: #999; font-size: 12px; margin-top: 8px; }
.reply-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.reply-content { white-space: pre-wrap; word-break: break-word; }
.customer-badge { color: #409eff; font-weight: 600; }
.agent-badge { color: #67c23a; font-weight: 600; }
</style>
