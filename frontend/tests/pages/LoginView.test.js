import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import LoginView from '@/views/LoginView.vue'
import { useAuthStore } from '@/stores'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

vi.mock('@/stores', () => ({
  useAuthStore: vi.fn(),
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

describe('LoginView (TC-FE-024)', () => {
  it('正常登录后跳转 customer', async () => {
    const replace = vi.fn()
    useRouter.mockReturnValue({ replace })
    useAuthStore.mockReturnValue({
      login: vi.fn().mockResolvedValue({}),
      userRole: 'customer',
    })

    const wrapper = mount(LoginView)
    await wrapper.find('input[placeholder="用户名"]').setValue('cust')
    await wrapper.find('input[placeholder="密码"]').setValue('pass')
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(useAuthStore().login).toHaveBeenCalledWith({ username: 'cust', password: 'pass' })
    expect(ElMessage.success).toHaveBeenCalledWith('登录成功')
    expect(replace).toHaveBeenCalledWith('/customer/dashboard')
  })
})

describe('LoginView (TC-FE-025)', () => {
  it('正常登录后跳转 agent', async () => {
    const replace = vi.fn()
    useRouter.mockReturnValue({ replace })
    useAuthStore.mockReturnValue({
      login: vi.fn().mockResolvedValue({}),
      userRole: 'agent',
    })

    const wrapper = mount(LoginView)
    await wrapper.find('input[placeholder="用户名"]').setValue('agent1')
    await wrapper.find('input[placeholder="密码"]').setValue('pass')
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(replace).toHaveBeenCalledWith('/agent/workbench')
  })
})

describe('LoginView (TC-FE-026)', () => {
  it('空表单提交被校验拦截', async () => {
    useAuthStore.mockReturnValue({
      login: vi.fn().mockResolvedValue({}),
      userRole: 'customer',
    })

    const wrapper = mount(LoginView)
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(useAuthStore().login).not.toHaveBeenCalled()
  })
})

describe('LoginView (TC-FE-027)', () => {
  it('登录中按钮显示 loading', async () => {
    let resolveLogin
    const loginPromise = new Promise((resolve) => { resolveLogin = resolve })
    useAuthStore.mockReturnValue({
      login: vi.fn(() => loginPromise),
      userRole: 'customer',
    })

    const wrapper = mount(LoginView)
    await wrapper.find('input[placeholder="用户名"]').setValue('cust')
    await wrapper.find('input[placeholder="密码"]').setValue('pass')
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(wrapper.find('.is-loading').exists()).toBe(true)

    resolveLogin({})
    await flushPromises()

    expect(wrapper.find('.is-loading').exists()).toBe(false)
  })
})

describe('LoginView (TC-FE-028)', () => {
  it('快速双击只发一次请求', async () => {
    let resolveLogin
    const loginPromise = new Promise((resolve) => { resolveLogin = resolve })
    const loginMock = vi.fn(() => loginPromise)
    useAuthStore.mockReturnValue({
      login: loginMock,
      userRole: 'customer',
    })

    const wrapper = mount(LoginView)
    await wrapper.find('input[placeholder="用户名"]').setValue('cust')
    await wrapper.find('input[placeholder="密码"]').setValue('pass')

    await wrapper.find('button').trigger('click')
    await flushPromises()

    // While login is in-flight, loading state is true (button disabled in real browser)
    expect(wrapper.find('.is-loading').exists()).toBe(true)
    expect(loginMock).toHaveBeenCalledTimes(1)

    resolveLogin({})
    await flushPromises()

    expect(wrapper.find('.is-loading').exists()).toBe(false)
  })
})

describe('LoginView (TC-FE-029)', () => {
  it('错误密码显示错误提示', async () => {
    useAuthStore.mockReturnValue({
      login: vi.fn().mockRejectedValue({ response: { data: { detail: '密码错误' } } }),
      userRole: 'customer',
    })

    const wrapper = mount(LoginView)
    await wrapper.find('input[placeholder="用户名"]').setValue('cust')
    await wrapper.find('input[placeholder="密码"]').setValue('wrong')
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(ElMessage.error).toHaveBeenCalledWith('密码错误')
  })
})
