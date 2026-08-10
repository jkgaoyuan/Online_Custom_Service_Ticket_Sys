<template>
  <el-card>
    <el-table :data="store.agentPerformance" v-loading="store.loading">
      <el-table-column prop="agent_name" label="客服" />
      <el-table-column prop="total_assigned" label="分配工单数" />
      <el-table-column prop="resolved_count" label="已解决数" />
      <el-table-column label="平均首次响应（小时）">
        <template #default="{ row }">
          {{ row.avg_first_resp_hours.toFixed(1) }}
        </template>
      </el-table-column>
      <el-table-column label="平均解决时长（小时）">
        <template #default="{ row }">
          {{ row.avg_resolution_hours.toFixed(1) }}
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!store.loading && store.agentPerformance.length === 0" description="暂无数据" />
  </el-card>
</template>

<script setup>
import { useReportsStore } from '@/stores'

const store = useReportsStore()
</script>
