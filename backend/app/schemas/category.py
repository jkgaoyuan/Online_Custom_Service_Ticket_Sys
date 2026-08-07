from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str = Field(..., max_length=50)
    code: str = Field(..., max_length=30)
    description: Optional[str] = Field(None, max_length=255)
    default_priority: str = Field(default="P2", pattern="^(P0|P1|P2|P3)$")
    sla_config: dict = Field(
        default_factory=lambda: {"first_resp_hours": 4, "resolution_hours": 24}
    )
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    code: Optional[str] = Field(None, max_length=30)
    description: Optional[str] = Field(None, max_length=255)
    default_priority: Optional[str] = Field(None, pattern="^(P0|P1|P2|P3)$")
    sla_config: Optional[dict] = None
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
