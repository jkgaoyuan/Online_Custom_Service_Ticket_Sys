from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.auth_service import list_active_users

router = APIRouter()


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    role: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("agent", "supervisor", "admin")),
):
    users = await list_active_users(db, role=role)
    return [UserResponse.model_validate(user) for user in users]
