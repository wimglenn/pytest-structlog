import structlog

from pytest_structlog import StructuredLogCapture

logger = structlog.get_logger()


def test_count(log: StructuredLogCapture):
    for i in range(3):
        logger.info("hello iteration", it=i)
    assert log.count("hello iteration") == 3
    assert log.count("hello iteration", it=1) == 1
    assert log.count("hello iteration", k=1) == 0
