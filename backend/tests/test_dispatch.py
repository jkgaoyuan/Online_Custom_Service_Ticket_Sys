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
    log_manual_assign,
    _get_agent_loads,
    WEIGHT_LOAD,
    WEIGHT_SKILL_MATCH,
    WEIGHT_PROFICIENCY,
    WEIGHT_NO_SKILL,
)
from tests.conftest import _create_user, _create_category, _create_ticket


# ====== 基础评分函数测试 ======

# API-DISPATCH-101: 无技能负载 0 得分 = 无技能惩罚
async def test_score_agent_no_skill_zero_load(db):
    score = _score_agent(1, None, 0)
    assert score == WEIGHT_NO_SKILL


# API-DISPATCH-102: 负载 1 无技能扣分
async def test_score_agent_load_penalty(db):
    score = _score_agent(1, None, 1)
    assert score == WEIGHT_NO_SKILL + WEIGHT_LOAD * 1


# API-DISPATCH-103: 技能 proficiency 5 满分加成
async def test_score_agent_max_skill(db):
    score = _score_agent(1, 5, 0)
    assert score == WEIGHT_SKILL_MATCH + WEIGHT_PROFICIENCY * 5


# API-DISPATCH-104: 技能与负载综合评分
async def test_score_agent_combined(db):
    score = _score_agent(1, 3, 2)
    expected = WEIGHT_SKILL_MATCH + WEIGHT_PROFICIENCY * 3 + WEIGHT_LOAD * 2
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
    assert candidates[0]["score"] == round(WEIGHT_NO_SKILL, 2)
    assert candidates[0]["is_available"] is True
    assert candidates[0]["max_concurrent_tickets"] == 5


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


# API-DISPATCH-111: 高负载 agent 仍返回但标记 is_available=False
async def test_suggest_includes_overloaded_as_unavailable(db):
    agent_over = await _create_user(db, "sugg_agent_over", "agent")
    agent_free = await _create_user(db, "sugg_agent_free", "agent")
    customer = await _create_user(db, "sugg_cust4", "customer")
    category = await _create_category(db)
    # 默认 max_concurrent_tickets = 5，创建 5 个 in_progress 工单使其满载
    for i in range(5):
        await _create_ticket(
            db, f"over {i}", "desc", category.id, customer.id, assignee_id=agent_over.id, status="in_progress"
        )
    ticket = await _create_ticket(db, "sugg", "desc", category.id, customer.id)
    candidates = await suggest_assignees(db, ticket)
    assert len(candidates) == 2
    over = [c for c in candidates if c["agent_id"] == agent_over.id][0]
    free = [c for c in candidates if c["agent_id"] == agent_free.id][0]
    assert over["is_available"] is False
    assert over["current_load"] == 5
    assert free["is_available"] is True
    assert free["current_load"] == 0


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
    # 让 agent 负载高（4/5）且无技能 => 负分，但仍 available
    for i in range(4):
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


# API-DISPATCH-117: log_manual_assign 写入 manual 类型日志
async def test_log_manual_assign_creates_log(db):
    agent = await _create_user(db, "manual_agent1", "agent")
    customer = await _create_user(db, "manual_cust1", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "manual", "desc", category.id, customer.id)
    await db.commit()
    log = await log_manual_assign(db, ticket.id, agent.id, "人工分派测试")
    await db.commit()
    assert log.dispatch_type == "manual"
    assert log.agent_id == agent.id
    assert log.ticket_id == ticket.id
    # 验证 commit 后 DB 可查
    result = await db.execute(select(DispatchLog).where(DispatchLog.id == log.id))
    db_log = result.scalar_one_or_none()
    assert db_log is not None
    assert db_log.dispatch_type == "manual"


