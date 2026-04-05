# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Shared CRUD helpers using DataFlow Express API.

All single-record database operations should use these functions instead of
constructing WorkflowBuilder + LocalRuntime per call. db.express_sync is ~23x
faster for single-record CRUD (see rules/patterns.md).

For multi-step workflows (sagas, bulk operations, conditional branching),
use WorkflowBuilder directly — that's what it's designed for.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_db():
    """Lazy import to avoid circular imports at module load time."""
    from hr_advisory.models.database import db
    import hr_advisory.models  # noqa: F401 — ensure models are registered

    return db


def create(model_name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Create a single record via db.express_sync."""
    db = _get_db()
    return db.express_sync.create(model_name, data)


def read(model_name: str, record_id: int | str) -> dict[str, Any] | None:
    """Read a single record by ID via db.express_sync.

    Returns None if the record is not found or has an error.
    """
    db = _get_db()
    result = db.express_sync.read(model_name, str(record_id))
    if not result or result.get("error") or result.get("failed"):
        return None
    return result


def list_records(
    model_name: str,
    filter_dict: dict[str, Any] | None = None,
    limit: int = 10000,
) -> list[dict[str, Any]]:
    """List records with optional filter via db.express_sync."""
    db = _get_db()
    result = db.express_sync.list(model_name, filter_dict or {}, limit=limit)
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and "records" in result:
        return result["records"]
    return []


def update(
    model_name: str,
    record_id: int | str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Update a single record by ID via db.express_sync."""
    db = _get_db()
    return db.express_sync.update(model_name, str(record_id), updates)


def delete(model_name: str, record_id: int | str) -> dict[str, Any] | bool:
    """Delete a single record by ID via db.express_sync."""
    db = _get_db()
    return db.express_sync.delete(model_name, str(record_id))


def count(model_name: str, filter_dict: dict[str, Any] | None = None) -> int:
    """Count records matching filter via db.express_sync."""
    db = _get_db()
    return db.express_sync.count(model_name, filter_dict or {})
