import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import UsersView from '@/views/admin/UsersView.vue'

vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
    ElMessageBox: { confirm: vi.fn().mockResolvedValue() },
  }
})

vi.mock('@/stores', () => ({
  useUsersStore: vi.fn(),
}))

const createStore = (overrides = {}) => ({
  users: [
    {
      id: 1,
      username: 'user1',
      email: 'user1@example.com',
      role: 'customer',
      is_active: true,
      ticket_count: 3,
      created_at: '2024-08-01T10:00:00Z',
    },
    {
      id: 2,
      username: 'agent1',
      email: 'agent1@example.com',
      role: 'agent',
      is_active: false,
      ticket_count: 10,
      created_at: '2024-08-02T11:00:00Z',
    },
  ],
  loading: false,
  pagination: { total: 2, page: 1, page_size: 20 },
  filters: { role: '', is_active: '' },
  fetchUsers: vi.fn(),
  updateUser: vi.fn().mockResolvedValue({}),
  resetPassword: vi.fn().mockResolvedValue({ temp_password: 'TempPass123!' }),
  ...overrides,
})

describe('UsersView (TC-FE-052)', () => {
  it('用户列表渲染与分页', async () => {
    const { useUsersStore } = await import('@/stores')
    useUsersStore.mockReturnValue(createStore())

    const wrapper = mount(UsersView)
    await flushPromises()

    expect(wrapper.find('.el-table').exists()).toBe(true)
    expect(wrapper.find('.el-pagination').exists()).toBe(true)

    const rows = wrapper.findAll('.el-table__row')
    expect(rows.length).toBe(2)
    expect(wrapper.text()).toContain('user1')
    expect(wrapper.text()).toContain('agent1')
  })
})

describe('UsersView (TC-FE-053)', () => {
  it('编辑用户角色后刷新', async () => {
    const { useUsersStore } = await import('@/stores')
    useUsersStore.mockReturnValue(createStore())

    const wrapper = mount(UsersView)
    await flushPromises()

    const editBtn = wrapper.findAll('.el-button').find((b) => b.text().includes('编辑'))
    expect(editBtn).toBeDefined()
    await editBtn.trigger('click')
    await flushPromises()

    // 修改角色
    wrapper.vm.editForm.role = 'supervisor'
    await flushPromises()

    // 点击保存
    const saveBtn = wrapper.findAll('.el-dialog').at(0).findAll('.el-button').find((b) => b.text().includes('保存'))
    expect(saveBtn).toBeDefined()
    await saveBtn.trigger('click')
    await flushPromises()

    const store = useUsersStore()
    expect(store.updateUser).toHaveBeenCalledWith(1, {
      username: 'user1',
      email: 'user1@example.com',
      role: 'supervisor',
    })
    expect(store.fetchUsers).toHaveBeenCalled()
  })
})