# API-DISPATCH-118: 相同负载且无技能时排序稳定（按 agent_id 升序）
async def test_suggest_tie_breaking_deterministic(db):
    agent_a = await _create_user(db, "sugg_agent_a", "agent")
    agent_b = await _create_user(db, "sugg_agent_b", "agent")
    customer = await _create_user(db, "sugg_cust6", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "sugg", "desc", category.id, customer.id)
    candidates = await suggest_assignees(db, ticket)
    assert len(candidates) == 2
    # 稳定排序：score 相同则保持 DB 查询顺序（即 agent_id 升序）
    assert candidates[0]["agent_id"] < candidates[1]["agent_id"]
    assert candidates[0]["score"] == round(WEIGHT_NO_SKILL, 2)
    assert candidates[1]["score"] == round(WEIGHT_NO_SKILL, 2)


# ====== M2-T5 新增场景测试 ======

# M2-T5-01: 技能 agent 得分高于无技能 agent，即使负载略高
async def test_skill_beats_lower_load_no_skill(db):
    agent_skill = await _create_user(db, "m2_skill_agent", "agent")
    agent_free = await _create_user(db, "m2_free_agent", "agent")
    customer = await _create_user(db, "m2_cust1", "customer")
    category = await _create_category(db)
    db.add(AgentSkill(agent_id=agent_skill.id, category_id=category.id, proficiency=3))
    await db.commit()
    # skill agent 负载 2/5
    for i in range(2):
        await _create_ticket(
            db, f"skill_load {i}", "desc", category.id, customer.id, assignee_id=agent_skill.id, status="in_progress"
        )
    ticket = await _create_ticket(db, "m2", "desc", category.id, customer.id)
    candidates = await suggest_assignees(db, ticket)
    skill = [c for c in candidates if c["agent_id"] == agent_skill.id][0]
    free = [c for c in candidates if c["agent_id"] == agent_free.id][0]
    # skill agent: 15 + 3*3 + (-2)*2 = 15 + 9 - 4 = 20
    # free agent: -5 + 0 = -5
    assert skill["score"] > free["score"]
    assert candidates[0]["agent_id"] == agent_skill.id


# M2-T5-02: 满负载有技能 agent 标记 unavailable，auto_assign 选无技能 agent
async def test_full_load_skilled_agent_unavailable(db):
    agent_full = await _create_user(db, "m2_full_agent", "agent")
    agent_free = await _create_user(db, "m2_free_agent2", "agent")
    customer = await _create_user(db, "m2_cust2", "customer")
    category = await _create_category(db)
    db.add(AgentSkill(agent_id=agent_full.id, category_id=category.id, proficiency=5))
    await db.commit()
    # 满载 5/5
    for i in range(5):
        await _create_ticket(
            db, f"full {i}", "desc", category.id, customer.id, assignee_id=agent_full.id, status="in_progress"
        )
    ticket = await _create_ticket(db, "m2", "desc", category.id, customer.id)
    candidates = await suggest_assignees(db, ticket)
    full = [c for c in candidates if c["agent_id"] == agent_full.id][0]
    free = [c for c in candidates if c["agent_id"] == agent_free.id][0]
    assert full["is_available"] is False
    assert free["is_available"] is True
    # auto_assign 应该选 free agent（即使无技能，得分 -5 > 0 不成立，等等...）
    # 无技能 agent 得分 = -5，不大于 0，所以 auto_assign 返回 None
    result = await auto_assign(db, ticket)
    assert result is None


# M2-T5-03: 所有 agent 都满负载
async def test_all_agents_full_load(db):
    agent_a = await _create_user(db, "m2_full_a", "agent")
    agent_b = await _create_user(db, "m2_full_b", "agent")
    customer = await _create_user(db, "m2_cust3", "customer")
    category = await _create_category(db)
    for agent in (agent_a, agent_b):
        for i in range(5):
            await _create_ticket(
                db, f"full_{agent.id}_{i}", "desc", category.id, customer.id, assignee_id=agent.id, status="in_progress"
            )
    ticket = await _create_ticket(db, "m2", "desc", category.id, customer.id)
    candidates = await suggest_assignees(db, ticket)
    assert len(candidates) == 2
    assert all(c["is_available"] is False for c in candidates)
    result = await auto_assign(db, ticket)
    assert result is None


