from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.dependencies import require_role
from app.exceptions import NotFoundException
from app.models.agent_skill import AgentSkill
from app.models.category import Category
from app.models.dispatch_log import DispatchLog
from app.models.user import User
from app.schemas.agent_skill import (
    AgentSkillCreate,
    AgentSkillResponse,
    AgentSkillUpdate,
)
from app.schemas.dispatch import AssignSuggestion, DispatchLogResponse
from app.services.agent_skill_service import (
    create_agent_skill,
    delete_agent_skill,
    get_agent_skill_by_id,
    get_agent_skills_by_agent,
    get_all_agent_skills,
    update_agent_skill,
)
from app.services.dispatch_service import suggest_assignees, auto_assign
from app.services.ticket_service import get_ticket_by_id
from app.routers.tickets import check_ticket_access

router = APIRouter()


async def _enrich_skill_response(db: AsyncSession, skill: AgentSkill) -> dict:
    agent = await db.get(User, skill.agent_id)
    category = await db.get(Category, skill.category_id)
    return {
        "id": skill.id,
        "agent_id": skill.agent_id,
        "category_id": skill.category_id,
        "proficiency": skill.proficiency,
        "agent_name": agent.username if agent else None,
        "category_name": category.name if category else None,
    }


@router.post(
    "/admin/agent-skills",
    response_model=AgentSkillResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_skill(
    data: AgentSkillCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "supervisor")),
):
    skill = await create_agent_skill(db, data)
    return await _enrich_skill_response(db, skill)


@router.get("/admin/agent-skills", response_model=list[AgentSkillResponse])
async def admin_list_skills(
    agent_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "supervisor")),
):
    if agent_id:
        skills = await get_agent_skills_by_agent(db, agent_id)
    else:
        skills = await get_all_agent_skills(db)

    if not skills:
        return []

    agent_ids = {s.agent_id for s in skills}
    category_ids = {s.category_id for s in skills}
    agents = {
        u.id: u
        for u in (await db.execute(select(User).where(User.id.in_(agent_ids)))).scalars().all()
    }
    categories = {
        c.id: c
        for c in (await db.execute(select(Category).where(Category.id.in_(category_ids)))).scalars().all()
    }

    return [
        {
            "id": s.id,
            "agent_id": s.agent_id,
            "category_id": s.category_id,
            "proficiency": s.proficiency,
            "agent_name": agents.get(s.agent_id).username if agents.get(s.agent_id) else None,
            "category_name": categories.get(s.category_id).name if categories.get(s.category_id) else None,
        }
        for s in skills
    ]


@router.put("/admin/agent-skills/{skill_id}", response_model=AgentSkillResponse)
async def admin_update_skill(
    skill_id: int,
    data: AgentSkillUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "supervisor")),
):
    skill = await get_agent_skill_by_id(db, skill_id)
    if not skill:
        raise NotFoundException("技能记录不存在")
    skill = await update_agent_skill(db, skill, data)
    return await _enrich_skill_response(db, skill)


@router.delete(
    "/admin/agent-skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def admin_delete_skill(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "supervisor")),
):
    skill = await get_agent_skill_by_id(db, skill_id)
    if not skill:
        raise NotFoundException("技能记录不存在")
    await delete_agent_skill(db, skill)


@router.post("/tickets/{ticket_id}/suggest-assignees", response_model=list[AssignSuggestion])
async def suggest_assignees_endpoint(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "supervisor", "admin")),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(db, ticket, current_user)
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
    await check_ticket_access(db, ticket, current_user)
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
