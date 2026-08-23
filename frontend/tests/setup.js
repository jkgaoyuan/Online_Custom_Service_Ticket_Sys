import { vi } from 'vitest'
import { config } from '@vue/test-utils'
import { h, provide, inject, unref } from 'vue'
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
global.ResizeObserver = class {
  constructor() {}
  observe() {}
  unobserve() {}
  disconnect() {}
}

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
    return () => h('button', { class: [`el-button el-button--${props.type || 'default'}`, props.loading && 'is-loading'], type: 'button' }, slots.default?.())
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
        ? h('div', { class: 'el-dialog-wrapper el-dialog' }, [
            h('div', { class: 'el-dialog__header' }, props.title),
            h('div', { class: 'el-dialog__body' }, slots.default?.()),
            h('div', { class: 'el-dialog__footer' }, slots.footer?.()),
          ])
        : h('div')
  },
}

const simpleStubs = [
  'ElOption',
  'ElSelect',
]

simpleStubs.forEach((name) => {
  config.global.stubs[name] = true
})

// ElForm stub with basic validation support
config.global.stubs['ElForm'] = {
  props: ['model', 'rules'],
  setup(props, { slots, expose }) {
    const validate = async () => {
      if (!props.rules || !props.model) return true
      for (const [key, rules] of Object.entries(props.rules)) {
        for (const rule of rules) {
          if (rule.required && !props.model[key]) {
            throw { [key]: [new Error(rule.message)] }
          }
          if (rule.max && props.model[key] && props.model[key].length > rule.max) {
            throw { [key]: [new Error(rule.message)] }
          }
        }
      }
      return true
    }
    expose({ validate })
    return () => h('form', {}, slots.default?.())
  },
}

config.global.stubs['ElFormItem'] = {
  props: ['prop', 'label'],
  setup(props, { slots }) {
    return () => h('div', { class: 'el-form-item' }, slots.default?.())
  },
}
config.global.stubs['ElPagination'] = {
  props: ['currentPage', 'pageSize', 'total'],
  setup(props, { emit }) {
    return () => h('div', { class: 'el-pagination' }, `Total: ${props.total ?? 0}`)
  },
}

// ElEmpty stub
config.global.stubs['ElEmpty'] = {
  props: ['description'],
  setup(props, { slots }) {
    return () => h('div', { class: 'el-empty' }, props.description || slots.default?.())
  },
}

// ElCheckbox stub
config.global.stubs['ElCheckbox'] = {
  props: ['modelValue'],
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () => h('input', {
      type: 'checkbox',
      class: 'el-checkbox__original',
      checked: props.modelValue,
      onChange: (e) => emit('update:modelValue', e.target.checked),
    })
  },
}

// ElTable and ElTableColumn need to render slots so row content is visible
const TableDataSymbol = Symbol('tableData')

config.global.stubs['ElTable'] = {
  props: ['data', 'vLoading'],
  setup(props, { slots }) {
    const data = Array.isArray(unref(props.data)) ? unref(props.data) : []
    provide(TableDataSymbol, data)
    return () => h('div', { class: 'el-table' }, [
      slots.default?.(),
      ...data.map((row, i) => h('div', { class: 'el-table__row', key: i })),
    ])
  },
}

config.global.stubs['ElTableColumn'] = {
  props: ['prop', 'label', 'width'],
  setup(props, { slots }) {
    const data = inject(TableDataSymbol, [])
    return () => h('div', { class: 'el-table-column' },
      data.map((row, index) => h('div', { class: 'el-table__cell', key: index }, slots.default?.({ row }) || String(row[props.prop] ?? '')))
    )
  },
}
