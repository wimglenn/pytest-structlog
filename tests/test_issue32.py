import pytest
import structlog


@pytest.fixture
def stdlib_bound_logger_configure():
    structlog.configure(
        processors=[
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
    )


@pytest.fixture
def stdlib_bound_logger_configure_dict_tb():
    structlog.configure(
        processors=[
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
    )


def log_exception():
    logger = structlog.get_logger()
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("event_name")


def test_exception_traceback(stdlib_bound_logger_configure, log):
    log_exception()
    [event] = log.events
    err = event["exception"]
    assert err.startswith("Traceback")
    assert "ZeroDivisionError" in err


def test_exception_dict_traceback(stdlib_bound_logger_configure_dict_tb, log):
    log_exception()
    [event] = log.events
    [err] = event["exception"]
    assert isinstance(err, dict)
    assert err["exc_type"] == "ZeroDivisionError"
    assert err["exc_value"] == "division by zero"
