# 前端测试用例编写计划

> **现状诊断**：当前 `frontend/package.json` 中无任何测试依赖与测试脚本，需先搭建测试基础设施，再按模块编写用例。  
> **评审状态**：已通过子 agent 合规性评审，本计划已修复覆盖类型、设计方法、MVP 构成、代码匹配度等问题。

---

## 一、测试框架选型与安装

| 依赖 | 版本 | 用途 |
|------|------|------|
| `vitest` | ^1.x | 测试运行器（与 Vite 原生集成） |
| `@vue/test-utils` | ^2.4.x | Vue 组件挂载与交互 |
| `jsdom` | ^24.x | DOM 环境模拟 |
| `@pinia/testing` | ^0.1.x | Pinia store mock 辅助 |

**安装命令**：

```bash
cd frontend
npm install -D vitest @vue/test-utils jsdom @pinia/testing
```

**package.json 新增脚本**：

```json
"scripts": {
  "test": "vitest run",
  "test:watch": "vitest",
  "test:ui": "vitest --ui"
}
```

**`vite.config.js` 追加 test 字段**：

```js
import { defineConfig } from 'vite'

export default defineConfig({
  // ...existing config
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['tests/**/*.{test,spec}.{js,ts}'],
    deps: {
      inline: ['element-plus'],
    },
    setupFiles: ['./tests/setup.js'],
  },
})
```

---

## 二、全局 Mock 策略（`tests/setup.js`）

```js
import { vi } from 'vitest'

// Element Plus 图标
vi.mock('@element-plus/icons-vue', () => ({
  HomeFilled: { template: '<span />' },
  Tickets: { template: '<span />' },
  CirclePlus: { template: '<span />' },
}))

// ECharts（避免 Canvas 依赖）
vi.mock('vue-echarts', () => ({
  default: { template: '<div class="echarts-mock" />' },
}))

// matchMedia（Element Plus 需要）
window.matchMedia = vi.fn().mockImplementation(query => ({
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
  width: 0, height: 0, top: 0, left: 0, bottom: 0, right: 0,
}))

// localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })
```

---

## 三、测试文件组织结构

```
frontend/tests/
├── setup.js
├── api/
│   └── client.test.js
├── stores/
│   ├── auth.test.js
│   ├── tickets.test.js
│   ├── dispatch.test.js
│   ├── reports.test.js
│   └── users.test.js
├── components/
│   ├── StatusBadge.test.js
│   ├── PriorityTag.test.js
│   ├── ReplyBox.test.js
│   ├── AssignSuggestionList.test.js
│   └── reports/
│       ├── OverviewPanel.test.js
│       ├── SatisfactionPanel.test.js
│       └── CategoryDistributionChart.test.js
├── pages/
│   ├── LoginView.test.js
│   ├── customer/
│   │   ├── CreateTicketView.test.js
│   │   ├── MyTicketsView.test.js
│   │   └── TicketDetailView.test.js
│   ├── agent/
│   │   ├── AgentTicketsView.test.js
│   │   └── AgentTicketDetailView.test.js
│   └── admin/
│       ├── UsersView.test.js
│       └── ReportsView.test.js
└── router/
    └── guards.test.js
```

---

## 四、命名规范示例

```typescript
describe('StatusBadge (TC-FE-001)', () => {
  it('renders correct label and type for in_progress status', () => {
    // ...
  })
})
```

---

## 五、用例设计明细（54 条）

### 5.1 通用组件层

| 用例ID | 测试模块 | 测试场景 | 前置条件 | 操作步骤 | 测试数据 | 预期结果 | 优先级 | 覆盖类型 | 设计方法 |
|--------|----------|----------|----------|----------|----------|----------|--------|----------|----------|
| TC-FE-001 | StatusBadge | 正常状态渲染 in_progress | 无 | 1. 挂载组件 | `status: 'in_progress'` | 渲染"处理中"，type="warning" | P0 | 正向 | 等价类划分 |
| TC-FE-002 | StatusBadge | 未知状态 Fallback 显示原始值 | 无 | 1. 挂载组件 | `status: 'unknown_state'` | 渲染"unknown_state"，type="info" | P1 | 边界 | 错误推测法 |
| TC-FE-003 | PriorityTag | 各优先级渲染 | 无 | 1. 分别传入 P0~P3 | `priority: 'P0'` | 正确渲染对应标签和颜色 | P0 | 正向 | 等价类划分 |
| TC-FE-004 | ReplyBox | 正常提交回复 | 无 | 1. 输入内容 2. 点击提交 | `content: '测试回复'` | 触发 submit 事件，携带内容 | P0 | 正向 | 场景法 |
| TC-FE-005 | ReplyBox | 空内容提交被拦截 | 无 | 1. 不输入直接点击提交 | `content: ''` | 不触发 submit，显示校验提示 | P1 | 边界 | 边界值分析 |

