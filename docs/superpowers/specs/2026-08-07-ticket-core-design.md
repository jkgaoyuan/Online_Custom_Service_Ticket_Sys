# T003 工单核心模块设计文档

> 版本: v1.0  
> 日期: 2026-08-07  
> 状态: 待评审  
> 对应任务: T003（工单核心模块：创建/查询/回复/状态流转）  

---

## 一、设计目标

实现工单系统的最小可用核心链路，覆盖：
- 客户通过 Web 表单提交工单
- 客服在工作台查看、回复、处理工单
- 工单状态按标准流程流转
- 数据范围隔离（客户只能看到自己的工单，客服按分配范围查看）

---

## 二、范围与边界

**包含（T003 范围）：**
| 模块 | 说明 |
|------|------|
| 分类管理（Category） | 基础分类表 + 管理员 CRUD（M1-T11/T12） |
| 工单核心（Ticket） | 模型、创建、列表、详情、基础分派（M1-T13~T16） |
| 工单回复（TicketReply） | 模型、回复接口、内部备注标记（M1-T17/T18） |
| 状态流转 | open→in_progress→resolved→closed 基础流转（M1-T19） |
| 前端页面 | 客户提交页、客户列表/详情、客服工作台（M1-T21~T23） |
| 测试 | 后端 ≥15 条测试 + 前端 ≥10 条测试 |

**不包含（后续任务）：**
- 智能分派算法（T004）——仅保留 assignee_id 字段，支持手动分派和简单创建时分配
- SLA 记录与超时监控（T006）
- 邮件 Webhook 接入（T005）
- 满意度评价（M2-T12）
- 统计报表（T007）

---

## 三、数据模型

基于 `ARCHITECTURE.md` 定义，精确复用以下表结构：

### 3.1 `categories` — 工单分类表

```python
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    default_priority: Mapped[str] = mapped_column(String(10), nullable=False, default="P2")
    sla_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default={"first_resp_hours": 4, "resolution_hours": 24})
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

### 3.2 `tickets` — 工单表

```python
class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_no: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="P2")
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False)
    requester_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    assignee_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="web")
    email_message_id: Mapped[str] = mapped_column(String(100), nullable=True)
    satisfaction: Mapped[str] = mapped_column(String(20), nullable=True)
    satisfaction_note: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
```

**索引：** `idx_tickets_assignee`, `idx_tickets_status`, `idx_tickets_created_at`

### 3.3 `ticket_replies` — 工单回复表

```python
class TicketReply(Base):
    __tablename__ = "ticket_replies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

**索引：** `idx_replies_ticket`

---

## 四、状态机设计

```
                    ┌─────────────┐
         ┌─────────►│    open     │◄────────┐
         │          │   (新建)     │         │
         │          └──────┬──────┘         │
    客户回复               │                 │
         │          ┌──────▼──────┐         │
         └──────────┤ in_progress │         │
                    │   (处理中)   │         │
                    └──────┬──────┘         │
                           │                │
              需客户补充    │    直接解决     │
                           │                │
              ┌────────────┼────────────┐   │
              ▼            ▼            ▼   │
        ┌─────────┐  ┌─────────┐  ┌────────┐│
        │ waiting │  │resolved │  │ closed ││
        │等待回复  │  │ 已解决   │  │ 已关闭  │┘
        └────┬────┘  └────┬────┘  └────────┘
             │            │
             └────────────┘
                  客户确认/超时自动关闭
```

**T003 范围内支持的流转：**
- `open` → `in_progress`: 客服首次回复或主管分派时自动流转
- `in_progress` → `resolved`: 客服标记已解决
- `resolved` → `closed`: 客服确认关闭（T003 暂不实现自动关闭）
- `waiting` 状态：T003 支持状态值定义，但 waiting 的完整客户回复自动流转逻辑延至 M2

**状态值约束：** `CHECK (status IN ('open','in_progress','waiting','resolved','closed'))`

---

## 五、API 设计

### 5.1 分类管理（管理员权限）

| 方法 | 路径 | 说明 | 角色 |
|------|------|------|------|
| GET | `/api/v1/categories` | 列表（全部可用分类） | 任意登录用户 |
| POST | `/api/v1/admin/categories` | 创建分类 | admin |
| PUT | `/api/v1/admin/categories/{id}` | 更新分类 | admin |
| DELETE | `/api/v1/admin/categories/{id}` | 删除分类（软删除/检查无关联工单） | admin |

### 5.2 工单核心

