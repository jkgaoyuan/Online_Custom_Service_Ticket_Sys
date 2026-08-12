import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import OverviewPanel from '@/components/reports/OverviewPanel.vue'

const createStore = (overview) => ({
  overview,
})

vi.mock('@/stores', () => ({
  useReportsStore: vi.fn(),
}))

describe('OverviewPanel (TC-FE-048)', () => {
  it('渲染指标卡片', async () => {
    const { useReportsStore } = await import('@/stores')
    useReportsStore.mockReturnValue(
      createStore({
        total_tickets: 128,
        today_new: 5,
        week_new: 32,
        month_new: 98,
        sla_compliance_rate: 0.956,
        avg_satisfaction: 4.32,
        status_distribution: {
          open: 10,
          in_progress: 20,
          waiting: 5,
          resolved: 80,
          closed: 13,
        },
      })
    )

    const wrapper = mount(OverviewPanel)
    await flushPromises()

    expect(wrapper.text()).toContain('工单总量')
    expect(wrapper.text()).toContain('128')
    expect(wrapper.text()).toContain('今日新增')
    expect(wrapper.text()).toContain('5')
    expect(wrapper.text()).toContain('本周新增')
    expect(wrapper.text()).toContain('32')
    expect(wrapper.text()).toContain('本月新增')
    expect(wrapper.text()).toContain('98')

    expect(wrapper.text()).toContain('SLA 达标率')
    expect(wrapper.text()).toContain('95.6%')
    expect(wrapper.text()).toContain('平均满意度')
    expect(wrapper.text()).toContain('4.32')

    // 图表区域应存在（vue-echarts 被 mock 为空 div）
    expect(wrapper.find('.echarts-mock').exists()).toBe(true)
  })

  it('无数据时显示空状态', async () => {
    const { useReportsStore } = await import('@/stores')
    useReportsStore.mockReturnValue(createStore(null))

    const wrapper = mount(OverviewPanel)
    await flushPromises()

    expect(wrapper.find('.el-empty').exists()).toBe(true)
    expect(wrapper.text()).toContain('暂无数据')
  })
})
