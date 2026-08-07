<template>
  <el-tag :type="priorityType" size="small">{{ priorityLabel }}</el-tag>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ priority: String })
const priorityMap = {
  P0: { label: '紧急', type: 'danger' },
  P1: { label: '高', type: 'warning' },
  P2: { label: '中', type: 'primary' },
  P3: { label: '低', type: 'info' },
}
const priorityLabel = computed(() => priorityMap[props.priority]?.label || props.priority)
const priorityType = computed(() => priorityMap[props.priority]?.type || 'info')
</script>