### 5.2 路由与权限层

| 用例ID | 测试模块 | 测试场景 | 前置条件 | 操作步骤 | 测试数据 | 预期结果 | 优先级 | 覆盖类型 | 设计方法 |
|--------|----------|----------|----------|----------|----------|----------|--------|----------|----------|
| TC-FE-006 | Router Guard | 未认证访问受保护路由跳转登录 | 无 Token | 1. 访问 /customer/dashboard | `to: '/customer/dashboard'` | 重定向到 /login | P0 | 权限 | 场景法 |
| TC-FE-007 | Router Guard | 已登录 customer 访问登录页跳转仪表盘 | 已登录 customer | 1. 访问 /login | `role: 'customer'` | 重定向到 /customer/dashboard | P0 | 正向 | 场景法 |
| TC-FE-008 | Router Guard | agent 越权访问 admin 路由被拦截 | 已登录 agent | 1. 访问 /admin/users | `role: 'agent'` | 重定向到 /login | P0 | 权限 | 场景法 |
| TC-FE-009 | Router Guard | supervisor 访问 admin 路由允许通过 | 已登录 supervisor | 1. 访问 /admin/users | `role: 'supervisor'` | 允许进入 | P0 | 权限 | 场景法 |
| TC-FE-010 | CustomerLayout | 菜单按角色渲染 | 已登录 customer | 1. 挂载布局 | `role: 'customer'` | 渲染仪表盘/我的工单/提交工单菜单 | P0 | 正向 | 等价类划分 |

### 5.3 全局状态层（Pinia Store）

| 用例ID | 测试模块 | 测试场景 | 前置条件 | 操作步骤 | 测试数据 | 预期结果 | 优先级 | 覆盖类型 | 设计方法 |
|--------|----------|----------|----------|----------|----------|----------|--------|----------|----------|
| TC-FE-011 | Auth Store | 登录成功持久化到 localStorage | 无 | 1. 调用 login | `username: 'admin'` | token/user 写入 localStorage，isLoggedIn=true | P0 | 正向 | 场景法 |
| TC-FE-012 | Auth Store | Token 过期 401 清除态并跳转 | 已登录 | 1. 模拟 API 返回 401 | `status: 401` | 清除 localStorage，跳转 /login | P0 | 异常 | 场景法 |
| TC-FE-013 | Auth Store | initAuth 从 localStorage 恢复用户 | localStorage 有 token | 1. 调用 initAuth | `token: 'valid_token'` | 异步获取 user，状态恢复 | P1 | 正向 | 场景法 |
| TC-FE-014 | Auth Store | Token 被篡改后 initAuth 失败清除态 | localStorage token 被手动修改 | 1. 调用 initAuth | `token: 'tampered_token'` | getMe 失败，清除 auth 状态 | P1 | 安全 | 错误推测法 |
| TC-FE-015 | Tickets Store | 创建工单后返回数据 | 无 | 1. 调用 createTicket | `title: '新工单'` | 返回创建成功的工单数据 | P0 | 正向 | 场景法 |
| TC-FE-016 | Tickets Store | replyTicket 成功后追加到 replies | 当前工单已加载 | 1. 调用 replyTicket | `content: '回复'` | replies 数组 push 新回复 | P1 | 数据联动 | 场景法 |
| TC-FE-017 | Tickets Store | updateStatus 更新当前工单状态 | 当前工单 open | 1. 调用 updateStatus | `status: 'in_progress'` | currentTicket.status 更新 | P0 | 数据联动 | 场景法 |
| TC-FE-018 | Tickets Store | fetchTickets 设置 loading 状态 | 无 | 1. 触发 fetchTickets | `page: 1` | loading 从 false→true→false | P1 | 正向 | 场景法 |
| TC-FE-019 | Tickets Store | assistTicket 追加协作记录 | 当前工单已加载 | 1. 调用 assistTicket | `notes: '协助说明'` | collaborations unshift 新记录 | P1 | 数据联动 | 场景法 |

### 5.4 API 客户端层

