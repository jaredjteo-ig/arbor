# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Shadow Agent entity resolver.

Covers: entity name mapping, relative date resolution, missing required param detection.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

_kaizen_mods = [
    "kaizen",
    "kaizen.core",
    "kaizen.core.base_agent",
    "kaizen.memory",
    "kaizen.config",
    "kaizen.config.providers",
    "kaizen.signatures",
    "kaizen.core.workflow_generator",
    "kaizen.nodes",
    "kaizen.nodes.ai",
    "kaizen.nodes.ai.llm_agent",
]
for _m in _kaizen_mods:
    if _m not in sys.modules:
        sys.modules[_m] = MagicMock()


from hr_advisory.shadow.entity_resolver import (
    _resolve_date,
    detect_missing_required,
    resolve_entities,
)


class TestResolveEntities:
    """Entity resolution must map extracted names to API parameter names."""

    def test_employee_name_mapping(self) -> None:
        """'name' should map to 'full_name' for the employees module."""
        resolved, warnings = resolve_entities(
            module="employees",
            action="create",
            entities={"name": "John Tan"},
            tool_params=["full_name", "email"],
        )
        assert resolved["full_name"] == "John Tan"
        assert "name" not in resolved

    def test_employee_salary_mapping(self) -> None:
        """'salary' should map to 'basic_salary' for the employees module."""
        resolved, warnings = resolve_entities(
            module="employees",
            action="create",
            entities={"salary": 5000},
            tool_params=["basic_salary"],
        )
        assert resolved["basic_salary"] == 5000

    def test_employee_start_date_mapping(self) -> None:
        """'start' and 'start_date' should map to 'date_of_joining'."""
        resolved, warnings = resolve_entities(
            module="employees",
            action="create",
            entities={"start_date": "2026-04-01"},
            tool_params=["date_of_joining"],
        )
        assert resolved["date_of_joining"] == "2026-04-01"

    def test_employee_department_mapping(self) -> None:
        """'department' should map to 'department_name'."""
        resolved, warnings = resolve_entities(
            module="employees",
            action="create",
            entities={"department": "Engineering"},
            tool_params=["department_name"],
        )
        assert resolved["department_name"] == "Engineering"

    def test_employee_role_mapping(self) -> None:
        """'role' should map to 'designation'."""
        resolved, warnings = resolve_entities(
            module="employees",
            action="create",
            entities={"role": "Software Engineer"},
            tool_params=["designation"],
        )
        assert resolved["designation"] == "Software Engineer"

    def test_leave_type_mapping(self) -> None:
        """'type' should map to 'leave_type_id' for the leave module."""
        resolved, warnings = resolve_entities(
            module="leave",
            action="apply",
            entities={"type": "annual"},
            tool_params=["leave_type_id"],
        )
        assert resolved["leave_type_id"] == "annual"

    def test_leave_days_mapping(self) -> None:
        """'days' should map to 'duration' for the leave module."""
        resolved, warnings = resolve_entities(
            module="leave",
            action="apply",
            entities={"days": 3},
            tool_params=["duration"],
        )
        assert resolved["duration"] == 3

    def test_leave_reason_mapping(self) -> None:
        """'reason' should map to 'remarks' for the leave module."""
        resolved, warnings = resolve_entities(
            module="leave",
            action="apply",
            entities={"reason": "Family event"},
            tool_params=["remarks"],
        )
        assert resolved["remarks"] == "Family event"

    def test_payroll_month_mapping(self) -> None:
        """'month' should map to 'pay_period' for the payroll module."""
        resolved, warnings = resolve_entities(
            module="payroll",
            action="calculate",
            entities={"month": "March"},
            tool_params=["pay_period"],
        )
        assert resolved["pay_period"] == "March"

    def test_attendance_no_mappings(self) -> None:
        """Attendance module should pass entities through unchanged."""
        resolved, warnings = resolve_entities(
            module="attendance",
            action="clock_in",
            entities={"location": "office"},
            tool_params=["location"],
        )
        assert resolved["location"] == "office"

    def test_unknown_entity_produces_warning(self) -> None:
        """Entities that cannot be mapped should produce a warning."""
        resolved, warnings = resolve_entities(
            module="employees",
            action="create",
            entities={"favorite_color": "blue"},
            tool_params=["full_name", "email"],
        )
        assert len(warnings) > 0
        assert any("favorite_color" in w for w in warnings)

    def test_passthrough_for_already_correct_params(self) -> None:
        """Entities that already match tool param names pass through unchanged."""
        resolved, warnings = resolve_entities(
            module="employees",
            action="create",
            entities={"email": "john@example.com"},
            tool_params=["email", "full_name"],
        )
        assert resolved["email"] == "john@example.com"
        assert len(warnings) == 0

    def test_multiple_entity_mappings(self) -> None:
        """Multiple entities should all be resolved in one call."""
        resolved, warnings = resolve_entities(
            module="employees",
            action="create",
            entities={"name": "Jane", "salary": 6000, "department": "HR"},
            tool_params=["full_name", "basic_salary", "department_name"],
        )
        assert resolved["full_name"] == "Jane"
        assert resolved["basic_salary"] == 6000
        assert resolved["department_name"] == "HR"
        assert len(warnings) == 0

    def test_unknown_module_passes_through(self) -> None:
        """Unknown modules should pass entities through without mapping."""
        resolved, warnings = resolve_entities(
            module="unknown_module",
            action="do_something",
            entities={"key": "value"},
            tool_params=["key"],
        )
        assert resolved["key"] == "value"

    def test_relative_date_resolved_in_entities(self) -> None:
        """Relative date strings in entity values should be resolved."""
        resolved, warnings = resolve_entities(
            module="employees",
            action="create",
            entities={"start_date": "tomorrow"},
            tool_params=["date_of_joining"],
        )
        expected = (date.today() + timedelta(days=1)).isoformat()
        assert resolved["date_of_joining"] == expected


