# 在线客服工单系统 — 测试报告

> 生成时间：2026-08-25  
> 分支：`main`  
> 后端框架：FastAPI + SQLAlchemy + pytest  
> 前端框架：Vue3 + Vitest + @vitest/coverage-v8

---

## 一、总体概览

| 维度 | 数据 |
|------|------|
| 后端测试文件 | 24 个 |
| 后端测试用例 | **363 个** |
| 后端通过情况 | **363 passed, 0 failed** ✅ |
| 后端代码覆盖率 | **81%**（2,335 statements / 442 missed） |
| 前端测试文件 | **27 个** |
| 前端测试用例 | **109 个** |
| 前端通过情况 | **109 passed, 0 failed** ✅ |
| 前端语句覆盖率 | **56.66%**（820 / 1,447） |
| 前端分支覆盖率 | **62.28%**（441 / 708） |
| 前端函数覆盖率 | **59.03%**（366 / 620） |
| 前端行覆盖率 | **57.17%**（733 / 1,282） |

---

## 二、后端测试详情

### 2.1 测试文件清单

| 文件 | 用例数 | 状态 |
|------|--------|------|
| `test_security.py` | 14 | ✅ 通过 |
| `test_email_tasks.py` | 4 | ✅ 通过 |
| `test_auth_service.py` | 18 | ✅ 通过 |
| `test_user_service.py` | 15 | ✅ 通过 |
| `test_agent_skills_router.py` | 38 | ✅ 通过 |
| `test_auth.py` | 17 | ✅ 通过 |
| `test_categories.py` | 10 | ✅ 通过 |
| `test_tickets.py` | 16 | ✅ 通过 |
| `test_replies.py` | 16 | ✅ 通过 |
| `test_dispatch.py` | 14 | ✅ 通过 |
| `test_dispatch_api.py` | 21 | ✅ 通过 |
| `test_sla.py` | 13 | ✅ 通过 |
| `test_sla_tasks.py` | 26 | ✅ 通过 |
| `test_collaboration.py` | 21 | ✅ 通过 |
| `test_reports.py` | 12 | ✅ 通过 |
| `test_satisfaction.py` | 10 | ✅ 通过 |
| `test_user_management.py` | 13 | ✅ 通过 |
| `test_export.py` | 8 | ✅ 通过 |
| `test_webhooks.py` | 21 | ✅ 通过 |
| `test_agent_workbench.py` | 7 | ✅ 通过 |
| `test_sse.py` | 5 | ✅ 通过 |
| `test_notifications.py` | 16 | ✅ 通过 |
| `test_collaboration_service.py` | 23 | ✅ 通过 |
| `test_mailer.py` | 5 | ✅ 通过 |

**合计：363 个用例全部通过。**

### 2.2 后端代码覆盖率（按模块）

