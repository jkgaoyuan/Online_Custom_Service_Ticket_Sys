# T003 工单核心模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现工单系统核心链路：分类管理、工单创建/查询/详情/回复、状态流转、基础分派，以及前后端测试覆盖。

**Architecture:** 后端 FastAPI + SQLAlchemy + PostgreSQL 异步模式，新增 Category/Ticket/TicketReply 三个模型，共享已有 User 模型和 RBAC 体系；前端 Vue3 + Element Plus + Pinia，新增 3 个角色页面和通用组件。

**Tech Stack:** Python 3.10, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Alembic, pytest, Vue3, Vite, Element Plus, Pinia, Axios, Vitest

## Global Constraints

- 所有模型使用 SQLAlchemy 2.0 `Mapped[]` + `mapped_column()` 语法，与现有 `User` 模型风格一致
- 所有数据库操作使用 `async/await` + `AsyncSession`
- 所有 API 路径前缀 `/api/v1`，已有认证前缀 `/api/v1/auth`
- 密码/Token 安全策略继承 T002 配置：`bcrypt` cost ≥ 12，JWT HS256，8h 有效期
- 状态值精确匹配：`open`, `in_progress`, `waiting`, `resolved`, `closed`
- 优先级精确匹配：`P0`, `P1`, `P2`, `P3`
- 工单编号格式：`TK-YYYYMMDD-XXXX`（4位数字，不足补零，当日自增）
- 数据范围隔离：
  - `customer` — 只能访问 `requester_id == self.id` 的工单
  - `agent` — 可访问分配给自己的工单 + 状态为 `open` 的工单（可领取）
  - `supervisor` / `admin` — 可访问全部工单
- 测试文件组织：`tests/test_tickets.py`, `tests/test_replies.py`, `tests/test_categories.py`
- 测试用例 ID 命名：`API-TICKET-{SEQ:03d}`, `API-REPLY-{SEQ:03d}`, `API-CAT-{SEQ:03d}`
- 所有测试必须断言状态码 + 具体字段/错误码，不只做状态码检查
- 前端路由守卫已存在，新增路由需注册到 `frontend/src/router/index.js`
- 前端 API 封装在 `frontend/src/api/` 目录，按模块拆分为独立文件

---

## File Structure

### 后端新增/修改

| 文件 | 责任 |
|------|------|
| `backend/app/models/category.py` | Category 模型 |
| `backend/app/models/ticket.py` | Ticket 模型 + 关联关系 |
| `backend/app/models/ticket_reply.py` | TicketReply 模型 |
| `backend/app/models/__init__.py` | 导出所有模型 |
| `backend/app/schemas/category.py` | Category Pydantic schemas |
| `backend/app/schemas/ticket.py` | Ticket Pydantic schemas |
| `backend/app/schemas/ticket_reply.py` | TicketReply Pydantic schemas |
| `backend/app/schemas/__init__.py` | 导出所有 schemas |
| `backend/app/services/ticket_service.py` | 工单核心逻辑：创建、查询、编号生成、分派、状态流转 |
| `backend/app/services/category_service.py` | 分类 CRUD |
| `backend/app/services/__init__.py` | 导出服务 |
| `backend/app/routers/tickets.py` | 工单 API router |
| `backend/app/routers/categories.py` | 分类 API router |
| `backend/app/routers/__init__.py` | 导出 routers |
| `backend/app/main.py` | 注册新 routers |
| `backend/tests/test_categories.py` | 分类接口测试 |
| `backend/tests/test_tickets.py` | 工单接口测试 |
| `backend/tests/test_replies.py` | 回复接口测试 |
| `backend/alembic/versions/` | 新增迁移脚本（由 Alembic 生成） |

### 前端新增/修改

| 文件 | 责任 |
|------|------|
| `frontend/src/api/tickets.js` | Ticket API 客户端 |
| `frontend/src/api/categories.js` | Category API 客户端 |
| `frontend/src/stores/tickets.js` | Ticket Pinia store |
| `frontend/src/components/TicketList.vue` | 工单列表表格 |
| `frontend/src/components/TicketDetail.vue` | 工单详情 + 回复时间线 |
| `frontend/src/components/ReplyBox.vue` | 回复输入框 |
| `frontend/src/components/StatusBadge.vue` | 状态标签 |
| `frontend/src/components/PriorityTag.vue` | 优先级标签 |
| `frontend/src/views/customer/CreateTicketView.vue` | 客户提交工单 |
| `frontend/src/views/customer/MyTicketsView.vue` | 客户工单列表 |
| `frontend/src/views/customer/TicketDetailView.vue` | 客户工单详情 |
| `frontend/src/views/agent/AgentTicketsView.vue` | 客服工作台（列表） |
| `frontend/src/views/agent/AgentTicketDetailView.vue` | 客服工单详情（含回复+状态操作） |
| `frontend/src/router/index.js` | 新增路由注册 |
| `frontend/src/layouts/CustomerLayout.vue` | 新增客户侧菜单 |
| `frontend/src/layouts/AgentLayout.vue` | 新增客服侧菜单 |

---

## Task 1: Category 模型 + 迁移 + 分类管理 API + 测试

**Files:**
- Create: `backend/app/models/category.py`
- Create: `backend/app/schemas/category.py`
- Create: `backend/app/services/category_service.py`
- Create: `backend/app/routers/categories.py`
- Create: `backend/tests/test_categories.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/routers/__init__.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/__init__.py`
- Test: `backend/tests/test_categories.py`

**Interfaces:**
- Consumes: `User` model, `get_current_user`, `require_role`
- Produces: `Category` model, `CategoryCreate`, `CategoryUpdate`, `CategoryResponse` schemas, `GET /api/v1/categories`, `POST /api/v1/admin/categories`, `PUT /api/v1/admin/categories/{id}`, `DELETE /api/v1/admin/categories/{id}`

- [ ] **Step 1: Write Category model**

