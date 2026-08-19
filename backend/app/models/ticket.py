from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_no: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="P2")
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=False
    )
    requester_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    assignee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="web")
    email_message_id: Mapped[str] = mapped_column(String(100), nullable=True)
    satisfaction: Mapped[str] = mapped_column(String(20), nullable=True)
    satisfaction_note: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    satisfaction_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    category: Mapped["Category"] = relationship("Category")
    requester: Mapped["User"] = relationship("User", foreign_keys=[requester_id])
    assignee: Mapped["User"] = relationship("User", foreign_keys=[assignee_id])
    replies: Mapped[list["TicketReply"]] = relationship("TicketReply", back_populates="ticket", cascade="all, delete-orphan")
    collaborations: Mapped[list["TicketCollaboration"]] = relationship("TicketCollaboration", back_populates="ticket", cascade="all, delete-orphan")
