import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AssignSuggestionList from '@/components/AssignSuggestionList.vue'

describe('AssignSuggestionList (TC-FE-047)', () => {
  it('渲染建议列表并触发分配', async () => {
    const suggestions = [
      { agent_id: 2, agent_name: '客服B', score: 95, current_load: 3, reason: '擅长此类问题' },
      { agent_id: 3, agent_name: '客服C', score: 88, current_load: 5, reason: '负载较低' },
    ]

    const wrapper = mount(AssignSuggestionList, {
      props: { suggestions },
    })
    await flushPromises()

    expect(wrapper.find('h4').text()).toBe('建议分配')
    expect(wrapper.find('.el-table').exists()).toBe(true)

    const rows = wrapper.findAll('.el-table__row')
    expect(rows.length).toBe(2)
    expect(wrapper.text()).toContain('客服B')
    expect(wrapper.text()).toContain('客服C')

    const assignButtons = wrapper.findAll('.el-button')
    expect(assignButtons.length).toBe(2)

    await assignButtons[0].trigger('click')
    expect(wrapper.emitted('assign')).toHaveLength(1)
    expect(wrapper.emitted('assign')[0]).toEqual([2])
  })

  it('空建议时显示空状态', () => {
    const wrapper = mount(AssignSuggestionList, {
      props: { suggestions: [] },
    })

    expect(wrapper.find('.el-empty').exists()).toBe(true)
    expect(wrapper.text()).toContain('暂无可建议的客服')
  })
})
