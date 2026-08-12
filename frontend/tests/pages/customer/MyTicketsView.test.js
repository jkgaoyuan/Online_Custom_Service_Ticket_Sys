import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import MyTicketsView from '@/views/customer/MyTicketsView.vue'
import { useTicketsStore } from '@/stores'
import { useRouter } from 'vue-router'

vi.mock('@/stores', () => ({
  useTicketsStore: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: vi.fn(),
}))

describe('MyTicketsView (TC-FE-035)', () => {
  it('正常渲染工单列表', async () => {
    useTicketsStore.mockReturnValue({
      tickets: [
        { id: 1, ticket_no: 'T-001', title: 'Test Ticket', status: 'open', priority: 'P1', created_at: '2024-01-01T00:00:00' },
      ],
      pagination: { total: 1, page: 1, page_size: 20 },
      loading: false,
      fetchTickets: vi.fn(),
    })

    const wrapper = mount(MyTicketsView)
    await flushPromises()

    expect(wrapper.find('.el-table').exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'StatusBadge' }).exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'PriorityTag' }).exists()).toBe(true)
  })
})

describe('MyTicketsView (TC-FE-036)', () => {
  it('空数据表格为空', async () => {
    useTicketsStore.mockReturnValue({
      tickets: [],
      pagination: { total: 0, page: 1, page_size: 20 },
      loading: false,
      fetchTickets: vi.fn(),
    })

    const wrapper = mount(MyTicketsView)
    await flushPromises()

    expect(wrapper.findAll('.el-table__row')).toHaveLength(0)
  })
})

describe('MyTicketsView (TC-FE-037)', () => {
  it('分页切换触发重新加载', async () => {
    const fetchTickets = vi.fn()
    useTicketsStore.mockReturnValue({
      tickets: [],
      pagination: { total: 50, page: 1, page_size: 20 },
      loading: false,
      fetchTickets,
    })

    const wrapper = mount(MyTicketsView)
    await flushPromises()

    wrapper.vm.page = 2
    await wrapper.vm.load()

    expect(fetchTickets).toHaveBeenCalledWith({ page: 2, page_size: 20 })
  })
})

describe('MyTicketsView (TC-FE-038)', () => {
  it('点击查看跳转详情', async () => {
    const push = vi.fn()
    useRouter.mockReturnValue({ push })
    useTicketsStore.mockReturnValue({
      tickets: [
        { id: 42, ticket_no: 'T-042', title: 'Bug Report', status: 'open', priority: 'P2', created_at: '2024-01-01T00:00:00' },
      ],
      pagination: { total: 1, page: 1, page_size: 20 },
      loading: false,
      fetchTickets: vi.fn(),
    })

    const wrapper = mount(MyTicketsView)
    await flushPromises()

    await wrapper.find('button').trigger('click')
    expect(push).toHaveBeenCalledWith('/customer/tickets/42')
  })
})
