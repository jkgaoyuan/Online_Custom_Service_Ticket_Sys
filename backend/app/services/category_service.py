from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateException
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


async def create_category(db: AsyncSession, data: CategoryCreate) -> Category:
    category = Category(**data.model_dump())
    db.add(category)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise DuplicateException("分类编码已存在")
    await db.refresh(category)
    return category


async def get_categories(db: AsyncSession) -> list[Category]:
    result = await db.execute(select(Category).where(Category.is_active == True))
    return result.scalars().all()


async def get_category_by_id(db: AsyncSession, category_id: int) -> Category | None:
    result = await db.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()


async def update_category(
    db: AsyncSession, category: Category, data: CategoryUpdate
) -> Category:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise DuplicateException("分类编码已存在")
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category: Category) -> None:
    category.is_active = False
    await db.commit()
