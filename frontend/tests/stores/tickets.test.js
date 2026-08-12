import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useTicketsStore } from '@/stores/tickets'

vi.mock('@/api/tickets', () => ({
  ticketApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    reply: vi.fn(),
    updateStatus: vi.fn(),
    assign: vi.fn(),
    transfer: vi.fn(),
    assist: vi.fn(),
    submitSatisfaction: vi.fn(),
  },
  replyApi: {
    list: vi.fn(),
  },
}))

vi.mock('@/api/categories', () => ({
  categoryApi: {
    list: vi.fn(),
  },
}))

import { ticketApi, replyApi } from '@/api/tickets'
import { categoryApi } from '@/api/categories'

describe('Tickets Store (TC-FE-015)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('returns created ticket data after createTicket', async () => {
    const mockTicket = { id: 1, title: '新工单', status: 'open' }
    ticketApi.create.mockResolvedValue({ data: mockTicket })

    const store = useTicketsStore()
    const result = await store.createTicket({ title: '新工单', category_id: 1 })

    expect(ticketApi.create).toHaveBeenCalledWith({
      title: '新工单',
      category_id: 1,
    })
    expect(result).toEqual(mockTicket)
  })
})

describe('Tickets Store (TC-FE-016)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('appends new reply to replies array after replyTicket', async () => {
    const mockReply = { id: 10, content: '回复内容', ticket_id: 1 }
    ticketApi.reply.mockResolvedValue({ data: mockReply })

    const store = useTicketsStore()
    store.currentTicket = { id: 1, title: '测试工单' }
    store.replies = [{ id: 9, content: '旧回复' }]

    const result = await store.replyTicket(1, { content: '回复内容' })

    expect(ticketApi.reply).toHaveBeenCalledWith(1, { content: '回复内容' })
    expect(store.replies).toHaveLength(2)
    expect(store.replies[1]).toEqual(mockReply)
    expect(result).toEqual(mockReply)
  })
})

describe('Tickets Store (TC-FE-017)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('updates currentTicket status after updateStatus', async () => {
    const updatedTicket = { id: 1, title: '测试', status: 'in_progress' }
    ticketApi.updateStatus.mockResolvedValue({ data: updatedTicket })

    const store = useTicketsStore()
    store.currentTicket = { id: 1, title: '测试', status: 'open' }

    const result = await store.updateStatus(1, 'in_progress')

    expect(ticketApi.updateStatus).toHaveBeenCalledWith(1, 'in_progress')
    expect(store.currentTicket.status).toBe('in_progress')
    expect(result).toEqual(updatedTicket)
  })
})

describe('Tickets Store (TC-FE-018)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('toggles loading state during fetchTickets', async () => {
    ticketApi.list.mockResolvedValue({
      data: { items: [], total: 0, page: 1, page_size: 20 },
    })

    const store = useTicketsStore()
    expect(store.loading).toBe(false)

    const promise = store.fetchTickets({ page: 1 })
    expect(store.loading).toBe(true)

    await promise
    expect(store.loading).toBe(false)
    expect(ticketApi.list).toHaveBeenCalledWith({ page: 1 })
  })
})

describe('Tickets Store (TC-FE-019)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('prepends collaboration record after assistTicket', async () => {
    const mockCollab = { id: 5, notes: '协助说明', agent_id: 2 }
    ticketApi.assist.mockResolvedValue({ data: mockCollab })

    const store = useTicketsStore()
    store.currentTicket = { id: 1, title: '测试', collaborations: [] }

    const result = await store.assistTicket(1, { notes: '协助说明' })

    expect(ticketApi.assist).toHaveBeenCalledWith(1, { notes: '协助说明' })
    expect(store.currentTicket.collaborations).toHaveLength(1)
    expect(store.currentTicket.collaborations[0]).toEqual(mockCollab)
    expect(result).toEqual(mockCollab)
  })
})
