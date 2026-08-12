import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AgentPerformanceTable from '@/components/reports/AgentPerformanceTable.vue'

const createStore = (data, loading = false) => ({
  agentPerformance: data,
  loading,
})

vi.mock('@/stores', () => ({
  useReportsStore: vi.fn(),
}))

describe('AgentPerformanceTable (TC-FE-051)', () => {
  it('渲染性能表格', async () => {
    const { useReportsStore } = await import('@/stores')
    useReportsStore.mockReturnValue(
      createStore([
        {
          agent_name: '客服A',
          total_assigned: 45,
          resolved_count: 40,
          avg_first_resp_hours: 1.2,
          avg_resolution_hours: 4.5,
        },
        {
          agent_name: '客服B',
          total_assigned: 38,
          resolved_count: 35,
          avg_first_resp_hours: 2.1,
          avg_resolution_hours: 5.8,
        },
      ])
    )

    const wrapper = mount(AgentPerformanceTable)
    await flushPromises()

    expect(wrapper.find('.el-table').exists()).toBe(true)

    const rows = wrapper.findAll('.el-table__row')
    expect(rows.length).toBe(2)

    expect(wrapper.text()).toContain('客服A')
    expect(wrapper.text()).toContain('45')
    expect(wrapper.text()).toContain('40')
    expect(wrapper.text()).toContain('1.2')
    expect(wrapper.text()).toContain('4.5')

    expect(wrapper.text()).toContain('客服B')
    expect(wrapper.text()).toContain('38')
    expect(wrapper.text()).toContain('35')
  })

  it('空数据时显示空状态', async () => {
    const { useReportsStore } = await import('@/stores')
    useReportsStore.mockReturnValue(createStore([]))

    const wrapper = mount(AgentPerformanceTable)
    await flushPromises()

    expect(wrapper.find('.el-empty').exists()).toBe(true)
    expect(wrapper.text()).toContain('暂无数据')
  })
})
