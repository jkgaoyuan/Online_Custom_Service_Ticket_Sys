<template>
  <div v-if="suggestions.length">
    <h4>建议分配</h4>
    <el-table :data="suggestions" size="small">
      <el-table-column prop="agent_name" label="客服" />
      <el-table-column prop="score" label="得分" width="80" />
      <el-table-column prop="current_load" label="当前负载" width="100" />
      <el-table-column prop="reason" label="原因" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button size="small" @click="$emit('assign', row.agent_id)">分配</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
  <el-empty v-else description="暂无可建议的客服" />
</template>

<script setup>
const props = defineProps({ suggestions: Array })
const emit = defineEmits(['assign'])
</script>
