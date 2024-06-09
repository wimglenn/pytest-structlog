def test_blacklist_mode(pytester):
    """
    The user specifies which processors they want to evict. All other pre-configured
    processors will remain. This tests that a password is removed from the logged
    event, because the configured "password_nerf" processor didn't get evicted.
    """
    pytester.makepyprojecttoml(
        """
        [tool.pytest.ini_options]
        structlog_evict = ["JSONRenderer"]
        """
    )
    pytester.makepyfile(
        """
        import pytest
        import structlog

        logger = structlog.get_logger()

        def password_nerf(logger, log_method, event_dict):
            event_dict.pop("password", None)
            return event_dict

        @pytest.fixture
        def stdlib_bound_logger_configure():
            structlog.configure(
                processors=[
                    password_nerf,
                    structlog.processors.JSONRenderer(),
                ],
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
            )

        def test_foo(stdlib_bound_logger_configure, log):
            logger.info("letmein", username="wim", password="hunter2")
            assert log.events == [
                {
                    "level": "info",
                    "event": "letmein",
                    "username": "wim",
                },
            ]
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_blacklist_mode_evict(pytester):
    """
    The user specifies which processors they want to evict. All other pre-configured
    processors will remain. This tests that a password remains in the logged
    event, because the configured "password_nerf" processor was evicted.
    """
    pytester.makepyprojecttoml(
        """
        [tool.pytest.ini_options]
        structlog_evict = ["JSONRenderer", "password_nerf"]
        """
    )
    pytester.makepyfile(
        """
        import pytest
        import structlog

        logger = structlog.get_logger()

        def password_nerf(logger, log_method, event_dict):
            event_dict.pop("password", None)
            return event_dict

        @pytest.fixture
        def stdlib_bound_logger_configure():
            structlog.configure(
                processors=[
                    password_nerf,
                    structlog.processors.JSONRenderer(),
                ],
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
            )

        def test_foo(stdlib_bound_logger_configure, log):
            logger.info("letmein", username="wim", password="hunter2")
            assert log.events == [
                {
                    "level": "info",
                    "event": "letmein",
                    "username": "wim",
                    "password": "hunter2",
                },
            ]
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_whitelist_mode(pytester):
    """
    The user specifies which processors they want to keep. All other pre-configured
    processors are removed. This tests that a password remains in the logged
    event, because the "password_nerf" processor got evicted by default.
    """
    pytester.makepyfile(
        """
        import pytest
        import structlog

        logger = structlog.get_logger()

        def password_nerf(logger, log_method, event_dict):
            event_dict.pop("password", None)
            return event_dict

        @pytest.fixture
        def stdlib_bound_logger_configure():
            structlog.configure(
                processors=[
                    password_nerf,
                    structlog.processors.JSONRenderer(),
                ],
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
            )

        def test_foo(stdlib_bound_logger_configure, log):
            logger.info("letmein", username="wim", password="hunter2")
            assert log.events == [
                {
                    "level": "info",
                    "event": "letmein",
                    "username": "wim",
                    "password": "hunter2",
                },
            ]
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_whitelist_mode_keep(pytester):
    """
    The user specifies which processors they want to keep. All other pre-configured
    processors are removed. This tests that a password is removed from the logged
    event, because the configured "password_nerf" processor was kept.
    """
    pytester.makepyprojecttoml(
        """
        [tool.pytest.ini_options]
        structlog_keep = ["password_nerf"]
        """
    )
    pytester.makepyfile(
        """
        import pytest
        import structlog

        logger = structlog.get_logger()

        def password_nerf(logger, log_method, event_dict):
            event_dict.pop("password", None)
            return event_dict

        @pytest.fixture
        def stdlib_bound_logger_configure():
            structlog.configure(
                processors=[
                    password_nerf,
                    structlog.processors.JSONRenderer(),
                ],
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
            )

        def test_foo(stdlib_bound_logger_configure, log):
            logger.info("letmein", username="wim", password="hunter2")
            import pytest_structlog
            print(structlog.get_config())
            assert log.events == [
                {
                    "level": "info",
                    "event": "letmein",
                    "username": "wim",
                },
            ]
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_custom_config_cant_specify_both(pytester):
    """
    Keep means "discard every pre-configured processor except the ones I specify".
    Evict means "keep every pre-configured processor except the ones I specify".
    You can not logically use "keep" and "evict" together, and the plugin prevents users
    from attempting to do so.
    """
    pytester.makepyprojecttoml(
        """
        [tool.pytest.ini_options]
        structlog_keep = "foo"
        structlog_evict = "bar"
        """
    )
    pytester.makepyfile(
        """
        import structlog
        logger = structlog.get_logger()
        
        def test_foo(log):
            logger.info("foo")
            assert log.has("foo")
        """
    )
    result = pytester.runpytest()
    assert result.ret != 0
    expected_error = (
        "ERROR: --structlog-keep and --structlog-evict settings are mutually exclusive."
        " Specify one or the other, not both."
    )
    assert expected_error in result.stderr.lines
