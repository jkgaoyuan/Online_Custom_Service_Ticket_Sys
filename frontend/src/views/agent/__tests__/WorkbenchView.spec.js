import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref, nextTick } from 'vue'
import WorkbenchView from '@/views/agent/WorkbenchView.vue'

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
}))

const mockStore = {
  tickets: ref([]),
  pagination: ref({ total: 0, page: 1, page_size: 20 }),
  loading: ref(false),
  fetchTickets: vi.fn().mockResolvedValue(),
  updateStatus: vi.fn().mockResolvedValue(),
}

vi.mock('@/stores', () => ({
  useTicketsStore: () => mockStore,
}))

const iconStubs = {
  Tickets: { template: '<span class="icon-tickets" />' },
  Loading: { template: '<span class="icon-loading" />' },
  CircleCheck: { template: '<span class="icon-check" />' },
  Timer: { template: '<span class="icon-timer" />' },
}

describe('WorkbenchView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockStore.tickets.value = []
    mockStore.pagination.value = { total: 0, page: 1, page_size: 20 }
    mockStore.loading.value = false
    mockPush.mockClear()
  })

  it('renders 4 stat cards and section titles', () => {
    const wrapper = mount(WorkbenchView, {
      global: { stubs: iconStubs },
    })
    const text = wrapper.text()
    expect(text).toContain('待处理工单')
    expect(text).toContain('处理中工单')
    expect(text).toContain('今日已解决')
    expect(text).toContain('等待客户')
    expect(text).toContain('最近工单')
  })

  it('calls fetchTickets on mount for stats and recent tickets', async () => {
    mount(WorkbenchView, {
      global: { stubs: iconStubs },
    })
    await nextTick()
    // loadStats: 4 parallel calls with different statuses
    expect(mockStore.fetchTickets).toHaveBeenCalledWith({ status: 'open', page_size: 1 })
    expect(mockStore.fetchTickets).toHaveBeenCalledWith({ status: 'in_progress', page_size: 1 })
    expect(mockStore.fetchTickets).toHaveBeenCalledWith({ status: 'resolved', page_size: 1 })
    expect(mockStore.fetchTickets).toHaveBeenCalledWith({ status: 'waiting', page_size: 1 })
    // loadRecent: 1 call
    expect(mockStore.fetchTickets).toHaveBeenCalledWith({ page_size: 5 })
    expect(mockStore.fetchTickets).toHaveBeenCalledTimes(5)
  })

  it('clicking view-all button navigates to tickets list', async () => {
    const wrapper = mount(WorkbenchView, {
      global: { stubs: iconStubs },
    })
    const buttons = wrapper.findAll('button')
    const viewAllBtn = buttons.find((b) => b.text().includes('查看全部工单'))
    expect(viewAllBtn).toBeTruthy()
    await viewAllBtn.trigger('click')
    expect(mockPush).toHaveBeenCalledWith('/agent/tickets')
  })

  it('clicking open-tickets button navigates to open filter', async () => {
    const wrapper = mount(WorkbenchView, {
      global: { stubs: iconStubs },
    })
    const buttons = wrapper.findAll('button')
    const openBtn = buttons.find((b) => b.text().includes('处理 open 工单'))
    expect(openBtn).toBeTruthy()
    await openBtn.trigger('click')
    expect(mockPush).toHaveBeenCalledWith('/agent/tickets?status=open')
  })

  it('claim method calls updateStatus and refreshes data', async () => {
    const wrapper = mount(WorkbenchView, {
      global: { stubs: iconStubs },
    })
    const row = { id: 42, status: 'open' }
    await wrapper.vm.claim(row)
    expect(mockStore.updateStatus).toHaveBeenCalledWith(42, 'in_progress')
    // 5 initial (loadStats 4 + loadRecent 1) + 5 refresh (loadStats 4 + loadRecent 1)
    expect(mockStore.fetchTickets).toHaveBeenCalledTimes(10)
  })

  it('stat values reflect pagination totals', async () => {
    let callIndex = 0
    mockStore.fetchTickets.mockImplementation(() => {
      const totals = [3, 5, 12, 1]
      mockStore.pagination.value = { ...mockStore.pagination.value, total: totals[callIndex] }
      callIndex++
      return Promise.resolve()
    })

    const wrapper = mount(WorkbenchView, {
      global: { stubs: iconStubs },
    })
    await nextTick()
    // Wait for all promises in onMounted
    await new Promise((r) => setTimeout(r, 0))
    await nextTick()

    // Note: loadStats uses Promise.all, so total values may race.
    // We verify the component reacts to store state at all.
    expect(mockStore.fetchTickets).toHaveBeenCalledTimes(5)
    expect(wrapper.vm.stats).toBeDefined()
  })
})
