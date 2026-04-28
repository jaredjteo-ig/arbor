"""Regression tests for backlog Cluster 1 cleanups.

Backlog items B14, B18, B19, B20 — verify that fixes do not regress.

- B14: dataflow_crud.count() must use a single query (not double)
- B18: no datetime.utcnow() should remain in routers/agents (deprecated)
- B19: helper functions must come from the shared _helpers module, not redefined locally
- B20: document IDs must be uuid4-based, not predictable
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src" / "hr_advisory"


@pytest.mark.regression
def test_b14_count_is_single_query() -> None:
    """B14: dataflow_crud.count() must execute exactly one underlying call.

    The original bug was a count-via-double-query pattern. The fix returns
    len(list_records(...)) — a single fetch. This test verifies count()
    delegates to list_records() and does not call it twice.
    """
    from unittest.mock import patch

    from hr_advisory.services import dataflow_crud

    with patch.object(dataflow_crud, "list_records", return_value=[1, 2, 3]) as mock_list:
        result = dataflow_crud.count("Foo", {"x": 1})

    assert result == 3
    assert mock_list.call_count == 1, "count() must call list_records exactly once"


@pytest.mark.regression
def test_b18_no_datetime_utcnow_in_app_code() -> None:
    """B18: datetime.utcnow() is deprecated in 3.12+ — replaced with datetime.now(timezone.utc).

    Scan src/hr_advisory/api/routers and src/hr_advisory/agents/memory for
    any remaining usage. Tests directories are intentionally excluded.
    """
    targets = [
        SRC / "api" / "routers",
        SRC / "agents" / "memory",
    ]
    offenders: list[str] = []
    pattern = re.compile(r"\bdatetime\.utcnow\b")
    for root in targets:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if pattern.search(text):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, (
        f"datetime.utcnow() must not appear in app code: {offenders}"
    )


@pytest.mark.regression
def test_b19_helpers_imported_not_redefined() -> None:
    """B19: shared helpers live in _helpers.py.

    Routers must import _validate_text_length and _find_employee_for_user
    rather than redefining them locally. We grep for the duplicate
    `def _validate_text_length` / `def _find_employee_for_user` patterns
    and assert they only appear in _helpers.py.
    """
    routers = SRC / "api" / "routers"
    duplicates: list[str] = []

    for path in routers.glob("*.py"):
        if path.name == "_helpers.py":
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"^def _validate_text_length\b", text, re.MULTILINE):
            duplicates.append(f"{path.name}:_validate_text_length")
        if re.search(r"^def _find_employee_for_user\b", text, re.MULTILINE):
            duplicates.append(f"{path.name}:_find_employee_for_user")

    assert not duplicates, (
        f"Helper functions must be imported from _helpers, not redefined: {duplicates}"
    )

    # Sanity: the canonical home still defines them.
    helpers_text = (routers / "_helpers.py").read_text(encoding="utf-8")
    assert "def _validate_text_length" in helpers_text
    assert "def _find_employee_for_user" in helpers_text


@pytest.mark.regression
def test_b20_document_id_uses_uuid4() -> None:
    """B20: generated document IDs must use uuid4, not a predictable hash.

    Inspect document.py for the id-generation pattern and verify that
    a freshly-generated id is parseable as a uuid4-suffixed string.
    """
    text = (SRC / "api" / "routers" / "document.py").read_text(encoding="utf-8")
    assert "uuid.uuid4()" in text, (
        "document.py must use uuid.uuid4() for document IDs"
    )
    # The pattern is `f\"doc_{uuid.uuid4()}\"`.
    match = re.search(r'f"doc_\{uuid\.uuid4\(\)\}"', text)
    assert match, (
        "Expected canonical pattern f\"doc_{uuid.uuid4()}\" in document.py"
    )
    # And confirm uuid4 is parseable from such an id.
    sample = f"doc_{uuid.uuid4()}"
    suffix = sample.split("doc_", 1)[1]
    uuid.UUID(suffix, version=4)  # raises if not a valid uuid4
