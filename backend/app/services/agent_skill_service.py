from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_skill import AgentSkill
from app.schemas.agent_skill import AgentSkillCreate, AgentSkillUpdate


async def create_agent_skill(
    db: AsyncSession, data: AgentSkillCreate
) -> AgentSkill:
    skill = AgentSkill(**data.model_dump())
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return skill


async def get_agent_skills_by_agent(
    db: AsyncSession, agent_id: int
) -> list[AgentSkill]:
    result = await db.execute(
        select(AgentSkill).where(AgentSkill.agent_id == agent_id)
    )
    return result.scalars().all()


async def get_all_agent_skills(db: AsyncSession) -> list[AgentSkill]:
    result = await db.execute(select(AgentSkill))
    return result.scalars().all()


async def get_agent_skill_by_id(
    db: AsyncSession, skill_id: int
) -> AgentSkill | None:
    result = await db.execute(
        select(AgentSkill).where(AgentSkill.id == skill_id)
    )
    return result.scalar_one_or_none()


async def update_agent_skill(
    db: AsyncSession, skill: AgentSkill, data: AgentSkillUpdate
) -> AgentSkill:
    skill.proficiency = data.proficiency
    await db.commit()
    await db.refresh(skill)
    return skill


async def delete_agent_skill(db: AsyncSession, skill: AgentSkill) -> None:
    await db.delete(skill)
    await db.commit()
