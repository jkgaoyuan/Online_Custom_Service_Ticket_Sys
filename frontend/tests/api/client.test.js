import { describe, it, expect, vi, beforeEach } from 'vitest'

async function createApiModule() {
  const requestHandlers = []
  const responseHandlers = []

  vi.doMock('axios', () => ({
    default: {
      create: vi.fn(() => ({
        defaults: { headers: {}, timeout: 10000 },
        interceptors: {
          request: {
            use: vi.fn((fn) => requestHandlers.push(fn)),
          },
          response: {
            use: vi.fn((fn1, fn2) => responseHandlers.push({ fulfilled: fn1, rejected: fn2 })),
          },
        },
        get: vi.fn(),
        post: vi.fn(),
      })),
    },
  }))

  vi.doMock('@/stores', () => ({
    useAuthStore: vi.fn(),
  }))

  const { default: api } = await import('@/api/index')
  const { useAuthStore } = await import('@/stores')
  return { api, useAuthStore, requestHandlers, responseHandlers }
}

describe('API Client (TC-FE-020)', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
  })

  it('attaches Authorization header when token exists', async () => {
    const { useAuthStore, requestHandlers } = await createApiModule()
    const authStore = { token: 'mock_token_123' }
    useAuthStore.mockReturnValue(authStore)

    const config = { headers: {} }
    expect(requestHandlers[0]).toBeDefined()
    const result = requestHandlers[0](config)

    expect(result.headers.Authorization).toBe('Bearer mock_token_123')
  })

  it('does not attach header when no token', async () => {
    const { useAuthStore, requestHandlers } = await createApiModule()
    const authStore = { token: '' }
    useAuthStore.mockReturnValue(authStore)

    const config = { headers: {} }
    const result = requestHandlers[0](config)

    expect(result.headers.Authorization).toBeUndefined()
  })
})

describe('API Client (TC-FE-021)', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
    delete window.location
    window.location = { href: '' }
  })

  it('triggers logout on 401 response', async () => {
    const { useAuthStore, responseHandlers } = await createApiModule()
    const clearAuth = vi.fn()
    const authStore = { token: 'old_token', clearAuth }
    useAuthStore.mockReturnValue(authStore)

    const error = { response: { status: 401 }, config: { url: '/test' } }
    expect(responseHandlers[0]).toBeDefined()
    const rejected = responseHandlers[0].rejected

    expect(() => rejected(error)).rejects.toEqual(error)
    expect(clearAuth).toHaveBeenCalled()
    expect(window.location.href).toBe('/login')
  })
})

describe('API Client (TC-FE-022)', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
  })

  it('has timeout configured to 10000ms', async () => {
    const { api } = await createApiModule()
    expect(api.defaults.timeout).toBe(10000)
  })
})

describe('API Client (TC-FE-023)', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
  })

  it('parses empty object response without error', async () => {
    const { responseHandlers } = await createApiModule()
    const response = { data: {}, status: 200, statusText: 'OK', headers: {}, config: {} }
    expect(responseHandlers[0]).toBeDefined()
    const result = responseHandlers[0].fulfilled(response)

    expect(result.data).toEqual({})
  })
})
