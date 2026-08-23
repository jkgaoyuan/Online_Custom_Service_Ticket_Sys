from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.exceptions import NotFoundException, PermissionDeniedException
from app.models.collaboration import TicketCollaboration
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.collaboration import CollaborationResponse
from app.schemas.sla import SLASummary
from app.schemas.ticket import (
    AssignRequest,
    SatisfactionSubmit,
    StatusUpdateRequest,
    TicketCreate,
    TicketDetailResponse,
    TicketResponse,
    TicketUpdate,
)
from app.schemas.ticket_reply import ReplyCreate, ReplyResponse
from app.schemas.user import UserResponse
from app.services.ticket_service import (
    create_ticket,
    get_ticket_by_id,
    get_tickets_query,
    submit_satisfaction,
    transition_ticket_status,
    update_ticket,
)
from app.services.reply_service import create_reply, get_replies_by_ticket
from app.services.dispatch_service import auto_assign, log_manual_assign
from app.services.sla_service import get_sla_record_by_ticket_id
from app.services.auth_service import list_active_users
from app.services.collaboration_service import get_collaborations
from app.core.sse import send_event

router = APIRouter()


async def check_ticket_access(db: AsyncSession, ticket: Ticket, current_user: User) -> None:
    if current_user.role == "customer" and ticket.requester_id != current_user.id:
        raise PermissionDeniedException("无权访问该工单")
    if current_user.role in ("supervisor", "admin"):
        return
    if current_user.role == "agent":
        if ticket.assignee_id == current_user.id or ticket.status == "open":
            return
        # 允许 agent 查看待认领的 in_progress 工单（无 assignee）
        if ticket.status == "in_progress" and ticket.assignee_id is None:
            return
        result = await db.execute(
            select(TicketCollaboration).where(
                TicketCollaboration.ticket_id == ticket.id,
                TicketCollaboration.to_user_id == current_user.id,
            )
        )
        if result.scalar_one_or_none():
            return
        result = await db.execute(
            select(TicketCollaboration).where(
                TicketCollaboration.ticket_id == ticket.id,
                TicketCollaboration.from_user_id == current_user.id,
                TicketCollaboration.type == "transfer",
            )
        )
        if result.scalar_one_or_none():
            return
        raise PermissionDeniedException("无权访问该工单")


@router.get("/agents", response_model=list[dict])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "supervisor", "admin")),
):
    users = await list_active_users(db, role="agent")
    return [{"id": user.id, "username": user.username} for user in users]


@router.get("/agent/stats", response_model=dict)
async def get_agent_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "supervisor", "admin")),
):
    # 当前实时状态统计
    result = await db.execute(
        select(Ticket.status, func.count(Ticket.id))
        .where(Ticket.assignee_id == current_user.id)
        .group_by(Ticket.status)
    )
    counts = {row[0]: row[1] for row in result.all()}

    # 今日已解决：今日 resolved 或 closed 的工单
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_result = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.assignee_id == current_user.id,
            Ticket.status.in_(["resolved", "closed"]),
            Ticket.resolved_at >= today_start,
        )
    )
    today_resolved = resolved_result.scalar() or 0

    return {
        "open": counts.get("open", 0),
        "in_progress": counts.get("in_progress", 0),
        "resolved": today_resolved,
        "waiting": counts.get("waiting", 0),
    }


