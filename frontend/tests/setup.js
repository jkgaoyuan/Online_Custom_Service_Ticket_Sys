import { vi } from 'vitest'
import { config } from '@vue/test-utils'
import { h } from 'vue'
import ElementPlus from 'element-plus'

// 全局注册 Element Plus，确保测试中能解析所有 el-* 组件
config.global.plugins = [ElementPlus]

// ECharts（避免 Canvas 依赖）
vi.mock('vue-echarts', () => ({
  default: { template: '<div class="echarts-mock" />' },
}))

// matchMedia（Element Plus 需要）
window.matchMedia = vi.fn().mockImplementation((query) => ({
  matches: false,
  media: query,
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
}))

// ResizeObserver polyfill for jsdom
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// scrollIntoView（Element Plus 分页/选择器需要）
Element.prototype.scrollIntoView = vi.fn()

// getBoundingClientRect（Element Plus 弹窗定位需要）
Element.prototype.getBoundingClientRect = vi.fn(() => ({
  width: 0,
  height: 0,
  top: 0,
  left: 0,
  bottom: 0,
  right: 0,
}))

// localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock navigator.clipboard
global.navigator.clipboard = {
  writeText: vi.fn().mockResolvedValue(undefined),
}

// Stub v-loading directive
config.global.directives = {
  loading: {
    mounted() {},
    updated() {},
    unmounted() {},
  },
}

// Custom stubs for Element Plus components that preserve slots and key props
config.global.stubs['ElButton'] = {
  props: ['size', 'type', 'loading'],
  setup(props, { slots }) {
    return () => h('button', { class: `el-button el-button--${props.type || 'default'}`, type: 'button' }, slots.default?.())
  },
}

config.global.stubs['ElTag'] = {
  props: ['type'],
  setup(props, { slots }) {
    return () => h('span', { class: `el-tag el-tag--${props.type || 'info'}` }, slots.default?.())
  },
}

config.global.stubs['ElDialog'] = {
  props: ['modelValue', 'title', 'width'],
  emits: ['update:modelValue'],
  setup(props, { slots, emit }) {
    return () =>
      props.modelValue
        ? h('div', { class: 'el-dialog-wrapper' }, [
            h('div', { class: 'el-dialog__header' }, props.title),
            h('div', { class: 'el-dialog__body' }, slots.default?.()),
            h('div', { class: 'el-dialog__footer' }, slots.footer?.()),
          ])
        : h('div')
  },
}

const simpleStubs = [
  'ElForm',
  'ElFormItem',
  'ElInput',
  'ElOption',
  'ElPagination',
  'ElSelect',
]

simpleStubs.forEach((name) => {
  config.global.stubs[name] = true
})

// ElTable and ElTableColumn need to render slots so row content is visible
config.global.stubs['ElTable'] = {
  props: ['data', 'vLoading'],
  setup(props, { slots }) {
    return () => h('div', { class: 'el-table' }, slots.default?.())
  },
}

config.global.stubs['ElTableColumn'] = {
  props: ['prop', 'label', 'width'],
  setup(props, { slots }) {
    return () => {
      return h('div', { class: 'el-table-column' }, slots.default?.({ row: {} }))
    }
  },
}
