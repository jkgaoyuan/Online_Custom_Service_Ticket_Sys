import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AdminTicketDetailView from '@/views/admin/AdminTicketDetailView.vue'

vi.mock('vue-router', async () => {
  const actual = await vi.importActual('vue-router')
  return {
    ...actual,
    useRoute: () => ({ params: { id: '1' } }),
    useRouter: vi.fn(() => ({ push: vi.fn() })),
  }
})

vi.mock('@/stores', () => ({
  useTicketsStore: vi.fn(),
  useDispatchStore: vi.fn(),
}))

vi.mock('@/stores/dispatch', () => ({
  useDispatchStore: vi.fn(),
}))

vi.mock('@/api/tickets', () => ({
  ticketApi: {
    getAgents: vi.fn().mockResolvedValue({
      data: [
        { id: 2, username: 'agent2' },
        { id: 3, username: 'agent3' },
      ],
    }),
  },
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  }
})

const createTicketsStore = (ticketOverrides = {}) => ({
  currentTicket: {
    id: 1,
    ticket_no: 'T-001',
    title: 'Admin 测试工单',
    status: 'in_progress',
    priority: 'P1',
    description: '问题描述',
    requester: { username: 'customer1' },
    assignee: { username: 'agent1' },
    collaborations: [],
    ...ticketOverrides,
  },
  replies: [
    { id: 1, content: '回复1', created_at: '2024-08-01 10:00', is_internal: false, author: { username: 'agent1', role: 'agent' } },
    { id: 2, content: '内部备注', created_at: '2024-08-01 11:00', is_internal: true, author: { username: 'admin1', role: 'admin' } },
  ],
  fetchTicket: vi.fn(),
  fetchReplies: vi.fn(),
  replyTicket: vi.fn(),
  updateStatus: vi.fn(),
  transferTicket: vi.fn(),
  assistTicket: vi.fn(),
  loadCollaborations: vi.fn(),
})

const createDispatchStore = (overrides = {}) => ({
  suggestions: [
    { agent_id: 2, agent_name: '客服B', score: 95, current_load: 3, reason: '擅长此类问题' },
  ],
  fetchSuggestions: vi.fn(),
  autoAssign: vi.fn().mockResolvedValue({ assigned: true }),
  manualAssign: vi.fn(),
  ...overrides,
})

describe('AdminTicketDetailView (TC-FE-057)', () => {
  it('加载并渲染工单详情', async () => {
    const { useTicketsStore, useDispatchStore } = await import('@/stores')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AdminTicketDetailView)
    await flushPromises()

    expect(wrapper.find('h2').text()).toBe('Admin 测试工单')
    expect(wrapper.find('.el-descriptions').exists()).toBe(true)
    expect(wrapper.text()).toContain('问题描述')
    expect(wrapper.text()).toContain('agent1')
    expect(wrapper.text()).toContain('customer1')
  })
})

describe('AdminTicketDetailView (TC-FE-058)', () => {
  it('点击标记已解决按钮更新状态', async () => {
    const { useTicketsStore, useDispatchStore } = await import('@/stores')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AdminTicketDetailView)
    await flushPromises()

    const resolveBtn = wrapper.findAll('.el-button').find((b) => b.text().includes('标记已解决'))
    expect(resolveBtn).toBeDefined()
    await resolveBtn.trigger('click')
    await flushPromises()

    const store = useTicketsStore()
    expect(store.updateStatus).toHaveBeenCalledWith(1, 'resolved')
  })

  it('点击等待客户按钮更新状态', async () => {
    const { useTicketsStore, useDispatchStore } = await import('@/stores')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AdminTicketDetailView)
    await flushPromises()

    const waitBtn = wrapper.findAll('.el-button').find((b) => b.text().includes('等待客户'))
    expect(waitBtn).toBeDefined()
    await waitBtn.trigger('click')
    await flushPromises()

    const store = useTicketsStore()
    expect(store.updateStatus).toHaveBeenCalledWith(1, 'waiting')
  })

  it('resolved 状态的工单禁用标记已解决和等待客户按钮', async () => {
    const { useTicketsStore, useDispatchStore } = await import('@/stores')
    useTicketsStore.mockReturnValue(createTicketsStore({ status: 'resolved' }))
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AdminTicketDetailView)
    await flushPromises()

    expect(wrapper.vm.canResolve).toBe(false)
    expect(wrapper.vm.canWait).toBe(false)
  })
})

describe('AdminTicketDetailView (TC-FE-059)', () => {
  it('点击转交工单打开转交对话框', async () => {
    const { useTicketsStore, useDispatchStore } = await import('@/stores')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AdminTicketDetailView, { attachTo: document.body })
    await flushPromises()

    const transferBtn = wrapper.findAll('.el-button').find((b) => b.text().includes('转交工单'))
    expect(transferBtn).toBeDefined()
    await transferBtn.trigger('click')
    await flushPromises()

    const dialogs = document.querySelectorAll('.el-dialog')
    expect(dialogs.length).toBeGreaterThanOrEqual(1)
    expect(document.body.textContent).toContain('转交工单')

    wrapper.unmount()
  })

  it('点击请求协助打开协助对话框', async () => {
    const { useTicketsStore, useDispatchStore } = await import('@/stores')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AdminTicketDetailView, { attachTo: document.body })
    await flushPromises()

    const assistBtn = wrapper.findAll('.el-button').find((b) => b.text().includes('请求协助'))
    expect(assistBtn).toBeDefined()
    await assistBtn.trigger('click')
    await flushPromises()

    const dialogs = document.querySelectorAll('.el-dialog')
    expect(dialogs.length).toBeGreaterThanOrEqual(1)
    expect(document.body.textContent).toContain('请求协助')

    wrapper.unmount()
  })
})

describe('AdminTicketDetailView (TC-FE-060)', () => {
  it('点击自动分派调用 dispatchStore.autoAssign', async () => {
    const { useTicketsStore, useDispatchStore } = await import('@/stores')

    useTicketsStore.mockReturnValue(createTicketsStore({ status: 'open', assignee: null }))
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AdminTicketDetailView)
    await flushPromises()

    const autoBtn = wrapper.findAll('.el-button').find((b) => b.text().includes('自动分派'))
    expect(autoBtn).toBeDefined()
    await autoBtn.trigger('click')
    await flushPromises()

    const dispatchStore = useDispatchStore()
    expect(dispatchStore.autoAssign).toHaveBeenCalledWith(1)
  })

  it('open 状态工单显示建议分配和自动分派按钮', async () => {
    const { useTicketsStore, useDispatchStore } = await import('@/stores')

    useTicketsStore.mockReturnValue(createTicketsStore({ status: 'open', assignee: null }))
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AdminTicketDetailView)
    await flushPromises()

    const buttons = wrapper.findAll('.el-button').map((b) => b.text())
    expect(buttons.some((t) => t.includes('建议分配'))).toBe(true)
    expect(buttons.some((t) => t.includes('自动分派'))).toBe(true)
  })

  it('in_progress 状态工单禁用分派按钮', async () => {
    const { useTicketsStore, useDispatchStore } = await import('@/stores')

    useTicketsStore.mockReturnValue(createTicketsStore({ status: 'in_progress' }))
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AdminTicketDetailView)
    await flushPromises()

    expect(wrapper.vm.canDispatch).toBe(false)
  })
})