| 用例ID | 测试模块 | 测试场景 | 前置条件 | 操作步骤 | 测试数据 | 预期结果 | 优先级 | 覆盖类型 | 设计方法 |
|--------|----------|----------|----------|----------|----------|----------|--------|----------|----------|
| TC-FE-020 | API Client | 请求自动附加 Authorization | 已登录 | 1. 发起请求 | `token: 'xxx'` | 请求头携带 Bearer token | P0 | 正向 | 场景法 |
| TC-FE-021 | API Client | 401 响应触发全局登出 | 已登录 | 1. 模拟返回 401 | `status: 401` | 调用 clearAuth 并跳转 /login | P0 | 权限 | 场景法 |
| TC-FE-022 | API Client | 请求超时抛出错误 | 网络延迟 | 1. 模拟延迟 11s | `delay: 11000` | 抛出超时错误 | P1 | 异常 | 错误推测法 |
| TC-FE-023 | API Client | 空对象响应正常解析 | 无 | 1. 模拟返回 `{}` | `data: {}` | 不报错，正常解析 | P1 | 边界 | 边界值分析 |

### 5.5 页面级组件 — LoginView

| 用例ID | 测试模块 | 测试场景 | 前置条件 | 操作步骤 | 测试数据 | 预期结果 | 优先级 | 覆盖类型 | 设计方法 |
|--------|----------|----------|----------|----------|----------|----------|--------|----------|----------|
| TC-FE-024 | LoginView | 正常登录后跳转 customer | 无 | 1. 输入信息 2. 点击登录 | `role: 'customer'` | 跳转 /customer/dashboard | P0 | 正向 | 场景法 |
| TC-FE-025 | LoginView | 正常登录后跳转 agent | 无 | 1. 输入信息 2. 点击登录 | `role: 'agent'` | 跳转 /agent/workbench | P0 | 正向 | 场景法 |
| TC-FE-026 | LoginView | 空表单提交被校验拦截 | 无 | 1. 直接点击登录 | `username: '', password: ''` | 不调用 API，显示校验提示 | P0 | 边界 | 边界值分析 |
| TC-FE-027 | LoginView | 登录中按钮显示 loading | 无 | 1. 点击登录 | `username: 'admin'` | 按钮 loading=true，完成后恢复 | P1 | 正向 | 场景法 |
| TC-FE-028 | LoginView | 快速双击只发一次请求 | 无 | 1. 快速双击登录 | `click: 2` | login 只被调用 1 次 | P1 | 边界 | 错误推测法 |
| TC-FE-029 | LoginView | 错误密码显示错误提示 | 无 | 1. 输入错误密码 | `password: 'wrong'` | ElMessage.error 被调用 | P0 | 异常 | 场景法 |

### 5.6 页面级组件 — CreateTicketView

| 用例ID | 测试模块 | 测试场景 | 前置条件 | 操作步骤 | 测试数据 | 预期结果 | 优先级 | 覆盖类型 | 设计方法 |
|--------|----------|----------|----------|----------|----------|----------|--------|----------|----------|
| TC-FE-030 | CreateTicketView | 正常提交工单并跳转 | 已登录 | 1. 填写表单 2. 点击提交 | `title: '测试', category_id: 1` | 调用 createTicket，跳转 /customer/tickets | P0 | 正向 | 场景法 |
| TC-FE-031 | CreateTicketView | 标题超过 200 字符被拦截 | 无 | 1. 输入 201 字符 | `title: 'a'.repeat(201)` | 校验失败，不提交 | P1 | 边界 | 边界值分析 |
| TC-FE-032 | CreateTicketView | 未选择分类被校验拦截 | 无 | 1. 分类留空 | `category_id: null` | 提示"请选择分类" | P0 | 边界 | 等价类划分 |
| TC-FE-033 | CreateTicketView | 进入页面加载分类下拉 | 无 | 1. 挂载组件 | 无 | onMounted 调用 fetchCategories | P0 | 正向 | 场景法 |
| TC-FE-034 | CreateTicketView | 提交中按钮 loading | 无 | 1. 点击提交 | 无 | 按钮 loading=true | P1 | 正向 | 场景法 |

### 5.7 页面级组件 — MyTicketsView

| 用例ID | 测试模块 | 测试场景 | 前置条件 | 操作步骤 | 测试数据 | 预期结果 | 优先级 | 覆盖类型 | 设计方法 |
|--------|----------|----------|----------|----------|----------|----------|--------|----------|----------|
| TC-FE-035 | MyTicketsView | 正常渲染工单列表 | 已登录 | 1. 挂载组件 | `tickets: [{id:1}]` | 渲染 el-table 和 StatusBadge/PriorityTag | P0 | 正向 | 场景法 |
| TC-FE-036 | MyTicketsView | 空数据表格为空 | 已登录 | 1. 挂载组件 | `tickets: []` | 表格行数为 0 | P1 | 边界 | 边界值分析 |
| TC-FE-037 | MyTicketsView | 分页切换触发重新加载 | 列表有 21 条 | 1. 点击第 2 页 | `page: 2` | 调用 fetchTickets({page:2}) | P1 | 正向 | 场景法 |
| TC-FE-038 | MyTicketsView | 点击查看跳转详情 | 列表已加载 | 1. 点击"查看" | `row.id: 42` | router.push('/customer/tickets/42') | P0 | 正向 | 场景法 |

