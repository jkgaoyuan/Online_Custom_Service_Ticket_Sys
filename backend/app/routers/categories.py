from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.services.category_service import (
    create_category,
    delete_category,
    get_categories,
    get_category_by_id,
    update_category,
)

router = APIRouter()


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_categories(db)


@router.post(
    "/admin/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category_endpoint(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    return await create_category(db, data)


@router.put("/admin/categories/{category_id}", response_model=CategoryResponse)
async def update_category_endpoint(
    category_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    category = await get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    return await update_category(db, category, data)


@router.delete("/admin/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category_endpoint(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    category = await get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    await delete_category(db, category)
