import structlog


logger = structlog.get_logger("some logger")


def test_first():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    logger.warning("test")


def test_second(log):
    logger.warning("test")
    assert log.has("test")


def test_third():
    logger.warning("test")
