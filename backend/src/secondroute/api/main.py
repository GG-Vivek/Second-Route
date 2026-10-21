"""
SecondRoute API Application.

Main FastAPI application with all routes, middleware, and lifecycle events.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import ProgrammingError

from secondroute.core.config import settings
from secondroute.core.db import close_db, init_db, set_current_org_id
from secondroute.feedback.audit import setup_audit_listeners
from secondroute.core.logging import (
    bind_request_context,
    clear_request_context,
    get_logger,
    get_request_id,
    set_request_id,
    setup_logging,
)

# Setup logging early
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info(
        "application_startup", version=settings.APP_VERSION, environment=settings.ENVIRONMENT
    )

    # The audit listeners have to be attached to the session here, once
    # every model is loaded. Without this the application records no
    # audit rows at all: the listeners are only wired up by the test
    # suite, so the audit log is empty in a running deployment.
    #
    # They are attached before the database rather than after it, because
    # they need the models loaded and not a working database: a database
    # that is briefly unavailable must not leave the audit log off.
    setup_audit_listeners()
    logger.info("audit_listeners_ready")

    await init_db()
    logger.info("database_initialized")

    yield

    # Shutdown
    logger.info("application_shutdown")
    await close_db()
    logger.info("database_closed")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SecondRoute - Decision engine for returned electronics",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)


def _mount_uploads(application: FastAPI) -> None:
    """Serve the photographs.

    A photo record carries the path the photograph is at, and nothing
    else ever served it, so a unit could list its photographs and never
    show one. The upload directory is served as it is.

    A machine that cannot create the directory is not a machine that can
    take photographs, so the application carries on without the mount and
    says so.
    """
    try:
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        application.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")
        logger.info("uploads_mounted", path=str(upload_dir))
    except OSError as exc:
        logger.warning("uploads_not_mounted", path=settings.UPLOAD_DIR, error=str(exc))


_mount_uploads(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next: Any) -> Any:
    """Add request ID to all requests for tracing."""
    import uuid

    request_id = request.headers.get("X-Request-ID", "")
    if not request_id:
        request_id = str(uuid.uuid4())

    set_request_id(request_id)
    bind_request_context(request_id=request_id, path=request.url.path, method=request.method)

    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        clear_request_context()


# The organisation context.
#
# Every request acts for one organisation, and both the application
# filter and the database's row-level security policies read that
# organisation. The authentication dependency sets it from the verified
# token when there is one.
#
# Without a token there is no tenant, and a write to a tenant-scoped
# table is refused by the policies - which is the right answer for a
# request that names no tenant, and the wrong answer for a developer who
# is trying the application out. So outside production the tenant can
# also be named with a header.
#
# This is a development affordance and nothing else. In production the
# header is ignored, so a caller cannot choose a tenant: the only way in
# is a token.
DEV_ORG_HEADER = "X-Org-Id"


def _development_org_header_allowed() -> bool:
    """Whether the organisation may be named with a header.

    Returns:
        True outside production.
    """
    return settings.ENVIRONMENT.lower() not in ("production", "prod")


@app.middleware("http")
async def resolve_organisation(request: Request, call_next: Any) -> Any:
    """Establish which organisation the request acts for."""
    if _development_org_header_allowed():
        org_id = request.headers.get(DEV_ORG_HEADER, "").strip()
        if org_id:
            set_current_org_id(org_id)
    return await call_next(request)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions."""
    logger.exception(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        exc_type=type(exc).__name__,
        exc_message=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "request_id": get_request_id(),
        },
    )


@app.exception_handler(ProgrammingError)
async def row_level_security_handler(request: Request, exc: ProgrammingError) -> JSONResponse:
    """Turn a refused write into a legible answer.

    The row-level security policies refuse a write that names no
    organisation, or one that names the wrong one. That is the isolation
    working, and it deserves an answer that says so rather than a
    generic "something went wrong".
    """
    message = str(getattr(exc, "orig", exc))
    if "row-level security" not in message and "row level security" not in message:
        return await global_exception_handler(request, exc)

    logger.warning(
        "rls.refused",
        path=request.url.path,
        method=request.method,
        exc_message=message,
    )
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "tenant_not_resolved",
            "message": (
                "This request does not name a tenant. Log in, or - outside "
                f"production - send the {DEV_ORG_HEADER} header."
            ),
            "request_id": get_request_id(),
        },
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint.

    A dependency that is not configured is not a failure. The cache is used
    for the session store and for the background jobs, and a deployment that
    does not run either of them should not be reported as degraded for the
    want of a cache it never asked for.

    Returns:
        dict: Health status of the application and its dependencies.
    """
    from secondroute.core.db import check_db_connection

    # Check database
    db_healthy = await check_db_connection()

    # Check the cache, when there is one to check.
    redis_state = "not_configured"
    if str(settings.REDIS_URL or "").strip():
        redis_state = "failed"
        try:
            import redis.asyncio as redis

            redis_client = redis.from_url(str(settings.REDIS_URL))
            await redis_client.ping()
            await redis_client.close()
            redis_state = "ok"
        except Exception:
            redis_state = "failed"

    # Only a dependency that is configured and broken degrades the service.
    degraded = not db_healthy or redis_state == "failed"
    status = "degraded" if degraded else "healthy"

    return {
        "status": status,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": {
            "database": "ok" if db_healthy else "failed",
            "redis": redis_state,
        },
    }


# API version prefix
API_PREFIX = settings.API_PREFIX

# Include routers (to be added in later phases)
from secondroute.identity import identity_router
from secondroute.intake import intake_router
from secondroute.feedback import feedback_router
from secondroute.admin.api import router as admin_router
from secondroute.auth import auth_router
from secondroute.auth.api import org_router, user_router, org_user_router
from secondroute.backtest.api import router as backtest_router
from secondroute.costs.api import router as costs_router
from secondroute.decision.api import router as decision_router
from secondroute.feedback.overrides import router as overrides_router
from secondroute.feedback.outcomes import router as outcomes_router
from secondroute.ingest.api import component_router
from secondroute.ingest.api import router as ingest_router
from secondroute.analytics.api import router as analytics_router
from secondroute.analytics.export_api import router as export_router
# from secondroute.api import condition, admin

app.include_router(identity_router, prefix=API_PREFIX)
app.include_router(intake_router, prefix=API_PREFIX)
app.include_router(feedback_router, prefix=API_PREFIX)
app.include_router(overrides_router, prefix=API_PREFIX)
app.include_router(outcomes_router, prefix=API_PREFIX)
app.include_router(costs_router, prefix=API_PREFIX)
app.include_router(decision_router, prefix=API_PREFIX)
app.include_router(ingest_router, prefix=API_PREFIX)
app.include_router(component_router, prefix=API_PREFIX)
app.include_router(admin_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(org_router, prefix=API_PREFIX)
app.include_router(user_router, prefix=API_PREFIX)
app.include_router(org_user_router, prefix=API_PREFIX)
app.include_router(backtest_router, prefix=API_PREFIX)
app.include_router(analytics_router, prefix=API_PREFIX)
app.include_router(export_router, prefix=API_PREFIX)
# ...


@app.get("/", tags=["Root"])
async def root() -> dict:
    """Root endpoint with basic API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "disabled",
        "health": "/health",
        "api": API_PREFIX,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "secondroute.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_config=None,  # Use structlog instead
    )