| 方法 | 路径 | 说明 | 角色 | 数据范围 |
|------|------|------|------|----------|
| POST | `/api/v1/tickets` | 创建工单 | customer/agent/admin | 自动填充 requester_id |
| GET | `/api/v1/tickets` | 工单列表（分页+筛选） | 任意登录用户 | customer 只看自己的；agent 看分配给自己的 + open；admin/supervisor 看全部 |
| GET | `/api/v1/tickets/{id}` | 工单详情 | 任意登录用户 | 同上数据范围 |
| POST | `/api/v1/tickets/{id}/replies` | 回复工单 | agent/supervisor/admin | 客户可见回复（is_internal=false）；内部备注仅内部可见 |
| POST | `/api/v1/tickets/{id}/assign` | 分派/转派 | agent/supervisor/admin | 更新 assignee_id，记录流转日志 |
| POST | `/api/v1/tickets/{id}/status` | 更新状态 | agent/supervisor/admin | 状态机校验 |

**请求/响应格式** 严格遵循 `ARCHITECTURE.md` 3.2 节契约。

---

## 六、前端设计

### 6.1 页面与路由

| 页面 | 路由 | 角色 | 说明 |
|------|------|------|------|
| 提交工单 | `/customer/tickets/new` | customer | 表单：标题、分类选择、描述、优先级 |
| 我的工单 | `/customer/tickets` | customer | 列表 + 分页 + 状态筛选 |
| 工单详情 | `/customer/tickets/:id` | customer | 详情 + 回复历史（仅非内部备注） |
| 客服工作台 | `/agent/workbench` | agent/supervisor | 列表 + 详情 + 回复框 + 状态按钮 + 分派 |

### 6.2 组件拆分

- `TicketForm.vue` — 工单表单（复用于客户提交和客服代创建）
- `TicketList.vue` — 工单列表表格
- `TicketDetail.vue` — 工单详情 + 回复时间线
- `ReplyBox.vue` — 回复输入框（支持内部备注开关）
- `StatusBadge.vue` — 状态标签组件
- `PriorityTag.vue` — 优先级标签组件

---

## 七、测试策略

遵循 `testing-guidelines.md`。

### 7.1 后端最小测试集（目标 ≥20 条）

| 维度 | 数量 | 示例 |
|------|------|------|
| P0 正向 | 5 | 创建工单、列表查询、详情查看、回复、状态流转 |
| P0 异常 | 5 | 404 不存在、409 状态冲突、422 校验失败、401 未认证 |
| P1 边界 | 4 | 标题 201/200 字符、负数 ID、空数组、空对象 |
| P1 权限 | 4 | 客户越权查看他人工单、客服修改非分配工单、未认证访问 |
| P1 安全 | 2 | SQL 注入尝试、XSS 内容过滤 |

### 7.2 前端最小测试集（目标 ≥10 条）

| 维度 | 数量 | 示例 |
|------|------|------|
| P0 渲染 | 2 | 列表正常加载、空状态 |
| P0 交互 | 2 | 表单提交、状态按钮点击 |
| P0 权限 | 1 | 未登录跳转 |
| P1 Loading Guard | 2 | 提交中禁用、重复点击忽略 |
| P1 数据联动 | 2 | 回复后列表刷新、状态变更后 Badge 更新 |
| P1 Fallback | 1 | 未知状态值显示原始字符串 |

---

## 八、关键决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 工单编号 | `TK-YYYYMMDD-XXXX` | 可读性好，支持日级别排序 |
| 状态机实现 | 数据库 CHECK + 服务层校验 | 数据库保底线，服务层提供友好错误 |
| 数据范围 | 查询时过滤，非中间件 | 不同接口过滤条件不同，中间件不适合 |
| 基础分派 | 创建时可选 assignee，或按最小负载 | 为 T004 智能分派预留接口，不阻塞 T003 |
| 回复附件 | T003 不包含 | YAGNI，M2 按需扩展 |

---

## 九、与现有代码的集成点

| 集成点 | 已有文件 | 扩展方式 |
|--------|----------|----------|
| 用户模型 | `app/models/user.py` | 新增关联关系（不需要修改） |
| 认证依赖 | `app/dependencies.py` | 复用 `get_current_user`, `require_role` |
| 数据库基类 | `app/database.py` | 复用 `Base` |
| 主路由注册 | `app/main.py` | include 新 routers |
| 前端路由 | `frontend/src/router/index.js` | 新增角色路由 |
| 前端布局 | `frontend/src/layouts/*.vue` | 新增菜单项 |
| 前端 API | `frontend/src/api/index.js` | 新增 ticket API 模块 |

---

## 十、验收标准

- [ ] 客户可注册/登录并提交工单
- [ ] 客服登录后可在工作台看到工单（含自动/手动分派）
- [ ] 客服可回复工单，客户可看到回复（内部备注不可见）
- [ ] 工单状态可正确流转（open → in_progress → resolved → closed）
- [ ] 后端测试 ≥20 条通过，前端测试 ≥10 条通过
- [ ] 所有 API 通过 `pytest` 和 `curl` 手动验证
