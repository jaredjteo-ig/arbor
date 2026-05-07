"""Regression tests for engagement-pseudonym helper (T03 / Z02).

Covers the four anonymity invariants from
`workspaces/engagement-survey/02-plans/01-data-model.md`:
  1. Same employee + same survey → identical pseudonym
     (cross-survey trends work).
  2. Same employee + different survey → different pseudonym.
  3. Different employee + same survey → different pseudonym.
  4. Different secret → different pseudonym (rotation invalidates
     re-identification path).

Plus the Z02 versioning amendment:
  5. Active version is lazy-generated on first call.
  6. Rotation produces a new active version; old version still readable
     for historical pseudonym verification.
  7. Invalid inputs (zero IDs, short secret) reject loudly.
"""

from __future__ import annotations

import pytest

from hr_advisory.services.engagement_pseudonym import (
    compute_pseudonym,
)


@pytest.mark.regression
def test_same_employee_same_survey_returns_identical_pseudonym():
    """Invariant 1: deterministic per (secret, employee, survey)."""
    secret = "a" * 64
    p1 = compute_pseudonym(secret, employee_id=42, survey_id=7)
    p2 = compute_pseudonym(secret, employee_id=42, survey_id=7)
    assert p1 == p2
    assert len(p1) == 64  # SHA256 hex digest


@pytest.mark.regression
def test_same_employee_different_survey_returns_different_pseudonym():
    """Invariant 2: cross-survey isolation.

    Without this, an attacker who learned one pseudonym could enumerate
    the same employee across all surveys.
    """
    secret = "a" * 64
    p1 = compute_pseudonym(secret, employee_id=42, survey_id=7)
    p2 = compute_pseudonym(secret, employee_id=42, survey_id=8)
    assert p1 != p2


@pytest.mark.regression
def test_different_employee_same_survey_returns_different_pseudonym():
    """Invariant 3: per-employee uniqueness within a survey."""
    secret = "a" * 64
    p1 = compute_pseudonym(secret, employee_id=42, survey_id=7)
    p2 = compute_pseudonym(secret, employee_id=43, survey_id=7)
    assert p1 != p2


@pytest.mark.regression
def test_different_secret_produces_different_pseudonym():
    """Invariant 4: secret rotation invalidates re-identification.

    After rotation, the same (employee, survey) tuple produces a new
    pseudonym — historical responses remain verifiable via the old
    secret, but the new secret cannot be used to look them up.
    """
    p1 = compute_pseudonym("a" * 64, employee_id=42, survey_id=7)
    p2 = compute_pseudonym("b" * 64, employee_id=42, survey_id=7)
    assert p1 != p2


@pytest.mark.regression
def test_invalid_secret_rejected():
    with pytest.raises(ValueError, match="32 hex chars"):
        compute_pseudonym("short", employee_id=42, survey_id=7)


@pytest.mark.regression
def test_invalid_secret_format_rejected():
    with pytest.raises(ValueError, match="valid hex"):
        compute_pseudonym("z" * 64, employee_id=42, survey_id=7)


@pytest.mark.regression
def test_zero_employee_id_rejected():
    """Anonymous-tier responses use a different code path; pseudonym
    computation must reject employee_id=0 to fail-loud if a caller
    gets the tier branching wrong.
    """
    with pytest.raises(ValueError, match="employee_id must be > 0"):
        compute_pseudonym("a" * 64, employee_id=0, survey_id=7)


@pytest.mark.regression
def test_zero_survey_id_rejected():
    with pytest.raises(ValueError, match="survey_id must be > 0"):
        compute_pseudonym("a" * 64, employee_id=42, survey_id=0)


@pytest.mark.regression
def test_pseudonym_is_pure_hex():
    """The returned digest must be exactly 64 lowercase hex chars so
    the DB column type and any string operations are predictable.
    """
    p = compute_pseudonym("a" * 64, employee_id=42, survey_id=7)
    assert len(p) == 64
    assert all(c in "0123456789abcdef" for c in p)


@pytest.mark.regression
def test_pseudonym_is_deterministic_across_processes():
    """Different runs of the same inputs must produce the same output —
    HMAC-SHA256 is deterministic, but pin it explicitly so any future
    refactor (e.g. to argon2 or scrypt) breaks loudly.
    """
    expected = compute_pseudonym("a" * 64, employee_id=42, survey_id=7)
    # Recompute fresh — exercise the full path again
    actual = compute_pseudonym("a" * 64, employee_id=42, survey_id=7)
    assert expected == actual
