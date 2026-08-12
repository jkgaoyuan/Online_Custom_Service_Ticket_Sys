import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PriorityTag from '@/components/PriorityTag.vue'

describe('PriorityTag (TC-FE-003)', () => {
  it('renders correct label and type for each priority', () => {
    const cases = [
      { priority: 'P0', label: '紧急', typeClass: 'el-tag--danger' },
      { priority: 'P1', label: '高', typeClass: 'el-tag--warning' },
      { priority: 'P2', label: '中', typeClass: 'el-tag--primary' },
      { priority: 'P3', label: '低', typeClass: 'el-tag--info' },
    ]
    for (const c of cases) {
      const wrapper = mount(PriorityTag, { props: { priority: c.priority } })
      expect(wrapper.text()).toBe(c.label)
      expect(wrapper.find('.el-tag').classes()).toContain(c.typeClass)
    }
  })
})
