from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_

from app.models.ticket import Ticket
from app.models.user import User
from app.models.agent_skill import AgentSkill
from app.models.dispatch_log import DispatchLog
from app.models.category import Category

from app.core.sse import send_event

# 权重常量（可配置，先硬编码 MVP）
WEIGHT_LOAD = -2.0        # 每多一个 in_progress 工单减 2 分
WEIGHT_SKILL_MATCH = 15.0  # 有匹配技能的基础分
WEIGHT_PROFICIENCY = 3.0   # 每点 proficiency 额外加分
WEIGHT_NO_SKILL = -5.0     # 无匹配技能的小惩罚


def _score_agent(agent_id: int, proficiency: int | None, current_load: int) -> float:
    """计算单个 agent 对某工单的得分。"""
    score = 0.0
    # 负载负向评分
    score += WEIGHT_LOAD * current_load
    # 技能评分
    if proficiency is not None:
        score += WEIGHT_SKILL_MATCH + WEIGHT_PROFICIENCY * proficiency
    else:
        score += WEIGHT_NO_SKILL
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
    """返回排序后的建议分配候选列表（包含所有 agent，已满负载标记 is_available=False）。"""
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
        proficiency = skills_map.get(agent.id)
        score = _score_agent(agent.id, proficiency, load)
        is_available = load < agent.max_concurrent_tickets
        reason_parts = []
        if proficiency is not None:
            reason_parts.append(f"技能匹配度 {proficiency}/5")
        else:
            reason_parts.append("无匹配技能")
        reason_parts.append(f"当前负载 {load}/{agent.max_concurrent_tickets}")
        reason = "；".join(reason_parts)
        candidates.append({
            "agent_id": agent.id,
            "agent_name": agent.username,
            "score": round(score, 2),
            "current_load": load,
            "max_concurrent_tickets": agent.max_concurrent_tickets,
            "is_available": is_available,
            "proficiency": proficiency,
            "reason": reason,
        })

    # 5. 按得分降序排序
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:top_n]


async def auto_assign(db: AsyncSession, ticket: Ticket) -> User | None:
    """自动分配最佳客服，返回 agent 或 None。同时写入 DispatchLog。

    只从 is_available=True 且 score > 0 的候选中选择。
    Does NOT commit. Caller must commit the session.
    """
    candidates = await suggest_assignees(db, ticket, top_n=5)
    # 过滤出可用且得分为正的候选
    available = [c for c in candidates if c["is_available"] and c["score"] > 0]
    if not available:
        return None
    best = available[0]
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
    # 发送 SSE 事件
    await send_event(agent.id, "ticket_assigned", {
        "ticket_id": ticket.id,
        "ticket_no": ticket.ticket_no,
        "title": ticket.title,
        "priority": ticket.priority,
        "status": ticket.status,
    })
    await send_event(agent.id, "stats_update", {})
    return agent


async def log_manual_assign(db: AsyncSession, ticket_id: int, agent_id: int, reason: str) -> DispatchLog:
    """记录人工分派日志。

    Does NOT commit. Caller must commit the session.
    """
    log = DispatchLog(
        ticket_id=ticket_id,
        agent_id=agent_id,
        dispatch_type="manual",
        reason=reason,
    )
    db.add(log)
    return log
