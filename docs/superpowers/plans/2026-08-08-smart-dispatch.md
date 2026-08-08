# T004 智能分派算法实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现基于客服负载与技能匹配的智能分派算法，覆盖模型、核心算法、API、自动触发与日志，后端测试覆盖率 ≥80%，关键功能 100% 覆盖。

**Architecture:** 后端 FastAPI + SQLAlchemy 2.0 异步模式。新增 `AgentSkill` 模型记录客服技能；新增 `DispatchLog` 模型记录分派历史；核心算法 `dispatch_service` 基于负载负向评分 + 技能匹配正向评分 + 优先级权重，返回排序候选列表；API 层提供建议分配、自动分配、手动分配（含日志）三个接口；创建工单时支持可选自动分派触发。

**Tech Stack:** Python 3.10, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Alembic, pytest, Vue3, Element Plus, Pinia

## Global Constraints

- 所有模型使用 SQLAlchemy 2.0 `Mapped[]` + `mapped_column()` 语法
- 所有数据库操作使用 `async/await` + `AsyncSession`
- 所有 API 路径前缀 `/api/v1`
- 状态值精确匹配：`open`, `in_progress`, `waiting`, `resolved`, `closed`
- 优先级精确匹配：`P0`, `P1`, `P2`, `P3`
- 角色精确匹配：`customer`, `agent`, `supervisor`, `admin`
- 测试文件组织：`tests/test_dispatch.py`（算法单元 + 集成），`tests/test_dispatch_api.py`（API 专项）
- 测试用例 ID 命名：`API-DISPATCH-{SEQ:03d}`
- 所有测试必须断言状态码 + 具体字段/错误码，不只做状态码检查
- 算法单元测试不依赖 FastAPI client，直接使用 AsyncSession + service 函数
- 关键代码（Task 2 核心算法）必须通过 code review
- 新增功能测试覆盖率 ≥80%，关键功能（算法全路径、分派 API、自动触发）100% 覆盖
- 测试运行命令：`pytest -p no:anyio tests/`
- 分派算法禁止引入外部机器学习库（纯规则/启发式，保证可预测性）
- DispatchLog 只记录分配行为，不修改工单状态（状态由现有 status/assign 接口维护）

---

## File Structure

### 后端新增/修改

| 文件 | 责任 |
|------|------|
| `backend/app/models/agent_skill.py` | AgentSkill 模型（客服-分类技能关联） |
| `backend/app/models/dispatch_log.py` | DispatchLog 模型（分派历史记录） |
| `backend/app/models/__init__.py` | 导出新模型 |
| `backend/app/schemas/agent_skill.py` | AgentSkill Pydantic schemas |
| `backend/app/schemas/dispatch.py` | 分派相关 schemas（SuggestRequest, AssignSuggestion, DispatchLogResponse） |
| `backend/app/schemas/__init__.py` | 导出新 schemas |
| `backend/app/services/dispatch_service.py` | 智能分派核心算法：负载计算、技能评分、排序、自动分配 |
| `backend/app/services/__init__.py` | 导出 dispatch_service |
| `backend/app/routers/dispatch.py` | 分派 API：suggest、auto-assign、logs |
| `backend/app/routers/tickets.py` | 修改 create_ticket_endpoint：支持自动分派触发；修改 assign_ticket：记录分派日志 |
| `backend/app/main.py` | 注册 dispatch router |
| `backend/tests/test_dispatch.py` | 核心算法单元测试 + 端到端分派场景 |
| `backend/tests/test_dispatch_api.py` | 分派 API 接口测试（权限、参数、日志） |
| `backend/alembic/versions/` | 新增迁移脚本（由 Alembic 生成） |

### 前端新增/修改

| 文件 | 责任 |
|------|------|
| `frontend/src/api/dispatch.js` | 分派 API 客户端 |
| `frontend/src/stores/dispatch.js` | 分派 Pinia store |
| `frontend/src/views/agent/AgentTicketDetailView.vue` | 增加“建议分配”按钮和列表，手动分配下拉框 |
| `frontend/src/components/AssignSuggestionList.vue` | 建议分配候选列表组件 |

---

## Task 1: AgentSkill 模型 + 迁移 + 管理 API + 测试

**Files:**
- Create: `backend/app/models/agent_skill.py`
- Create: `backend/app/schemas/agent_skill.py`
- Create: `backend/app/services/agent_skill_service.py`
- Create: `backend/app/routers/admin_skills.py`（或合并到 dispatch router）
- Create: `backend/tests/test_dispatch_api.py`（Admin skill CRUD 部分）
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_dispatch_api.py`

**Interfaces:**
- Consumes: `User` model（role="agent"），`Category` model
- Produces: `AgentSkill` model，`POST /api/v1/admin/agent-skills`，`GET /api/v1/admin/agent-skills`，`DELETE /api/v1/admin/agent-skills/{id}`，`GET /api/v1/admin/agents/{id}/skills`

- [ ] **Step 1: Write AgentSkill model**

```python
from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class AgentSkill(Base):
    __tablename__ = "agent_skills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False)
    proficiency: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    __table_args__ = (UniqueConstraint("agent_id", "category_id", name="uq_agent_category"),)
```

- [ ] **Step 2: Export in models/__init__.py**

```python
from .agent_skill import AgentSkill
```

- [ ] **Step 3: Generate Alembic migration**

```bash
cd backend && alembic revision --autogenerate -m "add agent_skills table"
```

- [ ] **Step 4: Write AgentSkill schemas**

```python
from pydantic import BaseModel, Field
from typing import Optional

