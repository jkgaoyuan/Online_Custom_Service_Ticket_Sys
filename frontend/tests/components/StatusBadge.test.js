import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatusBadge from '@/components/StatusBadge.vue'

describe('StatusBadge (TC-FE-001)', () => {
  it('renders correct label and type for in_progress status', () => {
    const wrapper = mount(StatusBadge, { props: { status: 'in_progress' } })
    expect(wrapper.text()).toBe('处理中')
    expect(wrapper.find('.el-tag').classes()).toContain('el-tag--warning')
  })

  it('renders correct label for each known status', () => {
    const cases = [
      { status: 'open', label: '待处理', typeClass: 'el-tag--info' },
      { status: 'waiting', label: '等待回复', typeClass: '' },
      { status: 'resolved', label: '已解决', typeClass: 'el-tag--success' },
      { status: 'closed', label: '已关闭', typeClass: 'el-tag--danger' },
    ]
    for (const c of cases) {
      const wrapper = mount(StatusBadge, { props: { status: c.status } })
      expect(wrapper.text()).toBe(c.label)
      if (c.typeClass) {
        expect(wrapper.find('.el-tag').classes()).toContain(c.typeClass)
      }
    }
  })
})

describe('StatusBadge (TC-FE-002)', () => {
  it('falls back to raw string for unknown status', () => {
    const wrapper = mount(StatusBadge, { props: { status: 'unknown_state' } })
    expect(wrapper.text()).toBe('unknown_state')
    expect(wrapper.find('.el-tag').classes()).toContain('el-tag--info')
  })
})