### 5.8 页面级组件 — 工单详情

| 用例ID | 测试模块 | 测试场景 | 前置条件 | 操作步骤 | 测试数据 | 预期结果 | 优先级 | 覆盖类型 | 设计方法 |
|--------|----------|----------|----------|----------|----------|----------|--------|----------|----------|
| TC-FE-039 | TicketDetail | 加载工单详情和回复 | 已登录 | 1. 进入页面 | `id: 1` | 调用 fetchTicket + fetchReplies | P0 | 正向 | 场景法 |
| TC-FE-040 | TicketDetail | 状态流转 open→in_progress | agent 已登录 | 1. 选择新状态 2. 点击更新 | `status: 'in_progress'` | 调用 updateStatus，currentTicket 更新 | P0 | 正向 | 场景法 |
| TC-FE-041 | TicketDetail | 转交工单 | agent 已登录 | 1. 点击转交 2. 选择目标 | `to_agent_id: 2` | 调用 transferTicket | P0 | 正向 | 场景法 |
| TC-FE-042 | TicketDetail | 协助请求 | agent 已登录 | 1. 点击协助 2. 填写备注 | `notes: '请协助处理'` | 调用 assistTicket | P0 | 正向 | 场景法 |
| TC-FE-043 | TicketDetail | 提交满意度评价 | customer，工单 resolved | 1. 选择评分 2. 提交 | `score: 5` | 调用 submitSatisfaction | P0 | 正向 | 场景法 |
| TC-FE-044 | TicketDetail | 关闭工单后回复框隐藏 | 工单 closed | 1. 查看页面 | `status: 'closed'` | 回复框禁用或隐藏 | P1 | 边界 | 场景法 |
| TC-FE-045 | TicketDetail | XSS 输入被转义不执行脚本 | 回复框输入 script 标签 | 1. 输入 `<script>alert(1)</script>` | `content: '<script>alert(1)</script>'` | 内容被转义渲染，不执行脚本 | P1 | 安全 | 错误推测法 |

### 5.9 新增覆盖模块

| 用例ID | 测试模块 | 测试场景 | 前置条件 | 操作步骤 | 测试数据 | 预期结果 | 优先级 | 覆盖类型 | 设计方法 |
|--------|----------|----------|----------|----------|----------|----------|--------|----------|----------|
| TC-FE-046 | AgentTicketsView | 渲染工单列表和分页 | agent 已登录 | 1. 挂载组件 | `tickets: [{id:1}]` | 渲染表格和分页器 | P0 | 正向 | 场景法 |
| TC-FE-047 | AssignSuggestionList | 渲染建议列表并触发分配 | agent 已登录 | 1. 挂载组件 2. 点击分配 | `suggestions: [{agent_id:1}]` | 触发 assign 事件携带 agent_id | P0 | 正向 | 场景法 |
| TC-FE-048 | OverviewPanel | 渲染指标卡片 | 无 | 1. 挂载组件 | `total: 100, open: 20` | 渲染数字和标签 | P0 | 正向 | 场景法 |
| TC-FE-049 | SatisfactionPanel | 渲染满意度分布 | 无 | 1. 挂载组件 | `avg_score: 4.2` | 渲染平均分和占比 | P0 | 正向 | 场景法 |
| TC-FE-050 | TrendChart | 空数据优雅降级 | 无 | 1. 传入空数组 | `data: []` | 不报错，显示无数据提示 | P1 | 边界 | 边界值分析 |
| TC-FE-051 | AgentPerformanceTable | 渲染性能表格 | 无 | 1. 传入数据 | `agents: [{name:'A'}]` | 正确渲染列和行 | P0 | 正向 | 场景法 |
| TC-FE-052 | UsersView | 用户列表渲染与分页 | admin 已登录 | 1. 挂载组件 | `users: [{id:1}]` | 渲染表格和分页 | P0 | 正向 | 场景法 |
| TC-FE-053 | UsersView | 编辑用户角色后刷新 | admin 已登录 | 1. 编辑 2. 保存 | `role: 'agent'` | 调用 updateUser，列表刷新 | P0 | 正向 | 场景法 |
| TC-FE-054 | ReportsView | 切换报表 Tab | admin 已登录 | 1. 点击不同 Tab | `tab: 'satisfaction'` | 渲染对应报表组件 | P1 | 正向 | 场景法 |

