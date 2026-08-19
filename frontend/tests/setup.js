import { config } from '@vue/test-utils'
import { vi } from 'vitest'
import { h } from 'vue'

// ResizeObserver polyfill for jsdom
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

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
      // Access parent table data via context or just render slots once with a mock row
      // Since test-utils shallow stubs don't propagate props down easily,
      // we render the slot content directly; the scoped slot won't have `row`
      // but in tests we can find elements by text without needing row data
      return h('div', { class: 'el-table-column' }, slots.default?.({ row: {} }))
    }
  },
}
