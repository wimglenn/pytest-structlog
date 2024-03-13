import logging.config

import pytest
import structlog

from pytest_structlog import StructuredLogCapture


@pytest.fixture
def stdlib_bound_logger_configure():
    """
    From the original structlog issue: https://github.com/hynek/structlog/issues/584#issue-2063338394
    """
    structlog.configure(
        processors=[
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
    )

    logging_config = {
        "version": 1,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    structlog.processors.add_log_level,
                    structlog.processors.JSONRenderer(),
                ],
            }
        },
        "handlers": {
            "json": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            },
        },
        "root": {
            "handlers": ["json"],
        },
    }
    logging.config.dictConfig(logging_config)


def log_exception():
    logger = structlog.get_logger()
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("event_name")


def test_exception_level(stdlib_bound_logger_configure, log: StructuredLogCapture):
    log_exception()
    assert log.events == [
        {"event": "event_name", "exc_info": True, "level": "error"},
    ]
