"""
SecondRoute Core Package

Core infrastructure: config, database, logging, authentication.
"""

from secondroute.core.config import Settings, get_settings, settings
from secondroute.core.db import (
    Base,
    async_session_factory,
    close_db,
    engine,
    get_session,
    get_session_context,
    init_db,
)
from secondroute.core.logging import (
    LoggerMixin,
    bind_request_context,
    clear_request_context,
    get_logger,
    get_request_id,
    set_request_id,
    setup_logging,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    "settings",
    # Database
    "Base",
    "engine",
    "async_session_factory",
    "get_session",
    "get_session_context",
    "init_db",
    "close_db",
    # Logging
    "setup_logging",
    "get_logger",
    "LoggerMixin",
    "bind_request_context",
    "clear_request_context",
    "set_request_id",
    "get_request_id",
]
