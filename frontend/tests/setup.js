import { vi } from 'vitest'
import { config } from '@vue/test-utils'
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

// ResizeObserver（Element Plus 表格需要）
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
