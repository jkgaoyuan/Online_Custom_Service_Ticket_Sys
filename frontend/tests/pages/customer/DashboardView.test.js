import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import DashboardView from '@/views/customer/DashboardView.vue'

vi.mock('vue-router', async () => {
  const actual = await vi.importActual('vue-router')
  return {
    ...actual,
    useRouter: vi.fn(() => ({ push: vi.fn() })),
  }
})

vi.mock('@/stores', () => ({
  useTicketsStore: vi.fn(),
  useAuthStore: vi.fn(),
}))

const createTicketsStore = (overrides = {}) => ({
  tickets: [
    {
      id: 1,
      ticket_no: 'TK-20240801-0001',
      title: '无法登录',
      status: 'open',
      priority: 'P1',
      created_at: '2024-08-01T10:00:00Z',
      satisfaction: null,
    },
    {
      id: 2,
      ticket_no: 'TK-20240801-0002',
      title: '页面加载慢',
      status: 'in_progress',
      priority: 'P2',
      created_at: '2024-08-02T11:00:00Z',
      satisfaction: null,
    },
    {
      id: 3,
      ticket_no: 'TK-20240801-0003',
      title: '已关闭问题',
      status: 'closed',
      priority: 'P3',
      created_at: '2024-08-03T12:00:00Z',
      satisfaction: 'satisfied',
    },
  ],
  loading: false,
  fetchTickets: vi.fn(),
  ...overrides,
})

const createAuthStore = (overrides = {}) => ({
  user: { username: 'customer1', role: 'customer' },
  ...overrides,
})

describe('DashboardView (TC-FE-064)', () => {
  it('渲染欢迎语与用户名', async () => {
    const { useTicketsStore, useAuthStore } = await import('@/stores')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useAuthStore.mockReturnValue(createAuthStore())

    const wrapper = mount(DashboardView)
    await flushPromises()

    expect(wrapper.text()).toContain('欢迎回来，customer1')
    expect(wrapper.text()).toContain('这里是您的服务概览，如需帮助可随时提交工单。')
  })

  it('渲染统计卡片', async () => {
    const { useTicketsStore, useAuthStore } = await import('@/stores')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useAuthStore.mockReturnValue(createAuthStore())

    const wrapper = mount(DashboardView)
    await flushPromises()

    // 3 tickets total
    expect(wrapper.text()).toContain('全部工单')
    // open + in_progress + waiting = 2 pending
    expect(wrapper.text()).toContain('处理中')
    // resolved + closed = 1 closed
    expect(wrapper.text()).toContain('已关闭')
    // closed without satisfaction = 0 pending rating (ticket 3 has satisfaction)
    expect(wrapper.text()).toContain('待评价')
  })

  it('未登录时不显示用户名', async () => {
    const { useTicketsStore, useAuthStore } = await import('@/stores')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useAuthStore.mockReturnValue(createAuthStore({ user: null }))

    const wrapper = mount(DashboardView)
    await flushPromises()

    expect(wrapper.text()).toContain('欢迎回来，客户')
  })

  it('点击提交新工单跳转', async () => {
    const { useRouter } = await import('vue-router')
    const routerPush = vi.fn()
    useRouter.mockReturnValue({ push: routerPush })

    const { useTicketsStore, useAuthStore } = await import('@/stores')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useAuthStore.mockReturnValue(createAuthStore())

    const wrapper = mount(DashboardView)
    await flushPromises()

    const newBtn = wrapper.findAll('.el-button').find((b) => b.text().includes('提交新工单'))
    expect(newBtn).toBeDefined()
    await newBtn.trigger('click')

    expect(routerPush).toHaveBeenCalledWith('/customer/tickets/new')
  })
})

describe('DashboardView (TC-FE-065)', () => {
  it('渲染最近工单列表', async () => {
    const { useTicketsStore, useAuthStore } = await import('@/stores')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useAuthStore.mockReturnValue(createAuthStore())

    const wrapper = mount(DashboardView)
    await flushPromises()

    expect(wrapper.text()).toContain('最近工单')
    expect(wrapper.text()).toContain('无法登录')
    expect(wrapper.text()).toContain('页面加载慢')
  })

  it('空数据时显示空状态', async () => {
    const { useTicketsStore, useAuthStore } = await import('@/stores')
    useTicketsStore.mockReturnValue(createTicketsStore({ tickets: [] }))
    useAuthStore.mockReturnValue(createAuthStore())

    const wrapper = mount(DashboardView)
    await flushPromises()

    expect(wrapper.find('.el-empty').exists()).toBe(true)
    expect(wrapper.text()).toContain('暂无工单，点击上方按钮提交您的问题')
  })

  it('点击查看全部跳转', async () => {
    const { useRouter } = await import('vue-router')
    const routerPush = vi.fn()
    useRouter.mockReturnValue({ push: routerPush })

    const { useTicketsStore, useAuthStore } = await import('@/stores')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useAuthStore.mockReturnValue(createAuthStore())

    const wrapper = mount(DashboardView)
    await flushPromises()

    const viewAllBtn = wrapper.findAll('.el-button').find((b) => b.text().includes('查看全部'))
    expect(viewAllBtn).toBeDefined()
    await viewAllBtn.trigger('click')

    expect(routerPush).toHaveBeenCalledWith('/customer/tickets')
  })

  it('点击工单查看跳转', async () => {
    const { useRouter } = await import('vue-router')
    const routerPush = vi.fn()
    useRouter.mockReturnValue({ push: routerPush })

    const { useTicketsStore, useAuthStore } = await import('@/stores')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useAuthStore.mockReturnValue(createAuthStore())

    const wrapper = mount(DashboardView)
    await flushPromises()

    const viewBtns = wrapper.findAll('.el-table__cell .el-button').filter((b) => b.text().includes('查看'))
    expect(viewBtns.length).toBeGreaterThan(0)
    await viewBtns[0].trigger('click')

    expect(routerPush).toHaveBeenCalledWith('/customer/tickets/1')
  })
})