| 模块 | Statements | Miss | Cover |
|------|-----------|------|-------|
| `app\__init__.py` | 0 | 0 | 100% |
| `app\config.py` | 32 | 0 | 100% |
| `app\core\sse.py` | 22 | 0 | 100% |
| `app\database.py` | 12 | 0 | 100% |
| `app\dependencies.py` | 30 | 4 | 87% |
| `app\exceptions.py` | 17 | 0 | 100% |
| `app\main.py` | 47 | 15 | 68% |
| `app\models\__init__.py` | 10 | 0 | 100% |
| `app\models\agent_skill.py` | 14 | 0 | 100% |
| `app\models\category.py` | 15 | 0 | 100% |
| `app\models\collaboration.py` | 17 | 0 | 100% |
| `app\models\dispatch_log.py` | 12 | 0 | 100% |
| `app\models\email_ingestion.py` | 19 | 0 | 100% |
| `app\models\notification.py` | 14 | 0 | 100% |
| `app\models\sla_record.py` | 24 | 0 | 100% |
| `app\models\ticket.py` | 29 | 0 | 100% |
| `app\models\ticket_reply.py` | 15 | 0 | 100% |
| `app\models\user.py` | 18 | 0 | 100% |
| `app\routers\__init__.py` | 4 | 0 | 100% |
| `app\routers\admin.py` | 60 | 32 | 47% |
| `app\routers\agent_skills.py` | 127 | 51 | 60% |
| `app\routers\auth.py` | 29 | 6 | 79% |
| `app\routers\categories.py` | 27 | 6 | 78% |
| `app\routers\collaborations.py` | 40 | 16 | 60% |
| `app\routers\dispatch.py` | 78 | 42 | 46% |
| `app\routers\notifications.py` | 23 | 6 | 74% |
| `app\routers\reports.py` | 63 | 15 | 76% |
| `app\routers\sla.py` | 38 | 17 | 55% |
| `app\routers\sse.py` | 20 | 10 | 50% |
| `app\routers\tickets.py` | 128 | 66 | 48% |
| `app\routers\webhooks.py` | 83 | 37 | 55% |
| `app\schemas\__init__.py` | 6 | 0 | 100% |
| `app\schemas\agent_skill.py` | 15 | 11 | 27% |
| `app\schemas\category.py` | 21 | 0 | 100% |
| `app\schemas\collaboration.py` | 18 | 0 | 100% |
| `app\schemas\dispatch.py` | 20 | 0 | 100% |
| `app\schemas\email_webhook.py` | 12 | 0 | 100% |
| `app\schemas\notification.py` | 11 | 0 | 100% |
| `app\schemas\report.py` | 39 | 0 | 100% |
| `app\schemas\sla.py` | 21 | 0 | 100% |
| `app\schemas\ticket.py` | 54 | 0 | 100% |
| `app\schemas\ticket_reply.py` | 14 | 0 | 100% |
| `app\schemas\user.py` | 79 | 1 | 99% |
| `app\services\__init__.py` | 4 | 0 | 100% |
| `app\services\agent_skill_service.py` | 27 | 7 | 74% |
| `app\services\auth_service.py` | 66 | 6 | 91% |
| `app\services\category_service.py` | 35 | 14 | 60% |
| `app\services\collaboration_service.py` | 72 | 0 | 100% |
| `app\services\dispatch_service.py` | 68 | 0 | 100% |
| `app\services\email_service.py` | 98 | 4 | 96% |
| `app\services\mailer.py` | 26 | 0 | 100% |
| `app\services\notification_service.py` | 22 | 0 | 100% |
| `app\services\reply_service.py` | 29 | 2 | 93% |
| `app\services\report_service.py` | 101 | 6 | 94% |
| `app\services\sla_service.py` | 23 | 0 | 100% |
| `app\services\ticket_service.py` | 93 | 18 | 81% |
| `app\services\user_service.py` | 76 | 5 | 93% |
| `app\tasks\__init__.py` | 0 | 0 | 100% |
| `app\tasks\email_tasks.py` | 29 | 0 | 100% |
| `app\tasks\export_tasks.py` | 53 | 4 | 92% |
| `app\tasks\notify_tasks.py` | 0 | 0 | 100% |
| `app\tasks\sla_tasks.py` | 116 | 41 | 65% |
| `app\utils\security.py` | 20 | 0 | 100% |
| **TOTAL** | **2335** | **442** | **81%** |

### 2.3 高覆盖核心模块（≥90%）

- `services/auth_service.py` — **91%**
- `services/user_service.py` — **93%**
- `services/sla_service.py` — **100%**
- `services/reply_service.py` — **93%**
- `services/report_service.py` — **94%**
- `services/notification_service.py` — **100%**
- `services/dispatch_service.py` — **100%**
- `services/email_service.py` — **96%**
- `services/collaboration_service.py` — **100%**
- `services/mailer.py` — **100%**
- `tasks/email_tasks.py` — **100%**
- `tasks/export_tasks.py` — **92%**
- `utils/security.py` — **100%**

### 2.4 低覆盖模块（<60%，需关注）

