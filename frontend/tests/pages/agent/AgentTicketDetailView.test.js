import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AgentTicketDetailView from '@/views/agent/AgentTicketDetailView.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '1' } }),
}))

vi.mock('@/stores', () => ({
  useTicketsStore: vi.fn(),
  useAuthStore: vi.fn(),
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
    title: '测试工单',
    status: 'in_progress',
    priority: 'P1',
    description: '问题描述',
    requester: { username: 'customer1' },
    collaborations: [],
    ...ticketOverrides,
  },
  replies: [
    { id: 1, content: '回复1', created_at: '2024-08-01 10:00', is_internal: false },
    { id: 2, content: '内部备注', created_at: '2024-08-01 11:00', is_internal: true },
  ],
  fetchTicket: vi.fn(),
  fetchReplies: vi.fn(),
  replyTicket: vi.fn(),
  updateStatus: vi.fn(),
  transferTicket: vi.fn(),
  assistTicket: vi.fn(),
})

const createAuthStore = () => ({
  userRole: 'agent',
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

describe('AgentTicketDetailView (TC-FE-AgentDetail)', () => {
  it('加载并渲染工单详情', async () => {
    const { useTicketsStore, useAuthStore } = await import('@/stores')
    const { useDispatchStore } = await import('@/stores/dispatch')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useAuthStore.mockReturnValue(createAuthStore())
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AgentTicketDetailView)
    await flushPromises()

    expect(wrapper.find('h2').text()).toBe('测试工单')
    expect(wrapper.find('.el-descriptions').exists()).toBe(true)
    expect(wrapper.text()).toContain('问题描述')
  })

  it('渲染回复记录并区分内部备注', async () => {
    const { useTicketsStore, useAuthStore } = await import('@/stores')
    const { useDispatchStore } = await import('@/stores/dispatch')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useAuthStore.mockReturnValue(createAuthStore())
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AgentTicketDetailView)
    await flushPromises()

    const timelineItems = wrapper.findAll('.el-timeline-item')
    expect(timelineItems.length).toBe(2)
    expect(wrapper.text()).toContain('内部')
  })

  it('点击标记已解决按钮更新状态', async () => {
    const { useTicketsStore, useAuthStore } = await import('@/stores')
    const { useDispatchStore } = await import('@/stores/dispatch')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useAuthStore.mockReturnValue(createAuthStore())
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AgentTicketDetailView)
    await flushPromises()

    const resolveBtn = wrapper.findAll('.el-button').find((b) => b.text().includes('标记已解决'))
    expect(resolveBtn).toBeDefined()
    await resolveBtn.trigger('click')
    await flushPromises()

    const store = useTicketsStore()
    expect(store.updateStatus).toHaveBeenCalledWith(1, 'resolved')
  })

  it('点击转交工单打开转交对话框', async () => {
    const { useTicketsStore, useAuthStore } = await import('@/stores')
    const { useDispatchStore } = await import('@/stores/dispatch')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useAuthStore.mockReturnValue(createAuthStore())
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AgentTicketDetailView, { attachTo: document.body })
    await flushPromises()

    const transferBtn = wrapper.findAll('.el-button').find((b) => b.text().includes('转交工单'))
    expect(transferBtn).toBeDefined()
    await transferBtn.trigger('click')
    await flushPromises()

    // 对话框应出现在 DOM 中
    const dialogs = document.querySelectorAll('.el-dialog')
    expect(dialogs.length).toBeGreaterThanOrEqual(1)
    expect(document.body.textContent).toContain('转交工单')

    wrapper.unmount()
  })

  it('点击请求协助打开协助对话框', async () => {
    const { useTicketsStore, useAuthStore } = await import('@/stores')
    const { useDispatchStore } = await import('@/stores/dispatch')
    useTicketsStore.mockReturnValue(createTicketsStore())
    useAuthStore.mockReturnValue(createAuthStore())
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AgentTicketDetailView, { attachTo: document.body })
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

  it('点击自动分派调用 dispatchStore.autoAssign', async () => {
    const { useTicketsStore, useAuthStore } = await import('@/stores')
    const { useDispatchStore } = await import('@/stores/dispatch')

    useTicketsStore.mockReturnValue(createTicketsStore({ status: 'open' }))
    useAuthStore.mockReturnValue(createAuthStore())
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AgentTicketDetailView)
    await flushPromises()

    const autoBtn = wrapper.findAll('.el-button').find((b) => b.text().includes('自动分派'))
    expect(autoBtn).toBeDefined()
    await autoBtn.trigger('click')
    await flushPromises()

    const dispatchStore = useDispatchStore()
    expect(dispatchStore.autoAssign).toHaveBeenCalledWith(1)
  })

  it('点击建议分配展示建议列表', async () => {
    const { useTicketsStore, useAuthStore } = await import('@/stores')
    const { useDispatchStore } = await import('@/stores/dispatch')

    useTicketsStore.mockReturnValue(createTicketsStore({ status: 'open' }))
    useAuthStore.mockReturnValue(createAuthStore())
    useDispatchStore.mockReturnValue(createDispatchStore())

    const wrapper = mount(AgentTicketDetailView)
    await flushPromises()

    const suggestBtn = wrapper.findAll('.el-button').find((b) => b.text().includes('建议分配'))
    expect(suggestBtn).toBeDefined()
    await suggestBtn.trigger('click')
    await flushPromises()

    expect(wrapper.find('.el-table').exists()).toBe(true)
    expect(wrapper.text()).toContain('客服B')
  })
})