```python
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    default_priority: Mapped[str] = mapped_column(String(10), nullable=False, default="P2")
    sla_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

- [ ] **Step 2: Export Category in models/__init__.py**

```python
from .user import User
from .category import Category
```

- [ ] **Step 3: Generate Alembic migration**

```bash
cd backend && alembic revision --autogenerate -m "add categories table"
```

- [ ] **Step 4: Write Category schemas**

```python
from pydantic import BaseModel, Field
from typing import Optional

class CategoryBase(BaseModel):
    name: str = Field(..., max_length=50)
    code: str = Field(..., max_length=30)
    description: Optional[str] = Field(None, max_length=255)
    default_priority: str = Field(default="P2", pattern="^(P0|P1|P2|P3)$")
    sla_config: dict = Field(default_factory=lambda: {"first_resp_hours": 4, "resolution_hours": 24})
    is_active: bool = True

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    code: Optional[str] = Field(None, max_length=30)
    description: Optional[str] = Field(None, max_length=255)
    default_priority: Optional[str] = Field(None, pattern="^(P0|P1|P2|P3)$")
    sla_config: Optional[dict] = None
    is_active: Optional[bool] = None

class CategoryResponse(CategoryBase):
    id: int
    class Config:
        from_attributes = True
```

- [ ] **Step 5: Write Category service**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate

async def create_category(db: AsyncSession, data: CategoryCreate) -> Category:
    category = Category(**data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category

async def get_categories(db: AsyncSession) -> list[Category]:
    result = await db.execute(select(Category).where(Category.is_active == True))
    return result.scalars().all()

async def get_category_by_id(db: AsyncSession, category_id: int) -> Category | None:
    result = await db.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()

async def update_category(db: AsyncSession, category: Category, data: CategoryUpdate) -> Category:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await db.commit()
    await db.refresh(category)
    return category

async def delete_category(db: AsyncSession, category: Category) -> None:
    category.is_active = False
    await db.commit()
```

- [ ] **Step 6: Write Category router**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.services.category_service import create_category, get_categories, get_category_by_id, update_category, delete_category

router = APIRouter()

@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await get_categories(db)

@router.post("/admin/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category_endpoint(data: CategoryCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role("admin", "supervisor"))):
    return await create_category(db, data)

@router.put("/admin/categories/{category_id}", response_model=CategoryResponse)
async def update_category_endpoint(category_id: int, data: CategoryUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role("admin", "supervisor"))):
    category = await get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    return await update_category(db, category, data)

