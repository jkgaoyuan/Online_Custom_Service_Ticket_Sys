from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.agent_skill import AgentSkill


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    default_priority: Mapped[str] = mapped_column(
        String(10), nullable=False, default="P2"
    )
    sla_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    agent_skills: Mapped[list[AgentSkill]] = relationship(
        "AgentSkill", back_populates="category", lazy="selectin"
    )
