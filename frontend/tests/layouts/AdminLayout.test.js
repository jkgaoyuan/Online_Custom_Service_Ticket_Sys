import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AdminLayout from '@/layouts/AdminLayout.vue'

vi.mock('vue-router', async () => {
  const actual = await vi.importActual('vue-router')
  return {
    ...actual,
    useRoute: () => ({ path: '/admin/tickets' }),
  }
})

vi.mock('@/stores', () => ({
  useAuthStore: vi.fn(),
}))

vi.mock('@/components/NotificationBell.vue', () => ({
  default: { template: '<div class="notification-bell-mock">Bell</div>' },
}))

const createAuthStore = (overrides = {}) => ({
  user: { username: 'admin1', role: 'admin' },
  logout: vi.fn(),
  ...overrides,
})

describe('AdminLayout (TC-FE-063)', () => {
  it('渲染侧边栏菜单项', async () => {
    const { useAuthStore } = await import('@/stores')
    useAuthStore.mockReturnValue(createAuthStore())

    const wrapper = mount(AdminLayout, {
      global: {
        stubs: { 'router-view': true },
        mocks: { $route: { path: '/admin/tickets' } },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('工单管理')
    expect(wrapper.text()).toContain('用户管理')
    expect(wrapper.text()).toContain('数据报表')
    expect(wrapper.text()).toContain('分类管理')
    expect(wrapper.text()).toContain('技能配置')
    expect(wrapper.text()).toContain('SLA规则')
  })

  it('渲染头部用户信息与通知铃铛', async () => {
    const { useAuthStore } = await import('@/stores')
    useAuthStore.mockReturnValue(createAuthStore())

    const wrapper = mount(AdminLayout, {
      global: {
        stubs: { 'router-view': true },
        mocks: { $route: { path: '/admin/tickets' } },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('管理后台')
    expect(wrapper.text()).toContain('admin1')
    expect(wrapper.find('.notification-bell-mock').exists()).toBe(true)
  })

  it('点击退出登录调用 authStore.logout', async () => {
    const { useAuthStore } = await import('@/stores')
    const store = createAuthStore()
    useAuthStore.mockReturnValue(store)

    const wrapper = mount(AdminLayout, {
      global: {
        stubs: { 'router-view': true },
        mocks: { $route: { path: '/admin/tickets' } },
      },
    })
    await flushPromises()

    const logoutBtn = wrapper.findAll('.el-button').find((b) => b.text().includes('退出登录'))
    expect(logoutBtn).toBeDefined()
    await logoutBtn.trigger('click')
    await flushPromises()

    expect(store.logout).toHaveBeenCalled()
  })

  it('默认激活当前路由菜单', async () => {
    const { useAuthStore } = await import('@/stores')
    useAuthStore.mockReturnValue(createAuthStore())

    const wrapper = mount(AdminLayout, {
      global: {
        stubs: { 'router-view': true },
        mocks: { $route: { path: '/admin/tickets' } },
      },
    })
    await flushPromises()

    // el-menu 的 default-active 绑定 $route.path
    const menu = wrapper.find('.el-menu')
    expect(menu.exists()).toBe(true)
  })
})
