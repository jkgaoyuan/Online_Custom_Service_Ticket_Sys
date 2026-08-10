<template>
  <div v-if="store.overview">
    <!-- 指标卡片 -->
    <el-row :gutter="16" class="metric-row">
      <el-col :span="6">
        <el-card>
          <div class="metric-value">{{ store.overview.total_tickets }}</div>
          <div class="metric-label">工单总量</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="metric-value">{{ store.overview.today_new }}</div>
          <div class="metric-label">今日新增</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="metric-value">{{ store.overview.week_new }}</div>
          <div class="metric-label">本周新增</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="metric-value">{{ store.overview.month_new }}</div>
          <div class="metric-label">本月新增</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表行 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="12">
        <el-card title="状态分布">
          <v-chart class="chart" :option="statusPieOption" autoresize />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <el-descriptions :column="1" title="服务质量">
            <el-descriptions-item label="SLA 达标率">
              {{ (store.overview.sla_compliance_rate * 100).toFixed(1) }}%
            </el-descriptions-item>
            <el-descriptions-item label="平均满意度">
              {{ store.overview.avg_satisfaction.toFixed(2) }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
  <el-empty v-else description="暂无数据" />
</template>

<script setup>
import { computed } from 'vue'
import { useReportsStore } from '@/stores'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { TooltipComponent, LegendComponent } from 'echarts/components'

use([CanvasRenderer, PieChart, TooltipComponent, LegendComponent])

const store = useReportsStore()

const STATUS_MAP = {
  open: '待处理',
  in_progress: '处理中',
  waiting: '待回复',
  resolved: '已解决',
  closed: '已关闭',
}

const statusPieOption = computed(() => {
  const dist = store.overview?.status_distribution || {}
  const data = Object.entries(dist).map(([key, value]) => ({
    name: STATUS_MAP[key] || key,
    value,
  }))
  return {
    tooltip: { trigger: 'item' },
    legend: { top: '5%', left: 'center' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 20, fontWeight: 'bold' } },
        data,
      },
    ],
  }
})
</script>

<style scoped>
.metric-row {
  margin-bottom: 16px;
}
.metric-value {
  font-size: 24px;
  font-weight: bold;
  text-align: center;
}
.metric-label {
  text-align: center;
  color: #666;
  margin-top: 8px;
}
.chart-row {
  margin-bottom: 16px;
}
.chart {
  height: 300px;
}
</style>
