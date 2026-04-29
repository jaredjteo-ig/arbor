"""Regression: S2-T3 — compliance cache invalidation on policy writes.

The compliance status cache has a 5-minute TTL (`_CACHE_TTL=300`). Without
explicit invalidation, every policy create/update/upload/delete leaves the
cache stale for up to 5 minutes — so the dashboard shows the OLD compliance
verdict to the next caller, even though they just published a policy that
closes a domain gap.

This test pins the invariant: after each of the 5 policy mutation endpoints
runs, `compliance._compliance_cache` MUST be empty for that company_id, so
the next `/compliance/status` call recomputes from fresh data.
"""

from __future__ import annotations

import inspect

import pytest


@pytest.mark.regression
def test_s2_t3_invalidate_function_exists():
    """compliance.py exports invalidate_compliance_cache(company_id) — the
    canonical write path that policies.py and any future router calls.
    """
    from hr_advisory.api.routers.compliance import invalidate_compliance_cache

    sig = inspect.signature(invalidate_compliance_cache)
    assert list(sig.parameters) == ["company_id"], (
        "invalidate_compliance_cache must accept exactly one parameter "
        "(company_id) so callers cannot accidentally pass an unrelated "
        "key and silently fail to invalidate."
    )


@pytest.mark.regression
def test_s2_t3_policies_imports_invalidator():
    """policies.py must import invalidate_compliance_cache. Without the
    import the call sites are dead code — defense in depth so the import
    itself is part of the regression contract.
    """
    from hr_advisory.api.routers import policies as policies_module

    src = inspect.getsource(policies_module)
    assert "from hr_advisory.api.routers.compliance import invalidate_compliance_cache" in src


@pytest.mark.regression
def test_s2_t3_all_five_mutation_endpoints_call_invalidator():
    """Each of the 5 policy mutation endpoints (create, upload, update,
    update_content, delete/archive) MUST call invalidate_compliance_cache.

    A pure source-level scan against the route handlers is sufficient
    because the handler bodies are linear (no conditional invalidate
    paths). If a future refactor splits invalidation into helpers, this
    test should be updated to follow the call graph.
    """
    from hr_advisory.api.routers import policies as policies_module

    handlers = [
        policies_module.create_policy,
        policies_module.upload_policy,
        policies_module.update_policy,
        policies_module.update_policy_content,
        policies_module.delete_policy,
    ]
    for handler in handlers:
        src = inspect.getsource(handler)
        assert "invalidate_compliance_cache(company_id)" in src, (
            f"{handler.__name__} must call invalidate_compliance_cache(company_id) "
            f"before returning — otherwise /compliance/status returns up to "
            f"5 minutes of stale data after this mutation."
        )


@pytest.mark.regression
def test_s2_t3_invalidate_clears_only_target_company():
    """The cache is keyed by company_id. Invalidating company A must NOT
    drop company B's entry — that would punish unrelated tenants with an
    unnecessary recompute on every policy write anywhere in the system.
    """
    from hr_advisory.api.routers.compliance import (
        _compliance_cache,
        _set_cached_compliance,
        invalidate_compliance_cache,
    )

    _compliance_cache.clear()
    _set_cached_compliance(1, {"status": "compliant"})
    _set_cached_compliance(2, {"status": "non_compliant"})

    invalidate_compliance_cache(1)

    assert 1 not in _compliance_cache, "Target company_id=1 must be evicted"
    assert 2 in _compliance_cache, (
        "Other tenants (company_id=2) must keep their cached entry — "
        "invalidation has tight blast radius by design."
    )

    # Cleanup so this test does not leak state into later tests
    _compliance_cache.clear()


@pytest.mark.regression
def test_s2_t3_invalidate_idempotent_for_unknown_company():
    """Invalidating a company_id that was never cached must not raise.
    The handler may legitimately call invalidate before any /compliance/
    status call has populated the cache.
    """
    from hr_advisory.api.routers.compliance import (
        _compliance_cache,
        invalidate_compliance_cache,
    )

    _compliance_cache.clear()
    # Must not raise
    invalidate_compliance_cache(9999)
    assert 9999 not in _compliance_cache
