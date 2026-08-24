import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AdminTicketsView from '@/views/admin/AdminTicketsView.vue'
import { useTicketsStore } from '@/stores'

vi.mock('@/stores', () => ({
  useTicketsStore: vi.fn(),
}))

vi.mock('vue-router', async () => {
  const actual = await vi.importActual('vue-router')
  return {
    ...actual,
    useRouter: vi.fn(() => ({ push: vi.fn() })),
  }
})

const createStore = (overrides = {}) => ({
  tickets: [
    {
      id: 1,
      ticket_no: 'TK-20240801-0001',
      title: '无法登录',
      status: 'open',
      priority: 'P1',
      requester: { username: 'customer1' },
      assignee: { username: 'agent1' },
      created_at: '2024-08-01T10:00:00Z',
    },
    {
      id: 2,
      ticket_no: 'TK-20240801-0002',
      title: '页面加载慢',
      status: 'in_progress',
      priority: 'P2',
      requester: { username: 'customer2' },
      assignee: null,
      created_at: '2024-08-02T11:00:00Z',
    },
  ],
  loading: false,
  pagination: { total: 2, page: 1, page_size: 20 },
  fetchTickets: vi.fn(),
  ...overrides,
})

describe('AdminTicketsView (TC-FE-061)', () => {
  it('加载并渲染工单列表', async () => {
    useTicketsStore.mockReturnValue(createStore())

    const wrapper = mount(AdminTicketsView)
    await flushPromises()

    expect(wrapper.find('.el-table').exists()).toBe(true)
    expect(wrapper.text()).toContain('无法登录')
    expect(wrapper.text()).toContain('页面加载慢')
    expect(wrapper.text()).toContain('未分配')
  })

  it('筛选状态切换触发 fetchTickets', async () => {
    const store = createStore()
    useTicketsStore.mockReturnValue(store)

    const wrapper = mount(AdminTicketsView)
    await flushPromises()

    // 直接修改 filterStatus 并触发 handleFilter
    wrapper.vm.filterStatus = 'open'
    await wrapper.vm.handleFilter()
    await flushPromises()

    expect(store.fetchTickets).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'open', page: 1, page_size: 20 })
    )
  })

  it('筛选优先级切换触发 fetchTickets', async () => {
    const store = createStore()
    useTicketsStore.mockReturnValue(store)

    const wrapper = mount(AdminTicketsView)
    await flushPromises()

    wrapper.vm.filterPriority = 'P1'
    await wrapper.vm.handleFilter()
    await flushPromises()

    expect(store.fetchTickets).toHaveBeenCalledWith(
      expect.objectContaining({ priority: 'P1', page: 1, page_size: 20 })
    )
  })
})

describe('AdminTicketsView (TC-FE-062)', () => {
  it('分页切换触发 fetchTickets', async () => {
    const store = createStore()
    useTicketsStore.mockReturnValue(store)

    const wrapper = mount(AdminTicketsView)
    await flushPromises()

    wrapper.vm.currentPage = 2
    await wrapper.vm.handleFilter()
    await flushPromises()

    expect(store.fetchTickets).toHaveBeenCalledWith(
      expect.objectContaining({ page: 2, page_size: 20 })
    )
  })

  it('空数据时表格无行', async () => {
    useTicketsStore.mockReturnValue(createStore({ tickets: [], pagination: { total: 0, page: 1, page_size: 20 } }))

    const wrapper = mount(AdminTicketsView)
    await flushPromises()

    const rows = wrapper.findAll('.el-table__row')
    expect(rows.length).toBe(0)
    expect(wrapper.find('.el-pagination').text()).toContain('Total: 0')
  })

  it('点击查看按钮触发路由跳转', async () => {
    const { useRouter } = await import('vue-router')
    const routerPush = vi.fn()
    useRouter.mockReturnValue({ push: routerPush })

    useTicketsStore.mockReturnValue(createStore())

    const wrapper = mount(AdminTicketsView)
    await flushPromises()

    const viewBtn = wrapper.findAll('.el-button').find((b) => b.text().includes('查看'))
    expect(viewBtn).toBeDefined()
    await viewBtn.trigger('click')

    expect(routerPush).toHaveBeenCalledWith('/admin/tickets/1')
  })
})
