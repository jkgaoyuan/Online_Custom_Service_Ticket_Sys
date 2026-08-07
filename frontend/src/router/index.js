import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores'

const routes = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  // Customer routes
  {
    path: '/customer',
    name: 'CustomerLayout',
    component: () => import('@/layouts/CustomerLayout.vue'),
    meta: { requiresAuth: true, role: 'customer' },
    children: [
      {
        path: 'dashboard',
        name: 'CustomerDashboard',
        component: () => import('@/views/customer/DashboardView.vue'),
      },
    ],
  },
  // Agent routes
  {
    path: '/agent',
    name: 'AgentLayout',
    component: () => import('@/layouts/AgentLayout.vue'),
    meta: { requiresAuth: true, role: 'agent' },
    children: [
      {
        path: 'workbench',
        name: 'AgentWorkbench',
        component: () => import('@/views/agent/WorkbenchView.vue'),
      },
    ],
  },
  // Admin & Supervisor routes (shared layout)
  {
    path: '/admin',
    name: 'AdminLayout',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, role: 'admin' },
    children: [
      {
        path: 'users',
        name: 'AdminUsers',
        component: () => import('@/views/admin/UsersView.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // 已登录用户访问登录页，按角色跳转
  if (to.path === '/login' && authStore.isLoggedIn) {
    const role = authStore.userRole
    if (role === 'customer') return next('/customer/dashboard')
    if (role === 'agent') return next('/agent/workbench')
    return next('/admin/users')
  }

  // 需要认证但未登录
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    return next('/login')
  }

  // 角色校验
  if (to.meta.role && authStore.isLoggedIn) {
    const requiredRole = to.meta.role
    const userRole = authStore.userRole

    // admin 路由允许 admin 和 supervisor 访问
    if (requiredRole === 'admin' && ['admin', 'supervisor'].includes(userRole)) {
      return next()
    }

    if (requiredRole !== userRole) {
      return next('/login')
    }
  }

  next()
})

export default router
