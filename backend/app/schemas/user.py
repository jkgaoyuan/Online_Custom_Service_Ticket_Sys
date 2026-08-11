from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

from app.utils.security import check_password_strength


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="customer", pattern=r"^(customer|agent|supervisor|admin)$")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not check_password_strength(v):
            raise ValueError("密码长度至少 8 位，且需包含大写字母、小写字母、数字、特殊字符中的至少 2 种")
        return v


class UserCreateInternal(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(..., pattern=r"^(agent|supervisor|admin)$")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not check_password_strength(v):
            raise ValueError("密码长度至少 8 位，且需包含大写字母、小写字母、数字、特殊字符中的至少 2 种")
        return v


class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    username: str | None = Field(None, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr | None = Field(None, max_length=100)
    role: str | None = Field(None, pattern=r"^(customer|agent|supervisor|admin)$")
    is_active: bool | None = None


class UserListItem(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    ticket_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[UserListItem]


class UserStats(BaseModel):
    total_tickets: int
    resolved_tickets: int
    open_tickets: int
    avg_first_resp_minutes: float | None = None


class UserDetailResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    stats: UserStats | None = None

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
