from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.dependencies import require_role
from app.exceptions import NotFoundException
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
    return await create_agent_skill(db, data)


@router.get("/admin/agent-skills", response_model=list[AgentSkillResponse])
async def admin_list_skills(
    agent_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin", "supervisor")),
):
    if agent_id:
        return await get_agent_skills_by_agent(db, agent_id)
    return await get_all_agent_skills(db)


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
    return await update_agent_skill(db, skill, data)


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