class TestResolveDate:
    """Date resolution must handle relative and absolute date strings."""

    def test_iso_date_passthrough(self) -> None:
        """ISO format dates should pass through unchanged."""
        assert _resolve_date("2026-04-01") == "2026-04-01"

    def test_tomorrow(self) -> None:
        """'tomorrow' should resolve to tomorrow's date."""
        expected = (date.today() + timedelta(days=1)).isoformat()
        assert _resolve_date("tomorrow") == expected

    def test_today(self) -> None:
        """'today' should resolve to today's date."""
        expected = date.today().isoformat()
        assert _resolve_date("today") == expected

    def test_next_week(self) -> None:
        """'next week' should resolve to the start of next week (Monday)."""
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        expected = (today + timedelta(days=days_until_monday)).isoformat()
        assert _resolve_date("next week") == expected

    def test_monday(self) -> None:
        """'Monday' should resolve to the next Monday."""
        today = date.today()
        days_until_monday = (0 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        expected = (today + timedelta(days=days_until_monday)).isoformat()
        assert _resolve_date("Monday") == expected

    def test_next_monday(self) -> None:
        """'next Monday' should resolve to the next Monday."""
        today = date.today()
        days_until_monday = (0 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        expected = (today + timedelta(days=days_until_monday)).isoformat()
        assert _resolve_date("next Monday") == expected

    def test_friday(self) -> None:
        """'Friday' should resolve to the next Friday."""
        today = date.today()
        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0:
            days_until_friday = 7
        expected = (today + timedelta(days=days_until_friday)).isoformat()
        assert _resolve_date("Friday") == expected

    def test_non_date_string_passthrough(self) -> None:
        """Non-date strings should pass through unchanged."""
        assert _resolve_date("John Tan") == "John Tan"

    def test_non_string_passthrough(self) -> None:
        """Non-string values should pass through unchanged."""
        assert _resolve_date(42) == 42
        assert _resolve_date(None) is None


class TestDetectMissingRequired:
    """Missing required parameter detection after entity resolution."""

    def test_all_present(self) -> None:
        """No missing params when all required params are present."""
        missing = detect_missing_required(
            tool_params=["email", "full_name"],
            resolved={"email": "j@t.com", "full_name": "John"},
        )
        assert missing == []

    def test_some_missing(self) -> None:
        """Missing params should be returned in a list."""
        missing = detect_missing_required(
            tool_params=["email", "full_name", "role"],
            resolved={"email": "j@t.com"},
        )
        assert "full_name" in missing
        assert "role" in missing

    def test_all_missing(self) -> None:
        """When no required params are present, all should be listed."""
        missing = detect_missing_required(
            tool_params=["email", "full_name"],
            resolved={},
        )
        assert len(missing) == 2

    def test_empty_tool_params(self) -> None:
        """When tool has no required params, nothing should be missing."""
        missing = detect_missing_required(
            tool_params=[],
            resolved={"extra": "value"},
        )
        assert missing == []
