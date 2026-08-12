import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElMessage } from 'element-plus'
import ReplyBox from '@/components/ReplyBox.vue'

vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: { warning: vi.fn() },
  }
})

describe('ReplyBox (TC-FE-004)', () => {
  it('emits replied event with content and is_internal on submit', async () => {
    const wrapper = mount(ReplyBox, { props: { ticketId: 1 } })
    await wrapper.find('textarea').setValue('测试回复')
    await wrapper.find('.el-checkbox__original').setValue(true)
    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('replied')).toHaveLength(1)
    expect(wrapper.emitted('replied')[0]).toEqual([
      { content: '测试回复', is_internal: true },
    ])
  })

  it('clears content and isInternal after successful submit', async () => {
    const wrapper = mount(ReplyBox, { props: { ticketId: 1 } })
    await wrapper.find('textarea').setValue('测试回复')
    await wrapper.find('button').trigger('click')

    expect(wrapper.find('textarea').element.value).toBe('')
    expect(wrapper.vm.isInternal).toBe(false)
  })
})

describe('ReplyBox (TC-FE-005)', () => {
  it('blocks empty content submission and shows warning', async () => {
    const wrapper = mount(ReplyBox, { props: { ticketId: 1 } })
    await wrapper.find('button').trigger('click')

    expect(ElMessage.warning).toHaveBeenCalledWith('回复内容不能为空')
    expect(wrapper.emitted('replied')).toBeUndefined()
  })

  it('blocks whitespace-only content', async () => {
    const wrapper = mount(ReplyBox, { props: { ticketId: 1 } })
    await wrapper.find('textarea').setValue('   ')
    await wrapper.find('button').trigger('click')

    expect(ElMessage.warning).toHaveBeenCalledWith('回复内容不能为空')
    expect(wrapper.emitted('replied')).toBeUndefined()
  })
})
