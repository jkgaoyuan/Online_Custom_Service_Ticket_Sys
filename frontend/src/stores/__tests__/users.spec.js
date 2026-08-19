import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUsersStore } from '@/stores/users'

vi.mock('@/api', () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
  },
}))

import api from '@/api'

describe('useUsersStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchUsers — success updates users and total', async () => {
    const store = useUsersStore()
    api.get.mockResolvedValue({
      data: {
        items: [
          { id: 1, username: 'alice', role: 'customer' },
          { id: 2, username: 'bob', role: 'agent' },
        ],
        total: 42,
      },
    })

    await store.fetchUsers()

    expect(api.get).toHaveBeenCalledWith('/admin/users', { params: {} })
    expect(store.users).toHaveLength(2)
    expect(store.total).toBe(42)
    expect(store.loading).toBe(false)
  })

  it('fetchUsers — calls with role=agent param', async () => {
    const store = useUsersStore()
    api.get.mockResolvedValue({ data: { items: [], total: 0 } })

    await store.fetchUsers({ role: 'agent' })

    expect(api.get).toHaveBeenCalledWith('/admin/users', { params: { role: 'agent' } })
  })

  it('updateUser — sends PUT to correct endpoint', async () => {
    const store = useUsersStore()
    api.put.mockResolvedValue({
      data: { id: 3, username: 'charlie', email: 'charlie@example.com', role: 'admin' },
    })

    const result = await store.updateUser(3, { username: 'charlie', email: 'charlie@example.com', role: 'admin' })

    expect(api.put).toHaveBeenCalledWith('/admin/users/3', { username: 'charlie', email: 'charlie@example.com', role: 'admin' })
    expect(result).toEqual({ id: 3, username: 'charlie', email: 'charlie@example.com', role: 'admin' })
  })

  it('resetPassword — returns temp_password', async () => {
    const store = useUsersStore()
    api.post.mockResolvedValue({ data: { temp_password: 'Ab3#x9Lm' } })

    const result = await store.resetPassword(7)

    expect(api.post).toHaveBeenCalledWith('/admin/users/7/reset-password')
    expect(result.temp_password).toBe('Ab3#x9Lm')
  })
})