@router.post(
    "/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED
)
async def create_ticket_endpoint(
    data: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await create_ticket(db, data, current_user.id)
    if data.auto_dispatch and ticket.assignee_id is None:
        await auto_assign(db, ticket)
        await db.commit()
        await db.refresh(ticket)
    if ticket.assignee_id is not None:
        await send_event(ticket.assignee_id, "ticket_assigned", {
            "ticket_id": ticket.id,
            "ticket_no": ticket.ticket_no,
            "title": ticket.title,
            "priority": ticket.priority,
            "status": ticket.status,
        })
        await send_event(ticket.assignee_id, "stats_update", {})
    return ticket


@router.get("/tickets", response_model=dict)
async def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    category_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await get_tickets_query(
        db, current_user, status, priority, category_id, page, page_size
    )
    # Serialize items and inject requester info for list view
    items = []
    for ticket in result["items"]:
        data = TicketResponse.model_validate(ticket).model_dump()
        if ticket.requester:
            data["requester"] = UserResponse.model_validate(ticket.requester).model_dump()
        items.append(data)
    return {
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "items": items,
    }


@router.get("/tickets/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(
            selectinload(Ticket.requester),
            selectinload(Ticket.collaborations).selectinload(TicketCollaboration.from_user),
            selectinload(Ticket.collaborations).selectinload(TicketCollaboration.to_user),
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(db, ticket, current_user)

    sla = await get_sla_record_by_ticket_id(db, ticket_id)
    response = TicketDetailResponse.model_validate(ticket)
    if sla:
        response.sla = SLASummary.model_validate(sla)
    return response


@router.post("/tickets/{ticket_id}/replies", response_model=ReplyResponse, status_code=status.HTTP_201_CREATED)
async def reply_ticket(
    ticket_id: int,
    data: ReplyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(db, ticket, current_user)
    is_agent_reply = current_user.role in ("agent", "supervisor", "admin") and not data.is_internal
    if is_agent_reply and ticket.status == "open":
        ticket.status = "in_progress"
        ticket.assignee_id = current_user.id
    elif not is_agent_reply and ticket.status == "waiting":
        # 客户回复 waiting 工单，自动恢复为处理中
        ticket.status = "in_progress"
    reply = await create_reply(db, ticket, data, current_user.id, is_agent_reply=is_agent_reply)
    # 状态变更后需要显式提交
    await db.commit()
    await db.refresh(ticket)
    # 如果工单有 assignee_id，发送 stats_update SSE 事件
    if ticket.assignee_id is not None:
        await send_event(ticket.assignee_id, "stats_update", {})
    return reply


@router.get("/tickets/{ticket_id}/replies", response_model=list[ReplyResponse])
async def list_replies(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(db, ticket, current_user)
    include_internal = current_user.role in ("agent", "supervisor", "admin")
    return await get_replies_by_ticket(db, ticket_id, include_internal)


@router.post("/tickets/{ticket_id}/status", response_model=TicketResponse)
async def update_ticket_status(
    ticket_id: int,
    req: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(db, ticket, current_user)
    if current_user.role not in ("agent", "supervisor", "admin"):
        raise PermissionDeniedException("无权修改工单状态")
    ticket = await transition_ticket_status(db, ticket, req.status)
    if ticket.assignee_id is not None:
        await send_event(ticket.assignee_id, "stats_update", {})
    return ticket


@router.post("/tickets/{ticket_id}/assign", response_model=TicketResponse)
async def assign_ticket(
    ticket_id: int,
    req: AssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "supervisor", "admin")),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(db, ticket, current_user)
    ticket.assignee_id = req.assignee_id
    if ticket.status == "open":
        ticket.status = "in_progress"
    # 记录手动分派日志
    await log_manual_assign(db, ticket.id, req.assignee_id, f"手动分派 by user {current_user.id}")
    await db.commit()
    await db.refresh(ticket)
    await send_event(req.assignee_id, "ticket_assigned", {
        "ticket_id": ticket.id,
        "ticket_no": ticket.ticket_no,
        "title": ticket.title,
        "priority": ticket.priority,
        "status": ticket.status,
    })
    await send_event(req.assignee_id, "stats_update", {})
    return ticket


@router.post("/tickets/{ticket_id}/satisfaction", response_model=TicketResponse)
async def submit_satisfaction_endpoint(
    ticket_id: int,
    data: SatisfactionSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(db, ticket, current_user)
    ticket = await submit_satisfaction(
        db, ticket, current_user.id, data.rating, data.note
    )
    return ticket