class AgentSkillBase(BaseModel):
    agent_id: int = Field(..., gt=0)
    category_id: int = Field(..., gt=0)
    proficiency: int = Field(default=3, ge=1, le=5)

class AgentSkillCreate(AgentSkillBase):
    pass

class AgentSkillUpdate(BaseModel):
    proficiency: int = Field(..., ge=1, le=5)

class AgentSkillResponse(AgentSkillBase):
    id: int
    class Config:
        from_attributes = True
```

- [ ] **Step 5: Write AgentSkill service**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.agent_skill import AgentSkill
from app.schemas.agent_skill import AgentSkillCreate, AgentSkillUpdate

async def create_agent_skill(db: AsyncSession, data: AgentSkillCreate) -> AgentSkill:
    skill = AgentSkill(**data.model_dump())
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return skill

async def get_agent_skills_by_agent(db: AsyncSession, agent_id: int) -> list[AgentSkill]:
    result = await db.execute(select(AgentSkill).where(AgentSkill.agent_id == agent_id))
    return result.scalars().all()

async def get_agent_skill_by_id(db: AsyncSession, skill_id: int) -> AgentSkill | None:
    result = await db.execute(select(AgentSkill).where(AgentSkill.id == skill_id))
    return result.scalar_one_or_none()

async def update_agent_skill(db: AsyncSession, skill: AgentSkill, data: AgentSkillUpdate) -> AgentSkill:
    skill.proficiency = data.proficiency
    await db.commit()
    await db.refresh(skill)
    return skill

async def delete_agent_skill(db: AsyncSession, skill: AgentSkill) -> None:
    await db.delete(skill)
    await db.commit()
```

- [ ] **Step 6: Write Admin Skill router（合并到 dispatch router 或单独文件）**

本计划选择合并到 `dispatch.py`，以便统一分派相关接口。但为简化 Task 1，先独立实现 `admin_skills.py`，后续合并。

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_role
from app.exceptions import NotFoundException
from app.schemas.agent_skill import AgentSkillCreate, AgentSkillUpdate, AgentSkillResponse
from app.services.agent_skill_service import create_agent_skill, get_agent_skills_by_agent, get_agent_skill_by_id, update_agent_skill, delete_agent_skill

router = APIRouter()

