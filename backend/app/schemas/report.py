from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OverviewResponse(BaseModel):
    total_tickets: int
    today_new: int
    week_new: int
    month_new: int
    status_distribution: dict[str, int]
    sla_compliance_rate: float
    avg_satisfaction: float


class AgentPerformanceResponse(BaseModel):
    agent_id: int
    agent_name: str
    total_assigned: int
    resolved_count: int
    avg_first_resp_hours: float
    avg_resolution_hours: float


class CategoryDistributionResponse(BaseModel):
    category_id: int
    category_name: str
    count: int
    percentage: float


class TrendResponse(BaseModel):
    bucket: str
    created: int
    resolved: int


class SatisfactionResponse(BaseModel):
    distribution: dict[str, int]
    avg_score: float
    participation_rate: float
    total_rated: int
    total_in_range: int


class ExportRequest(BaseModel):
    report_type: Literal[
        "overview",
        "agent_performance",
        "category_distribution",
        "trend",
        "satisfaction",
    ]
    format: Literal["xlsx", "csv"] = "xlsx"
    start_date: date | None = None
    end_date: date | None = None
    filters: dict = Field(default_factory=dict)
