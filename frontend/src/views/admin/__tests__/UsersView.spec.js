import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref, nextTick } from 'vue'
import UsersView from '@/views/admin/UsersView.vue'

const mockStore = {
  users: ref([
    { id: 1, username: 'alice', email: 'alice@example.com', role: 'customer', is_active: true, ticket_count: 5, created_at: '2024-01-15T08:00:00Z' },
    { id: 2, username: 'bob', email: 'bob@example.com', role: 'agent', is_active: false, ticket_count: 12, created_at: '2024-02-20T10:30:00Z' },
  ]),
  total: ref(100),
  loading: ref(false),
  fetchUsers: vi.fn(),
  updateUser: vi.fn(),
  resetPassword: vi.fn(),
}

vi.mock('@/stores/users', () => ({
  useUsersStore: () => mockStore,
}))

vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: { success: vi.fn(), error: vi.fn() },
    ElMessageBox: { confirm: vi.fn().mockResolvedValue() },
  }
})

describe('UsersView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockStore.users.value = [
      { id: 1, username: 'alice', email: 'alice@example.com', role: 'customer', is_active: true, ticket_count: 5, created_at: '2024-01-15T08:00:00Z' },
      { id: 2, username: 'bob', email: 'bob@example.com', role: 'agent', is_active: false, ticket_count: 12, created_at: '2024-02-20T10:30:00Z' },
    ]
    mockStore.total.value = 100
    mockStore.loading.value = false
  })

  it('renders and calls fetchUsers on mount', async () => {
    mount(UsersView)
    await nextTick()
    expect(mockStore.fetchUsers).toHaveBeenCalled()
  })

  it('clicking edit button opens edit dialog', async () => {
    const wrapper = mount(UsersView)
    await nextTick()

    const row = mockStore.users.value[0]
    wrapper.vm.openEdit(row)
    await nextTick()

    expect(wrapper.vm.editDialogVisible).toBe(true)
    expect(wrapper.vm.editForm.id).toBe(row.id)
    expect(wrapper.vm.editForm.username).toBe(row.username)
  })

  it('clicking reset-password button opens reset dialog', async () => {
    const wrapper = mount(UsersView)
    await nextTick()

    const row = mockStore.users.value[1]
    wrapper.vm.openResetPassword(row)
    await nextTick()

    expect(wrapper.vm.resetDialogVisible).toBe(true)
    expect(wrapper.vm.resetTarget).toEqual(row)
  })

  it('role tag mapping is correct', async () => {
    const wrapper = mount(UsersView)
    await nextTick()

    const vm = wrapper.vm
    expect(vm.roleTagType('customer')).toBe('info')
    expect(vm.roleTagType('agent')).toBe('primary')
    expect(vm.roleTagType('supervisor')).toBe('warning')
    expect(vm.roleTagType('admin')).toBe('danger')
    expect(vm.roleTagType('unknown')).toBe('info')

    expect(vm.roleLabel('customer')).toBe('客户')
    expect(vm.roleLabel('agent')).toBe('客服')
    expect(vm.roleLabel('supervisor')).toBe('主管')
    expect(vm.roleLabel('admin')).toBe('管理员')
    expect(vm.roleLabel('unknown')).toBe('unknown')
  })
})
