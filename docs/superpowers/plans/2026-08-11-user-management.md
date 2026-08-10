# 用户管理后台实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现管理员对用户账户的完整管理：列表查询、编辑、禁用/启用、重置密码。复用现有 `users` 表，无需新增表。

**Architecture:** 后端新增 admin 级别用户管理 API（列表、详情、编辑、重置密码），前端实现 `UsersView.vue` 管理页面。`supervisor` 可查看客服列表和创建 agent，`admin` 拥有全部权限。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, pytest, Vue 3, Element Plus

## Global Constraints
- 用户禁用使用软删除（`is_active = False`），保留历史数据关联
- 密码重置生成 12 位随机临时密码，仅返回一次明文
- 用户名/邮箱唯一性校验，编辑时排除自身
- 测试使用 `client` + `admin_auth_headers` + `supervisor_auth_headers` fixtures
- `supervisor` 只能修改 `agent` 角色用户，不能修改 `admin`
- API 响应使用 Pydantic Schema 序列化

---

## File Map

| 文件 | 职责 | 操作 |
|------|------|------|
| `backend/app/schemas/user.py` | 新增 `UserUpdate`, `UserListResponse`, `UserDetailResponse` | 修改 |
| `backend/app/services/user_service.py` | `list_users`, `update_user`, `reset_user_password` | 创建 |
| `backend/app/routers/admin.py` | 新增用户管理端点（或扩展 auth router） | 修改/创建 |
| `backend/app/main.py` | 注册 admin router | 修改 |
| `backend/tests/test_user_management.py` | 用户管理测试 | 创建 |
| `frontend/src/views/admin/UsersView.vue` | 用户管理页面（当前 TODO） | 重写 |
| `frontend/src/stores/users.js` | 用户管理状态 store | 创建 |

---

### Task 1: 后端 Schema 扩展

**Files:**
- Modify: `backend/app/schemas/user.py`

**Interfaces:**
- Consumes: 现有 `User` 模型字段
- Produces: `UserUpdate`, `UserListResponse`, `UserDetailResponse` Schema

- [ ] **Step 1: 在 user.py 中追加 Schema**

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, pattern="^(customer|agent|supervisor|admin)$")
    is_active: Optional[bool] = None


class UserListItem(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    ticket_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[UserListItem]


class UserStats(BaseModel):
    total_tickets: int
    resolved_tickets: int
    open_tickets: int
    avg_first_resp_minutes: Optional[float] = None


class UserDetailResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    stats: Optional[UserStats] = None

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/user.py
git commit -m "feat(user-mgmt): add user update and list/detail schemas"
```

---

### Task 2: 用户管理 Service

**Files:**
- Create: `backend/app/services/user_service.py`

**Interfaces:**
- Consumes: `User` 模型，`create_notification` service
- Produces: `list_users`, `update_user`, `reset_user_password` 函数

- [ ] **Step 1: 创建 user_service.py**

```python
import secrets
import string
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket
from app.models.user import User
from app.services.notification_service import create_notification
from app.utils.security import get_password_hash


async def list_users(
    db: AsyncSession,
    role: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
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

    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    result = await db.execute(
        base_stmt
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    users = result.scalars().all()

    # 批量统计工单数
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


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user(db: AsyncSession, user_id: int, update_data: dict) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

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
    await db.commit()
    await db.refresh(user)
    return user


async def reset_user_password(db: AsyncSession, user_id: int) -> str:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    temp_password = ''.join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(12)
    )
    user.password_hash = get_password_hash(temp_password)
    user.updated_at = datetime.utcnow()

    await create_notification(
        db,
        user_id=user_id,
        type="password_reset",
        title="您的密码已被管理员重置",
        message="请使用临时密码登录后立即修改密码。",
        data={"user_id": user_id},
    )

    await db.commit()
    return temp_password
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/user_service.py
git commit -m "feat(user-mgmt): add user list, update, and reset password service"
```

---

### Task 3: Admin Router — 用户管理端点

**Files:**
- Create: `backend/app/routers/admin.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `list_users`, `update_user`, `reset_user_password`, `get_user_by_id` services
- Produces: `GET /admin/users`, `GET /admin/users/{id}`, `PUT /admin/users/{id}`, `POST /admin/users/{id}/reset-password`

- [ ] **Step 1: 创建 admin router**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.user import UserListResponse, UserDetailResponse, UserUpdate, UserResponse
from app.services.user_service import list_users, update_user, reset_user_password, get_user_by_id
from app.services.report_service import get_agent_stats  # 复用报表服务中的统计

router = APIRouter()


@router.get("/admin/users", response_model=UserListResponse)
async def list_users_endpoint(
    role: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    # supervisor 只能查看 agent 列表
    if current_user.role == "supervisor" and role is None:
        role = "agent"
    if current_user.role == "supervisor" and role and role != "agent":
        raise HTTPException(status_code=403, detail="无权查看该角色用户")

    return await list_users(db, role=role, is_active=is_active, page=page, page_size=page_size)


@router.get("/admin/users/{user_id}", response_model=UserDetailResponse)
async def get_user_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    # supervisor 只能查看 agent 详情
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if current_user.role == "supervisor" and user.role != "agent":
        raise HTTPException(status_code=403, detail="无权查看该用户")

    # 统计（简化版，可复用 report_service）
    stats = None
    if user.role in ("agent", "supervisor", "admin"):
        from sqlalchemy import func, select
        from app.models.ticket import Ticket
        total_tickets = await db.execute(
            select(func.count(Ticket.id)).where(Ticket.assignee_id == user_id)
        )
        resolved_tickets = await db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.assignee_id == user_id, Ticket.status == "closed"
            )
        )
        open_tickets = await db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.assignee_id == user_id, Ticket.status != "closed"
            )
        )
        stats = {
            "total_tickets": total_tickets.scalar(),
            "resolved_tickets": resolved_tickets.scalar(),
            "open_tickets": open_tickets.scalar(),
            "avg_first_resp_minutes": None,
        }

    return UserDetailResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        stats=stats,
    )


