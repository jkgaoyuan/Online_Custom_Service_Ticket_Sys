import { describe, it, expect, vi } from 'vitest'
import { createRouter, createWebHistory } from 'vue-router'
import { mount } from '@vue/test-utils'
import { useAuthStore } from '@/stores'
import CustomerLayout from '@/layouts/CustomerLayout.vue'

vi.mock('@/stores', () => ({
  useAuthStore: vi.fn(),
}))

const Dummy = { template: '<div />' }

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'Login', component: Dummy, meta: { requiresAuth: false } },
  {
    path: '/customer',
    name: 'CustomerLayout',
    component: Dummy,
    meta: { requiresAuth: true, role: 'customer' },
    redirect: '/customer/dashboard',
    children: [
      { path: 'dashboard', name: 'CustomerDashboard', component: Dummy },
      { path: 'tickets/new', name: 'CreateTicket', component: Dummy },
      { path: 'tickets', name: 'MyTickets', component: Dummy },
      { path: 'tickets/:id', name: 'CustomerTicketDetail', component: Dummy },
    ],
  },
  {
    path: '/agent',
    name: 'AgentLayout',
    component: Dummy,
    meta: { requiresAuth: true, role: 'agent' },
    redirect: '/agent/workbench',
    children: [
      { path: 'workbench', name: 'AgentWorkbench', component: Dummy },
      { path: 'tickets', name: 'AgentTickets', component: Dummy },
      { path: 'tickets/:id', name: 'AgentTicketDetail', component: Dummy },
    ],
  },
  {
    path: '/admin',
    name: 'AdminLayout',
    component: Dummy,
    meta: { requiresAuth: true, role: 'admin' },
    redirect: '/admin/users',
    children: [
      { path: 'users', name: 'AdminUsers', component: Dummy },
      { path: 'reports', name: 'AdminReports', component: Dummy },
    ],
  },
]

function createTestRouter() {
  const router = createRouter({
    history: createWebHistory(),
    routes,
  })

  router.beforeEach((to, from, next) => {
    const authStore = useAuthStore()

    if (to.path === '/login' && authStore.isLoggedIn) {
      const role = authStore.userRole
      if (role === 'customer') return next('/customer/dashboard')
      if (role === 'agent') return next('/agent/workbench')
      if (role === 'admin' || role === 'supervisor') return next('/admin/users')
      authStore.clearAuth()
      return next()
    }

    if (to.meta.requiresAuth && !authStore.isLoggedIn) {
      return next('/login')
    }

    if (to.meta.role && authStore.isLoggedIn) {
      const requiredRole = to.meta.role
      const userRole = authStore.userRole

      if (requiredRole === 'admin' && ['admin', 'supervisor'].includes(userRole)) {
        return next()
      }

      if (requiredRole !== userRole) {
        return next('/login')
      }
    }

    next()
  })

  return router
}

describe('Router Guard (TC-FE-006)', () => {
  it('未认证访问受保护路由跳转登录', async () => {
    useAuthStore.mockReturnValue({ isLoggedIn: false, userRole: null, clearAuth: vi.fn() })
    const router = createTestRouter()
    await router.push('/customer/dashboard')
    expect(router.currentRoute.value.path).toBe('/login')
  })
})

describe('Router Guard (TC-FE-007)', () => {
  it('已登录 customer 访问登录页跳转仪表盘', async () => {
    useAuthStore.mockReturnValue({ isLoggedIn: true, userRole: 'customer', clearAuth: vi.fn() })
    const router = createTestRouter()
    await router.push('/login')
    expect(router.currentRoute.value.path).toBe('/customer/dashboard')
  })
})

describe('Router Guard (TC-FE-008)', () => {
  it('agent 越权访问 admin 路由被拦截', async () => {
    useAuthStore.mockReturnValue({ isLoggedIn: true, userRole: 'agent', clearAuth: vi.fn() })
    const router = createTestRouter()
    await router.push('/admin/users')
    // Guard redirects to /login first, then the /login guard redirects agent to /agent/workbench
    expect(router.currentRoute.value.path).toBe('/agent/workbench')
  })
})

describe('Router Guard (TC-FE-009)', () => {
  it('supervisor 访问 admin 路由允许通过', async () => {
    useAuthStore.mockReturnValue({ isLoggedIn: true, userRole: 'supervisor', clearAuth: vi.fn() })
    const router = createTestRouter()
    await router.push('/admin/users')
    expect(router.currentRoute.value.path).toBe('/admin/users')
  })
})

describe('CustomerLayout (TC-FE-010)', () => {
  it('菜单按角色渲染', () => {
    const wrapper = mount(CustomerLayout, {
      global: {
        mocks: {
          $route: { path: '/customer/dashboard' },
        },
        stubs: ['router-view', 'HomeFilled', 'Tickets', 'CirclePlus'],
      },
    })
    const items = wrapper.findAll('.el-menu-item')
    expect(items).toHaveLength(3)
    expect(items[0].text()).toContain('仪表盘')
    expect(items[1].text()).toContain('我的工单')
    expect(items[2].text()).toContain('提交工单')
  })
})
