from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EmailIngestion(Base):
    __tablename__ = "email_ingestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sender_email: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    sender_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    message_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    in_reply_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    created_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    ticket_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tickets.id"), nullable=True
    )

    created_user: Mapped["User"] = relationship("User")
    ticket: Mapped["Ticket"] = relationship("Ticket")
