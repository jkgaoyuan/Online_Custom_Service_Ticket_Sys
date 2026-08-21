from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.user import User


class AgentSkill(Base):
    __tablename__ = "agent_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=False
    )
    proficiency: Mapped[int] = mapped_column(Integer, default=3)  # 1-5

    __table_args__ = (
        UniqueConstraint("agent_id", "category_id", name="uq_agent_category"),
    )

    agent: Mapped[User] = relationship(
        "User", back_populates="skills", lazy="selectin"
    )
    category: Mapped[Category] = relationship(
        "Category", back_populates="agent_skills", lazy="selectin"
    )
