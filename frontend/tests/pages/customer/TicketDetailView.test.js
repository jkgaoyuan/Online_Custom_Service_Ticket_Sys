import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TicketDetailView from '@/views/customer/TicketDetailView.vue'
import { useTicketsStore } from '@/stores'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

vi.mock('@/stores', () => ({
  useTicketsStore: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: vi.fn(),
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: { success: vi.fn(), error: vi.fn() },
  }
})

describe('TicketDetailView (TC-FE-039)', () => {
  it('加载工单详情和回复', () => {
    const fetchTicket = vi.fn()
    const fetchReplies = vi.fn()
    useRoute.mockReturnValue({ params: { id: '123' } })
    useTicketsStore.mockReturnValue({
      currentTicket: { id: 123, title: 'Test', status: 'open', ticket_no: 'T-123', priority: 'P2', created_at: '2024-01-01', description: 'desc' },
      replies: [],
      fetchTicket,
      fetchReplies,
    })

    mount(TicketDetailView)
    expect(fetchTicket).toHaveBeenCalledWith('123')
    expect(fetchReplies).toHaveBeenCalledWith('123')
  })
})

describe('TicketDetailView (TC-FE-043)', () => {
  it('提交满意度评价', async () => {
    const submitSatisfaction = vi.fn().mockResolvedValue({})
    useRoute.mockReturnValue({ params: { id: '123' } })
    useTicketsStore.mockReturnValue({
      currentTicket: { id: 123, title: 'Test', status: 'closed', ticket_no: 'T-123', priority: 'P2', created_at: '2024-01-01', description: 'desc', satisfaction: null },
      replies: [],
      fetchTicket: vi.fn(),
      fetchReplies: vi.fn(),
      submitSatisfaction,
    })

    const wrapper = mount(TicketDetailView)
    await flushPromises()

    const ratingButtons = wrapper.findAll('.rating-buttons button')
    expect(ratingButtons.length).toBeGreaterThan(0)
    await ratingButtons[0].trigger('click')
    await flushPromises()

    const submitBtn = wrapper.findAll('.satisfaction-card button').find(b => b.text().trim() === '提交评价')
    expect(submitBtn).toBeDefined()
    await submitBtn.trigger('click')
    await flushPromises()

    expect(submitSatisfaction).toHaveBeenCalledWith('123', { rating: 'satisfied', note: '' })
    expect(ElMessage.success).toHaveBeenCalledWith('评价提交成功，感谢您的反馈！')
  })
})

describe('TicketDetailView (TC-FE-045)', () => {
  it('XSS 输入被转义不执行脚本', async () => {
    useRoute.mockReturnValue({ params: { id: '123' } })
    useTicketsStore.mockReturnValue({
      currentTicket: {
        id: 123,
        title: 'XSS Test',
        status: 'open',
        ticket_no: 'T-123',
        priority: 'P2',
        created_at: '2024-01-01',
        description: '<script>alert(1)</script>',
      },
      replies: [{ id: 1, content: '<img src=x onerror=alert(1)>', created_at: '2024-01-01' }],
      fetchTicket: vi.fn(),
      fetchReplies: vi.fn(),
    })

    const wrapper = mount(TicketDetailView)
    await flushPromises()

    expect(wrapper.html()).toContain('&lt;script&gt;alert(1)&lt;/script&gt;')
    expect(wrapper.html()).toContain('&lt;img src=x onerror=alert(1)&gt;')
    expect(wrapper.findAll('script')).toHaveLength(0)
  })
})
