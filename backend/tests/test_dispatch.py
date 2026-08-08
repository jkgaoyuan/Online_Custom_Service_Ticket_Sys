import pytest
from sqlalchemy import select

from app.models.ticket import Ticket
from app.models.user import User
from app.models.agent_skill import AgentSkill
from app.models.category import Category
from app.models.dispatch_log import DispatchLog
from app.services.dispatch_service import (
    _score_agent,
    suggest_assignees,
    auto_assign,
    _get_agent_loads,
    WEIGHT_LOAD,
    WEIGHT_SKILL,
    MAX_LOAD,
)
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
        await _create_ticket(
            db, f"load {i}", "desc", category.id, customer.id, assignee_id=agent.id, status="in_progress"
        )
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
        await _create_ticket(
            db, f"over {i}", "desc", category.id, customer.id, assignee_id=agent.id, status="in_progress"
        )
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
        await _create_ticket(
            db, f"heavy {i}", "desc", category.id, customer.id, assignee_id=agent.id, status="in_progress"
        )
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
    result = await db.execute(select(DispatchLog).where(DispatchLog.ticket_id == ticket.id))
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.dispatch_type == "auto"
    assert log.agent_id == agent.id
