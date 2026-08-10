<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card title="分类占比">
          <v-chart class="chart" :option="pieOption" autoresize />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card title="分类明细">
          <el-table :data="store.categoryDistribution" v-loading="store.loading">
            <el-table-column prop="category_name" label="分类" />
            <el-table-column prop="count" label="数量" />
            <el-table-column label="占比">
              <template #default="{ row }">
                {{ (row.percentage * 100).toFixed(1) }}%
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
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

const pieOption = computed(() => {
  const data = store.categoryDistribution.map((item) => ({
    name: item.category_name,
    value: item.count,
  }))
  return {
    tooltip: { trigger: 'item' },
    legend: { top: '5%', left: 'center' },
    series: [
      {
        type: 'pie',
        radius: '60%',
        data,
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' },
        },
      },
    ],
  }
})
</script>

<style scoped>
.chart {
  height: 300px;
}
</style>
