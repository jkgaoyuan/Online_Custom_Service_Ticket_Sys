<template>
  <el-dropdown trigger="click" @visible-change="onDropdownVisibleChange">
    <el-badge :value="unreadCount" :hidden="unreadCount === 0" class="notification-badge">
      <el-icon :size="20" class="bell-icon"><Bell /></el-icon>
    </el-badge>
    <template #dropdown>
      <el-dropdown-menu class="notification-menu">
        <div v-if="notifications.length === 0" class="notification-empty">
          暂无通知
        </div>
        <el-dropdown-item
          v-for="notif in recentNotifications"
          :key="notif.id"
          @click="handleClick(notif)"
          class="notification-item"
        >
          <div class="notification-title" :class="{ unread: !notif.is_read }">
            {{ notif.title }}
          </div>
          <div class="notification-time">{{ formatTime(notif.created_at) }}</div>
        </el-dropdown-item>
        <el-dropdown-item v-if="notifications.length > 0" divided class="notification-footer">
          <el-button link type="primary" size="small" @click.stop="handleMarkAllRead">
            全部已读
          </el-button>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import { useNotificationsStore } from '@/stores'

const router = useRouter()
const notificationsStore = useNotificationsStore()

const unreadCount = computed(() => notificationsStore.unreadCount)
const notifications = computed(() => notificationsStore.notifications)

const recentNotifications = computed(() => notifications.value.slice(0, 10))

function onDropdownVisibleChange(visible) {
  if (visible) {
    notificationsStore.fetchNotifications()
  }
}

function handleClick(notif) {
  if (notif.data?.ticket_id) {
    router.push(`/tickets/${notif.data.ticket_id}`)
  }
  if (!notif.is_read) {
    notificationsStore.markRead(notif.id)
  }
}

function handleMarkAllRead() {
  notificationsStore.markAllRead()
}

function formatTime(ts) {
  if (!ts) return ''
  const date = new Date(ts)
  const now = new Date()
  const diff = Math.floor((now - date) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  return date.toLocaleDateString()
}
</script>

<style scoped>
.notification-badge {
  cursor: pointer;
  line-height: 1;
}
.bell-icon {
  color: #606266;
}
.notification-menu {
  width: 280px;
  max-height: 400px;
  overflow-y: auto;
}
.notification-empty {
  padding: 20px;
  text-align: center;
  color: #909399;
  font-size: 14px;
}
.notification-item {
  padding: 10px 16px;
  cursor: pointer;
}
.notification-title {
  font-size: 14px;
  color: #303133;
  white-space: normal;
  word-break: break-all;
  line-height: 1.4;
}
.notification-title.unread {
  font-weight: 600;
  color: #409eff;
}
.notification-time {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.notification-footer {
  display: flex;
  justify-content: center;
  padding: 8px;
}
</style>
