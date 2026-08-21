from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.agent_skill import AgentSkill
from app.models.category import Category
from app.models.user import User
from app.schemas.agent_skill import AgentSkillUpdate

router = APIRouter()


class AgentSkillCreateRequest(BaseModel):
    category_id: int = Field(..., gt=0)
    proficiency: int = Field(default=3, ge=1, le=5)


class CategoryInfo(BaseModel):
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class AgentInfo(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class AgentSkillWithCategoryResponse(BaseModel):
    id: int
    agent_id: int
    category_id: int
    proficiency: int
    category: CategoryInfo

    model_config = ConfigDict(from_attributes=True)


class AgentSkillWithAgentAndCategoryResponse(BaseModel):
    id: int
    agent_id: int
    category_id: int
    proficiency: int
    agent: AgentInfo
    category: CategoryInfo

    model_config = ConfigDict(from_attributes=True)


class AgentSkillListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AgentSkillWithAgentAndCategoryResponse]


async def _get_agent(db: AsyncSession, agent_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == agent_id))
    return result.scalar_one_or_none()


async def _get_skill_with_agent(
    db: AsyncSession, skill_id: int
) -> tuple[AgentSkill, User] | None:
    result = await db.execute(
        select(AgentSkill, User)
        .join(User, AgentSkill.agent_id == User.id)
        .where(AgentSkill.id == skill_id)
    )
    row = result.one_or_none()
    if row is None:
        return None
    return row[0], row[1]


@router.get(
    "/admin/agents/{agent_id}/skills",
    response_model=list[AgentSkillWithCategoryResponse],
)
async def get_agent_skills(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    agent = await _get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="用户不存在")
    if current_user.role == "supervisor" and agent.role != "agent":
        raise HTTPException(status_code=403, detail="无权查看该用户")

    result = await db.execute(
        select(AgentSkill, Category)
        .join(Category, AgentSkill.category_id == Category.id)
        .where(AgentSkill.agent_id == agent_id)
    )
    rows = result.all()

    return [
        {
            "id": skill.id,
            "agent_id": skill.agent_id,
            "category_id": skill.category_id,
            "proficiency": skill.proficiency,
            "category": {
                "id": cat.id,
                "name": cat.name,
                "code": cat.code,
            },
        }
        for skill, cat in rows
    ]


@router.post(
    "/admin/agents/{agent_id}/skills",
    response_model=AgentSkillWithCategoryResponse,
)
async def create_or_update_agent_skill(
    agent_id: int,
    data: AgentSkillCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    agent = await _get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="用户不存在")
    if current_user.role == "supervisor" and agent.role != "agent":
        raise HTTPException(status_code=403, detail="无权修改该用户")

    existing_result = await db.execute(
        select(AgentSkill).where(
            AgentSkill.agent_id == agent_id,
            AgentSkill.category_id == data.category_id,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.proficiency = data.proficiency
        await db.commit()
        await db.refresh(existing)
        skill = existing
    else:
        skill = AgentSkill(
            agent_id=agent_id,
            category_id=data.category_id,
            proficiency=data.proficiency,
        )
        db.add(skill)
        await db.commit()
        await db.refresh(skill)

    cat_result = await db.execute(
        select(Category).where(Category.id == skill.category_id)
    )
    category = cat_result.scalar_one()

    return {
        "id": skill.id,
        "agent_id": skill.agent_id,
        "category_id": skill.category_id,
        "proficiency": skill.proficiency,
        "category": {
            "id": category.id,
            "name": category.name,
            "code": category.code,
        },
    }


@router.put(
    "/admin/skills/{skill_id}",
    response_model=AgentSkillWithCategoryResponse,
)
async def update_skill(
    skill_id: int,
    data: AgentSkillUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    row = await _get_skill_with_agent(db, skill_id)
    if not row:
        raise HTTPException(status_code=404, detail="技能不存在")
    skill, agent = row
    if current_user.role == "supervisor" and agent.role != "agent":
        raise HTTPException(status_code=403, detail="无权修改该技能")

    skill.proficiency = data.proficiency
    await db.commit()
    await db.refresh(skill)

    cat_result = await db.execute(
        select(Category).where(Category.id == skill.category_id)
    )
    category = cat_result.scalar_one()

    return {
        "id": skill.id,
        "agent_id": skill.agent_id,
        "category_id": skill.category_id,
        "proficiency": skill.proficiency,
        "category": {
            "id": category.id,
            "name": category.name,
            "code": category.code,
        },
    }


@router.delete("/admin/skills/{skill_id}")
async def delete_skill(
    skill_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    row = await _get_skill_with_agent(db, skill_id)
    if not row:
        raise HTTPException(status_code=404, detail="技能不存在")
    skill, agent = row
    if current_user.role == "supervisor" and agent.role != "agent":
        raise HTTPException(status_code=403, detail="无权删除该技能")

    await db.delete(skill)
    await db.commit()
    return {"detail": "删除成功"}


@router.get("/admin/skills", response_model=AgentSkillListResponse)
async def list_skills(
    agent_id: int | None = None,
    category_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    base_stmt = (
        select(AgentSkill, User, Category)
        .join(User, AgentSkill.agent_id == User.id)
        .join(Category, AgentSkill.category_id == Category.id)
    )
    count_stmt = (
        select(func.count(AgentSkill.id))
        .select_from(AgentSkill)
        .join(User, AgentSkill.agent_id == User.id)
    )

    filters = []
    if agent_id is not None:
        filters.append(AgentSkill.agent_id == agent_id)
    if category_id is not None:
        filters.append(AgentSkill.category_id == category_id)
    if current_user.role == "supervisor":
        filters.append(User.role == "agent")

    if filters:
        base_stmt = base_stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    result = await db.execute(
        base_stmt.order_by(AgentSkill.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": skill.id,
                "agent_id": skill.agent_id,
                "category_id": skill.category_id,
                "proficiency": skill.proficiency,
                "agent": {
                    "id": agent.id,
                    "username": agent.username,
                },
                "category": {
                    "id": cat.id,
                    "name": cat.name,
                    "code": cat.code,
                },
            }
            for skill, agent, cat in rows
        ],
    }
