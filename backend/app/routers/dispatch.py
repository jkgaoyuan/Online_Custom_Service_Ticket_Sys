from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.exceptions import NotFoundException
from app.schemas.agent_skill import (
    AgentSkillCreate,
    AgentSkillResponse,
    AgentSkillUpdate,
)
from app.services.agent_skill_service import (
    create_agent_skill,
    delete_agent_skill,
    get_agent_skill_by_id,
    get_agent_skills_by_agent,
    get_all_agent_skills,
    update_agent_skill,
)

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
