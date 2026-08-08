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
MAX_LOAD = 10             # 超过 10 个处理中工单直接排除


def _score_agent(agent_id: int, proficiency: int | None, current_load: int) -> float:
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
        score = _score_agent(agent.id, proficiency, load)
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
    """自动分配最佳客服，返回 agent 或 None。同时写入 DispatchLog。

    Does NOT commit. Caller must commit the session.
    """
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
