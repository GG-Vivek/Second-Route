"""
Structured logging configuration using structlog.

Provides JSON-formatted logs with consistent fields.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

from secondroute.core.config import settings


def add_app_context(logger: WrappedLogger, name: str, event_dict: EventDict) -> EventDict:
    """Add application context to all log entries."""
    event_dict["app"] = settings.APP_NAME
    event_dict["version"] = settings.APP_VERSION
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def add_request_id(logger: WrappedLogger, name: str, event_dict: EventDict) -> EventDict:
    """Add request ID if available in context."""
    # Request ID would be added by middleware
    return event_dict


def drop_color_message_key(logger: WrappedLogger, name: str, event_dict: EventDict) -> EventDict:
    """Remove color_message key added by structlog.dev."""
    event_dict.pop("color_message", None)
    return event_dict


def setup_logging() -> None:
    """Configure structlog for the application."""

    # Standard library logging setup
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # Configure structlog
    from structlog.types import Processor

    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        add_app_context,
        add_request_id,
        drop_color_message_key,
    ]

    if settings.DEBUG:
        # Pretty console output for development
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        # JSON output for production
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]


class LoggerMixin:
    """Mixin to add structured logging to any class."""

    @property
    def logger(self) -> structlog.BoundLogger:
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__module__ + "." + self.__class__.__name__)
        return self._logger


# Context variable for request ID
import contextvars

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def set_request_id(request_id: str) -> None:
    """Set request ID in context variable."""
    request_id_var.set(request_id)


def get_request_id() -> str:
    """Get request ID from context variable."""
    return request_id_var.get()


def bind_request_context(**kwargs: Any) -> None:
    """Bind additional context to current structlog context."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_request_context() -> None:
    """Clear all context variables."""
    structlog.contextvars.clear_contextvars()
