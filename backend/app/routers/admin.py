from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.exceptions import PermissionDeniedException
from app.models.user import User
from app.schemas.user import (
    PasswordResetResponse,
    UserDetailResponse,
    UserListItem,
    UserListResponse,
    UserResponse,
    UserStats,
    UserUpdate,
)
from app.services.user_service import get_user_by_id, get_user_stats, list_users, reset_user_password, update_user

router = APIRouter()


@router.get("/users", response_model=UserListResponse)
async def get_users(
    role: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    if current_user.role == "supervisor":
        if role is not None and role != "agent":
            raise PermissionDeniedException("主管只能查看客服用户")
        role = "agent"

    result = await list_users(db, role=role, is_active=is_active, page=page, page_size=page_size)
    items = [UserListItem.model_validate(item) for item in result["items"]]
    return UserListResponse(
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        items=items,
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if current_user.role == "supervisor" and user.role != "agent":
        raise PermissionDeniedException("主管只能查看客服用户")

    stats = None
    if user.role in ("agent", "supervisor", "admin"):
        stats_data = await get_user_stats(db, user_id)
        if stats_data:
            stats = UserStats.model_validate(stats_data)

    return UserDetailResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        stats=stats,
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def modify_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    target_user = await get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if current_user.role == "supervisor":
        if target_user.role != "agent":
            raise PermissionDeniedException("主管只能修改客服用户")
        if data.role is not None and data.role != "agent":
            raise PermissionDeniedException("主管不能将用户角色改为非客服")

    if current_user.id == user_id and data.role is not None and data.role != current_user.role:
        raise HTTPException(status_code=400, detail="管理员不能修改自己的角色")

    updated = await update_user(db, user_id, data)
    return UserResponse.model_validate(updated)


@router.post("/users/{user_id}/reset-password", response_model=PasswordResetResponse)
async def reset_password(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    temp_password = await reset_user_password(db, user_id)
    return {"temp_password": temp_password}
