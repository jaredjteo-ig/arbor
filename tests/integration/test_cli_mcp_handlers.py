"""S4-T6: smoke test for the multi-channel handlers in platform.py.

Round-12 #10 / cluster 0 surfaced that `platform._register_handlers` was
silently broken once (the `_lookup_provisions` ImportError). A smoke test
that invokes each registered handler with a minimal payload would have
caught that the same day.

This test captures every handler registered via the `@app.handler` decorator
inside `_register_handlers`, then invokes each with a small valid payload and
asserts the response is a dict (not an exception) and includes the documented
keys for that handler.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable

import pytest


class _FakeNexus:
    """Capture the handlers Nexus registers via the decorator pattern.

    `app.handler(name, description=...)` is used as a decorator factory; we
    just record the wrapped function under its declared name so the test
    can invoke it directly.
    """

    def __init__(self) -> None:
        self.registered: dict[str, Callable] = {}

    def handler(self, name: str, description: str | None = None) -> Callable:
        def decorator(fn: Callable) -> Callable:
            self.registered[name] = fn
            return fn

        return decorator


def _captured_handlers() -> dict[str, Callable]:
    """Build a fake Nexus + invoke `_register_handlers` to harvest the
    inner functions. This is the only way to reach them — they are
    closures inside `_register_handlers`.
    """
    from hr_advisory.api.platform import _register_handlers

    app = _FakeNexus()
    session_store = object()  # never accessed by the handler closures
    _register_handlers(app, session_store)
    return app.registered


def _invoke(handler: Callable, **kwargs: Any) -> dict:
    """Run an async handler synchronously for testing."""
    if inspect.iscoroutinefunction(handler):
        return asyncio.run(handler(**kwargs))
    return handler(**kwargs)


@pytest.mark.integration
def test_s4_t6_all_three_handlers_registered():
    """`platform._register_handlers` MUST register the three documented
    multi-channel handlers. A future refactor that drops one (say,
    `search_kb`) would cause CLI/MCP callers to silently fail with
    "no such handler" — a regression that round-13 explicitly flagged.
    """
    handlers = _captured_handlers()

    assert set(handlers) == {"advisory_query", "compliance_check", "search_kb"}, (
        f"Expected exactly the 3 documented handlers, got: {sorted(handlers)}"
    )


@pytest.mark.integration
def test_s4_t6_advisory_query_handler_returns_dict():
    """`advisory_query(query)` must return a dict on a benign input.

    The handler runs the AdvisoryEngine which in turn requires LLM
    credentials. We provide a query that the screening layer can short-
    circuit (BLOCK/ESCALATE both return without invoking the engine),
    so this test does not require live LLM access.
    """
    handlers = _captured_handlers()
    advisory = handlers["advisory_query"]

    # An empty/sanitized query takes the screening short-circuit path
    # (or returns a benign engine response). Either way: dict.
    response = _invoke(advisory, query="What is annual leave entitlement?")

    assert isinstance(response, dict), (
        f"advisory_query must return dict; got {type(response).__name__}"
    )
    # Documented keys regardless of code path
    assert "query" in response
    assert "risk_tier" in response


@pytest.mark.integration
def test_s4_t6_advisory_query_handler_signature_is_tenantless():
    """CRIT-S1 (round-13): the handler must NOT accept `company_id` from
    the caller. This invariant is also pinned in test_round13_critical_fixes.py
    but repeated here so the smoke test fails fast if a future refactor
    re-adds the parameter.
    """
    handlers = _captured_handlers()
    advisory = handlers["advisory_query"]

    sig = inspect.signature(advisory)
    assert list(sig.parameters) == ["query"], (
        "advisory_query handler must accept ONLY `query`. Adding company_id "
        "back without trusted-channel auth would re-open round-13 CRIT-S1."
    )


@pytest.mark.integration
def test_s4_t6_compliance_check_handler_returns_dict():
    handlers = _captured_handlers()
    compliance = handlers["compliance_check"]

    response = _invoke(compliance, domains="employment_act")

    assert isinstance(response, dict)
    # Documented response shape
    assert "domains_checked" in response
    assert "status" in response
    assert "risk_tier" in response
    assert "findings" in response
    assert isinstance(response["findings"], list)


@pytest.mark.integration
def test_s4_t6_compliance_check_handler_signature_is_tenantless():
    """CRIT-S1: compliance_check must not accept company_id either."""
    handlers = _captured_handlers()
    compliance = handlers["compliance_check"]

    sig = inspect.signature(compliance)
    assert list(sig.parameters) == ["domains"], (
        "compliance_check handler must accept ONLY `domains`."
    )


@pytest.mark.integration
def test_s4_t6_search_kb_handler_returns_dict():
    handlers = _captured_handlers()
    search = handlers["search_kb"]

    # Use a low top_k to keep the test fast.
    response = _invoke(search, query="annual leave", top_k=3)

    assert isinstance(response, dict), (
        f"search_kb must return dict; got {type(response).__name__}"
    )


@pytest.mark.integration
def test_s4_t6_handlers_are_async_callables():
    """All three handlers are coroutines (registered with `async def`).
    A future refactor that converts one to sync would break the Nexus
    multi-channel adapter that awaits them.
    """
    handlers = _captured_handlers()
    for name, fn in handlers.items():
        assert inspect.iscoroutinefunction(fn), (
            f"Handler '{name}' must be `async def` — Nexus awaits it."
        )