# M2-T5-04: 多个 agent 技能不同 proficiency 排序正确
async def test_proficiency_sorting(db):
    agent_p5 = await _create_user(db, "m2_p5", "agent")
    agent_p3 = await _create_user(db, "m2_p3", "agent")
    agent_p1 = await _create_user(db, "m2_p1", "agent")
    customer = await _create_user(db, "m2_cust4", "customer")
    category = await _create_category(db)
    db.add(AgentSkill(agent_id=agent_p5.id, category_id=category.id, proficiency=5))
    db.add(AgentSkill(agent_id=agent_p3.id, category_id=category.id, proficiency=3))
    db.add(AgentSkill(agent_id=agent_p1.id, category_id=category.id, proficiency=1))
    await db.commit()
    ticket = await _create_ticket(db, "m2", "desc", category.id, customer.id)
    candidates = await suggest_assignees(db, ticket)
    assert candidates[0]["agent_id"] == agent_p5.id
    assert candidates[1]["agent_id"] == agent_p3.id
    assert candidates[2]["agent_id"] == agent_p1.id
    # p5: 15 + 15 = 30; p3: 15 + 9 = 24; p1: 15 + 3 = 18
    assert candidates[0]["score"] == 30.0
    assert candidates[1]["score"] == 24.0
    assert candidates[2]["score"] == 18.0


# M2-T5-05: auto_assign 后 ticket 状态流转正确
async def test_auto_assign_status_transition(db):
    agent = await _create_user(db, "m2_transition_agent", "agent")
    customer = await _create_user(db, "m2_cust5", "customer")
    category = await _create_category(db)
    db.add(AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=2))
    await db.commit()
    ticket = await _create_ticket(db, "m2", "desc", category.id, customer.id, status="open")
    assert ticket.status == "open"
    result = await auto_assign(db, ticket)
    assert result is not None
    assert ticket.assignee_id == agent.id
    assert ticket.status == "in_progress"


# M2-T5-06: 满负载 agent 不在 auto_assign 候选中
async def test_auto_assign_excludes_full_load(db):
    agent_full = await _create_user(db, "m2_auto_full", "agent")
    agent_avail = await _create_user(db, "m2_auto_avail", "agent")
    customer = await _create_user(db, "m2_cust6", "customer")
    category = await _create_category(db)
    db.add(AgentSkill(agent_id=agent_full.id, category_id=category.id, proficiency=5))
    db.add(AgentSkill(agent_id=agent_avail.id, category_id=category.id, proficiency=1))
    await db.commit()
    # agent_full 满载
    for i in range(5):
        await _create_ticket(
            db, f"auto_full {i}", "desc", category.id, customer.id, assignee_id=agent_full.id, status="in_progress"
        )
    ticket = await _create_ticket(db, "m2", "desc", category.id, customer.id)
    result = await auto_assign(db, ticket)
    # agent_avail 得分 = 15 + 3 = 18 > 0，应被选中
    assert result is not None
    assert result.id == agent_avail.id


# M2-T5-07: 自定义 max_concurrent_tickets 生效
async def test_custom_max_concurrent(db):
    agent = await _create_user(db, "m2_custom_max", "agent")
    agent.max_concurrent_tickets = 2
    await db.commit()
    customer = await _create_user(db, "m2_cust7", "customer")
    category = await _create_category(db)
    for i in range(2):
        await _create_ticket(
            db, f"custom {i}", "desc", category.id, customer.id, assignee_id=agent.id, status="in_progress"
        )
    ticket = await _create_ticket(db, "m2", "desc", category.id, customer.id)
    candidates = await suggest_assignees(db, ticket)
    agent_cand = [c for c in candidates if c["agent_id"] == agent.id][0]
    assert agent_cand["max_concurrent_tickets"] == 2
    assert agent_cand["is_available"] is False
    assert agent_cand["current_load"] == 2