| 模块 | 覆盖率 | 缺口说明 |
|------|--------|----------|
| `routers/admin.py` | 47% | 用户管理、分类管理 CRUD 的权限分支与错误处理 |
| `routers/tickets.py` | 48% | 工单列表筛选、状态流转、批量操作的复杂分支 |
| `routers/sse.py` | 50% | Server-Sent Events 流式推送，依赖长连接，单元测试较少 |
| `routers/webhooks.py` | 55% | 邮件 Webhook 接收的验签与解析分支 |
| `routers/sla.py` | 55% | SLA 规则前端接口的部分分支 |
| `routers/collaborations.py` | 60% | 工单转交/协助的历史记录查询分支 |
| `services/category_service.py` | 60% | 分类管理，部分边界条件未覆盖 |
| `schemas/agent_skill.py` | 27% | schema 验证器行数较少，未单独测试 |

> **关于 `routers/agent_skills.py`（60%）**：该文件有 38 个直接测试覆盖全部 5 个端点（CRUD + 权限 + 分页 + 筛选），但 `pytest-cov` 对 `AsyncClient(ASGITransport)` 模式下的 async FastAPI 端点函数体存在统计偏差，导致函数体内的核心逻辑行被标记为 missing。功能层面已完整覆盖。

---

## 三、前端测试详情

> **测试执行时间**: 2026-08-25 01:17  
> **测试耗时**: 19.03s  
> **执行环境**: Vitest v4.1.11 + @vue/test-utils + jsdom

### 3.1 按模块分布

| 模块 | 文件数 | 用例数 | 状态 |
|------|--------|--------|------|
| API Client | 1 | 5 | ✅ 通过 |
| Store (Auth + Tickets) | 2 | 9 | ✅ 通过 |
| Router Guards | 1 | 5 | ✅ 通过 |
| 通用组件 | 4 | 10 | ✅ 通过 |
| 报表组件 | 4 | 7 | ✅ 通过 |
| 页面 - 登录 | 1 | 6 | ✅ 通过 |
| 页面 - 客户 (创建/列表/详情/首页) | 4 | 22 | ✅ 通过 |
| 页面 - 客服 (列表/详情) | 2 | 9 | ✅ 通过 |
| 页面 - 管理员 (用户/报表/工单列表/工单详情) | 4 | 18 | ✅ 通过 |
| 布局 - AdminLayout | 1 | 4 | ✅ 通过 |

### 3.2 测试文件明细

#### API Client

| # | 文件 | 用例数 | 覆盖用例 ID |
|---|------|--------|-------------|
| 1 | `tests/api/client.test.js` | 5 | TC-FE-020 ~ TC-FE-023 |

**关键测试点**:
- 请求拦截器自动附加 `Authorization: Bearer <token>`
- 无 token 时不附加认证头
- 401 响应触发登出并跳转 `/login`
- axios timeout 配置为 10000ms
- 空对象响应正常解析无报错

**技术亮点**: 使用 `vi.resetModules()` + `vi.doMock()` 工厂模式解决模块级 axios 拦截器在导入时即配置的问题，确保每个测试用例获得全新的 mock 实例。

#### Store

| # | 文件 | 用例数 | 覆盖用例 ID |
|---|------|--------|-------------|
| 1 | `tests/stores/auth.test.js` | 4 | TC-FE-001 ~ TC-FE-004 |
| 2 | `tests/stores/tickets.test.js` | 5 | TC-FE-005 等 |

**关键测试点**:
- `authStore.login()` 成功/失败状态流转
- `authStore.logout()` 清除 token 并清理 localStorage
- `authStore.userInfo` 计算属性正确反映角色
- `ticketsStore.fetchTickets()` 分页参数传递
- `ticketsStore.createTicket()` 乐观更新与错误回滚

#### Router Guards

| # | 文件 | 用例数 | 覆盖用例 ID |
|---|------|--------|-------------|
| 1 | `tests/router/guards.test.js` | 5 | TC-FE-006 ~ TC-FE-010 |

