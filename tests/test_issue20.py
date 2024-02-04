import pytest
import structlog

from pytest_structlog import StructuredLogCapture


logger = structlog.get_logger()


@pytest.fixture
def issue20_setup():
    pytest.importorskip("structlog.contextvars")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
    )
    yield
    structlog.contextvars.clear_contextvars()


def test_contextvar(issue20_setup, log: StructuredLogCapture):
    structlog.contextvars.clear_contextvars()
    logger.info("log1", log1var="value")
    structlog.contextvars.bind_contextvars(contextvar="cv")
    logger.info("log2", log2var="value")
    assert log.has("log2", log2var="value", contextvar="cv")
