import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { reactive, nextTick } from 'vue'
import ReportsView from '@/views/admin/ReportsView.vue'

const createStore = () => reactive({
  activeTab: 'overview',
  loading: false,
  dateRange: ['2024-08-01', '2024-08-07'],
  exportTask: null,
  exporting: false,
  exportFormat: null,
  overview: null,
  agentPerformance: [],
  categoryDistribution: [],
  trend: [],
  satisfaction: null,
  fetchCurrentTab: vi.fn(),
  submitExport: vi.fn().mockResolvedValue('task-123'),
  pollExportStatus: vi.fn().mockResolvedValue({ status: 'completed', download_url: '/download/1' }),
})

vi.mock('@/stores', () => ({
  useReportsStore: vi.fn(),
}))

vi.mock('@/api', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: new Blob(['test']) }),
  },
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  }
})

describe('ReportsView (TC-FE-054)', () => {
  it('切换报表 Tab 渲染对应组件', async () => {
    const { useReportsStore } = await import('@/stores')
    const store = createStore()
    useReportsStore.mockReturnValue(store)

    const wrapper = mount(ReportsView)
    await flushPromises()

    // 默认 overview tab
    expect(wrapper.text()).toContain('综合概览')
    expect(wrapper.findComponent({ name: 'OverviewPanel' }).exists()).toBe(true)

    // 点击客服绩效 tab
    const agentTab = wrapper.findAll('.el-tabs__item').find((t) => t.text().includes('客服绩效'))
    expect(agentTab).toBeDefined()
    await agentTab.trigger('click')
    await flushPromises()

    store.activeTab = 'agent_performance'
    await nextTick()

    expect(wrapper.findComponent({ name: 'AgentPerformanceTable' }).exists()).toBe(true)

    // 点击满意度 tab
    store.activeTab = 'satisfaction'
    await nextTick()
    expect(wrapper.findComponent({ name: 'SatisfactionPanel' }).exists()).toBe(true)

    // 点击时段趋势 tab
    store.activeTab = 'trend'
    await nextTick()
    expect(wrapper.findComponent({ name: 'TrendChart' }).exists()).toBe(true)
  })
})