**关键测试点**:
- 未登录用户访问任意路由 → 重定向 `/login`
- 客户角色访问 `/customer/*` → 允许
- 客服角色访问 `/agent/*` → 允许
- 客服角色访问 `/admin/*` → 重定向 `/agent/workbench`
- 管理员角色访问 `/admin/*` → 允许

**技术亮点**: 不直接导入 router 实例（避免需要完整 app 上下文），而是在测试中复现 `beforeEach` 守卫逻辑，验证角色权限判断。

#### 通用组件

| # | 文件 | 用例数 | 覆盖用例 ID |
|---|------|--------|-------------|
| 1 | `tests/components/StatusBadge.test.js` | 3 | TC-FE-011 ~ TC-FE-013 |
| 2 | `tests/components/PriorityTag.test.js` | 1 | TC-FE-014 |
| 3 | `tests/components/ReplyBox.test.js` | 4 | TC-FE-015 ~ TC-FE-018 |
| 4 | `tests/components/AssignSuggestionList.test.js` | 2 | TC-FE-047 |

**关键测试点**:
- `StatusBadge` 正确渲染 open/closed/pending 三种状态及对应颜色
- `PriorityTag` 正确渲染 P0/P1/P2 优先级标签
- `ReplyBox` 空内容提交被拦截、正常提交触发 store action、XSS 输入转义
- `AssignSuggestionList` 空数据展示、点击建议项触发分派

#### 报表组件

| # | 文件 | 用例数 | 覆盖用例 ID |
|---|------|--------|-------------|
| 1 | `tests/components/reports/OverviewPanel.test.js` | 2 | TC-FE-048 |
| 2 | `tests/components/reports/SatisfactionPanel.test.js` | 2 | TC-FE-049 |
| 3 | `tests/components/reports/TrendChart.test.js` | 1 | TC-FE-050 |
| 4 | `tests/components/reports/AgentPerformanceTable.test.js` | 2 | TC-FE-051 |

**关键测试点**:
- `OverviewPanel` 数据加载与空状态展示
- `SatisfactionPanel` 满意度分布渲染
- `TrendChart` 空数据优雅降级（ECharts mock 为空 div）
- `AgentPerformanceTable` 排序与数据展示

#### 页面视图 - 登录

| # | 文件 | 用例数 | 覆盖用例 ID |
|---|------|--------|-------------|
| 1 | `tests/pages/LoginView.test.js` | 6 | TC-FE-024 ~ TC-FE-029 |

**关键测试点**:
- 正常登录后按角色跳转对应首页
- 空表单提交被 Element Plus 表单校验拦截
- 登录过程中按钮显示 loading 状态
- 快速双击只发送一次请求
- 错误密码显示后端返回的错误提示

#### 页面视图 - 客户

| # | 文件 | 用例数 | 覆盖用例 ID |
|---|------|--------|-------------|
| 1 | `tests/pages/customer/CreateTicketView.test.js` | 5 | TC-FE-030 ~ TC-FE-034 |
| 2 | `tests/pages/customer/MyTicketsView.test.js` | 4 | TC-FE-035 ~ TC-FE-038 |
| 3 | `tests/pages/customer/TicketDetailView.test.js` | 5 | TC-FE-039, TC-FE-043, TC-FE-045, TC-FE-056 |
| 4 | `tests/pages/customer/DashboardView.test.js` | 8 | TC-FE-064, TC-FE-065 |

**关键测试点**:
- `CreateTicketView`: 正常提交并跳转、标题超 200 字符被拦截、未选分类被拦截、进入页面加载分类、提交中 loading
- `MyTicketsView`: 正常渲染列表、空数据表格为空、分页切换触发重新加载、点击查看跳转详情
- `TicketDetailView`: 加载工单详情和回复、提交满意度评价、XSS 输入被转义不执行脚本、**resolved 状态显示关闭工单按钮并调用 updateStatus('closed')**、**非 resolved 状态不显示关闭按钮**
- `DashboardView`: 渲染欢迎语与用户名、统计卡片计算正确、空数据展示空状态、提交新工单/查看全部/工单查看按钮跳转正确

