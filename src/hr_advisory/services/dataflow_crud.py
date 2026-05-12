"""Shared CRUD helpers using DataFlow Express API.

All single-record database operations should use these functions instead of
constructing WorkflowBuilder + LocalRuntime per call. db.express_sync is ~23x
faster for single-record CRUD.

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


def _coerce_id(record_id: int | str) -> int | str:
    """Coerce ID to int if it looks numeric. PostgreSQL requires int for integer PKs."""
    if isinstance(record_id, int):
        return record_id
    if isinstance(record_id, str) and record_id.isdigit():
        return int(record_id)
    return record_id


def read(model_name: str, record_id: int | str) -> dict[str, Any] | None:
    """Read a single record by ID via db.express_sync.

    Returns None if the record is not found or has an error.

    Fallback: some DataFlow models (observed: PayrollRun) intermittently
    return None from express_sync.read while express_sync.list with the same
    id filter succeeds. When read fails we retry once via list — same row,
    same shape, just routed through the list node.
    """
    db = _get_db()
    coerced_id = _coerce_id(record_id)
    result = db.express_sync.read(model_name, coerced_id)
    if result and not result.get("error") and not result.get("failed"):
        return result
    rows = db.express_sync.list(model_name, filter={"id": coerced_id})
    if rows and isinstance(rows, list) and len(rows) > 0:
        return rows[0]
    return None


def list_records(
    model_name: str,
    filter_dict: dict[str, Any] | None = None,
    limit: int = 1000,
    cache_ttl: int | None = None,
) -> list[dict[str, Any]]:
    """List records with optional filter.

    Args:
        cache_ttl: Cache TTL in seconds. Pass 0 to bypass DataFlow's
            cache + node-level caches by reading directly from
            PostgreSQL via psycopg2.

    NOTE: DataFlow's express list and underlying List node have
    persistent caching issues that return stale results even when
    cache_ttl=0 is requested (Redis cache + node-level query cache
    both hold stale data after intervening writes). To guarantee
    fresh reads in correctness-critical paths (e.g. /my-pending,
    aggregator), use cache_ttl=0 — this dispatches via direct SQL,
    skipping DataFlow's caching layers entirely.
    """
    if cache_ttl == 0:
        return _list_records_direct_sql(model_name, filter_dict or {}, limit)

    db = _get_db()
    kwargs: dict[str, Any] = {"limit": limit}
    if cache_ttl is not None:
        kwargs["cache_ttl"] = cache_ttl
    result = db.express_sync.list(model_name, filter_dict or {}, **kwargs)
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and "records" in result:
        return result["records"]
    return []


_TABLE_NAME_OVERRIDES: dict[str, str] = {
    # Models whose conventional snake_case + 's' form doesn't match.
    # Add here as needed.
}

# B1 (red-team): every SQL identifier (table or column name) MUST match
# this regex before f-string interpolation. Per
# `.claude/rules/infrastructure-sql.md` Rule 1.
import re as _re

_SQL_IDENTIFIER_RE = _re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")


def _validate_sql_identifier(name: str) -> str:
    """Reject anything that's not a safe SQL identifier.

    Used by `_list_records_direct_sql` for table + column names that
    must be interpolated (parameterised SQL only handles values, not
    identifiers).

    Raises ValueError on bad input. The 63-char cap matches PostgreSQL's
    `NAMEDATALEN - 1` limit; longer names would be silently truncated
    by the server, hiding bugs.
    """
    if not isinstance(name, str) or not _SQL_IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name


def _model_to_table(model_name: str) -> str:
    """Convert a CamelCase model name to its snake_case plural table name.

    Handles the conventional DataFlow-generated mapping:
      User                          -> users
      EmploymentEvent               -> employment_events
      EngagementSurveyResponse      -> engagement_survey_responses
      Company                       -> companies
    """
    if model_name in _TABLE_NAME_OVERRIDES:
        return _TABLE_NAME_OVERRIDES[model_name]
    # Convert CamelCase to snake_case
    out = []
    for i, ch in enumerate(model_name):
        if ch.isupper() and i > 0:
            out.append("_")
        out.append(ch.lower())
    base = "".join(out)
    # Pluralise — DataFlow uses simple s / ies / es rules.
    if base.endswith("y") and not base.endswith(("ay", "ey", "iy", "oy", "uy")):
        return base[:-1] + "ies"
    if base.endswith(("s", "x", "ch", "sh")):
        return base + "es"
    return base + "s"


def _list_records_direct_sql(
    model_name: str,
    filter_dict: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    """Run a direct SELECT via psycopg2 — bypasses DataFlow caching.

    Used when correctness > performance. Returns rows as dicts shaped
    like DataFlow's express list output.
    """
    import os
    import psycopg2
    import psycopg2.extras

    # B1 (red-team): validate every SQL identifier before f-string
    # interpolation. Today every caller passes literal class names like
    # "EngagementSurveyResponse" + literal column-name keys, but a
    # future caller could leak user input here — keep the guard tight.
    # ValueError from validation MUST escape — silent-empty would mask
    # the bug per rules/no-stubs.md Rule 3.
    table = _validate_sql_identifier(_model_to_table(model_name))
    if filter_dict:
        for k in filter_dict.keys():
            _validate_sql_identifier(k)  # column name guard

    conn = None
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        sql = f"SELECT * FROM {table}"
        params: list[Any] = []
        if filter_dict:
            clauses = []
            for k, v in filter_dict.items():
                if v is None:
                    clauses.append(f"{k} IS NULL")
                else:
                    clauses.append(f"{k} = %s")
                    params.append(v)
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
        # int() coercion below is the value guard for limit; the SQL
        # string itself is built from a validated integer literal.
        sql += f" LIMIT {int(limit)}"
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        # Convert datetime fields to ISO strings to match DataFlow's
        # stringly-typed return shape (callers compare against strings).
        from datetime import date, datetime as _dt
        for row in rows:
            for k, v in list(row.items()):
                if isinstance(v, _dt):
                    row[k] = v.isoformat()
                elif isinstance(v, date):
                    row[k] = v.isoformat()
        cur.close()
        return rows
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "list_records_direct_sql_failed",
            extra={
                "model": model_name,
                "table": table,
                "filter": filter_dict,
                "error": str(exc),
            },
        )
        return []
    finally:
        if conn is not None:
            conn.close()


def update(
    model_name: str,
    record_id: int | str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Update a single record by ID via db.express_sync."""
    db = _get_db()
    return db.express_sync.update(model_name, _coerce_id(record_id), updates)


def delete(model_name: str, record_id: int | str) -> dict[str, Any]:
    """Delete a single record by ID via db.express_sync."""
    db = _get_db()
    return db.express_sync.delete(model_name, _coerce_id(record_id))


def count(
    model_name: str,
    filter_dict: dict[str, Any] | None = None,
) -> int:
    """Count records matching a filter.

    express_sync doesn't have a native count, so we fetch all matching
    records and return len(). Single query — no double-fetch.
    """
    all_records = list_records(model_name, filter_dict)
    return len(all_records)
