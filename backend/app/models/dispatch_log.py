from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DispatchLog(Base):
    __tablename__ = "dispatch_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id"), nullable=False)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    dispatch_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "auto", "manual", "suggest"
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
