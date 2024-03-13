import logging

import pytest
import structlog

from pytest_structlog import StructuredLogCapture


logger = structlog.get_logger("test")


def spline_reticulator():
    logger.info("reticulating splines", n_splines=123)


def main_ish():
    structlog.configure(processors=[])
    # this confingure call should be a no-op after fixture was injected
    logger.debug("yo")


def binding():
    log = logger.bind(k="v")
    log.debug("dbg")
    log.info("inf", kk="more context")
    log = log.unbind("k")
    log.warning("uh-oh")


def i_warned_you_twice():
    logger.warn("and you didn't listen")
    logger.warning("now look what happened")


def test_capture_creates_items(log: StructuredLogCapture):
    assert not log.events
    spline_reticulator()
    assert log.events


def test_assert_without_context(log: StructuredLogCapture):
    spline_reticulator()
    assert log.has("reticulating splines")


def test_assert_with_subcontext(log: StructuredLogCapture):
    spline_reticulator()
    assert log.has("reticulating splines", n_splines=123)


def test_assert_with_bogus_context(log: StructuredLogCapture):
    spline_reticulator()
    assert not log.has("reticulating splines", n_splines=0)


def test_assert_with_all_context(log: StructuredLogCapture):
    spline_reticulator()
    assert log.has("reticulating splines", n_splines=123, level="info")


def test_assert_with_super_context(log: StructuredLogCapture):
    spline_reticulator()
    assert not log.has("reticulating splines", n_splines=123, level="info", k="v")


def test_configurator(log: StructuredLogCapture):
    main_ish()
    assert log.has("yo", level="debug")


def test_multiple_events(log: StructuredLogCapture):
    binding()
    assert log.has("dbg", k="v", level="debug")
    assert log.has("inf", k="v", kk="more context", level="info")


def test_length(log: StructuredLogCapture):
    binding()
    assert len(log.events) == 3


d0, d1, d2 = [
    {"event": "dbg", "k": "v", "level": "debug"},
    {"event": "inf", "k": "v", "level": "info", "kk": "more context"},
    {"event": "uh-oh", "level": "warning"},
]


def test_membership(log: StructuredLogCapture):
    binding()
    assert d0 in log.events


def test_superset_single(log: StructuredLogCapture):
    binding()
    assert log.events >= [d0]


def test_superset_multi(log: StructuredLogCapture):
    binding()
    assert log.events >= [d0, d2]


def test_superset_respects_ordering(log: StructuredLogCapture):
    binding()
    assert not log.events >= [d2, d0]


def test_superset_multi_all(log: StructuredLogCapture):
    binding()
    assert log.events >= [d0, d1, d2]


def test_superset_multi_strict(log: StructuredLogCapture):
    binding()
    assert not log.events > [d0, d1, d2]


def test_equality(log: StructuredLogCapture):
    binding()
    assert log.events == [d0, d1, d2]


def test_inequality(log: StructuredLogCapture):
    binding()
    assert log.events != [d0, {}, d1, d2]


def test_total_ordering(log: StructuredLogCapture):
    binding()
    assert log.events <= [d0, d1, d2, {}]
    assert log.events < [d0, d1, d2, {}]
    assert log.events > [d0, d1]


def test_dupes(log: StructuredLogCapture):
    logger.info("a")
    logger.info("a")
    logger.info("b")
    assert log.events >= [{"event": "a", "level": "info"}]
    assert log.events >= [
        {"event": "a", "level": "info"},
        {"event": "b", "level": "info"},
    ]
    assert log.events >= [
        {"event": "a", "level": "info"},
        {"event": "a", "level": "info"},
        {"event": "b", "level": "info"},
    ]
    assert not log.events >= [
        {"event": "a", "level": "info"},
        {"event": "a", "level": "info"},
        {"event": "a", "level": "info"},
        {"event": "b", "level": "info"},
    ]


def test_event_factories(log: StructuredLogCapture):
    assert log.debug("debug-level", extra=True) == {
        "event": "debug-level",
        "level": "debug",
        "extra": True,
    }
    assert log.info("info-level", more="yes") == {
        "event": "info-level",
        "level": "info",
        "more": "yes",
    }
    assert log.warning("warning-level", another=42) == {
        "event": "warning-level",
        "level": "warning",
        "another": 42,
    }
    assert log.error("error-level", added=1) == {
        "event": "error-level",
        "level": "error",
        "added": 1,
    }
    assert log.critical("crit-level", above="beyond") == {
        "event": "crit-level",
        "level": "critical",
        "above": "beyond",
    }


@pytest.mark.parametrize(
    "level, name",
    [
        (logging.DEBUG, "debug"),
        (logging.INFO, "info"),
        (logging.WARNING, "warning"),
        (logging.ERROR, "error"),
        (logging.CRITICAL, "critical"),
    ],
)
def test_dynamic_event_factory(log, level, name):
    expected = {"event": "dynamic-level", "level": name, "other": 42}

    assert log.log(level, "dynamic-level", other=42) == expected
    assert log.log(name, "dynamic-level", other=42) == expected
    assert log.log(name.upper(), "dynamic-level", other=42) == expected


def test_event_factory_bad_level_number(log: StructuredLogCapture):
    assert log.log(1234, "text") == {"event": "text", "level": "level 1234"}


def test_warn_warning_alias(log: StructuredLogCapture):
    i_warned_you_twice()
    assert log.events == [
        {"event": "and you didn't listen", "level": "warning"},
        {"event": "now look what happened", "level": "warning"},
    ]
