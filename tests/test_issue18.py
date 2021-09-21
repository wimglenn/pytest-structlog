import pytest

import structlog


logger = structlog.get_logger(__name__)


@pytest.fixture
def stdlib_configure():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=structlog.threadlocal.wrap_dict(dict),
    )


def test_positional_formatting(stdlib_configure, log):
    items_count = 2
    dt = 0.02
    logger.info("Processed %d CC items in total in %.2f seconds", items_count, dt)
    assert log.has("Processed 2 CC items in total in 0.02 seconds", level="info")
