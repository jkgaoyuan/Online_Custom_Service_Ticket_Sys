# M2-T20 用户管理后台设计文档

> 版本: v1.0  
> 日期: 2026-08-11  
> 状态: 设计评审  
> 对应任务: M2-T20（管理后台用户管理部分）

---

## 一、设计目标

实现管理员对用户账户的完整管理能力：

- 管理员可查看所有用户列表，按角色/状态筛选
- 管理员可创建用户（指定角色、初始密码）
- 管理员可编辑用户信息（用户名、邮箱、角色、状态）
- 管理员可禁用/启用用户（软删除，保留数据）
- 管理员可重置用户密码（生成临时密码或发送重置链接）
- 客服主管可查看客服列表和负载情况

---

## 二、范围与边界

**本设计包含：**

| 模块 | 说明 | 对应子任务 |
|------|------|-----------|
| 用户列表 API | 分页查询 + 角色/状态筛选 | M2-T20 |
| 用户详情 API | 查看用户信息 + 关联统计 | M2-T20 |
| 创建用户 API | 管理员直接创建（已部分存在） | M2-T20 |
| 编辑用户 API | 修改信息、角色、状态 | M2-T20 |
| 重置密码 API | 管理员重置指定用户密码 | M2-T20 |
| 用户管理页面 | 前端表格 + 操作按钮 | M2-T20 |

**本设计不包含（留给后续任务）：**

- 用户自服务（修改个人信息、修改密码）
- 批量导入/导出用户
- 用户组织架构（部门/组）
- 用户登录日志/审计日志
- 用户头像/个人资料扩展

---

## 三、关键决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 用户禁用 | 软删除（`is_active = FALSE`） | 保留历史工单关联，避免数据断裂 |
| 密码重置 | 管理员设置临时密码，用户首次登录强制修改 | 最简单可靠，不依赖邮件系统 |
| 角色修改 | 管理员可修改任意角色 | 人员调动常见需求 |
| 创建用户权限 | 仅 admin 可创建所有角色；supervisor 仅可创建 agent | 分级管理，减少 admin 负担 |
| 用户统计 | 列表接口附带工单数量（缓存或子查询） | 管理后台一目了然 |
| 排序 | 默认按创建时间倒序，支持按用户名排序 | 最新用户优先展示 |

---

## 四、数据模型

### 4.1 复用现有 `users` 表

`users` 表已包含所有必要字段，无需新增表：

```sql
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50) NOT NULL UNIQUE,
    email           VARCHAR(100) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('customer','agent','supervisor','admin')),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 无需新增字段

现有字段已满足用户管理需求：
- `is_active` — 禁用/启用控制
- `role` — 角色变更
- `updated_at` — 记录修改时间

---

## 五、业务逻辑

### 5.1 用户列表查询

```python
async def list_users(db, role: str | None = None, is_active: bool | None = None,
                    page: int = 1, page_size: int = 20) -> dict:
    """
    分页查询用户列表，支持角色和状态筛选。
    返回用户信息 + 关联工单数量统计。
    """
    from sqlalchemy import select, func, and_

    # 基础查询
    base_stmt = select(User)
    count_stmt = select(func.count(User.id))

    filters = []
    if role:
        filters.append(User.role == role)
    if is_active is not None:
        filters.append(User.is_active == is_active)

    if filters:
        base_stmt = base_stmt.where(and_(*filters))
        count_stmt = count_stmt.where(and_(*filters))

    # 分页
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    result = await db.execute(
        base_stmt
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    users = result.scalars().all()

    # 统计每个用户的工单数（子查询或批量查询）
    user_ids = [u.id for u in users]
    stats_stmt = (
        select(Ticket.assignee_id, func.count(Ticket.id))
        .where(Ticket.assignee_id.in_(user_ids))
        .group_by(Ticket.assignee_id)
    )
    stats_result = await db.execute(stats_stmt)
    ticket_counts = {uid: cnt for uid, cnt in stats_result.all()}

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at,
                "ticket_count": ticket_counts.get(u.id, 0),
            }
            for u in users
        ],
    }
```

### 5.2 编辑用户

```python
async def update_user(db, user_id: int, update_data: dict) -> User:
    """
    更新用户信息。
    允许修改：username, email, role, is_active
    不允许修改：id, password_hash（通过单独重置密码接口）
    """
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 校验唯一性（username / email）
    if "username" in update_data and update_data["username"] != user.username:
        dup = await db.execute(
            select(User).where(User.username == update_data["username"], User.id != user_id)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="用户名已存在")
        user.username = update_data["username"]

    if "email" in update_data and update_data["email"] != user.email:
        dup = await db.execute(
            select(User).where(User.email == update_data["email"], User.id != user_id)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="邮箱已存在")
        user.email = update_data["email"]

    if "role" in update_data:
        if update_data["role"] not in ("customer", "agent", "supervisor", "admin"):
            raise HTTPException(status_code=400, detail="无效的角色")
        user.role = update_data["role"]

    if "is_active" in update_data:
        user.is_active = bool(update_data["is_active"])

    user.updated_at = datetime.utcnow()
    return user
```

### 5.3 重置密码

```python
import secrets
import string

async def reset_user_password(db, user_id: int) -> str:
    """
    管理员重置用户密码，生成 12 位随机临时密码。
    返回临时密码（明文，仅展示一次）。
    """
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    user.password_hash = get_password_hash(temp_password)
    user.updated_at = datetime.utcnow()

    # 可选：发送密码重置通知（站内信）
    await create_notification(
        db,
        user_id=user_id,
        type="password_reset",
        title="您的密码已被管理员重置",
        message="请使用临时密码登录后立即修改密码。",
        data={"user_id": user_id},
    )

    return temp_password
