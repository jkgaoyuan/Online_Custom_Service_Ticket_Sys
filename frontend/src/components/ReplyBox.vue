<template>
  <div class="reply-box">
    <el-input v-model="content" type="textarea" :rows="3" placeholder="输入回复..." />
    <el-checkbox v-if="showInternal" v-model="isInternal">内部备注（客户不可见）</el-checkbox>
    <el-button type="primary" @click="submit" :loading="loading">发送</el-button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
const props = defineProps({
  ticketId: Number,
  showInternal: { type: Boolean, default: true },
})
const emit = defineEmits(['replied'])
const content = ref('')
const isInternal = ref(false)
const loading = ref(false)
const submit = async () => {
  if (!content.value.trim()) {
    ElMessage.warning('回复内容不能为空')
    return
  }
  loading.value = true
  try {
    emit('replied', { content: content.value, is_internal: isInternal.value })
    content.value = ''
    isInternal.value = false
  } finally {
    loading.value = false
  }
}
</script>