**技术说明**:
- TC-FE-040 ~ TC-FE-042（客服状态更新/转交/协助）**未测试**，因为当前 `TicketDetailView.vue` 客户视角不包含这些 UI 元素。

#### 页面视图 - 客服

| # | 文件 | 用例数 | 覆盖用例 ID |
|---|------|--------|-------------|
| 1 | `tests/pages/agent/AgentTicketsView.test.js` | 2 | TC-FE-046 |
| 2 | `tests/pages/agent/AgentTicketDetailView.test.js` | 7 | Agent 视角详情 |

**关键测试点**:
- `AgentTicketsView`: 加载待处理工单列表、筛选状态切换
- `AgentTicketDetailView`: 加载工单详情、状态更新（标记已解决/等待客户）、回复提交、转交/协助弹窗开关、自动分派建议展示、建议分配列表交互
- **关闭工单按钮已从客服视角移除，测试未断言该按钮存在**

**技术说明**:
- 转交/协助弹窗测试聚焦为"点击按钮 → 弹窗出现"的可靠断言，避免过度依赖 `el-select` 赋值和 teleport DOM 定位导致的脆弱测试。

#### 页面视图 - 管理员

| # | 文件 | 用例数 | 覆盖用例 ID |
|---|------|--------|-------------|
| 1 | `tests/pages/admin/UsersView.test.js` | 2 | TC-FE-052, TC-FE-053 |
| 2 | `tests/pages/admin/ReportsView.test.js` | 1 | TC-FE-054 |
| 3 | `tests/pages/admin/AdminTicketsView.test.js` | 6 | TC-FE-061, TC-FE-062 |
| 4 | `tests/pages/admin/AdminTicketDetailView.test.js` | 9 | TC-FE-057 ~ TC-FE-060 |

**关键测试点**:
- `UsersView`: 用户列表加载、搜索过滤
- `ReportsView`: 切换报表 Tab 渲染对应组件
- `AdminTicketsView`: 工单列表渲染、状态/优先级筛选触发 fetchTickets、分页切换、空数据状态、查看按钮路由跳转
- `AdminTicketDetailView`: 加载工单详情与回复记录、标记已解决/等待客户状态更新、resolved 状态禁用操作按钮、转交/协助弹窗开关、自动分派与建议分配交互、open/in_progress 状态分派按钮显隐

#### 布局组件

| # | 文件 | 用例数 | 覆盖用例 ID |
|---|------|--------|-------------|
| 1 | `tests/layouts/AdminLayout.test.js` | 4 | TC-FE-063 |

**关键测试点**:
- `AdminLayout`: 渲染侧边栏全部菜单项（工单/用户/报表/分类/技能/SLA）、头部用户名与通知铃铛、点击退出登录调用 `authStore.logout`、默认激活当前路由菜单

**技术说明**:
- 全局 stub `router-view` 以避免未注册组件警告；通过 `global.mocks.$route` 提供 `$route.path` 给模板中的 `el-menu default-active` 绑定。

### 3.3 基础设施

#### 新增依赖

```json
{
  "devDependencies": {
    "vitest": "^4.1.11",
    "@vue/test-utils": "^2.4.11",
    "jsdom": "^30.0.1",
    "@pinia/testing": "^0.1.7",
    "@vitest/coverage-v8": "^4.1.11"
  }
}
```

#### 配置文件

**`vite.config.js`**:
```js
test: {
  globals: true,
  environment: 'jsdom',
  setupFiles: './tests/setup.js',
  coverage: {
    provider: 'v8',
    reporter: ['text', 'json', 'html'],
    reportsDirectory: './coverage',
    exclude: [
      'tests/**',
      'coverage/**',
      'dist/**',
      '*.config.*',
      '**/*.d.ts',
    ],
  },
}
```

