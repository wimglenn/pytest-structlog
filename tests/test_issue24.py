import os

import pytest
import structlog

from pytest_structlog import StructuredLogCapture

logger = structlog.get_logger()


@pytest.fixture(scope="module")
def issue24_setup():
    """Isolate this module's contextvars from other tests, even while issue 24 is present"""
    pytest.importorskip("structlog.contextvars")
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()


# Make sure that at least one process runs the test at least twice
try:
    RUN_COUNT = int(os.environ.get("PYTEST_XDIST_WORKER_COUNT", 1)) + 1
except Exception:
    RUN_COUNT = 2


@pytest.mark.parametrize("n", list(range(RUN_COUNT)))
def test_contextvar_isolation_in_events(issue24_setup, log: StructuredLogCapture, n):
    logger.info("without_context")
    structlog.contextvars.bind_contextvars(ctx=n)
    logger.info("with_context")
    assert log.events == [
        # in issue 24 the first event has "ctx" from previous run
        {"event": "without_context", "level": "info"},
        {"event": "with_context", "level": "info", "ctx": n},
    ]
    assert structlog.contextvars.get_contextvars() == {"ctx": n}