---

## 六、最小可发布测试集（MVP，15 条）

| 类别 | 规范要求 | 用例ID | 说明 |
|------|----------|--------|------|
| P0 渲染 | 2 条 | TC-FE-001, TC-FE-035 | StatusBadge、MyTicketsView 正常渲染 |
| P0 交互 | 2 条 | TC-FE-024, TC-FE-030 | LoginView 登录跳转、CreateTicketView 提交工单 |
| P0 权限 | 1 条 | TC-FE-006 | 未认证路由拦截 |
| P1 Loading Guard | 2 条 | TC-FE-027, TC-FE-028 | 登录中 loading、快速重复点击只发一次 |
| P1 Fallback | 1 条 | TC-FE-002 | 未知状态显示原始值 |
| P1 数据联动 | 2 条 | TC-FE-017, TC-FE-016 | updateStatus 更新 currentTicket、replyTicket 追加 replies |
| P0 交互 | — | TC-FE-038, TC-FE-040, TC-FE-043 | 状态流转、转交工单、满意度评价 |
| P0 权限 | — | TC-FE-012 | Token 过期清除态 |
| P1 安全 | — | TC-FE-014 | Token 篡改后 initAuth 失败 |
| P1 边界 | — | TC-FE-026 | 空表单提交拦截 |

---

## 七、执行路线图

| 阶段 | 任务 | 用例数 | 优先级 |
|------|------|--------|--------|
| **Phase 0** | 安装 vitest + @vue/test-utils + jsdom + @pinia/testing，配置 vite.config.js 和 setup.js | — | 阻塞 |
| **Phase 1** | 通用组件（StatusBadge / PriorityTag / ReplyBox）+ Store（auth / tickets）+ API Client | 23 条 | P0 |
| **Phase 2** | 路由守卫 + LoginView | 9 条 | P0 |
| **Phase 3** | 客户侧页面（CreateTicketView / MyTicketsView / TicketDetailView） | 16 条 | P0 |
| **Phase 4** | 坐席侧页面（AgentTicketsView / AgentTicketDetailView / AssignSuggestionList） | 6 条 | P0/P1 |
| **Phase 5** | 报表组件 + 管理后台（UsersView / ReportsView） | 7 条 | P1 |
| **Phase 6** | 补充 stores（dispatch / reports / users）+ 边界/安全专项 | 按需 | P1/P2 |

---

## 八、与原计划的关键差异（评审修正记录）

| 改动项 | 原问题 | 修复方式 |
|--------|--------|----------|
| 覆盖类型 | 使用自定义枚举（渲染/交互/Loading Guard 等） | 全部改为 **正向/异常/边界/权限/安全/性能** |
| 设计方法 | TC-FE-042 用「状态机」不在允许列表内 | 改为 **场景法** |
| MVP 构成 | 20 条全为 P0，缺失规范要求的 P1 类别 | 调整为 15 条，含 P1 Loading Guard/Fallback/数据联动/安全 |
| 乐观更新 TC-FE-015 | 测试了代码中不存在的机制（replyTicket 非乐观更新） | 改为测试「replyTicket 成功后追加到 replies」 |
| Loading Guard TC-FE-017 | 测试了代码中不存在的互斥逻辑 | 改为测试「fetchTickets 设置 loading 状态」 |
| ECharts Mock | 完全缺失 | setup.js 中 mock `vue-echarts` 为空 div |
| Element Plus Polyfill | 只有 matchMedia | 追加 ResizeObserver、scrollIntoView、getBoundingClientRect |
| 安全维度 | 50 条中无安全用例 | 新增 TC-FE-014（Token 篡改）、TC-FE-045（XSS） |
| 未覆盖文件 | AgentTicketsView 等 7+ 文件缺失 | 新增 TC-FE-046/047/050 等用例覆盖 |
| describe/it 示例 | 未提供 | 在计划开头给出完整命名示例 |

---

## 九、修订记录

| 日期 | 修订人 | 内容 |
|------|--------|------|
| 2026-08-12 | — | 初版计划输出 |
| 2026-08-12 | 子 agent 评审 | 修复覆盖类型、设计方法、MVP 构成、代码匹配度、Mock 策略、遗漏模块等问题 |
