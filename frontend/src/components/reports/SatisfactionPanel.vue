<template>
  <div v-if="store.satisfaction">
    <!-- 指标卡片 -->
    <el-row :gutter="16" class="metric-row">
      <el-col :span="8">
        <el-card>
          <div class="metric-value">
            {{ (store.satisfaction.participation_rate * 100).toFixed(1) }}%
          </div>
          <div class="metric-label">参与率</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <div class="metric-value">{{ store.satisfaction.avg_score.toFixed(2) }}</div>
          <div class="metric-label">平均分</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <div class="metric-value">{{ store.satisfaction.total_rated }}</div>
          <div class="metric-label">总评价数</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 柱状图 -->
    <el-card title="满意度分布">
      <v-chart class="chart" :option="barOption" autoresize />
    </el-card>
  </div>
  <el-empty v-else description="暂无数据" />
</template>

<script setup>
import { computed } from 'vue'
import { useReportsStore } from '@/stores'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { GridComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const store = useReportsStore()

const LABEL_MAP = {
  satisfied: '满意',
  neutral: '一般',
  dissatisfied: '不满意',
}

const barOption = computed(() => {
  const dist = store.satisfaction?.distribution || {}
  const categories = ['satisfied', 'neutral', 'dissatisfied']
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: categories.map((key) => LABEL_MAP[key]),
    },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: categories.map((key) => dist[key] || 0),
        itemStyle: { borderRadius: [4, 4, 0, 0] },
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
.chart {
  height: 300px;
}
</style>