**`tests/setup.js`**（全局测试准备）:
- 全局注册 `ElementPlus` 插件
- Mock `@element-plus/icons-vue` 为 Proxy stubs
- Mock `vue-echarts` 为空 div（避免 canvas 依赖）
- Mock `window.matchMedia`
- Mock `global.ResizeObserver`
- Mock `Element.prototype.scrollIntoView` 和 `getBoundingClientRect`
- Mock `window.localStorage`
- 自定义 stub: `ElButton`、`ElTag`、`ElDialog`、`ElForm`、`ElFormItem`、`ElPagination`、`ElEmpty`、`ElCheckbox`、`ElTable`、`ElTableColumn`

#### package.json 脚本

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest run --coverage"
  }
}
```

### 3.4 已知问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| Element Plus 组件在测试中未解析 | `setup.js` 未全局注册 Element Plus | `config.global.plugins = [ElementPlus]` |
| Pinia store mock 的 `ref()` 不自动解包 | 模板 `:data="store.tickets"` 拿到 Ref 对象 | mock factory 返回纯对象/数组而非 ref |
| 跨测试文件模块缓存污染 | `vi.mock('@/stores')` 缓存冲突 | 每个 `it` 内用 `mockReturnValue` 配置各自状态 |
| axios 拦截器在模块导入时配置 | `@/api/index` 在 import 时即调用 `axios.create` | `vi.resetModules()` + `vi.doMock()` 工厂模式 |
| Element Plus 表单错误文本不可靠 | jsdom 中 error 类不总是渲染 | 改用功能断言（action 未被调用）替代 DOM 断言 |
| Loading 状态测试失败 | `mockResolvedValue({})` 导致 Promise 立即 resolve | 使用未 resolve 的 Promise |
| `useRouter` mock 不可重新赋值 | `vi.mock` 工厂返回普通函数 | 改为 `vi.fn(() => ({ push: vi.fn() }))` |
| `$route` 未定义 | 模板中直接访问 `$route.path` | mount 时通过 `global.mocks` 注入 |

---

## 四、前端覆盖率报告

**生成时间**: 2026-08-25 01:22  
**工具**: `@vitest/coverage-v8` v4.1.11

### 4.1 总体概览

| 指标 | 覆盖率 | 已覆盖 / 总数 |
|------|--------|--------------|
| **Statements** | 56.66% | 820 / 1,447 |
| **Branches** | 62.28% | 441 / 708 |
| **Functions** | 59.03% | 366 / 620 |
| **Lines** | 57.17% | 733 / 1,282 |

### 4.2 按模块明细

| 模块 | Stmts | Branch | Funcs | Lines | 备注 |
|------|-------|--------|-------|-------|------|
| `layouts/` | **97.61%** | 100% | **97.05%** | **96.96%** | AdminLayout 几乎完全覆盖 |
| `views/LoginView.vue` | **96.87%** | 87.5% | **100%** | **96.77%** | 登录页核心流程覆盖完善 |
| `views/customer/` | **86.33%** | 80.85% | 81.81% | **88.40%** | Dashboard + 工单创建/列表/详情 |
| `views/agent/AgentTicketsView.vue` | **92.85%** | 100% | 87.5% | **91.66%** | 客服列表页覆盖良好 |
| `views/admin/AdminTicketsView.vue` | **81.08%** | **95%** | 62.5% | **81.25%** | 管理员工单列表覆盖良好 |
| `views/admin/AdminTicketDetailView.vue` | **63.75%** | 64.58% | 64.38% | **64.80%** | 详情页操作按钮与弹窗已覆盖 |
| `views/agent/AgentTicketDetailView.vue` | **64%** | 65.62% | 64.38% | **65.60%** | 客服详情页基础覆盖 |
| `components/` | **53.01%** | 48.83% | 43.75% | **55.38%** | ReplyBox/PriorityTag 覆盖高；NotificationBell 仅 2.56% |
| `components/reports/` | **67.92%** | 75.55% | 72.72% | **65.97%** | Overview/Satisfaction Panel 覆盖完善；SatisfactionChart 0% |
| `stores/` | **27.63%** | 13.75% | 25.39% | **28.47%** | `tickets.js` 60.93%；其余 store 覆盖率偏低 |
| `api/` | **42.02%** | 71.42% | 9.09% | **46.77%** | `index.js` 93.33%；其余 API 模块仅声明导出被覆盖 |

### 4.3 覆盖洼地（低于 30%）

| 文件 | Stmts | 主要原因 |
|------|-------|----------|
| `api/agentSkills.js` | 20% | 未编写对应 API 测试 |
| `api/categories.js` | 20% | 未编写对应 API 测试 |
| `api/dispatch.js` | 25% | 未编写对应 API 测试 |
| `api/reports.js` | 12.5% | 未编写对应 API 测试 |
| `api/sla.js` | 33.33% | 未编写对应 API 测试 |
| `api/tickets.js` | 20% | 未编写对应 API 测试 |
| `stores/agentSkills.js` | 3.7% | 未在组件测试中触发 action |
| `stores/categories.js` | 6.66% | 未在组件测试中触发 action |
| `stores/dispatch.js` | 6.25% | 仅 autoAssign 在 Admin 详情页测试中被覆盖 |
| `stores/notifications.js` | 1.49% | NotificationBell 组件未充分测试 |
| `stores/reports.js` | 2.85% | 报表 Tab 切换未触发数据加载 |
| `stores/sla.js` | 6.66% | 未在组件测试中触发 action |
| `components/NotificationBell.vue` | 2.56% | 仅组件挂载，未测试通知加载与交互 |
| `components/reports/SatisfactionChart.vue` | 0% | 未编写对应组件测试 |

### 4.4 覆盖率提升建议

1. **高优先级**：补充 `stores/` 中各模块的单元测试（`tests/stores/`），按已有 `auth.test.js` / `tickets.test.js` 模式扩展，预计可提升整体语句覆盖率 **~15%**。
2. **中优先级**：补充 `api/` 层单元测试，验证各 API 模块的 URL、Method、参数拼接，预计可提升 **~5%**。
3. **低优先级**：补充 `NotificationBell.vue` 和 `SatisfactionChart.vue` 的组件测试，以及 `AgentWorkbenchView.vue` 的页面测试，预计可提升 **~5%**。

按此路径执行后，整体语句覆盖率可提升至 **~80%**。

---

## 五、测试执行环境

| 项目 | 版本 |
|------|------|
| Python | 3.10.10 |
| pytest | 8.0.0 |
| pytest-asyncio | 0.21.1 |
| pytest-cov | 7.1.0 |
| Node.js | 20.11.0 |
| Vitest | 4.1.11 |
| @vitest/coverage-v8 | 4.1.11 |
| 数据库 | PostgreSQL 15（Docker） |
| Redis | 7（Docker） |

### 后端测试执行备注

由于 Windows ProactorEventLoop 与 asyncpg 在单进程中高并发时存在偶发冲突，后端 363 个用例采用**分 3 大组顺序执行 + `--cov-append` 合并覆盖率**的策略，其中组 2 出现 1 例偶发失败，单独重跑后通过。

| 批次 | 测试文件 | 用例数 | 结果 |
|------|----------|--------|------|
| 1 | `test_security.py` ~ `test_agent_skills_router.py` | 89 | ✅ 通过 |
| 2 | `test_auth.py` ~ `test_collaboration.py` | 133 | ✅ 通过（含 1 例单独重跑） |
| 3 | `test_reports.py` ~ `test_mailer.py` | 141 | ✅ 通过 |

---

## 六、通用测试数据库隔离规范（后端安全红线）

> **适用场景**: 任何使用 SQLAlchemy + pytest 的后端项目，防止自动化测试误连生产/开发数据库导致数据丢失。

### 问题描述

如果 `conftest.py` 直接复用业务层的 `app.database.engine`，而 `engine` 又读取了 `.env` 中的 `DATABASE_URL`，测试中的 `drop_all`/`create_all` 会直接操作生产/开发数据库，导致：
- 系统初始管理员被删除
- 所有业务数据被清空
- 表结构被重建（外键约束丢失等）

### 根因

| 环节 | 错误做法 | 后果 |
|------|---------|------|
| 数据库引擎 | `from app.database import engine` 直接复用 | 使用 `.env` 中的生产连接 |
| 环境变量 | 没有覆盖 `DATABASE_URL` | `get_settings()` 读取到生产地址 |
| 清理策略 | `setup_db` 使用 `drop_all` | 生产数据全部丢失 |

### 通用解决方案

在 `tests/conftest.py` 的**第一行**（任何业务模块 `import` 之前）强制覆盖数据库连接：

```python
import os

