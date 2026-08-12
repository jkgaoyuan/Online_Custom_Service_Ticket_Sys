import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TrendChart from '@/components/reports/TrendChart.vue'

vi.mock('@/stores', () => ({
  useReportsStore: () => ({
    dateRange: ['2024-08-01', '2024-08-07'],
    trend: [],
    loading: false,
  }),
}))

vi.mock('@/api/reports', () => ({
  reportApi: {
    trend: vi.fn().mockResolvedValue({ data: [] }),
  },
}))

describe('TrendChart (TC-FE-050)', () => {
  it('空数据优雅降级', async () => {
    const wrapper = mount(TrendChart)
    await flushPromises()

    // 不应报错，渲染正常
    expect(wrapper.find('.el-card').exists()).toBe(true)
    expect(wrapper.find('.echarts-mock').exists()).toBe(true)
    expect(wrapper.find('.el-radio-group').exists()).toBe(true)
  })
})
