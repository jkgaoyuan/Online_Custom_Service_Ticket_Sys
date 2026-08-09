from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SLARecord(Base):
    __tablename__ = "sla_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    first_resp_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    first_resp_due: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolution_due: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    first_resp_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_resp_breached: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_breached: Mapped[bool] = mapped_column(Boolean, default=False)

    first_resp_warned_agent_3h: Mapped[bool] = mapped_column(Boolean, default=False)
    first_resp_warned_agent_2h: Mapped[bool] = mapped_column(Boolean, default=False)
    first_resp_warned_supervisor_1h: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_warned_agent_3h: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_warned_agent_2h: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_warned_supervisor_1h: Mapped[bool] = mapped_column(Boolean, default=False)

    ticket: Mapped["Ticket"] = relationship("Ticket")
