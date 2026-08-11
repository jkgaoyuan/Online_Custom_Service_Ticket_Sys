from datetime import datetime, timedelta

from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import DuplicateException
from app.models.user import User
from app.schemas.user import UserCreate, UserCreateInternal
from app.utils.security import get_password_hash, verify_password

settings = get_settings()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    user = await get_user_by_username(db, username)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


async def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(user_id), "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def register_user(db: AsyncSession, data: UserCreate) -> User:
    if await get_user_by_username(db, data.username):
        raise DuplicateException("用户名已存在")
    if await get_user_by_email(db, data.email):
        raise DuplicateException("邮箱已存在")

    user = User(
        username=data.username,
        email=data.email,
        password_hash=get_password_hash(data.password),
        role=data.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_user_by_admin(db: AsyncSession, data: UserCreateInternal) -> User:
    if await get_user_by_username(db, data.username):
        raise DuplicateException("用户名已存在")
    if await get_user_by_email(db, data.email):
        raise DuplicateException("邮箱已存在")

    user = User(
        username=data.username,
        email=data.email,
        password_hash=get_password_hash(data.password),
        role=data.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def list_active_users(db: AsyncSession, role: str | None = None) -> list[User]:
    stmt = select(User).where(User.is_active.is_(True))
    if role:
        stmt = stmt.where(User.role == role)
    result = await db.execute(stmt.order_by(User.username))
    return result.scalars().all()


async def create_default_admin(db: AsyncSession) -> None:
    admin = await get_user_by_username(db, "admin")
    if admin is None:
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=get_password_hash("admin123"),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        await db.commit()
