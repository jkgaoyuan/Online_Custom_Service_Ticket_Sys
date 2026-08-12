import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import SatisfactionPanel from '@/components/reports/SatisfactionPanel.vue'

const createStore = (satisfaction) => ({
  satisfaction,
})

vi.mock('@/stores', () => ({
  useReportsStore: vi.fn(),
}))

describe('SatisfactionPanel (TC-FE-049)', () => {
  it('渲染满意度分布', async () => {
    const { useReportsStore } = await import('@/stores')
    useReportsStore.mockReturnValue(
      createStore({
        participation_rate: 0.72,
        avg_score: 4.15,
        total_rated: 92,
        distribution: {
          satisfied: 60,
          neutral: 22,
          dissatisfied: 10,
        },
      })
    )

    const wrapper = mount(SatisfactionPanel)
    await flushPromises()

    expect(wrapper.text()).toContain('参与率')
    expect(wrapper.text()).toContain('72.0%')
    expect(wrapper.text()).toContain('平均分')
    expect(wrapper.text()).toContain('4.15')
    expect(wrapper.text()).toContain('总评价数')
    expect(wrapper.text()).toContain('92')

    // vue-echarts 被 mock 为空 div
    expect(wrapper.find('.echarts-mock').exists()).toBe(true)
  })

  it('无数据时显示空状态', async () => {
    const { useReportsStore } = await import('@/stores')
    useReportsStore.mockReturnValue(createStore(null))

    const wrapper = mount(SatisfactionPanel)
    await flushPromises()

    expect(wrapper.find('.el-empty').exists()).toBe(true)
    expect(wrapper.text()).toContain('暂无数据')
  })
})
