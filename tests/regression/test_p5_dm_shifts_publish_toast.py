"""Red-team P5-DM-2 followup — Publish Week silent-success.

Origin: 2026-05-19 P5-DU pilot. Clicking "Publish Week" on /shifts
created a `ShiftPublish` row on the backend (verified: rows id=1 + id=2
landed in prod), but the UI gave no feedback — no toast, no state
indicator. From the user's perspective the click silently did nothing,
so the next instinct was to click again, creating duplicate audit
rows.

This file pins the structural fix: `handlePublish` calls
`toast.success(...)` on the happy path and `toast.error(...)` on the
error path, and the button is disabled mid-flight so rapid double-
clicks don't fire twice.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIFTS_PAGE = (
    REPO_ROOT / "apps/web/src/app/(dashboard)/shifts/page.tsx"
)


@pytest.mark.regression
def test_p5dm_shifts_publish_imports_toast():
    """The shifts page must import toast from the design system so the
    publish handler can surface success/error explicitly."""
    src = SHIFTS_PAGE.read_text()
    assert 'import { toast } from "@/components/design-system"' in src


@pytest.mark.regression
def test_p5dm_shifts_publish_handler_emits_success_toast():
    """`handlePublish` must call `toast.success(...)` after a
    successful publishSchedule call. Without this the user sees no
    indication their click did anything."""
    src = SHIFTS_PAGE.read_text()
    section = src[src.index("const handlePublish") :]
    # End at the next `const ` declaration to keep the slice tight.
    section = section[: section.index("const handleDeleteAssignment")]
    assert "toast.success(" in section
    assert 'published' in section.lower()


@pytest.mark.regression
def test_p5dm_shifts_publish_handler_emits_error_toast():
    """On failure the handler must also surface the error visibly —
    not just set the inline `setError` state which the user can miss."""
    src = SHIFTS_PAGE.read_text()
    section = src[src.index("const handlePublish") :]
    section = section[: section.index("const handleDeleteAssignment")]
    assert "toast.error(" in section


@pytest.mark.regression
def test_p5dm_shifts_publish_handler_dedupes_double_click():
    """Rapid double-click must not fire publishSchedule twice (would
    create duplicate ShiftPublish audit rows). Pinned via the
    `isPublishing` guard + the button's `disabled` prop."""
    src = SHIFTS_PAGE.read_text()
    assert "isPublishing" in src
    # Guard at the top of handlePublish
    section = src[src.index("const handlePublish") :]
    section = section[: section.index("const handleDeleteAssignment")]
    assert "if (isPublishing) return" in section
    # Button disables mid-flight
    assert "disabled={isPublishing}" in src
    # And the label switches to communicate progress.
    assert 'isPublishing ? "Publishing' in src
