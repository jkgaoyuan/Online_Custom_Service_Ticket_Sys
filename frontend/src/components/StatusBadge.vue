<template>
  <el-tag :type="statusType">{{ statusLabel }}</el-tag>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ status: String })
const statusMap = {
  open: { label: '待处理', type: 'info' },
  in_progress: { label: '处理中', type: 'warning' },
  waiting: { label: '等待回复', type: '' },
  resolved: { label: '已解决', type: 'success' },
  closed: { label: '已关闭', type: 'danger' },
}
const statusLabel = computed(() => statusMap[props.status]?.label || props.status)
const statusType = computed(() => statusMap[props.status]?.type || 'info')
</script>