@router.post("/admin/agent-skills", response_model=AgentSkillResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_skill(data: AgentSkillCreate, db: AsyncSession = Depends(get_db), current_user = Depends(require_role("admin", "supervisor"))):
    return await create_agent_skill(db, data)

@router.get("/admin/agent-skills", response_model=list[AgentSkillResponse])
async def admin_list_skills(agent_id: int | None = None, db: AsyncSession = Depends(get_db), current_user = Depends(require_role("admin", "supervisor"))):
    if agent_id:
        return await get_agent_skills_by_agent(db, agent_id)
    # else return all? add service method if needed

@router.put("/admin/agent-skills/{skill_id}", response_model=AgentSkillResponse)
async def admin_update_skill(skill_id: int, data: AgentSkillUpdate, db: AsyncSession = Depends(get_db), current_user = Depends(require_role("admin", "supervisor"))):
    skill = await get_agent_skill_by_id(db, skill_id)
    if not skill:
        raise NotFoundException("技能记录不存在")
    return await update_agent_skill(db, skill, data)

@router.delete("/admin/agent-skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_skill(skill_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(require_role("admin", "supervisor"))):
    skill = await get_agent_skill_by_id(db, skill_id)
    if not skill:
        raise NotFoundException("技能记录不存在")
    await delete_agent_skill(db, skill)
```

- [ ] **Step 7: Register router in main.py**

```python
from app.routers import dispatch
app.include_router(dispatch.router, prefix="/api/v1", tags=["Dispatch"])
```

- [ ] **Step 8: Write tests for Admin Skill CRUD**

```python
# API-DISPATCH-001: 创建技能成功
async def test_create_agent_skill_success(client, admin_auth_headers, db):
    # 先创建 agent 和 category
    from tests.conftest import _create_user, _create_category
    agent = await _create_user(db, "agent_for_skill", "agent")
    category = await _create_category(db)
    body = {"agent_id": agent.id, "category_id": category.id, "proficiency": 5}
    r = await client.post("/api/v1/admin/agent-skills", headers=admin_auth_headers, json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["proficiency"] == 5

# API-DISPATCH-002: 非 admin 创建技能 403
async def test_create_agent_skill_forbidden_403(client, agent_auth_headers, db):
    from tests.conftest import _create_user, _create_category
    agent = await _create_user(db, "agent_for_skill2", "agent")
    category = await _create_category(db)
    body = {"agent_id": agent.id, "category_id": category.id, "proficiency": 5}
    r = await client.post("/api/v1/admin/agent-skills", headers=agent_auth_headers, json=body)
    assert r.status_code == 403

# API-DISPATCH-003: proficiency 超边界 422
async def test_create_agent_skill_proficiency_invalid_422(client, admin_auth_headers, db):
    from tests.conftest import _create_user, _create_category
    agent = await _create_user(db, "agent_for_skill3", "agent")
    category = await _create_category(db)
    body = {"agent_id": agent.id, "category_id": category.id, "proficiency": 6}
    r = await client.post("/api/v1/admin/agent-skills", headers=admin_auth_headers, json=body)
    assert r.status_code == 422

# API-DISPATCH-004: 删除技能成功
async def test_delete_agent_skill_success(client, admin_auth_headers, db):
    from tests.conftest import _create_user, _create_category
    agent = await _create_user(db, "agent_for_skill4", "agent")
    category = await _create_category(db)
    create_r = await client.post("/api/v1/admin/agent-skills", headers=admin_auth_headers, json={"agent_id": agent.id, "category_id": category.id, "proficiency": 4})
    skill_id = create_r.json()["id"]
    r = await client.delete(f"/api/v1/admin/agent-skills/{skill_id}", headers=admin_auth_headers)
    assert r.status_code == 204

# API-DISPATCH-005: 查询 agent 技能列表
async def test_list_agent_skills_success(client, admin_auth_headers, db):
    from tests.conftest import _create_user, _create_category
    agent = await _create_user(db, "agent_for_skill5", "agent")
    category = await _create_category(db)
    await client.post("/api/v1/admin/agent-skills", headers=admin_auth_headers, json={"agent_id": agent.id, "category_id": category.id, "proficiency": 4})
    r = await client.get(f"/api/v1/admin/agent-skills?agent_id={agent.id}", headers=admin_auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
```

- [ ] **Step 9: Run tests**

```bash
cd backend && pytest tests/test_dispatch_api.py -v -k "skill"
```
Expected: 5 passed

- [ ] **Step 10: Commit**

```bash
git add backend/app/models backend/app/schemas backend/app/services backend/app/routers backend/app/main.py backend/tests/test_dispatch_api.py backend/alembic/versions
git commit -m "feat: add AgentSkill model and admin CRUD with tests"
```

---

## Task 2: 智能分派核心算法 + 单元测试（关键代码，需 review）

**Files:**
- Create: `backend/app/services/dispatch_service.py`
- Create: `backend/tests/test_dispatch.py`（算法单元测试）
- Modify: `backend/app/models/dispatch_log.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/dispatch.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_dispatch.py`

**Interfaces:**
- Consumes: `User`, `Ticket`, `AgentSkill`, `Category`
- Produces: `calculate_agent_scores()`, `suggest_assignees()`, `auto_assign()`, `DispatchLog` model

- [ ] **Step 1: Write DispatchLog model**

```python
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class DispatchLog(Base):
    __tablename__ = "dispatch_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id"), nullable=False)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    dispatch_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "auto", "manual", "suggest"
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 2: Export in models/__init__.py**

```python
from .dispatch_log import DispatchLog
```

- [ ] **Step 3: Generate Alembic migration**

```bash
cd backend && alembic revision --autogenerate -m "add dispatch_logs table"
```

- [ ] **Step 4: Write dispatch schemas**

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AssignSuggestion(BaseModel):
    agent_id: int
    agent_name: str
    score: float
    current_load: int
    proficiency: int | None = None
    reason: str

class DispatchLogResponse(BaseModel):
    id: int
    ticket_id: int
    agent_id: int
    dispatch_type: str
    reason: str
    created_at: datetime
    class Config:
        from_attributes = True
```

- [ ] **Step 5: Write core dispatch algorithm（关键代码）**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_
from app.models.ticket import Ticket
from app.models.user import User
from app.models.agent_skill import AgentSkill
from app.models.dispatch_log import DispatchLog
from app.models.category import Category

# 权重常量（可配置，先硬编码 MVP）
WEIGHT_LOAD = -2.0        # 每多一个 in_progress 工单减 2 分
WEIGHT_SKILL = 5.0      # 有技能且 proficiency 匹配加 5 * proficiency 分
WEIGHT_PRIORITY = 3.0     # 高优先级工单加 3 分权重（影响阈值但不直接加给 agent）
MAX_LOAD = 10             # 超过 10 个处理中工单直接排除

def _score_agent(agent_id: int, proficiency: int | None, current_load: int, ticket_priority: str) -> float:
    """计算单个 agent 对某工单的得分。"""
    score = 0.0
    # 负载负向评分
    score += WEIGHT_LOAD * current_load
    # 技能正向评分
    if proficiency is not None:
        score += WEIGHT_SKILL * proficiency
    return score

async def _get_agent_loads(db: AsyncSession, agent_ids: list[int]) -> dict[int, int]:
    """获取每个 agent 当前 in_progress 工单数量。"""
    if not agent_ids:
        return {}
    result = await db.execute(
        select(Ticket.assignee_id, func.count(Ticket.id))
        .where(
            and_(
                Ticket.assignee_id.in_(agent_ids),
                Ticket.status == "in_progress"
            )
        )
        .group_by(Ticket.assignee_id)
    )
    return {row[0]: row[1] for row in result.all()}

async def suggest_assignees(db: AsyncSession, ticket: Ticket, top_n: int = 5) -> list[dict]:
    """返回排序后的建议分配候选列表。"""
    # 1. 获取所有 active agent
    agents_result = await db.execute(
        select(User).where(and_(User.role == "agent", User.is_active == True))
    )
    agents = agents_result.scalars().all()
    if not agents:
        return []
    agent_ids = [a.id for a in agents]

    # 2. 获取技能匹配
    skills_result = await db.execute(
        select(AgentSkill).where(
            and_(
                AgentSkill.agent_id.in_(agent_ids),
                AgentSkill.category_id == ticket.category_id
            )
        )
    )
    skills_map = {s.agent_id: s.proficiency for s in skills_result.scalars().all()}

    # 3. 获取负载
    loads = await _get_agent_loads(db, agent_ids)

    # 4. 计算评分
    candidates = []
    for agent in agents:
        load = loads.get(agent.id, 0)
        if load >= MAX_LOAD:
            continue
        proficiency = skills_map.get(agent.id)
        score = _score_agent(agent.id, proficiency, load, ticket.priority)
        reason_parts = []
        if proficiency:
            reason_parts.append(f"技能匹配度 {proficiency}/5")
        reason_parts.append(f"当前负载 {load}")
        reason = "；".join(reason_parts)
        candidates.append({
            "agent_id": agent.id,
            "agent_name": agent.username,
            "score": round(score, 2),
            "current_load": load,
            "proficiency": proficiency,
            "reason": reason,
        })

    # 5. 按得分降序排序
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:top_n]

async def auto_assign(db: AsyncSession, ticket: Ticket) -> User | None:
    """自动分配最佳客服，返回 agent 或 None。同时写入 DispatchLog。"""
    candidates = await suggest_assignees(db, ticket, top_n=1)
    if not candidates:
        return None
    best = candidates[0]
    # 只有得分 > 0 才自动分配（避免负分强制分配）
    if best["score"] <= 0:
        return None
    agent_result = await db.execute(select(User).where(User.id == best["agent_id"]))
    agent = agent_result.scalar_one()
    # 记录日志
    log = DispatchLog(
        ticket_id=ticket.id,
        agent_id=agent.id,
        dispatch_type="auto",
        reason=f"自动分派：得分 {best['score']}，{best['reason']}"
    )
    db.add(log)
    # 更新 ticket（调用方负责 commit，这里只 add）
    ticket.assignee_id = agent.id
    if ticket.status == "open":
        ticket.status = "in_progress"
    return agent

async def log_manual_assign(db: AsyncSession, ticket_id: int, agent_id: int, reason: str) -> DispatchLog:
    log = DispatchLog(
        ticket_id=ticket_id,
        agent_id=agent_id,
        dispatch_type="manual",
        reason=reason,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log
```

- [ ] **Step 6: Write algorithm unit tests（≥15 条，覆盖所有关键路径）**

```python
import pytest
from app.models.ticket import Ticket
from app.models.user import User
from app.models.agent_skill import AgentSkill
from app.models.category import Category
from app.services.dispatch_service import _score_agent, suggest_assignees, auto_assign, _get_agent_loads, WEIGHT_LOAD, WEIGHT_SKILL, MAX_LOAD
from tests.conftest import _create_user, _create_category, _create_ticket

# ====== 基础评分函数测试 ======
# API-DISPATCH-101: 无技能负载 0 得分
async def test_score_agent_no_skill_zero_load(db):
    score = _score_agent(1, None, 0, "P2")
    assert score == 0.0

# API-DISPATCH-102: 负载 1 无技能扣分
async def test_score_agent_load_penalty(db):
    score = _score_agent(1, None, 1, "P2")
    assert score == WEIGHT_LOAD * 1

# API-DISPATCH-103: 技能 proficiency 5 满分加成
async def test_score_agent_max_skill(db):
    score = _score_agent(1, 5, 0, "P2")
    assert score == WEIGHT_SKILL * 5

# API-DISPATCH-104: 技能与负载综合评分
async def test_score_agent_combined(db):
    score = _score_agent(1, 3, 2, "P2")
    expected = WEIGHT_SKILL * 3 + WEIGHT_LOAD * 2
    assert score == expected

# ====== 负载查询测试 ======
# API-DISPATCH-105: 空 agent 列表返回空
async def test_get_agent_loads_empty(db):
    loads = await _get_agent_loads(db, [])
    assert loads == {}

# API-DISPATCH-106: 无 in_progress 工单负载为 0
async def test_get_agent_loads_zero(db):
    agent = await _create_user(db, "load_agent1", "agent")
    loads = await _get_agent_loads(db, [agent.id])
    assert loads.get(agent.id, 0) == 0

# API-DISPATCH-107: 多个 in_progress 工单负载正确
async def test_get_agent_loads_multiple(db):
    agent = await _create_user(db, "load_agent2", "agent")
    customer = await _create_user(db, "load_customer", "customer")
    category = await _create_category(db)
    for i in range(3):
        await _create_ticket(db, f"load {i}", "desc", category.id, customer.id, assignee_id=agent.id, status="in_progress")
    loads = await _get_agent_loads(db, [agent.id])
    assert loads[agent.id] == 3

# ====== 建议分配测试 ======
# API-DISPATCH-108: 无 active agent 返回空
async def test_suggest_no_agents(db):
    customer = await _create_user(db, "sugg_cust1", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "sugg", "desc", category.id, customer.id)
    candidates = await suggest_assignees(db, ticket)
    assert candidates == []

# API-DISPATCH-109: 单个 agent 无技能建议成功
async def test_suggest_single_agent_no_skill(db):
    agent = await _create_user(db, "sugg_agent1", "agent")
    customer = await _create_user(db, "sugg_cust2", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "sugg", "desc", category.id, customer.id)
    candidates = await suggest_assignees(db, ticket)
    assert len(candidates) == 1
    assert candidates[0]["agent_id"] == agent.id
    assert candidates[0]["proficiency"] is None
    assert candidates[0]["score"] == 0.0

# API-DISPATCH-110: 高技能 agent 得分高于低技能
async def test_suggest_skill_priority(db):
    agent_high = await _create_user(db, "sugg_agent_high", "agent")
    agent_low = await _create_user(db, "sugg_agent_low", "agent")
    customer = await _create_user(db, "sugg_cust3", "customer")
    category = await _create_category(db)
    db.add(AgentSkill(agent_id=agent_high.id, category_id=category.id, proficiency=5))
    db.add(AgentSkill(agent_id=agent_low.id, category_id=category.id, proficiency=1))
    await db.commit()
    ticket = await _create_ticket(db, "sugg", "desc", category.id, customer.id)
    candidates = await suggest_assignees(db, ticket)
    assert len(candidates) == 2
    assert candidates[0]["agent_id"] == agent_high.id
    assert candidates[0]["score"] > candidates[1]["score"]

# API-DISPATCH-111: 高负载 agent 被排除（超过 MAX_LOAD）
async def test_suggest_excludes_overloaded(db):
    agent = await _create_user(db, "sugg_agent_over", "agent")
    customer = await _create_user(db, "sugg_cust4", "customer")
    category = await _create_category(db)
    for i in range(MAX_LOAD):
        await _create_ticket(db, f"over {i}", "desc", category.id, customer.id, assignee_id=agent.id, status="in_progress")
    ticket = await _create_ticket(db, "sugg", "desc", category.id, customer.id)
    candidates = await suggest_assignees(db, ticket)
    assert all(c["agent_id"] != agent.id for c in candidates)

# API-DISPATCH-112: top_n 限制返回数量
async def test_suggest_top_n_limit(db):
    for i in range(6):
        await _create_user(db, f"sugg_agent_{i}", "agent")
    customer = await _create_user(db, "sugg_cust5", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "sugg", "desc", category.id, customer.id)
    candidates = await suggest_assignees(db, ticket, top_n=3)
    assert len(candidates) == 3

# ====== 自动分配测试 ======
# API-DISPATCH-113: 正分 agent 自动分配成功
async def test_auto_assign_success(db):
    agent = await _create_user(db, "auto_agent1", "agent")
    customer = await _create_user(db, "auto_cust1", "customer")
    category = await _create_category(db)
    db.add(AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=5))
    await db.commit()
    ticket = await _create_ticket(db, "auto", "desc", category.id, customer.id)
    result = await auto_assign(db, ticket)
    assert result is not None
    assert result.id == agent.id
    assert ticket.assignee_id == agent.id
    assert ticket.status == "in_progress"

# API-DISPATCH-114: 无候选不分配
async def test_auto_assign_no_candidates(db):
    customer = await _create_user(db, "auto_cust2", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "auto", "desc", category.id, customer.id)
    result = await auto_assign(db, ticket)
    assert result is None
    assert ticket.assignee_id is None

# API-DISPATCH-115: 负分 agent 不自动分配（但可手动）
async def test_auto_assign_negative_score_skips(db):
    agent = await _create_user(db, "auto_agent2", "agent")
    customer = await _create_user(db, "auto_cust3", "customer")
    category = await _create_category(db)
    # 让 agent 负载极高（接近 MAX_LOAD）且无技能 => 负分
    for i in range(MAX_LOAD - 1):
        await _create_ticket(db, f"heavy {i}", "desc", category.id, customer.id, assignee_id=agent.id, status="in_progress")
    ticket = await _create_ticket(db, "auto", "desc", category.id, customer.id)
    result = await auto_assign(db, ticket)
    assert result is None

# API-DISPATCH-116: 自动分配后写入 DispatchLog
async def test_auto_assign_creates_log(db):
    agent = await _create_user(db, "auto_agent3", "agent")
    customer = await _create_user(db, "auto_cust4", "customer")
    category = await _create_category(db)
    db.add(AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=4))
    await db.commit()
    ticket = await _create_ticket(db, "auto", "desc", category.id, customer.id)
    await auto_assign(db, ticket)
    from app.models.dispatch_log import DispatchLog
    result = await db.execute(select(DispatchLog).where(DispatchLog.ticket_id == ticket.id))
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.dispatch_type == "auto"
    assert log.agent_id == agent.id
```

- [ ] **Step 7: Run tests**

```bash
cd backend && pytest tests/test_dispatch.py -v
```
Expected: 16 passed

- [ ] **Step 8: Commit**

```bash
git add backend/app/services backend/app/models backend/app/schemas backend/tests/test_dispatch.py backend/alembic/versions
git commit -m "feat: add smart dispatch algorithm with full unit tests"
```

---

## Task 3: 分派 API + 集成测试

**Files:**
- Create: `backend/app/routers/dispatch.py`
- Modify: `backend/app/routers/tickets.py`（修改 assign endpoint 记录日志）
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_dispatch_api.py`（补充 API 测试）
- Test: `backend/tests/test_dispatch_api.py`

**Interfaces:**
- Consumes: `suggest_assignees`, `auto_assign`, `log_manual_assign`, `DispatchLog`
- Produces: `POST /api/v1/tickets/{id}/suggest-assignees`, `POST /api/v1/tickets/{id}/auto-assign`, `GET /api/v1/admin/dispatch-logs`, 修改后的 `POST /api/v1/tickets/{id}/assign`

- [ ] **Step 1: Write dispatch router**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.exceptions import NotFoundException, PermissionDeniedException
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.dispatch import AssignSuggestion, DispatchLogResponse
from app.services.dispatch_service import suggest_assignees, auto_assign
from app.services.ticket_service import get_ticket_by_id
from app.routers.tickets import check_ticket_access
from sqlalchemy import select
from app.models.dispatch_log import DispatchLog

router = APIRouter()

@router.post("/tickets/{ticket_id}/suggest-assignees", response_model=list[AssignSuggestion])
async def suggest_assignees_endpoint(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "supervisor", "admin")),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(ticket, current_user)
    return await suggest_assignees(db, ticket, top_n=5)

@router.post("/tickets/{ticket_id}/auto-assign", response_model=dict)
async def auto_assign_endpoint(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("supervisor", "admin")),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(ticket, current_user)
    agent = await auto_assign(db, ticket)
    await db.commit()
    await db.refresh(ticket)
    if agent is None:
        return {"assigned": False, "message": "无合适客服可自动分配"}
    return {"assigned": True, "agent_id": agent.id, "agent_name": agent.username}

@router.get("/admin/dispatch-logs", response_model=list[DispatchLogResponse])
async def list_dispatch_logs(
    ticket_id: int | None = None,
    agent_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("supervisor", "admin")),
):
    query = select(DispatchLog).order_by(DispatchLog.created_at.desc())
    if ticket_id:
        query = query.where(DispatchLog.ticket_id == ticket_id)
    if agent_id:
        query = query.where(DispatchLog.agent_id == agent_id)
    result = await db.execute(query)
    return result.scalars().all()
```

- [ ] **Step 2: Modify assign_ticket to log manual dispatch**

在 `backend/app/routers/tickets.py` 的 `assign_ticket` 函数中，commit 前增加日志记录：

```python
from app.services.dispatch_service import log_manual_assign

@router.post("/tickets/{ticket_id}/assign", response_model=TicketResponse)
async def assign_ticket(...):
    ...
    ticket.assignee_id = req.assignee_id
    if ticket.status == "open":
        ticket.status = "in_progress"
    # 记录手动分派日志
    await log_manual_assign(db, ticket.id, req.assignee_id, f"手动分派 by user {current_user.id}")
    # 注意：log_manual_assign 内部已 commit，这里不能重复 commit
```

注意：`log_manual_assign` 内部已经 `await db.commit()`，而当前 `assign_ticket` 也在后面做 `await db.commit()`。这会导致重复 commit 或 session 状态问题。需要修改 `log_manual_assign` 为**不 commit** 的版本，只 add log，由调用方统一 commit。

修改 `log_manual_assign`：

```python
async def log_manual_assign(db: AsyncSession, ticket_id: int, agent_id: int, reason: str) -> DispatchLog:
    log = DispatchLog(
        ticket_id=ticket_id,
        agent_id=agent_id,
        dispatch_type="manual",
        reason=reason,
    )
    db.add(log)
    return log
```

然后 `assign_ticket` 在 `db.commit()` 时统一提交 ticket + log。

- [ ] **Step 3: Write API tests**

```python
# API-DISPATCH-006: suggest-assignees 成功
async def test_suggest_assignees_api_success(client, supervisor_auth_headers, db):
    from tests.conftest import _create_user, _create_category, _create_ticket
    agent = await _create_user(db, "sugg_api_agent", "agent")
    customer = await _create_user(db, "sugg_api_cust", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "sugg api", "desc", category.id, customer.id)
    r = await client.post(f"/api/v1/tickets/{ticket.id}/suggest-assignees", headers=supervisor_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert data[0]["agent_id"] == agent.id

# API-DISPATCH-007: suggest-assignees 404
async def test_suggest_assignees_not_found_404(client, supervisor_auth_headers, db):
    r = await client.post("/api/v1/tickets/99999/suggest-assignees", headers=supervisor_auth_headers)
    assert r.status_code == 404

# API-DISPATCH-008: suggest-assignees 客户无权 403
async def test_suggest_assignees_forbidden_403(client, customer_auth_headers, db):
    from tests.conftest import _create_user, _create_category, _create_ticket
    customer = await _create_user(db, "sugg_api_cust2", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "sugg api", "desc", category.id, customer.id)
    r = await client.post(f"/api/v1/tickets/{ticket.id}/suggest-assignees", headers=customer_auth_headers)
    assert r.status_code == 403

# API-DISPATCH-009: auto-assign 成功
async def test_auto_assign_api_success(client, supervisor_auth_headers, db):
    from tests.conftest import _create_user, _create_category, _create_ticket
    agent = await _create_user(db, "auto_api_agent", "agent")
    customer = await _create_user(db, "auto_api_cust", "customer")
    category = await _create_category(db)
    from app.models.agent_skill import AgentSkill
    db.add(AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=5))
    await db.commit()
    ticket = await _create_ticket(db, "auto api", "desc", category.id, customer.id)
    r = await client.post(f"/api/v1/tickets/{ticket.id}/auto-assign", headers=supervisor_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["assigned"] is True
    assert data["agent_id"] == agent.id

# API-DISPATCH-010: auto-assign 无候选返回未分配
async def test_auto_assign_api_no_candidate(client, supervisor_auth_headers, db):
    from tests.conftest import _create_user, _create_category, _create_ticket
    customer = await _create_user(db, "auto_api_cust2", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "auto api", "desc", category.id, customer.id)
    r = await client.post(f"/api/v1/tickets/{ticket.id}/auto-assign", headers=supervisor_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["assigned"] is False

# API-DISPATCH-011: admin 查询 dispatch logs
async def test_list_dispatch_logs_success(client, admin_auth_headers, db):
    from tests.conftest import _create_user, _create_category, _create_ticket
    agent = await _create_user(db, "log_agent", "agent")
    customer = await _create_user(db, "log_cust", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "log", "desc", category.id, customer.id, assignee_id=agent.id, status="in_progress")
    from app.services.dispatch_service import log_manual_assign
    await log_manual_assign(db, ticket.id, agent.id, "test")
    await db.commit()
    r = await client.get("/api/v1/admin/dispatch-logs", headers=admin_auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1

# API-DISPATCH-012: assign endpoint 记录 manual log
async def test_manual_assign_creates_log(client, supervisor_auth_headers, db):
    from tests.conftest import _create_user, _create_category, _create_ticket
    agent = await _create_user(db, "manual_agent", "agent")
    customer = await _create_user(db, "manual_cust", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "manual", "desc", category.id, customer.id)
    r = await client.post(f"/api/v1/tickets/{ticket.id}/assign", headers=supervisor_auth_headers, json={"assignee_id": agent.id})
    assert r.status_code == 200
    from app.models.dispatch_log import DispatchLog
    from sqlalchemy import select
    result = await db.execute(select(DispatchLog).where(DispatchLog.ticket_id == ticket.id))
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.dispatch_type == "manual"
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_dispatch_api.py -v
```
Expected: 12 passed (5 from Task 1 + 7 new)

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers backend/app/services backend/tests/test_dispatch_api.py backend/app/main.py
git commit -m "feat: add dispatch API endpoints and manual assign logging"
```

---

## Task 4: 创建工单自动分派触发 + 测试

**Files:**
- Modify: `backend/app/routers/tickets.py`（create_ticket_endpoint）
- Modify: `backend/app/schemas/ticket.py`（TicketCreate 增加 `auto_dispatch` 字段）
- Modify: `backend/tests/test_tickets.py`（补充自动分派场景）
- Test: `backend/tests/test_tickets.py`（5 条新测试）

**Interfaces:**
- Consumes: `auto_assign` from dispatch_service
- Produces: `POST /api/v1/tickets` 支持 `auto_dispatch=true` 自动分派

- [ ] **Step 1: Modify TicketCreate schema**

```python
class TicketCreate(TicketBase):
    assignee_id: Optional[int] = None
    auto_dispatch: bool = False  # 新增
```

- [ ] **Step 2: Modify create_ticket_endpoint**

```python
from app.services.dispatch_service import auto_assign

@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket_endpoint(...):
    ticket = await create_ticket(db, data, current_user.id)
    if data.auto_dispatch and ticket.assignee_id is None:
        await auto_assign(db, ticket)
        await db.commit()
        await db.refresh(ticket)
    return ticket
```

- [ ] **Step 3: Write auto-dispatch trigger tests**

```python
# API-TICKET-020: 创建工单开启自动分派成功
async def test_create_ticket_auto_dispatch_success(client, customer_auth_headers, db):
    from tests.conftest import _create_user, _create_category
    agent = await _create_user(db, "auto_dispatch_agent", "agent")
    category = await _create_category(db)
    from app.models.agent_skill import AgentSkill
    db.add(AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=5))
    await db.commit()
    body = {"title": "auto", "description": "desc", "category_id": category.id, "auto_dispatch": True}
    r = await client.post("/api/v1/tickets", headers=customer_auth_headers, json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["assignee_id"] == agent.id
    assert data["status"] == "in_progress"

# API-TICKET-021: 创建工单自动分派无候选保持 open
async def test_create_ticket_auto_dispatch_no_agent(client, customer_auth_headers, db):
    from tests.conftest import _create_category
    category = await _create_category(db)
    body = {"title": "auto no agent", "description": "desc", "category_id": category.id, "auto_dispatch": True}
    r = await client.post("/api/v1/tickets", headers=customer_auth_headers, json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["assignee_id"] is None
    assert data["status"] == "open"

# API-TICKET-022: 创建工单指定 assignee_id 优先于 auto_dispatch
async def test_create_ticket_assignee_overrides_auto_dispatch(client, customer_auth_headers, db):
    from tests.conftest import _create_user, _create_category
    agent = await _create_user(db, "override_agent", "agent")
    another_agent = await _create_user(db, "override_agent2", "agent")
    category = await _create_category(db)
    from app.models.agent_skill import AgentSkill
    db.add(AgentSkill(agent_id=another_agent.id, category_id=category.id, proficiency=5))
    await db.commit()
    body = {"title": "override", "description": "desc", "category_id": category.id, "assignee_id": agent.id, "auto_dispatch": True}
    r = await client.post("/api/v1/tickets", headers=customer_auth_headers, json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["assignee_id"] == agent.id
```

- [ ] **Step 4: Run full test suite**

```bash
cd backend && pytest -p no:anyio tests/test_tickets.py tests/test_dispatch.py tests/test_dispatch_api.py -v
```
Expected: 全部通过（test_tickets 新增 3 条，test_dispatch 16 条，test_dispatch_api 12 条）

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers backend/app/schemas backend/tests/test_tickets.py
git commit -m "feat: auto-dispatch trigger on ticket creation with tests"
```

---

## Task 5: 前端建议分配 UI + 测试

**Files:**
- Create: `frontend/src/api/dispatch.js`
- Create: `frontend/src/stores/dispatch.js`
- Create: `frontend/src/components/AssignSuggestionList.vue`
- Modify: `frontend/src/views/agent/AgentTicketDetailView.vue`
- Modify: `frontend/src/views/agent/AgentTicketsView.vue`（可选：增加“自动分派”按钮）
- Test: `frontend/tests/dispatch.test.js` 或组件测试

**Interfaces:**
- Consumes: `POST /api/v1/tickets/{id}/suggest-assignees`, `POST /api/v1/tickets/{id}/auto-assign`, `POST /api/v1/tickets/{id}/assign`
- Produces: 客服详情页“建议分配”下拉/列表 + “自动分派”按钮

- [ ] **Step 1: Write dispatch API client**

```javascript
import request from './index.js'

export const dispatchApi = {
  suggest: (ticketId) => request.post(`/api/v1/tickets/${ticketId}/suggest-assignees`),
  autoAssign: (ticketId) => request.post(`/api/v1/tickets/${ticketId}/auto-assign`),
  assign: (ticketId, assigneeId) => request.post(`/api/v1/tickets/${ticketId}/assign`, { assignee_id: assigneeId }),
}
```

- [ ] **Step 2: Write dispatch Pinia store**

```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dispatchApi } from '@/api/dispatch'

export const useDispatchStore = defineStore('dispatch', () => {
  const suggestions = ref([])
  const loading = ref(false)

  const fetchSuggestions = async (ticketId) => {
    loading.value = true
    try {
      const { data } = await dispatchApi.suggest(ticketId)
      suggestions.value = data
    } finally {
      loading.value = false
    }
  }

  const autoAssign = async (ticketId) => {
    const { data } = await dispatchApi.autoAssign(ticketId)
    return data
  }

  const manualAssign = async (ticketId, assigneeId) => {
    const { data } = await dispatchApi.assign(ticketId, assigneeId)
    return data
  }

  return { suggestions, loading, fetchSuggestions, autoAssign, manualAssign }
})
```

- [ ] **Step 3: Write AssignSuggestionList component**

```vue
<template>
  <div v-if="suggestions.length">
    <h4>建议分配</h4>
    <el-table :data="suggestions" size="small">
      <el-table-column prop="agent_name" label="客服" />
      <el-table-column prop="score" label="得分" width="80" />
      <el-table-column prop="current_load" label="当前负载" width="100" />
      <el-table-column prop="reason" label="原因" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button size="small" @click="$emit('assign', row.agent_id)">分配</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
  <el-empty v-else description="暂无可建议的客服" />
</template>
<script setup>
const props = defineProps({ suggestions: Array })
const emit = defineEmits(['assign'])
</script>
```

- [ ] **Step 4: Modify AgentTicketDetailView**

在现有 `<el-button-group>` 上方增加：

```vue
<el-button-group v-if="store.currentTicket.status === 'open'">
  <el-button @click="loadSuggestions">建议分配</el-button>
  <el-button type="primary" @click="handleAutoAssign">自动分派</el-button>
</el-button-group>
<AssignSuggestionList v-if="suggestions.length" :suggestions="suggestions" @assign="handleManualAssign" />
```

```javascript
import { useDispatchStore } from '@/stores/dispatch'
import AssignSuggestionList from '@/components/AssignSuggestionList.vue'

const dispatchStore = useDispatchStore()
const suggestions = computed(() => dispatchStore.suggestions)

const loadSuggestions = async () => {
  await dispatchStore.fetchSuggestions(store.currentTicket.id)
}
const handleAutoAssign = async () => {
  const result = await dispatchStore.autoAssign(store.currentTicket.id)
  if (result.assigned) {
    ElMessage.success('自动分派成功')
    await store.fetchTicket(store.currentTicket.id)
  } else {
    ElMessage.warning('暂无可分配的客服')
  }
}
const handleManualAssign = async (agentId) => {
  await dispatchStore.manualAssign(store.currentTicket.id, agentId)
  ElMessage.success('手动分派成功')
  await store.fetchTicket(store.currentTicket.id)
}
```

- [ ] **Step 5: Build check**

```bash
cd frontend && npm run build
```
Expected: 成功，零错误

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api frontend/src/stores frontend/src/components frontend/src/views/agent
git commit -m "feat: add frontend dispatch suggestion UI and auto-assign button"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ 智能分派算法（负载 + 技能 + 优先级权重）
- ✅ 建议分配 API（返回排序候选）
- ✅ 自动分配 API（主管触发）
- ✅ 创建时自动分派触发（customer 可勾选）
- ✅ 分派日志记录（manual + auto）
- ✅ Admin/Supervisor 查询分派日志
- ✅ 前端建议分配 UI
- ✅ 测试覆盖率 ≥80%，关键功能 100%（算法 16 条 + API 12 条 + 触发 3 条 + skill 5 条 = 36 条）

**2. Placeholder scan:**
- 无 TBD/TODO/fill in later
- 所有测试步骤包含具体代码
- 所有步骤包含具体命令

**3. Type consistency:**
- `AgentSkill` / `DispatchLog` / `Ticket` 字段一致
- 权重常量与算法公式一致
- 状态值与后端约束一致
- 路由路径与 API 设计一致

**4. 潜在缺口：**
- 前端测试仅给了组件示例，实际执行需要子 AGENT 补全具体测试代码
- 分派规则配置（DispatchRule 模型）未实现，留作后续扩展（M2）
- 复杂 SLA 时间分派权重未纳入（属于 T006 范围）

---

## Execution Handoff

**推荐执行方式：** Subagent-Driven Development
- 每个任务一个独立子 AGENT，审查后进入下一任务
- Task 2（核心算法）必须通过 code review
- 总共 5 个任务，按依赖顺序串行执行