```

---

## 六、API 设计

### 6.1 用户列表

| 方法 | 路径 | 说明 | 角色 |
|------|------|------|------|
| GET | `/api/v1/admin/users` | 分页查询用户列表 | admin / supervisor |

**Query Params:**
- `role` — 筛选角色（customer/agent/supervisor/admin）
- `is_active` — 筛选状态（1/0）
- `page` — 页码，默认 1
- `page_size` — 每页数量，默认 20

**Response (200):**
```json
{
  "total": 156,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 1,
      "username": "admin01",
      "email": "admin@company.com",
      "role": "admin",
      "is_active": true,
      "created_at": "2026-08-01T10:00:00Z",
      "ticket_count": 0
    },
    {
      "id": 2,
      "username": "agent01",
      "email": "agent@company.com",
      "role": "agent",
      "is_active": true,
      "created_at": "2026-08-02T10:00:00Z",
      "ticket_count": 15
    }
  ]
}
```

> supervisor 调用时，返回角色为 `agent` 的用户列表（仅客服）。

### 6.2 用户详情

| 方法 | 路径 | 说明 | 角色 |
|------|------|------|------|
| GET | `/api/v1/admin/users/{id}` | 查看用户详情 + 统计 | admin / supervisor |

**Response (200):**
```json
{
  "id": 2,
  "username": "agent01",
  "email": "agent@company.com",
  "role": "agent",
  "is_active": true,
  "created_at": "2026-08-02T10:00:00Z",
  "updated_at": "2026-08-10T10:00:00Z",
  "stats": {
    "total_tickets": 45,
    "resolved_tickets": 38,
    "open_tickets": 7,
    "avg_first_resp_minutes": 18.5
  }
}
```

### 6.3 编辑用户

| 方法 | 路径 | 说明 | 角色 |
|------|------|------|------|
| PUT | `/api/v1/admin/users/{id}` | 修改用户信息 | admin（supervisor 只能修改 agent） |

**Request:**
```json
{
  "username": "agent01-new",
  "email": "agent01@company.com",
  "role": "agent",
  "is_active": true
}
```

### 6.4 重置密码

| 方法 | 路径 | 说明 | 角色 |
|------|------|------|------|
| POST | `/api/v1/admin/users/{id}/reset-password` | 重置用户密码 | admin |

**Response (200):**
```json
{
  "temp_password": "aB3xK9mPqR7w"
}
```

> **安全提示**：临时密码仅返回一次，不存储明文。用户需登录后立即修改。

### 6.5 创建用户（已存在，扩展）

现有 `POST /api/v1/auth/users` 已支持 admin 创建用户。需增加 `supervisor` 创建 `agent` 的权限支持。

---

## 七、与现有代码的集成点

| 集成点 | 已有文件 | 扩展方式 |
|--------|----------|----------|
| 用户创建 | `app/routers/auth.py` | 已有 `POST /auth/users`，扩展 supervisor 可创建 agent |
| 用户列表/编辑 | 新增 | 在 `admin` router 或新建 `users` router 中实现 |
| 密码哈希 | `app/services/auth_service.py` | 复用 `get_password_hash()` |
| 通知系统 | `app/services/notification_service.py` | 重置密码时发送站内通知 |
| 工单统计 | `app/services/report_service.py` | 用户详情中复用统计逻辑 |

---

## 八、测试策略

目标：**≥8 条后端测试**

| 维度 | 数量 | 示例 |
|------|------|------|
| P0 正向 — 列表 | 2 | 分页查询成功；按 role=agent 筛选正确 |
| P0 正向 — 编辑 | 2 | 修改角色成功；禁用用户成功 |
| P0 正向 — 重置密码 | 1 | 重置后密码可用，旧密码失效 |
| P0 异常 | 2 | 修改成已存在用户名 400；supervisor 修改 admin 403 |
| P1 权限 | 1 | customer 访问 admin/users 403 |

---

## 九、验收标准

- [ ] admin 可查看所有用户列表，按角色/状态筛选和分页
- [ ] admin 可创建任意角色的用户
- [ ] supervisor 可查看客服列表，可创建 agent
- [ ] admin 可编辑用户信息（用户名、邮箱、角色、状态）
- [ ] admin 可禁用用户，禁用后该用户无法登录
- [ ] admin 可重置用户密码，生成临时密码
- [ ] 用户列表展示关联工单数量
- [ ] 后端测试 ≥8 条全部通过
- [ ] 前端用户管理页面可正常使用（表格、筛选、编辑、禁用、重置密码）

---

## 十、前端设计（M2-T20）

### 10.1 用户管理页面

实现 `UsersView.vue`（当前为 TODO 占位）：

- **表格区域**：
  - 列：ID、用户名、邮箱、角色（标签展示）、状态（启用/禁用标签）、工单数、创建时间、操作
  - 操作列：编辑、重置密码、禁用/启用
- **筛选区域**：
  - 角色下拉筛选（全部/customer/agent/supervisor/admin）
  - 状态下拉筛选（全部/启用/禁用）
  - 搜索框（用户名/邮箱模糊搜索，可选）
- **分页区域**：Element Plus `Pagination`
- **新建按钮**：跳转到创建用户弹窗

### 10.2 编辑用户弹窗

- 表单：用户名、邮箱、角色选择器、状态开关
- 校验：用户名唯一、邮箱唯一、角色必填
- 保存后刷新列表

### 10.3 重置密码弹窗

- 确认弹窗："确定重置用户 xxx 的密码？"
- 成功后弹窗显示临时密码（可复制）
- 提示："请妥善保存，临时密码仅显示一次"

### 10.4 禁用/启用确认

- 操作前确认弹窗："确定禁用用户 xxx？禁用后该用户将无法登录。"
- 禁用按钮根据当前状态切换为启用