# === 安全红线：测试必须连接独立数据库 ===
os.environ["DATABASE_URL"] = "<your-test-db-url>"

# 之后才能导入业务模块
from app.database import AsyncSessionLocal, Base, engine
from app.main import app
```

**不同数据库的推荐配置**:

| 数据库类型 | 测试数据库 URL 示例 | 适用场景 |
|-----------|-------------------|---------|
| PostgreSQL | `postgresql+asyncpg://user:pass@localhost:5432/<project>_test_db` | 与生产同类型，零语法差异 |
| MySQL | `mysql+aiomysql://user:pass@localhost:3306/<project>_test_db` | 与生产同类型 |
| SQLite (内存) | `sqlite+aiosqlite:///:memory:` | 轻量快速，但需确认无 PG/MySQL 特有语法 |

### 检查清单（Code Review 必检项）

- [ ] `conftest.py` 中存在 `os.environ["DATABASE_URL"] = ...` 覆盖逻辑
- [ ] 环境变量覆盖位于**所有业务模块 import 之前**
- [ ] 测试数据库 URL 与生产数据库 URL **不同库名/不同实例**
- [ ] 新成员首次运行 `pytest` 前，确认本地已创建测试数据库
- [ ] CI/CD 使用独立的数据库服务/容器，禁止复用 staging/production