@router.put("/admin/users/{user_id}", response_model=UserResponse)
async def update_user_endpoint(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # supervisor 只能修改 agent
    if current_user.role == "supervisor":
        if user.role != "agent":
            raise HTTPException(status_code=403, detail="无权修改该用户")
        if data.role and data.role != "agent":
            raise HTTPException(status_code=403, detail="只能设置角色为 agent")

    # admin 不能修改自己的 role（防止误操作锁定）
    if current_user.id == user_id and data.role and data.role != user.role:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")

    updated = await update_user(db, user_id, data.model_dump(exclude_unset=True))
    return UserResponse.model_validate(updated)


@router.post("/admin/users/{user_id}/reset-password", response_model=dict)
async def reset_password_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    temp_password = await reset_user_password(db, user_id)
    return {"temp_password": temp_password}
```

- [ ] **Step 2: 在 main.py 注册 router**

在 `backend/app/main.py` 中导入并注册：

```python
from app.routers import admin

# ...
app.include_router(admin.router, prefix="/api/v1", tags=["Admin"])
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/admin.py backend/app/main.py
git commit -m "feat(user-mgmt): add admin user management endpoints"
```

---

### Task 4: 后端测试

**Files:**
- Create: `backend/tests/test_user_management.py`

**Interfaces:**
- Consumes: `client`, `db`, `admin_auth_headers`, `supervisor_auth_headers` fixtures
- Produces: 8 条测试全部通过

- [ ] **Step 1: 编写测试**

```python
from sqlalchemy import select

from app.models.user import User
from app.utils.security import get_password_hash, verify_password


# === P0 正向 ===

# USR-001: admin 查询用户列表成功
async def test_admin_list_users_200(client, admin_auth_headers, db):
    r = await client.get("/api/v1/admin/users", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "items" in data


# USR-002: 按 role=agent 筛选
async def test_list_users_filter_role_200(client, admin_auth_headers, db):
    r = await client.get("/api/v1/admin/users?role=agent", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    for item in data["items"]:
        assert item["role"] == "agent"


# USR-003: 编辑用户信息成功
async def test_update_user_200(client, admin_auth_headers, db):
    # 创建一个测试用户
    user = User(username="testuser99", email="test99@test.com", password_hash=get_password_hash("p"), role="customer")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    body = {"username": "testuser99_new", "email": "new99@test.com", "is_active": False}
    r = await client.put(
        f"/api/v1/admin/users/{user.id}",
        headers=admin_auth_headers,
        json=body,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "testuser99_new"
    assert data["is_active"] == False


# USR-004: 重置密码成功
async def test_reset_password_200(client, admin_auth_headers, db):
    user = User(username="resetme", email="reset@test.com", password_hash=get_password_hash("old"), role="customer")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    r = await client.post(
        f"/api/v1/admin/users/{user.id}/reset-password",
        headers=admin_auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["temp_password"]) == 12

    # 验证密码已变更
    await db.refresh(user)
    assert verify_password(data["temp_password"], user.password_hash)


# USR-005: supervisor 只能查看 agent 列表
async def test_supervisor_list_agent_only_200(client, supervisor_auth_headers, db):
    r = await client.get("/api/v1/admin/users", headers=supervisor_auth_headers)
    assert r.status_code == 200
    data = r.json()
    for item in data["items"]:
        assert item["role"] == "agent"


# === P0 异常 ===

# USR-006: customer 访问用户列表 403
async def test_customer_list_users_403(client, customer_auth_headers, db):
    r = await client.get("/api/v1/admin/users", headers=customer_auth_headers)
    assert r.status_code == 403


# USR-007: 修改成已存在用户名 400
async def test_update_user_duplicate_username_400(client, admin_auth_headers, db):
    # 现有 customer_test 用户
    existing = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    # 创建另一个用户
    user = User(username="dup_test", email="dup@test.com", password_hash=get_password_hash("p"), role="customer")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    body = {"username": existing.username}
    r = await client.put(
        f"/api/v1/admin/users/{user.id}",
        headers=admin_auth_headers,
        json=body,
    )
    assert r.status_code == 400
    assert "用户名已存在" in r.json()["detail"]


# USR-008: admin 修改自己的角色 400
async def test_admin_update_self_role_400(client, admin_auth_headers, db):
    # 获取 admin 用户 ID（假设 fixture 中 admin 用户名是 admin_test）
    admin = (await db.execute(select(User).where(User.username == "admin_test"))).scalar_one()
    body = {"role": "customer"}
    r = await client.put(
        f"/api/v1/admin/users/{admin.id}",
        headers=admin_auth_headers,
        json=body,
    )
    assert r.status_code == 400
    assert "不能修改自己的角色" in r.json()["detail"]

```

- [ ] **Step 2: 运行测试**

```bash
cd backend
pytest tests/test_user_management.py -v
```

Expected: 8 passed, 0 failed

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_user_management.py
git commit -m "test(user-mgmt): add 8 backend tests for user management"
```

---

### Task 5: 前端用户管理页面

**Files:**
- Modify: `frontend/src/views/admin/UsersView.vue`
- Create: `frontend/src/stores/users.js`

**Interfaces:**
- Consumes: `GET /api/v1/admin/users`, `PUT /api/v1/admin/users/{id}`, `POST /api/v1/admin/users/{id}/reset-password`
- Produces: 用户管理表格、编辑弹窗、重置密码弹窗

- [ ] **Step 1: 创建 users store**

```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useUsersStore = defineStore('users', () => {
  const users = ref([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchUsers(params = {}) {
    loading.value = true
    try {
      const response = await api.get('/admin/users', { params })
      users.value = response.data.items
      total.value = response.data.total
    } finally {
      loading.value = false
    }
  }

  async function updateUser(userId, data) {
    const response = await api.put(`/admin/users/${userId}`, data)
    return response.data
  }

  async function resetPassword(userId) {
    const response = await api.post(`/admin/users/${userId}/reset-password`)
    return response.data
  }

  return { users, total, loading, fetchUsers, updateUser, resetPassword }
})
```

- [ ] **Step 2: 重写 UsersView.vue**

```vue
<template>
  <div class="users-management">
    <h2>用户管理</h2>

    <!-- 筛选区域 -->
    <div class="filter-bar">
      <el-select v-model="filterRole" placeholder="角色" clearable @change="handleFilter">
        <el-option label="全部" value="" />
        <el-option label="客户" value="customer" />
        <el-option label="客服" value="agent" />
        <el-option label="主管" value="supervisor" />
        <el-option label="管理员" value="admin" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="状态" clearable @change="handleFilter">
        <el-option label="全部" value="" />
        <el-option label="启用" :value="true" />
        <el-option label="禁用" :value="false" />
      </el-select>
    </div>

    <!-- 用户表格 -->
    <el-table :data="usersStore.users" v-loading="usersStore.loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="role" label="角色">
        <template #default="{ row }">
          <el-tag :type="roleTagType(row.role)">{{ roleLabel(row.role) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="ticket_count" label="工单数" width="80" />
      <el-table-column prop="created_at" label="创建时间">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="warning" @click="openResetPassword(row)">重置密码</el-button>
          <el-button
            size="small"
            :type="row.is_active ? 'danger' : 'success'"
            @click="toggleStatus(row)"
          >
            {{ row.is_active ? '禁用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="usersStore.total"
      layout="total, prev, pager, next"
      @change="handleFilter"
    />

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑用户" width="400px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role">
            <el-option label="客户" value="customer" />
            <el-option label="客服" value="agent" />
            <el-option label="主管" value="supervisor" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitEdit" :loading="editLoading">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码弹窗 -->
    <el-dialog v-model="resetDialogVisible" title="重置密码" width="400px">
      <p>确定重置用户 <strong>{{ resetTarget?.username }}</strong> 的密码？</p>
      <p class="warning-text">重置后将生成临时密码，请妥善保存。</p>
      <div v-if="tempPassword" class="temp-password-box">
        <p>临时密码：<code>{{ tempPassword }}</code></p>
        <el-button size="small" @click="copyPassword">复制</el-button>
      </div>
      <template #footer>
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button v-if="!tempPassword" type="warning" @click="confirmReset" :loading="resetLoading">确认重置</el-button>
        <el-button v-else type="primary" @click="resetDialogVisible = false">完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useUsersStore } from '@/stores/users'
import { ElMessage, ElMessageBox } from 'element-plus'

const usersStore = useUsersStore()

const filterRole = ref('')
const filterStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(20)

const editDialogVisible = ref(false)
const editLoading = ref(false)
const editForm = reactive({ id: null, username: '', email: '', role: '' })

const resetDialogVisible = ref(false)
const resetLoading = ref(false)
const resetTarget = ref(null)
const tempPassword = ref('')

function roleTagType(role) {
  const map = { customer: 'info', agent: 'primary', supervisor: 'warning', admin: 'danger' }
  return map[role] || 'info'
}
function roleLabel(role) {
  const map = { customer: '客户', agent: '客服', supervisor: '主管', admin: '管理员' }
  return map[role] || role
}
function formatDate(d) {
  return d ? new Date(d).toLocaleString() : '-'
}

async function handleFilter() {
  const params = { page: currentPage.value, page_size: pageSize.value }
  if (filterRole.value) params.role = filterRole.value
  if (filterStatus.value !== '') params.is_active = filterStatus.value
  await usersStore.fetchUsers(params)
}

function openEdit(row) {
  editForm.id = row.id
  editForm.username = row.username
  editForm.email = row.email
  editForm.role = row.role
  editDialogVisible.value = true
}

async function submitEdit() {
  editLoading.value = true
  try {
    await usersStore.updateUser(editForm.id, {
      username: editForm.username,
      email: editForm.email,
      role: editForm.role,
    })
    ElMessage.success('保存成功')
    editDialogVisible.value = false
    await handleFilter()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    editLoading.value = false
  }
}

function openResetPassword(row) {
  resetTarget.value = row
  tempPassword.value = ''
  resetDialogVisible.value = true
}

async function confirmReset() {
  resetLoading.value = true
  try {
    const result = await usersStore.resetPassword(resetTarget.value.id)
    tempPassword.value = result.temp_password
    ElMessage.success('密码已重置')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '重置失败')
  } finally {
    resetLoading.value = false
  }
}

function copyPassword() {
  navigator.clipboard.writeText(tempPassword.value)
  ElMessage.success('已复制到剪贴板')
}

async function toggleStatus(row) {
  const action = row.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定${action}用户 ${row.username}？`, '确认')
    await usersStore.updateUser(row.id, { is_active: !row.is_active })
    ElMessage.success(`${action}成功`)
    await handleFilter()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '操作失败')
    }
  }
}

