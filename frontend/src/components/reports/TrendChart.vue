<template>
  <el-card>
    <div class="granularity-selector">
      <el-radio-group v-model="granularity" @change="handleGranularityChange">
        <el-radio-button label="day">日</el-radio-button>
        <el-radio-button label="week">周</el-radio-button>
        <el-radio-button label="month">月</el-radio-button>
      </el-radio-group>
    </div>
    <v-chart class="chart" :option="lineOption" autoresize />
  </el-card>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useReportsStore } from '@/stores'
import { reportApi } from '@/api/reports'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const store = useReportsStore()
const granularity = ref('day')

const handleGranularityChange = async () => {
  store.loading = true
  try {
    const [start, end] = store.dateRange
    const { data } = await reportApi.trend({
      granularity: granularity.value,
      start_date: start,
      end_date: end,
    })
    store.trend = data
  } finally {
    store.loading = false
  }
}

const formatBucket = (bucket) => {
  if (granularity.value === 'day') {
    return bucket.slice(5)
  }
  if (granularity.value === 'week') {
    const d = new Date(bucket)
    const end = new Date(d.getTime() + 6 * 24 * 60 * 60 * 1000)
    return `${d.getMonth() + 1}/${d.getDate()}-${end.getMonth() + 1}/${end.getDate()}`
  }
  if (granularity.value === 'month') {
    const d = new Date(bucket)
    return `${d.getFullYear()}年${d.getMonth() + 1}月`
  }
  return bucket
}

const lineOption = computed(() => {
  const data = store.trend || []
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['创建数', '解决数'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.map((item) => formatBucket(item.bucket)),
    },
    yAxis: { type: 'value' },
    series: [
      { name: '创建数', type: 'line', data: data.map((item) => item.created) },
      { name: '解决数', type: 'line', data: data.map((item) => item.resolved) },
    ],
  }
})
</script>

<style scoped>
.granularity-selector {
  margin-bottom: 16px;
}
.chart {
  height: 300px;
}
</style>