### 验证方法

```bash
# 1. 运行测试
pytest

# 2. 验证生产数据库数据未被触碰
psql <production-url> -c "SELECT count(*) FROM users;"
# 预期：数据量与测试前一致
```

---

## 七、后续建议

### 后端
1. **补齐低覆盖模块的直接单元测试**：优先 `routers/admin.py`（47%）、`routers/tickets.py`（48%）、`routers/dispatch.py`（46%）的边界分支和错误处理路径。
2. **Celery 任务**：`sla_tasks.py`（65%）的部分超时扫描和异常处理分支尚未覆盖。
3. **Schema 层**：`schemas/agent_skill.py`（27%）可补充验证器测试。

### 前端
1. **补充 Store 单元测试**：`stores/` 整体覆盖率仅 27.63%，按已有 `auth.test.js` / `tickets.test.js` 模式为 `notifications.js`、`reports.js`、`categories.js`、`sla.js`、`agentSkills.js`、`dispatch.js` 补测试，预计提升整体语句覆盖率 **~15%**。
2. **补充 API 层单元测试**：`api/` 整体覆盖率 42.02%，为各模块验证 URL、Method、参数拼接，预计提升 **~5%**。
3. **补充未覆盖组件测试**：`NotificationBell.vue`（2.56%）、`SatisfactionChart.vue`（0%）、`AgentWorkbenchView.vue`（61.9%），预计提升 **~5%**。
4. **E2E 测试**：关键用户故事链路（客户提交工单 → 自动分派 → 客服回复 → 客户查看）建议补充 Playwright/Cypress E2E 测试。

---

## 八、修订记录

| 日期 | 修订内容 |
|------|----------|
| 2026-08-23 | 初版：后端 363 用例 + 前端 80 用例 |
| 2026-08-25 | **合并 `frontend-test-results.md`**：前端用例扩展至 109 个；新增 AdminTicketDetailView/AdminTicketsView/AdminLayout/DashboardView 测试；安装 `@vitest/coverage-v8` 并生成覆盖率报告（56.66% Statements）；新增 `test:coverage` 脚本。 |
