import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AgentTicketsView from '@/views/agent/AgentTicketsView.vue'

const mockPush = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
}))

vi.mock('@/stores', () => ({
  useTicketsStore: () => ({
    tickets: [
      {
        id: 1,
        ticket_no: 'T-20240801-001',
        title: '测试工单1',
        status: 'open',
        priority: 'P1',
        requester: { username: 'user1' },
      },
      {
        id: 2,
        ticket_no: 'T-20240801-002',
        title: '测试工单2',
        status: 'in_progress',
        priority: 'P0',
        requester: { username: 'user2' },
      },
    ],
    pagination: { total: 2, page: 1, page_size: 20 },
    loading: false,
    fetchTickets: vi.fn(),
  }),
}))

describe('AgentTicketsView (TC-FE-046)', () => {
  it('渲染工单列表和分页', async () => {
    const wrapper = mount(AgentTicketsView)
    await flushPromises()

    expect(wrapper.find('h2').text()).toBe('客服工作台')
    expect(wrapper.find('.el-table').exists()).toBe(true)
    expect(wrapper.find('.el-pagination').exists()).toBe(true)

    const rows = wrapper.findAll('.el-table__row')
    expect(rows.length).toBe(2)
  })

  it('点击处理按钮跳转到详情页', async () => {
    const wrapper = mount(AgentTicketsView)
    await flushPromises()

    const buttons = wrapper.findAll('.el-button')
    const handleButton = buttons.find((b) => b.text().includes('处理'))
    expect(handleButton).toBeDefined()

    await handleButton.trigger('click')
    expect(mockPush).toHaveBeenCalledWith('/agent/tickets/1')
  })
})