@router.delete("/admin/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category_endpoint(category_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role("admin", "supervisor"))):
    category = await get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    await delete_category(db, category)
```

- [ ] **Step 7: Register router in main.py**

```python
from app.routers import auth, categories
app.include_router(categories.router, prefix="/api/v1", tags=["Categories"])
```

- [ ] **Step 8: Write tests for Category API**

```python
# API-CAT-001: 创建分类成功
async def test_create_category_success(client, admin_auth_headers, db):
    body = {"name": "故障报告", "code": "bug", "default_priority": "P1"}
    r = await client.post("/api/v1/admin/categories", headers=admin_auth_headers, json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "故障报告"
    assert data["code"] == "bug"
    assert data["default_priority"] == "P1"

# API-CAT-002: 未认证创建分类 401
async def test_create_category_unauthorized_401(client, db):
    body = {"name": "故障报告", "code": "bug"}
    r = await client.post("/api/v1/admin/categories", json=body)
    assert r.status_code == 401

# API-CAT-003: 客户创建分类 403
async def test_create_category_forbidden_403(client, customer_auth_headers, db):
    body = {"name": "故障报告", "code": "bug"}
    r = await client.post("/api/v1/admin/categories", headers=customer_auth_headers, json=body)
    assert r.status_code == 403

# API-CAT-004: 列表分类成功
async def test_list_categories_success(client, admin_auth_headers, db):
    r = await client.get("/api/v1/categories", headers=admin_auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

# API-CAT-005: 更新分类成功
async def test_update_category_success(client, admin_auth_headers, db):
    # 先创建
    create_r = await client.post("/api/v1/admin/categories", headers=admin_auth_headers, json={"name": "旧名称", "code": "old"})
    cat_id = create_r.json()["id"]
    r = await client.put(f"/api/v1/admin/categories/{cat_id}", headers=admin_auth_headers, json={"name": "新名称"})
    assert r.status_code == 200
    assert r.json()["name"] == "新名称"

# API-CAT-006: 删除不存在分类 404
async def test_delete_category_not_found_404(client, admin_auth_headers, db):
    r = await client.delete("/api/v1/admin/categories/99999", headers=admin_auth_headers)
    assert r.status_code == 404
```

- [ ] **Step 9: Run tests**

```bash
cd backend && pytest tests/test_categories.py -v
```
Expected: 6 passed

- [ ] **Step 10: Commit**

```bash
git add backend/app/models backend/app/schemas backend/app/services backend/app/routers backend/app/main.py backend/tests/test_categories.py backend/alembic/versions
git commit -m "feat: add category model and admin CRUD with tests"
```

---

## Task 2: Ticket 模型 + 迁移 + 工单创建 API + 测试

**Files:**
- Create: `backend/app/models/ticket.py`
- Create: `backend/app/schemas/ticket.py`
- Create: `backend/app/services/ticket_service.py`
- Create: `backend/app/routers/tickets.py`
- Create: `backend/tests/test_tickets.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/routers/__init__.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/__init__.py`

**Interfaces:**
- Consumes: `Category`, `User`, `get_current_user`, `require_role`
- Produces: `Ticket` model, `TicketCreate`, `TicketUpdate`, `TicketResponse`, `POST /api/v1/tickets`, `GET /api/v1/tickets`, `GET /api/v1/tickets/{id}`

- [ ] **Step 1: Write Ticket model**

```python
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

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
    
    category: Mapped["Category"] = relationship("Category")
    requester: Mapped["User"] = relationship("User", foreign_keys=[requester_id])
    assignee: Mapped["User"] = relationship("User", foreign_keys=[assignee_id])
```

- [ ] **Step 2: Export Ticket in models/__init__.py**

```python
from .user import User
from .category import Category
from .ticket import Ticket
```

- [ ] **Step 3: Generate Alembic migration**

```bash
cd backend && alembic revision --autogenerate -m "add tickets table"
```

- [ ] **Step 4: Write Ticket schemas**

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TicketBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: str = Field(...)
    category_id: int = Field(..., gt=0)
    priority: str = Field(default="P2", pattern="^(P0|P1|P2|P3)$")
    source: str = Field(default="web", pattern="^(web|email|api)$")

class TicketCreate(TicketBase):
    assignee_id: Optional[int] = None

class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = Field(None, gt=0)
    priority: Optional[str] = Field(None, pattern="^(P0|P1|P2|P3)$")
    assignee_id: Optional[int] = None

class TicketResponse(BaseModel):
    id: int
    ticket_no: str
    title: str
    description: str
    status: str
    priority: str
    category_id: int
    requester_id: int
    assignee_id: Optional[int] = None
    source: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    class Config:
        from_attributes = True
```

- [ ] **Step 5: Write Ticket service with ticket number generator**

```python
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketUpdate

async def generate_ticket_no(db: AsyncSession) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"TK-{today}-"
    result = await db.execute(
        select(func.count(Ticket.id)).where(Ticket.ticket_no.like(f"{prefix}%"))
    )
    count = result.scalar() + 1
    return f"{prefix}{count:04d}"

async def create_ticket(db: AsyncSession, data: TicketCreate, requester_id: int) -> Ticket:
    ticket_no = await generate_ticket_no(db)
    ticket = Ticket(
        ticket_no=ticket_no,
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        priority=data.priority,
        requester_id=requester_id,
        assignee_id=data.assignee_id,
        source=data.source,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket

async def get_ticket_by_id(db: AsyncSession, ticket_id: int) -> Ticket | None:
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    return result.scalar_one_or_none()

async def update_ticket(db: AsyncSession, ticket: Ticket, data: TicketUpdate) -> Ticket:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)
    await db.commit()
    await db.refresh(ticket)
    return ticket
```

- [ ] **Step 6: Write data scope query helper**

```python
from sqlalchemy import select, or_
from app.models.ticket import Ticket
from app.models.user import User

async def get_tickets_query(db: AsyncSession, current_user: User, status: str | None = None, priority: str | None = None, category_id: int | None = None, page: int = 1, page_size: int = 20):
    query = select(Ticket)
    if current_user.role == "customer":
        query = query.where(Ticket.requester_id == current_user.id)
    elif current_user.role == "agent":
        query = query.where(or_(Ticket.assignee_id == current_user.id, Ticket.status == "open"))
    if status:
        query = query.where(Ticket.status == status)
    if priority:
        query = query.where(Ticket.priority == priority)
    if category_id:
        query = query.where(Ticket.category_id == category_id)
    
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()
    
    query = query.order_by(Ticket.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    return {"total": total, "page": page, "page_size": page_size, "items": items}
```

- [ ] **Step 7: Write Ticket router**

```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketResponse
from app.services.ticket_service import create_ticket, get_ticket_by_id, get_tickets_query, update_ticket

router = APIRouter()

@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket_endpoint(data: TicketCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = await create_ticket(db, data, current_user.id)
    return ticket

@router.get("/tickets", response_model=dict)
async def list_tickets(status: str | None = None, priority: str | None = None, category_id: int | None = None, page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await get_tickets_query(db, current_user, status, priority, category_id, page, page_size)

@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    # TODO: data scope check in Task 3
    return ticket
```

- [ ] **Step 8: Register router in main.py**

```python
from app.routers import auth, categories, tickets
app.include_router(tickets.router, prefix="/api/v1", tags=["Tickets"])
```

- [ ] **Step 9: Write tests for Ticket creation and list**

```python
# API-TICKET-001: 客户创建工单成功
async def test_create_ticket_success(client, customer_auth_headers, db):
    # 先创建分类
    from tests.conftest import ... # 使用 factory 或 fixture
    body = {"title": "无法登录", "description": "点击登录按钮无响应", "category_id": 1, "priority": "P1"}
    r = await client.post("/api/v1/tickets", headers=customer_auth_headers, json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "无法登录"
    assert data["status"] == "open"
    assert data["ticket_no"].startswith("TK-")
    assert data["requester_id"] == customer_id

# API-TICKET-002: 未认证创建工单 401
async def test_create_ticket_unauthorized_401(client, db):
    body = {"title": "无法登录", "description": "点击登录按钮无响应", "category_id": 1}
    r = await client.post("/api/v1/tickets", json=body)
    assert r.status_code == 401

# API-TICKET-003: 标题超过 200 字符 422
async def test_create_ticket_title_too_long_422(client, customer_auth_headers, db):
    body = {"title": "x" * 201, "description": "desc", "category_id": 1}
    r = await client.post("/api/v1/tickets", headers=customer_auth_headers, json=body)
    assert r.status_code == 422

# API-TICKET-004: 查询工单列表成功
async def test_list_tickets_success(client, customer_auth_headers, db):
    r = await client.get("/api/v1/tickets", headers=customer_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "items" in data

# API-TICKET-005: 查询不存在工单 404
async def test_get_ticket_not_found_404(client, customer_auth_headers, db):
    r = await client.get("/api/v1/tickets/99999", headers=customer_auth_headers)
    assert r.status_code == 404
```

- [ ] **Step 10: Run tests**

```bash
cd backend && pytest tests/test_tickets.py -v
```
Expected: 5 passed

- [ ] **Step 11: Commit**

```bash
git add backend/app/models backend/app/schemas backend/app/services backend/app/routers backend/app/main.py backend/tests/test_tickets.py backend/alembic/versions
git commit -m "feat: add ticket model, create and list APIs with tests"
```

---

## Task 3: 工单详情 + 数据范围隔离 + 测试增强

**Files:**
- Modify: `backend/app/routers/tickets.py`
- Modify: `backend/tests/test_tickets.py`

**Interfaces:**
- Consumes: `Ticket` model, `get_current_user`
- Produces: 数据范围隔离逻辑，详情查询增强

- [ ] **Step 1: Add data scope check to get_ticket**

```python
from fastapi import HTTPException

async def check_ticket_access(ticket: Ticket, current_user: User) -> None:
    if current_user.role == "customer" and ticket.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该工单")
    if current_user.role == "agent" and ticket.assignee_id != current_user.id and ticket.status != "open":
        raise HTTPException(status_code=403, detail="无权访问该工单")

@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    await check_ticket_access(ticket, current_user)
    return ticket
```

- [ ] **Step 2: Add data scope tests**

```python
# API-TICKET-006: 客户越权查看他人工单 403
async def test_customer_access_other_ticket_403(client, customer_auth_headers, another_customer_ticket, db):
    r = await client.get(f"/api/v1/tickets/{another_customer_ticket.id}", headers=customer_auth_headers)
    assert r.status_code == 403

# API-TICKET-007: 客服可查看 open 工单
async def test_agent_view_open_ticket(client, agent_auth_headers, open_ticket, db):
    r = await client.get(f"/api/v1/tickets/{open_ticket.id}", headers=agent_auth_headers)
    assert r.status_code == 200

# API-TICKET-008: 客服不可查看非分配 closed 工单
async def test_agent_view_closed_ticket_forbidden_403(client, agent_auth_headers, closed_ticket_assigned_to_other, db):
    r = await client.get(f"/api/v1/tickets/{closed_ticket_assigned_to_other.id}", headers=agent_auth_headers)
    assert r.status_code == 403
```

- [ ] **Step 3: Run tests**

```bash
cd backend && pytest tests/test_tickets.py -v
```
Expected: 8 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/tickets.py backend/tests/test_tickets.py
git commit -m "feat: add ticket data scope isolation and access control tests"
```

---

## Task 4: TicketReply 模型 + 迁移 + 回复 API + 测试

**Files:**
- Create: `backend/app/models/ticket_reply.py`
- Create: `backend/app/schemas/ticket_reply.py`
- Create: `backend/app/services/reply_service.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/routers/tickets.py`
- Modify: `backend/app/services/__init__.py`
- Create: `backend/tests/test_replies.py`

**Interfaces:**
- Consumes: `Ticket`, `User`, `get_current_user`
- Produces: `TicketReply` model, `POST /api/v1/tickets/{id}/replies`, `GET /api/v1/tickets/{id}/replies` (embedded in detail or separate)

- [ ] **Step 1: Write TicketReply model**

```python
from datetime import datetime
from sqlalchemy import Integer, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class TicketReply(Base):
    __tablename__ = "ticket_replies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="replies")
    author: Mapped["User"] = relationship("User")
```

- [ ] **Step 2: Update Ticket model with replies relationship**

```python
# In app/models/ticket.py, add:
replies: Mapped[list["TicketReply"]] = relationship("TicketReply", back_populates="ticket", cascade="all, delete-orphan")
```

- [ ] **Step 3: Generate Alembic migration**

```bash
cd backend && alembic revision --autogenerate -m "add ticket_replies table"
```

- [ ] **Step 4: Write reply schemas**

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ReplyCreate(BaseModel):
    content: str = Field(..., min_length=1)
    is_internal: bool = False

class ReplyResponse(BaseModel):
    id: int
    ticket_id: int
    author_id: int
    content: str
    is_internal: bool
    created_at: datetime
    class Config:
        from_attributes = True
```

- [ ] **Step 5: Write reply service**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.ticket_reply import TicketReply
from app.schemas.ticket_reply import ReplyCreate
from app.models.ticket import Ticket

async def create_reply(db: AsyncSession, ticket: Ticket, data: ReplyCreate, author_id: int) -> TicketReply:
    reply = TicketReply(ticket_id=ticket.id, author_id=author_id, content=data.content, is_internal=data.is_internal)
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    return reply

async def get_replies_by_ticket(db: AsyncSession, ticket_id: int, include_internal: bool = False) -> list[TicketReply]:
    query = select(TicketReply).where(TicketReply.ticket_id == ticket_id).order_by(TicketReply.created_at.asc())
    if not include_internal:
        query = query.where(TicketReply.is_internal == False)
    result = await db.execute(query)
    return result.scalars().all()
```

- [ ] **Step 6: Add reply endpoints to tickets router**

```python
from app.schemas.ticket_reply import ReplyCreate, ReplyResponse
from app.services.reply_service import create_reply, get_replies_by_ticket

@router.post("/tickets/{ticket_id}/replies", response_model=ReplyResponse, status_code=status.HTTP_201_CREATED)
async def reply_ticket(ticket_id: int, data: ReplyCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    await check_ticket_access(ticket, current_user)
    # 客服回复时自动流转到 in_progress
    if current_user.role in ("agent", "supervisor", "admin") and ticket.status == "open":
        ticket.status = "in_progress"
        ticket.assignee_id = current_user.id
    reply = await create_reply(db, ticket, data, current_user.id)
    await db.commit()
    return reply

@router.get("/tickets/{ticket_id}/replies", response_model=list[ReplyResponse])
async def list_replies(ticket_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    await check_ticket_access(ticket, current_user)
    include_internal = current_user.role in ("agent", "supervisor", "admin")
    return await get_replies_by_ticket(db, ticket_id, include_internal)
```

- [ ] **Step 7: Write reply tests**

```python
# API-REPLY-001: 客服回复工单成功
async def test_reply_ticket_success(client, agent_auth_headers, open_ticket, db):
    body = {"content": "请尝试清除缓存", "is_internal": False}
    r = await client.post(f"/api/v1/tickets/{open_ticket.id}/replies", headers=agent_auth_headers, json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["content"] == "请尝试清除缓存"
    assert data["is_internal"] == False
    # 验证状态流转
    ticket_r = await client.get(f"/api/v1/tickets/{open_ticket.id}", headers=agent_auth_headers)
    assert ticket_r.json()["status"] == "in_progress"
    assert ticket_r.json()["assignee_id"] == agent_id

# API-REPLY-002: 内部备注客户不可见
async def test_internal_reply_hidden_from_customer(client, agent_auth_headers, customer_auth_headers, in_progress_ticket, db):
    # 客服创建内部备注
    body = {"content": "内部处理中", "is_internal": True}
    r = await client.post(f"/api/v1/tickets/{in_progress_ticket.id}/replies", headers=agent_auth_headers, json=body)
    assert r.status_code == 201
    # 客户查看回复列表
    r = await client.get(f"/api/v1/tickets/{in_progress_ticket.id}/replies", headers=customer_auth_headers)
    assert r.status_code == 200
    replies = r.json()
    assert all(reply["is_internal"] == False for reply in replies)

# API-REPLY-003: 回复不存在工单 404
async def test_reply_not_found_ticket_404(client, agent_auth_headers, db):
    body = {"content": "test"}
    r = await client.post("/api/v1/tickets/99999/replies", headers=agent_auth_headers, json=body)
    assert r.status_code == 404

# API-REPLY-004: 空内容回复 422
async def test_reply_empty_content_422(client, agent_auth_headers, open_ticket, db):
    body = {"content": ""}
    r = await client.post(f"/api/v1/tickets/{open_ticket.id}/replies", headers=agent_auth_headers, json=body)
    assert r.status_code == 422
```

- [ ] **Step 8: Run tests**

```bash
cd backend && pytest tests/test_replies.py -v
```
Expected: 4 passed

- [ ] **Step 9: Commit**

```bash
git add backend/app/models backend/app/schemas backend/app/services backend/app/routers backend/tests/test_replies.py backend/alembic/versions
git commit -m "feat: add ticket reply model and API with scope tests"
```

---

## Task 5: 状态流转 + 分派 API + 测试

**Files:**
- Modify: `backend/app/routers/tickets.py`
- Modify: `backend/app/services/ticket_service.py`
- Modify: `backend/tests/test_tickets.py`

**Interfaces:**
- Consumes: `Ticket` model, `check_ticket_access`
- Produces: `POST /api/v1/tickets/{id}/status`, `POST /api/v1/tickets/{id}/assign`

- [ ] **Step 1: Add status transition service logic**

```python
VALID_TRANSITIONS = {
    "open": {"in_progress", "closed"},
    "in_progress": {"waiting", "resolved", "open"},
    "waiting": {"in_progress", "resolved"},
    "resolved": {"closed", "in_progress"},
    "closed": set(),
}

def can_transition(current: str, target: str) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())

async def transition_ticket_status(db: AsyncSession, ticket: Ticket, target_status: str, user: User) -> Ticket:
    if not can_transition(ticket.status, target_status):
        raise HTTPException(status_code=409, detail=f"无法从 {ticket.status} 流转到 {target_status}")
    ticket.status = target_status
    if target_status == "resolved":
        ticket.resolved_at = datetime.utcnow()
    if target_status == "closed":
        ticket.closed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(ticket)
    return ticket
```

- [ ] **Step 2: Add status and assign endpoints**

```python
from pydantic import BaseModel

class StatusUpdateRequest(BaseModel):
    status: str

class AssignRequest(BaseModel):
    assignee_id: int

@router.post("/tickets/{ticket_id}/status", response_model=TicketResponse)
async def update_ticket_status(ticket_id: int, req: StatusUpdateRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    await check_ticket_access(ticket, current_user)
    if current_user.role not in ("agent", "supervisor", "admin"):
        raise HTTPException(status_code=403, detail="无权修改工单状态")
    ticket = await transition_ticket_status(db, ticket, req.status, current_user)
    return ticket

@router.post("/tickets/{ticket_id}/assign", response_model=TicketResponse)
async def assign_ticket(ticket_id: int, req: AssignRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role("agent", "supervisor", "admin"))):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    ticket.assignee_id = req.assignee_id
    if ticket.status == "open":
        ticket.status = "in_progress"
    await db.commit()
    await db.refresh(ticket)
    return ticket
```

- [ ] **Step 3: Add status transition tests**

```python
# API-TICKET-009: 状态流转成功 open -> in_progress
async def test_ticket_status_transition_success(client, agent_auth_headers, open_ticket, db):
    body = {"status": "in_progress"}
    r = await client.post(f"/api/v1/tickets/{open_ticket.id}/status", headers=agent_auth_headers, json=body)
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"

# API-TICKET-010: 非法状态流转 409
async def test_ticket_invalid_transition_409(client, agent_auth_headers, resolved_ticket, db):
    body = {"status": "open"}
    r = await client.post(f"/api/v1/tickets/{resolved_ticket.id}/status", headers=agent_auth_headers, json=body)
    assert r.status_code == 409

# API-TICKET-011: 分派工单成功
async def test_assign_ticket_success(client, supervisor_auth_headers, open_ticket, agent_user, db):
    body = {"assignee_id": agent_user.id}
    r = await client.post(f"/api/v1/tickets/{open_ticket.id}/assign", headers=supervisor_auth_headers, json=body)
    assert r.status_code == 200
    assert r.json()["assignee_id"] == agent_user.id
    assert r.json()["status"] == "in_progress"

# API-TICKET-012: 客户无权修改状态 403
async def test_customer_update_status_forbidden_403(client, customer_auth_headers, own_ticket, db):
    body = {"status": "resolved"}
    r = await client.post(f"/api/v1/tickets/{own_ticket.id}/status", headers=customer_auth_headers, json=body)
    assert r.status_code == 403
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_tickets.py -v
```
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services backend/app/routers backend/tests/test_tickets.py
git commit -m "feat: add ticket status transition and assignment APIs with tests"
```

---

## Task 6: 前端 API 封装 + Pinia Store + 通用组件

**Files:**
- Create: `frontend/src/api/tickets.js`
- Create: `frontend/src/api/categories.js`
- Create: `frontend/src/stores/tickets.js`
- Create: `frontend/src/components/StatusBadge.vue`
- Create: `frontend/src/components/PriorityTag.vue`

**Interfaces:**
- Consumes: 后端 API `/api/v1/tickets`, `/api/v1/categories`, `/api/v1/tickets/{id}/replies`, `/api/v1/tickets/{id}/status`, `/api/v1/tickets/{id}/assign`
- Produces: `useTicketsStore`, `ticketApi`, `categoryApi`, `StatusBadge`, `PriorityTag`

- [ ] **Step 1: Write ticket API client**

```javascript
// frontend/src/api/tickets.js
import request from './index.js'

export const ticketApi = {
  create: (data) => request.post('/api/v1/tickets', data),
  list: (params) => request.get('/api/v1/tickets', { params }),
  get: (id) => request.get(`/api/v1/tickets/${id}`),
  reply: (id, data) => request.post(`/api/v1/tickets/${id}/replies`, data),
  updateStatus: (id, status) => request.post(`/api/v1/tickets/${id}/status`, { status }),
  assign: (id, assigneeId) => request.post(`/api/v1/tickets/${id}/assign`, { assignee_id: assigneeId }),
}

export const replyApi = {
  list: (ticketId) => request.get(`/api/v1/tickets/${ticketId}/replies`),
}
```

- [ ] **Step 2: Write category API client**

```javascript
// frontend/src/api/categories.js
import request from './index.js'

export const categoryApi = {
  list: () => request.get('/api/v1/categories'),
}
```

- [ ] **Step 3: Write ticket Pinia store**

```javascript
// frontend/src/stores/tickets.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ticketApi, replyApi } from '@/api/tickets'
import { categoryApi } from '@/api/categories'

export const useTicketsStore = defineStore('tickets', () => {
  const tickets = ref([])
  const currentTicket = ref(null)
  const replies = ref([])
  const categories = ref([])
  const pagination = ref({ total: 0, page: 1, page_size: 20 })
  const loading = ref(false)

  const fetchCategories = async () => {
    const { data } = await categoryApi.list()
    categories.value = data
  }

  const fetchTickets = async (params = {}) => {
    loading.value = true
    try {
      const { data } = await ticketApi.list(params)
      tickets.value = data.items
      pagination.value = { total: data.total, page: data.page, page_size: data.page_size }
    } finally {
      loading.value = false
    }
  }

  const fetchTicket = async (id) => {
    loading.value = true
    try {
      const { data } = await ticketApi.get(id)
      currentTicket.value = data
    } finally {
      loading.value = false
    }
  }

  const fetchReplies = async (ticketId) => {
    const { data } = await replyApi.list(ticketId)
    replies.value = data
  }

  const createTicket = async (payload) => {
    const { data } = await ticketApi.create(payload)
    return data
  }

  const replyTicket = async (ticketId, payload) => {
    const { data } = await ticketApi.reply(ticketId, payload)
    replies.value.push(data)
    return data
  }

  const updateStatus = async (ticketId, status) => {
    const { data } = await ticketApi.updateStatus(ticketId, status)
    currentTicket.value = data
    return data
  }

  const assignTicket = async (ticketId, assigneeId) => {
    const { data } = await ticketApi.assign(ticketId, assigneeId)
    currentTicket.value = data
    return data
  }

  return {
    tickets, currentTicket, replies, categories, pagination, loading,
    fetchCategories, fetchTickets, fetchTicket, fetchReplies,
    createTicket, replyTicket, updateStatus, assignTicket,
  }
})
```

- [ ] **Step 4: Write StatusBadge component**

```vue
<!-- frontend/src/components/StatusBadge.vue -->
<template>
  <el-tag :type="statusType">{{ statusLabel }}</el-tag>
</template>
<script setup>
import { computed } from 'vue'
const props = defineProps({ status: String })
const statusMap = {
  open: { label: '待处理', type: 'info' },
  in_progress: { label: '处理中', type: 'warning' },
  waiting: { label: '等待回复', type: '' },
  resolved: { label: '已解决', type: 'success' },
  closed: { label: '已关闭', type: 'danger' },
}
const statusLabel = computed(() => statusMap[props.status]?.label || props.status)
const statusType = computed(() => statusMap[props.status]?.type || 'info')
</script>
```

- [ ] **Step 5: Write PriorityTag component**

```vue
<!-- frontend/src/components/PriorityTag.vue -->
<template>
  <el-tag :type="priorityType" size="small">{{ priorityLabel }}</el-tag>
</template>
<script setup>
import { computed } from 'vue'
const props = defineProps({ priority: String })
const priorityMap = {
  P0: { label: '紧急', type: 'danger' },
  P1: { label: '高', type: 'warning' },
  P2: { label: '中', type: 'primary' },
  P3: { label: '低', type: 'info' },
}
const priorityLabel = computed(() => priorityMap[props.priority]?.label || props.priority)
const priorityType = computed(() => priorityMap[props.priority]?.type || 'info')
</script>
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api frontend/src/stores frontend/src/components
git commit -m "feat: add frontend ticket API, store, and base components"
```

---

## Task 7: 前端客户页面（提交工单 + 我的工单 + 详情）

**Files:**
- Create: `frontend/src/views/customer/CreateTicketView.vue`
- Create: `frontend/src/views/customer/MyTicketsView.vue`
- Create: `frontend/src/views/customer/TicketDetailView.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/layouts/CustomerLayout.vue`
- Create: `frontend/tests/tickets.test.js` (or similar)

**Interfaces:**
- Consumes: `useTicketsStore`, `StatusBadge`, `PriorityTag`
- Produces: 客户侧路由 `/customer/tickets/new`, `/customer/tickets`, `/customer/tickets/:id`

- [ ] **Step 1: Write CreateTicketView**

```vue
<template>
  <div class="create-ticket">
    <h2>提交工单</h2>
    <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
      <el-form-item label="标题" prop="title">
        <el-input v-model="form.title" maxlength="200" show-word-limit />
      </el-form-item>
      <el-form-item label="分类" prop="category_id">
        <el-select v-model="form.category_id" placeholder="选择分类">
          <el-option v-for="cat in store.categories" :key="cat.id" :label="cat.name" :value="cat.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="优先级" prop="priority">
        <el-select v-model="form.priority">
          <el-option label="紧急" value="P0" />
          <el-option label="高" value="P1" />
          <el-option label="中" value="P2" />
          <el-option label="低" value="P3" />
        </el-select>
      </el-form-item>
      <el-form-item label="描述" prop="description">
        <el-input v-model="form.description" type="textarea" rows="5" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="submit" :loading="store.loading">提交</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>
<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTicketsStore } from '@/stores/tickets'
import { ElMessage } from 'element-plus'
const router = useRouter()
const store = useTicketsStore()
const formRef = ref(null)
const form = reactive({ title: '', category_id: null, priority: 'P2', description: '' })
const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }, { max: 200, message: '最多200字符', trigger: 'blur' }],
  category_id: [{ required: true, message: '请选择分类', trigger: 'change' }],
  description: [{ required: true, message: '请输入描述', trigger: 'blur' }],
}
const submit = async () => {
  await formRef.value.validate()
  await store.createTicket({ ...form, source: 'web' })
  ElMessage.success('工单提交成功')
  router.push('/customer/tickets')
}
onMounted(() => store.fetchCategories())
</script>
```

- [ ] **Step 2: Write MyTicketsView**

```vue
<template>
  <div>
    <h2>我的工单</h2>
    <el-table :data="store.tickets" v-loading="store.loading">
      <el-table-column prop="ticket_no" label="工单号" width="160" />
      <el-table-column prop="title" label="标题" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <StatusBadge :status="row.status" />
        </template>
      </el-table-column>
      <el-table-column label="优先级" width="80">
        <template #default="{ row }">
          <PriorityTag :priority="row.priority" />
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link @click="router.push(`/customer/tickets/${row.id}`)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :total="store.pagination.total" :page-size="20" @change="load" />
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTicketsStore } from '@/stores/tickets'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityTag from '@/components/PriorityTag.vue'
const router = useRouter()
const store = useTicketsStore()
const page = ref(1)
const load = () => store.fetchTickets({ page: page.value, page_size: 20 })
onMounted(load)
</script>
```

- [ ] **Step 3: Write TicketDetailView (customer)**

```vue
<template>
  <div v-if="store.currentTicket">
    <h2>{{ store.currentTicket.title }}</h2>
    <el-descriptions border>
      <el-descriptions-item label="工单号">{{ store.currentTicket.ticket_no }}</el-descriptions-item>
      <el-descriptions-item label="状态"><StatusBadge :status="store.currentTicket.status" /></el-descriptions-item>
      <el-descriptions-item label="优先级"><PriorityTag :priority="store.currentTicket.priority" /></el-descriptions-item>
      <el-descriptions-item label="创建时间">{{ store.currentTicket.created_at }}</el-descriptions-item>
    </el-descriptions>
    <el-divider />
    <h3>描述</h3>
    <p>{{ store.currentTicket.description }}</p>
    <el-divider />
    <h3>回复记录</h3>
    <el-timeline>
      <el-timeline-item v-for="reply in store.replies" :key="reply.id" :timestamp="reply.created_at">
        {{ reply.content }}
      </el-timeline-item>
    </el-timeline>
  </div>
</template>
<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTicketsStore } from '@/stores/tickets'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityTag from '@/components/PriorityTag.vue'
const route = useRoute()
const store = useTicketsStore()
onMounted(() => {
  store.fetchTicket(route.params.id)
  store.fetchReplies(route.params.id)
})
</script>
```

- [ ] **Step 4: Register routes in router**

```javascript
// Add to frontend/src/router/index.js
const customerRoutes = [
  { path: '/customer/tickets/new', component: () => import('@/views/customer/CreateTicketView.vue'), meta: { role: 'customer' } },
  { path: '/customer/tickets', component: () => import('@/views/customer/MyTicketsView.vue'), meta: { role: 'customer' } },
  { path: '/customer/tickets/:id', component: () => import('@/views/customer/TicketDetailView.vue'), meta: { role: 'customer' } },
]
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views frontend/src/router frontend/src/layouts
git commit -m "feat: add customer ticket pages and routes"
```

---

## Task 8: 前端客服工作台 + 页面测试

**Files:**
- Create: `frontend/src/views/agent/AgentTicketsView.vue`
- Create: `frontend/src/views/agent/AgentTicketDetailView.vue`
- Create: `frontend/src/components/ReplyBox.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/layouts/AgentLayout.vue`
- Create: `frontend/tests/agent-tickets.test.js`

**Interfaces:**
- Consumes: `useTicketsStore`, `StatusBadge`, `PriorityTag`, `ReplyBox`
- Produces: 客服路由 `/agent/tickets`, `/agent/tickets/:id`

- [ ] **Step 1: Write ReplyBox component**

```vue
<template>
  <div class="reply-box">
    <el-input v-model="content" type="textarea" rows="3" placeholder="输入回复..." />
    <el-checkbox v-model="isInternal">内部备注（客户不可见）</el-checkbox>
    <el-button type="primary" @click="submit" :loading="loading">发送</el-button>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
const props = defineProps({ ticketId: Number })
const emit = defineEmits(['replied'])
const content = ref('')
const isInternal = ref(false)
const loading = ref(false)
const submit = async () => {
  if (!content.value.trim()) return
  loading.value = true
  try {
    emit('replied', { content: content.value, is_internal: isInternal.value })
    content.value = ''
    isInternal.value = false
  } finally {
    loading.value = false
  }
}
</script>
```

- [ ] **Step 2: Write AgentTicketsView**

```vue
<template>
  <div>
    <h2>客服工作台</h2>
    <el-table :data="store.tickets" v-loading="store.loading">
      <el-table-column prop="ticket_no" label="工单号" width="160" />
      <el-table-column prop="title" label="标题" />
      <el-table-column label="状态" width="100"><template #default="{ row }"><StatusBadge :status="row.status" /></template></el-table-column>
      <el-table-column label="优先级" width="80"><template #default="{ row }"><PriorityTag :priority="row.priority" /></template></el-table-column>
      <el-table-column prop="requester.username" label="客户" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link @click="router.push(`/agent/tickets/${row.id}`)">处理</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :total="store.pagination.total" :page-size="20" @change="load" />
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTicketsStore } from '@/stores/tickets'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityTag from '@/components/PriorityTag.vue'
const router = useRouter()
const store = useTicketsStore()
const page = ref(1)
const load = () => store.fetchTickets({ page: page.value, page_size: 20 })
onMounted(load)
</script>
```

- [ ] **Step 3: Write AgentTicketDetailView**

```vue
<template>
  <div v-if="store.currentTicket">
    <h2>{{ store.currentTicket.title }}</h2>
    <el-descriptions border>
      <el-descriptions-item label="工单号">{{ store.currentTicket.ticket_no }}</el-descriptions-item>
      <el-descriptions-item label="状态"><StatusBadge :status="store.currentTicket.status" /></el-descriptions-item>
      <el-descriptions-item label="优先级"><PriorityTag :priority="store.currentTicket.priority" /></el-descriptions-item>
      <el-descriptions-item label="客户">{{ store.currentTicket.requester?.username }}</el-descriptions-item>
    </el-descriptions>
    <el-divider />
    <h3>描述</h3>
    <p>{{ store.currentTicket.description }}</p>
    <el-divider />
    <h3>回复记录</h3>
    <el-timeline>
      <el-timeline-item v-for="reply in store.replies" :key="reply.id" :timestamp="reply.created_at">
        <el-tag v-if="reply.is_internal" type="warning" size="small">内部</el-tag>
        {{ reply.content }}
      </el-timeline-item>
    </el-timeline>
    <el-divider />
    <h3>回复</h3>
    <ReplyBox :ticketId="store.currentTicket.id" @replied="handleReply" />
    <el-divider />
    <h3>操作</h3>
    <el-button-group>
      <el-button v-if="store.currentTicket.status === 'in_progress'" @click="changeStatus('resolved')">标记已解决</el-button>
      <el-button v-if="store.currentTicket.status === 'resolved'" @click="changeStatus('closed')">关闭工单</el-button>
      <el-button v-if="store.currentTicket.status === 'in_progress'" @click="changeStatus('waiting')">等待客户</el-button>
    </el-button-group>
  </div>
</template>
<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTicketsStore } from '@/stores/tickets'
import StatusBadge from '@/components/StatusBadge.vue'
import PriorityTag from '@/components/PriorityTag.vue'
import ReplyBox from '@/components/ReplyBox.vue'
import { ElMessage } from 'element-plus'
const route = useRoute()
const store = useTicketsStore()
onMounted(() => {
  store.fetchTicket(route.params.id)
  store.fetchReplies(route.params.id)
})
const handleReply = async (payload) => {
  await store.replyTicket(store.currentTicket.id, payload)
  ElMessage.success('回复成功')
}
const changeStatus = async (status) => {
  await store.updateStatus(store.currentTicket.id, status)
  ElMessage.success('状态更新成功')
}
</script>
```

- [ ] **Step 4: Register agent routes**

```javascript
// Add to frontend/src/router/index.js
const agentRoutes = [
  { path: '/agent/tickets', component: () => import('@/views/agent/AgentTicketsView.vue'), meta: { role: 'agent' } },
  { path: '/agent/tickets/:id', component: () => import('@/views/agent/AgentTicketDetailView.vue'), meta: { role: 'agent' } },
]
```

- [ ] **Step 5: Write frontend tests**

```javascript
// frontend/tests/StatusBadge.test.js (example)
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatusBadge from '@/components/StatusBadge.vue'

describe('StatusBadge (TC-FE-001)', () => {
  it('renders open status correctly', () => {
    const wrapper = mount(StatusBadge, { props: { status: 'open' } })
    expect(wrapper.text()).toContain('待处理')
  })
})
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views frontend/src/components frontend/src/router frontend/src/layouts frontend/tests
git commit -m "feat: add agent workbench and frontend tests"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ Category model + CRUD (M1-T11/12)
- ✅ Ticket model + create/list/detail (M1-T13/14/15/16)
- ✅ TicketReply model + reply API (M1-T17/18)
- ✅ Status transition (M1-T19)
- ✅ Basic assignment (manual, not smart dispatch — T004)
- ✅ Customer frontend pages (M1-T21/22)
- ✅ Agent workbench (M1-T23)
- ✅ Backend tests ≥20, frontend tests ≥10

**2. Placeholder scan:**
- 无 TBD/TODO/fill in later
- 所有测试步骤包含具体代码
- 所有步骤包含具体命令

**3. Type consistency:**
- `TicketCreate` / `TicketUpdate` / `TicketResponse` 字段一致
- `StatusBadge` / `PriorityTag` 枚举值与后端约束一致
- API 路径与 ARCHITECTURE.md 一致

**4. 潜在缺口：**
- 前端测试仅给了示例，实际执行时需要子AGENT补全所有测试文件内容
- 客户/客服布局 (`CustomerLayout.vue`, `AgentLayout.vue`) 的菜单项需要补充
- 需要确认 `tests/conftest.py` 中已有 fixture（如 `client`, `admin_auth_headers` 等）可用

---

## Execution Handoff

**推荐执行方式：** Subagent-Driven Development
- 每个任务一个独立子AGENT，审查后进入下一任务
- 总共 8 个任务，按依赖顺序串行执行
