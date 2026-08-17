from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.exceptions import (
    DuplicateException,
    NotFoundException,
    PermissionDeniedException,
    TicketSystemException,
)
from app.routers import admin, auth, categories, dispatch, notifications, reports, sla, tickets, webhooks
import logging

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建默认管理员和邮件默认分类
    from app.services.auth_service import create_default_admin
    from app.services.email_service import ensure_default_email_category

    async with AsyncSessionLocal() as db:
        try:
            await create_default_admin(db)
        except Exception as exc:
            logger.warning("create_default_admin failed: %s", exc)
            await db.rollback()

        try:
            await ensure_default_email_category(db)
        except Exception as exc:
            logger.warning("ensure_default_email_category failed: %s", exc)
            await db.rollback()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


@app.exception_handler(TicketSystemException)
async def ticket_system_exception_handler(request: Request, exc: TicketSystemException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(notifications.router, prefix="/api/v1", tags=["Notifications"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(categories.router, prefix="/api/v1", tags=["Categories"])
app.include_router(tickets.router, prefix="/api/v1", tags=["Tickets"])
app.include_router(sla.router, prefix="/api/v1", tags=["SLA"])
app.include_router(dispatch.router, prefix="/api/v1", tags=["Dispatch"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])
app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])
app.include_router(admin.router, prefix="/api/v1", tags=["Admin"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
