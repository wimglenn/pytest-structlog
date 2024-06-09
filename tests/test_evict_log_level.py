def test_evict_log_level_from_event_dict(pytester):
    """
    It should be possible to prevent "level" injection into the event dict.
    """
    pytester.makepyprojecttoml(
        """
        [tool.pytest.ini_options]
        structlog_evict = ["add_log_level"]
        """
    )
    pytester.makepyfile(
        """
        import pytest
        import structlog.processors

        logger = structlog.get_logger()

        @pytest.fixture
        def stdlib_bound_logger_configure():
            structlog.configure(
                processors=[
                    structlog.processors.add_log_level,
                    structlog.processors.JSONRenderer(),
                ],
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
            )

        def test_foo(stdlib_bound_logger_configure, log):
            logger.info("the-event", k="v")
            assert log.events == [
                {
                    "event": "the-event",
                    "k": "v",
                },
            ]
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
