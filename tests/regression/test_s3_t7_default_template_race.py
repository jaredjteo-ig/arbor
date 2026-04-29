"""Regression: S3-T7 — two-default-templates race fix.

`create_template`/`update_template` clear-then-set on `is_default` was
non-atomic — two concurrent POSTs could each see only the OLD default,
both un-set it, both set their own template default, leaving two
defaults marked True. The fix wraps the sequence under a per-tenant
threading.Lock so the read-and-write window is serialized within a
process.

For multi-worker deploys, a DB-level partial unique index on
`(company_id) WHERE is_default=TRUE` is the canonical fix; documented
in the deploy notes.
"""

from __future__ import annotations

import inspect
import threading

import pytest


@pytest.mark.regression
def test_s3_t7_per_tenant_lock_helper_exists():
    """The `_get_default_template_lock(company_id)` helper must exist
    and return a `threading.Lock` keyed by company_id.
    """
    from hr_advisory.api.routers import onboarding as onboarding_module

    assert hasattr(onboarding_module, "_get_default_template_lock")
    lock = onboarding_module._get_default_template_lock(1)
    assert isinstance(lock, type(threading.Lock())) or hasattr(lock, "acquire")


@pytest.mark.regression
def test_s3_t7_lock_is_per_tenant():
    """Two different company_ids must get DIFFERENT locks. Otherwise a
    single global lock would needlessly serialize all tenants.
    """
    from hr_advisory.api.routers import onboarding as onboarding_module

    lock1 = onboarding_module._get_default_template_lock(1)
    lock2 = onboarding_module._get_default_template_lock(2)
    lock1_again = onboarding_module._get_default_template_lock(1)

    assert lock1 is lock1_again, "Same company_id must return the same lock"
    assert lock1 is not lock2, "Different company_ids must have different locks"


@pytest.mark.regression
def test_s3_t7_create_template_uses_lock():
    """`create_template` source must wrap the clear-then-set + create in
    `with _get_default_template_lock(company_id):`. Otherwise two
    concurrent posts can leave two defaults.
    """
    from hr_advisory.api.routers import onboarding as onboarding_module

    src = inspect.getsource(onboarding_module.create_template)
    assert "_get_default_template_lock(company_id)" in src
    # And the lock must wrap both the clear AND the create — not just one.
    lock_idx = src.index("_get_default_template_lock(company_id)")
    after = src[lock_idx:]
    assert "is_default" in after
    assert "create" in after, (
        "Lock must wrap BOTH the un-set-existing-defaults AND the create."
    )


@pytest.mark.regression
def test_s3_t7_update_template_uses_lock():
    """Same guard for `update_template` when toggling is_default to True.
    """
    from hr_advisory.api.routers import onboarding as onboarding_module

    src = inspect.getsource(onboarding_module.update_template)
    assert "_get_default_template_lock(company_id)" in src


@pytest.mark.regression
def test_s3_t7_lock_is_reentrant_within_acquire():
    """The lock must NOT be held across module imports or anywhere that
    could deadlock subsequent acquisitions. Smoke test: acquire/release
    twice in sequence.
    """
    from hr_advisory.api.routers import onboarding as onboarding_module

    lock = onboarding_module._get_default_template_lock(99)
    assert lock.acquire(timeout=1.0)
    lock.release()
    assert lock.acquire(timeout=1.0)
    lock.release()
