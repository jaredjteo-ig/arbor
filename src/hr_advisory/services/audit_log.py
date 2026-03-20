# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Audit logging for sensitive operations (PDPA compliance).

Emits structured log events for security-relevant actions.  These logs
are designed to be forwarded to a SIEM or audit store for compliance.

All audit events include: action, actor (user_id), target (entity_id),
timestamp, and additional metadata.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("hr_advisory.audit")

__all__ = ["log_audit_event", "AuditAction"]


class AuditAction:
    """Constants for audit event actions."""

    # LLM key lifecycle
    LLM_KEY_CREATED = "llm_key.created"
    LLM_KEY_VIEWED = "llm_key.viewed"
    LLM_KEY_DELETED = "llm_key.deleted"
    LLM_KEY_VALIDATED = "llm_key.validated"
    LLM_KEY_STATUS_CHANGED = "llm_key.status_changed"
    LLM_KEY_DECRYPTED = "llm_key.decrypted"
    LLM_KEY_ROTATED = "llm_key.rotated"

    # Budget
    LLM_BUDGET_CHANGED = "llm_budget.changed"
    LLM_BUDGET_EXCEEDED = "llm_budget.exceeded"

    # User key lifecycle
    USER_LLM_KEY_CREATED = "user_llm_key.created"
    USER_LLM_KEY_DELETED = "user_llm_key.deleted"


def log_audit_event(
    action: str,
    actor_user_id: int | None = None,
    company_id: int | None = None,
    target_entity: str | None = None,
    target_id: int | str | None = None,
    details: dict | None = None,
) -> None:
    """Log an audit event for PDPA compliance.

    Args:
        action: The action performed (use AuditAction constants).
        actor_user_id: The user who performed the action.
        company_id: The company context.
        target_entity: The type of entity acted upon (e.g. "CompanyLLMConfig").
        target_id: The ID of the entity acted upon.
        details: Additional metadata (provider, status change, etc).
    """
    event = {
        "action": action,
        "actor_user_id": actor_user_id,
        "company_id": company_id,
        "target_entity": target_entity,
        "target_id": target_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if details:
        event["details"] = details

    # Use WARNING level so audit events are always captured even at INFO log level
    logger.warning(
        "audit.event action=%s actor=%s company=%s entity=%s id=%s details=%s",
        action,
        actor_user_id,
        company_id,
        target_entity,
        target_id,
        details or {},
    )