onMounted(() => handleFilter())
</script>

<style scoped>
.users-management { padding: 24px; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; }
.warning-text { color: #e6a23c; font-size: 13px; margin-top: 8px; }
.temp-password-box { margin-top: 16px; padding: 12px; background: #f5f7fa; border-radius: 4px; }
.temp-password-box code { font-size: 16px; font-weight: bold; color: #409eff; }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/admin/UsersView.vue frontend/src/stores/users.js
git commit -m "feat(user-mgmt): implement user management page with edit and reset password"
```

---

## Self-Review Checklist

| Spec 要求 | 对应 Task | 状态 |
|-----------|-----------|------|
| 用户列表（分页、筛选） | Task 2/3 | ✅ `list_users` + `GET /admin/users` |
| 用户编辑（用户名、邮箱、角色、状态） | Task 2/3 | ✅ `update_user` + `PUT` 端点 |
| 禁用/启用用户（软删除） | Task 2/3 | ✅ `is_active` 字段控制 |
| 重置密码（临时密码） | Task 2/3 | ✅ `reset_user_password` 生成 12 位随机密码 |
| supervisor 权限限制 | Task 3 | ✅ 只能查看/修改 agent |
| 前端用户管理页面 | Task 5 | ✅ `UsersView.vue` 表格 + 弹窗 |

**Placeholder scan:** 无 TBD/TODO
**Type consistency:** `UserListItem`/`UserDetailResponse` 与 `User` 模型字段一致

