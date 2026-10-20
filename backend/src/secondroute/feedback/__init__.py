"""
Feedback module for Phase 1.

Provides audit log and outcome tracking functionality.
"""

from secondroute.feedback.api import router as feedback_router
from secondroute.feedback.audit import setup_audit_listeners
from secondroute.feedback.models import AuditLog, AuditAction, Override

# Note: Audit listeners are NOT initialized at import time.
# Call setup_audit_listeners() explicitly after all models are loaded and database is ready.
# This is typically done in the application startup (main.py lifespan).

__all__ = [
    "feedback_router",
    "AuditLog",
    "AuditAction",
    "setup_audit_listeners",
]
