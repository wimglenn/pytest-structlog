import pytest
import structlog


logger = structlog.get_logger("the-logger-name")


@pytest.fixture(autouse=True)
def inject_logger_name(log):
    original_processors = structlog.get_config().get("processors", [])
    if structlog.stdlib.add_logger_name not in original_processors:
        processors = [structlog.stdlib.add_logger_name] + original_processors
        log.original_configure(processors=processors)
        yield
        log.original_configure(processors=original_processors)


def test_logger_name(log):
    logger.info("foo", k="bar")
    assert log.has("foo", k="bar", logger="the-logger-name")
