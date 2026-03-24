"""Test-wide fixtures for proper resource cleanup.

Ensures LocalRuntime instances are properly closed after each test module,
preventing connection pool exhaustion when running the full test suite.

The Kailash SDK's LocalRuntime creates async event loops and connection pools.
Without explicit .close() or context manager usage, these pools leak and
exhaust PostgreSQL's max_connections when running many tests.
"""

import gc
import logging
import weakref

import pytest

logger = logging.getLogger(__name__)

# Track all LocalRuntime instances created during tests
_runtime_refs: list[weakref.ref] = []
_original_init = None


def _tracking_init(self, *args, **kwargs):
    """Wrapper around LocalRuntime.__init__ that tracks instances."""
    _original_init(self, *args, **kwargs)
    _runtime_refs.append(weakref.ref(self))


def pytest_configure(config):
    """Monkey-patch LocalRuntime to track all instances for cleanup."""
    global _original_init
    try:
        from kailash.runtime import LocalRuntime

        _original_init = LocalRuntime.__init__
        LocalRuntime.__init__ = _tracking_init
    except ImportError:
        pass


def pytest_unconfigure(config):
    """Restore original LocalRuntime.__init__."""
    global _original_init
    if _original_init is not None:
        try:
            from kailash.runtime import LocalRuntime

            LocalRuntime.__init__ = _original_init
        except ImportError:
            pass


@pytest.fixture(autouse=True, scope="module")
def _cleanup_runtimes_after_module():
    """Close all LocalRuntime instances created during a test module.

    Runs after each module to prevent pool accumulation across files.
    """
    yield

    closed = 0
    for ref in _runtime_refs:
        runtime = ref()
        if runtime is not None:
            try:
                runtime.close()
                closed += 1
            except Exception:
                pass
    _runtime_refs.clear()

    if closed > 0:
        logger.debug("Closed %d leaked LocalRuntime instances after module", closed)

    # Force GC to release any remaining references
    gc.collect()


@pytest.fixture(scope="session")
def shared_runtime():
    """Provide a single LocalRuntime shared across the test session.

    Tests that need a runtime should use this fixture instead of
    creating new LocalRuntime() instances:

        def test_something(shared_runtime):
            results, _ = shared_runtime.execute(wf.build())

    The runtime is properly closed at session end.
    """
    from kailash.runtime import LocalRuntime

    runtime = LocalRuntime()
    yield runtime
    runtime.close()
