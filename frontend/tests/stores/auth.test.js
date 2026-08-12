import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores'

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  getMe: vi.fn(),
}))

vi.mock('@/stores/tickets', () => ({ useTicketsStore: vi.fn() }))
vi.mock('@/stores/dispatch', () => ({ useDispatchStore: vi.fn() }))
vi.mock('@/stores/reports', () => ({ useReportsStore: vi.fn() }))
vi.mock('@/stores/users', () => ({ useUsersStore: vi.fn() }))

import { login, getMe } from '@/api/auth'

describe('Auth Store (TC-FE-011)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('persists token and user to localStorage on successful login', async () => {
    const mockUser = { id: 1, username: 'admin', role: 'admin' }
    login.mockResolvedValue({
      data: { access_token: 'mock_token', user: mockUser },
    })

    const store = useAuthStore()
    const result = await store.login({ username: 'admin', password: '123456' })

    expect(result.access_token).toBe('mock_token')
    expect(store.token).toBe('mock_token')
    expect(store.user).toEqual(mockUser)
    expect(store.isLoggedIn).toBe(true)
    expect(localStorage.setItem).toHaveBeenCalledWith('token', 'mock_token')
    expect(localStorage.setItem).toHaveBeenCalledWith(
      'user',
      JSON.stringify(mockUser)
    )
  })
})

describe('Auth Store (TC-FE-012)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('clears auth state when 401 occurs during initAuth', async () => {
    getMe.mockRejectedValue({ response: { status: 401 } })

    const store = useAuthStore()
    store.token = 'expired_token'
    await store.initAuth()

    expect(store.token).toBe('')
    expect(store.user).toBeNull()
    expect(store.isLoggedIn).toBe(false)
    expect(localStorage.removeItem).toHaveBeenCalledWith('token')
    expect(localStorage.removeItem).toHaveBeenCalledWith('user')
  })
})

describe('Auth Store (TC-FE-013)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('restores user from localStorage token via initAuth', async () => {
    const mockUser = { id: 2, username: 'agent1', role: 'agent' }
    getMe.mockResolvedValue({ data: mockUser })

    const store = useAuthStore()
    store.token = 'valid_token'
    store.user = null

    await store.initAuth()

    expect(getMe).toHaveBeenCalled()
    expect(store.user).toEqual(mockUser)
    expect(store.isLoggedIn).toBe(true)
  })
})

describe('Auth Store (TC-FE-014)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('clears state when tampered token fails initAuth', async () => {
    getMe.mockRejectedValue(new Error('Invalid token'))

    const store = useAuthStore()
    store.token = 'tampered_token'

    await store.initAuth()

    expect(store.token).toBe('')
    expect(store.user).toBeNull()
    expect(localStorage.removeItem).toHaveBeenCalledWith('token')
    expect(localStorage.removeItem).toHaveBeenCalledWith('user')
  })
})
