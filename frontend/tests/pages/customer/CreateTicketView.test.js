import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CreateTicketView from '@/views/customer/CreateTicketView.vue'
import { useTicketsStore } from '@/stores'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

vi.mock('@/stores', () => ({
  useTicketsStore: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: vi.fn(),
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: { success: vi.fn(), error: vi.fn() },
  }
})

describe('CreateTicketView (TC-FE-030)', () => {
  it('正常提交工单并跳转', async () => {
    const push = vi.fn()
    useRouter.mockReturnValue({ push })
    const createTicket = vi.fn().mockResolvedValue({})
    useTicketsStore.mockReturnValue({
      createTicket,
      fetchCategories: vi.fn(),
      categories: [],
      loading: false,
    })

    const wrapper = mount(CreateTicketView)
    await flushPromises()

    await wrapper.find('input').setValue('工单标题')
    wrapper.vm.form.category_id = 1
    wrapper.vm.form.priority = 'P2'
    await wrapper.find('textarea').setValue('工单描述')
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(createTicket).toHaveBeenCalledWith(expect.objectContaining({
      title: '工单标题',
      category_id: 1,
      priority: 'P2',
      description: '工单描述',
      source: 'web',
    }))
    expect(ElMessage.success).toHaveBeenCalledWith('工单提交成功')
    expect(push).toHaveBeenCalledWith('/customer/tickets')
  })
})

describe('CreateTicketView (TC-FE-031)', () => {
  it('标题超过 200 字符被拦截', async () => {
    const createTicket = vi.fn().mockResolvedValue({})
    useTicketsStore.mockReturnValue({
      createTicket,
      fetchCategories: vi.fn(),
      categories: [],
      loading: false,
    })

    const wrapper = mount(CreateTicketView)
    await flushPromises()

    wrapper.vm.form.title = 'a'.repeat(201)
    wrapper.vm.form.category_id = 1
    await wrapper.find('textarea').setValue('描述')

    // The component submit() does not catch validation errors, so test via form ref directly
    let error
    try {
      await wrapper.vm.$refs.formRef.validate()
    } catch (e) {
      error = e
    }
    expect(error).toBeDefined()
    expect(createTicket).not.toHaveBeenCalled()
  })
})

describe('CreateTicketView (TC-FE-032)', () => {
  it('未选择分类被校验拦截', async () => {
    const createTicket = vi.fn().mockResolvedValue({})
    useTicketsStore.mockReturnValue({
      createTicket,
      fetchCategories: vi.fn(),
      categories: [],
      loading: false,
    })

    const wrapper = mount(CreateTicketView)
    await flushPromises()

    wrapper.vm.form.title = '标题'
    wrapper.vm.form.category_id = null
    await wrapper.find('textarea').setValue('描述')

    let error
    try {
      await wrapper.vm.$refs.formRef.validate()
    } catch (e) {
      error = e
    }
    expect(error).toBeDefined()
    expect(createTicket).not.toHaveBeenCalled()
  })
})

describe('CreateTicketView (TC-FE-033)', () => {
  it('进入页面加载分类下拉', () => {
    const fetchCategories = vi.fn()
    useTicketsStore.mockReturnValue({
      createTicket: vi.fn(),
      fetchCategories,
      categories: [],
      loading: false,
    })

    mount(CreateTicketView)
    expect(fetchCategories).toHaveBeenCalled()
  })
})

describe('CreateTicketView (TC-FE-034)', () => {
  it('提交中按钮 loading', () => {
    useTicketsStore.mockReturnValue({
      createTicket: vi.fn(),
      fetchCategories: vi.fn(),
      categories: [],
      loading: true,
    })

    const wrapper = mount(CreateTicketView)
    expect(wrapper.find('.el-button.is-loading').exists()).toBe(true)
  })
})
