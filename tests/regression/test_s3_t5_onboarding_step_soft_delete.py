"""Regression: S3-T5 — onboarding step soft-delete (round-13 H11).

A hard delete on `OnboardingStep` orphans every `OnboardingStepProgress`
row in active assignments — employees see blanks and percentages skew.
S3-T5 replaces hard-delete with `is_active=False`, so:

  - Existing assignments resolve steps from their own progress rows
    and continue to render correctly.
  - New assignments construct from the template via `_get_steps_for_module`
    which filters archived steps by default.
  - Admin views (template editor, audit) pass `include_archived=True`
    so they can see and re-activate the soft-deleted rows.
"""

from __future__ import annotations

import inspect

import pytest


@pytest.mark.regression
def test_s3_t5_onboarding_step_has_is_active_field():
    """The OnboardingStep model must expose `is_active` so soft-delete
    has a place to land. Without the field DELETE has nowhere to go.
    """
    from hr_advisory.models.company_user import OnboardingStep

    annotations = OnboardingStep.__annotations__
    assert "is_active" in annotations, (
        "OnboardingStep needs an is_active field for soft-delete; without "
        "it DELETE has to fall back to hard delete and orphans progress."
    )
    assert annotations["is_active"] is bool


@pytest.mark.regression
def test_s3_t5_delete_step_is_soft():
    """The DELETE handler must call dataflow_crud.update with is_active=False
    rather than dataflow_crud.delete — pre-S3-T5 it called delete.
    """
    from hr_advisory.api.routers import onboarding as onboarding_module

    src = inspect.getsource(onboarding_module.delete_step)
    assert 'dataflow_crud.update("OnboardingStep"' in src
    assert '"is_active": False' in src
    # And it must NOT call dataflow_crud.delete on OnboardingStep
    assert 'dataflow_crud.delete("OnboardingStep"' not in src, (
        "DELETE handler must NOT hard-delete OnboardingStep — "
        "that orphans OnboardingStepProgress rows in active assignments."
    )


@pytest.mark.regression
def test_s3_t5_get_steps_filters_archived_by_default():
    """`_get_steps_for_module` MUST filter out archived steps unless the
    caller opts into `include_archived=True`. Default-deny is the safe
    posture for assignment construction.
    """
    from hr_advisory.api.routers import onboarding as onboarding_module

    sig = inspect.signature(onboarding_module._get_steps_for_module)
    assert "include_archived" in sig.parameters
    # Default must be False — assignment construction should not silently
    # include archived steps.
    assert sig.parameters["include_archived"].default is False


@pytest.mark.regression
def test_s3_t5_idempotent_delete_returns_already_archived():
    """Soft-deleting a step that's already archived must return a clean
    "already archived" message rather than re-flipping the flag.
    """
    from hr_advisory.api.routers import onboarding as onboarding_module

    src = inspect.getsource(onboarding_module.delete_step)
    assert "already archived" in src, (
        "delete_step must return an already-archived message on repeat "
        "calls — without this check the audit trail records a redundant "
        "update event for every retry."
    )
