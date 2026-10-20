"""
SecondRoute API Application.

Main FastAPI application with all routes, middleware, and lifecycle events.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from secondroute.core.config import settings
from secondroute.core.db import close_db, init_db
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


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        dict: Health status of the application and its dependencies.
    """
    import redis.asyncio as redis

    from secondroute.core.db import check_db_connection

    # Check database
    db_healthy = await check_db_connection()

    # Check Redis
    redis_healthy = False
    try:
        redis_client = redis.from_url(str(settings.REDIS_URL))
        await redis_client.ping()
        await redis_client.close()
        redis_healthy = True
    except Exception:
        pass

    status = "healthy" if db_healthy and redis_healthy else "degraded"

    return {
        "status": status,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": {
            "database": "ok" if db_healthy else "failed",
            "redis": "ok" if redis_healthy else "failed",
        },
    }


# API version prefix
API_PREFIX = settings.API_PREFIX

# Include routers (to be added in later phases)
from secondroute.identity import identity_router
from secondroute.intake import intake_router
from secondroute.feedback import feedback_router
from secondroute.feedback.overrides import router as overrides_router
from secondroute.costs.api import router as costs_router
from secondroute.decision.api import router as decision_router
from secondroute.backtest.api import router as backtest_router
# from secondroute.api import condition, analytics, admin

app.include_router(identity_router, prefix=API_PREFIX)
app.include_router(intake_router, prefix=API_PREFIX)
app.include_router(feedback_router, prefix=API_PREFIX)
app.include_router(overrides_router, prefix=API_PREFIX)
app.include_router(costs_router, prefix=API_PREFIX)
app.include_router(decision_router, prefix=API_PREFIX)
app.include_router(backtest_router, prefix=API_PREFIX)
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
