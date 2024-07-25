from __future__ import annotations

import functools
import logging
import os
from typing import Any
from typing import Callable
from typing import Generator
from typing import List
from typing import NoReturn
from typing import Sequence
from typing import Union

import pytest
import structlog
from pytest import FixtureRequest
from pytest import MonkeyPatch
from structlog.contextvars import clear_contextvars
from structlog.typing import EventDict
from structlog.typing import WrappedLogger


class EventList(List[EventDict]):
    """A list subclass that overrides ordering operations.
    Instead of A <= B being a lexicographical comparison,
    now it means every element of A is contained within B,
    in the same order, although there may be other items
    interspersed throughout (i.e. A is a subsequence of B)
    """

    def __ge__(self, other: Sequence[EventDict]) -> bool:
        return is_subseq(other, self)

    def __gt__(self, other: Sequence[EventDict]) -> bool:
        return len(self) > len(other) and is_subseq(other, self)

    def __le__(self, other: Sequence[EventDict]) -> bool:
        return is_subseq(self, other)

    def __lt__(self, other: Sequence[EventDict]) -> bool:
        return len(self) < len(other) and is_subseq(self, other)


_absent = object()


def level_to_name(level: Union[str, int]) -> str:
    """Given the name or number for a log-level, return the lower-case level name."""
    if isinstance(level, str):
        return level.lower()
    return logging.getLevelName(level).lower()


def is_submap(d1: EventDict, d2: EventDict) -> bool:
    """Is every pair from d1 also in d2? (unique and order insensitive)"""
    return all(d2.get(k, _absent) == v for k, v in d1.items())


def is_subseq(l1: Sequence[Any], l2: Sequence[Any]) -> bool:
    """Is every element of l1 also in l2? (non-unique and order sensitive)"""
    it = iter(l2)
    return all(d in it for d in l1)


class StructuredLogCapture:
    """Processor which accumulates log events during testing. The log fixture
    provided by pytest_structlog is an instance of this class."""

    def __init__(self) -> None:
        self.original_configure: Callable = structlog.configure
        self.original_config: dict[str, Any] = structlog.get_config()
        self.configure_once: Callable = structlog.configure_once
        self.events: EventList = EventList()
        self._add_log_level = settings.use_processor("add_log_level")[0]

    def _reset(self) -> None:
        self.original_configure(**self.original_config)
        structlog.configure = self.original_configure
        structlog.configure_once = self.configure_once

    def __call__(
        self, logger: WrappedLogger, method_name: str, event_dict: EventDict
    ) -> NoReturn:
        """Captures a logging event, appending it as a dict in the event list."""
        if self._add_log_level:
            structlog.stdlib.add_log_level(logger, method_name, event_dict)
        self.events.append(event_dict)
        raise structlog.DropEvent

    def has(self, message: str, **context: Any) -> bool:
        """Returns whether the event message has been logged, with optional
        subcontext. Usage in test code would be with an assertion, e.g.:

            assert log.has("foo")
            assert log.has("bar", k1="v1", k2="v2")
        """
        context["event"] = message
        return any(is_submap(context, e) for e in self.events)

    def log(self, level: Union[int, str], event: str, **kw: Any) -> dict[str, Any]:
        """Create log event to assert against."""
        return dict(level=level_to_name(level), event=event, **kw)

    def debug(self, event: str, **kw: Any) -> dict[str, Any]:
        """Create debug-level log event to assert against."""
        return self.log(logging.DEBUG, event, **kw)

    def info(self, event: str, **kw: Any) -> dict[str, Any]:
        """Create info-level log event to assert against."""
        return self.log(logging.INFO, event, **kw)

    def warning(self, event: str, **kw: Any) -> dict[str, Any]:
        """Create warning-level log event to assert against."""
        return self.log(logging.WARNING, event, **kw)

    def error(self, event: str, **kw: Any) -> dict[str, Any]:
        """Create error-level log event to assert against."""
        return self.log(logging.ERROR, event, **kw)

    def critical(self, event: str, **kw: Any) -> dict[str, Any]:
        """Create critical-level log event to assert against."""
        return self.log(logging.CRITICAL, event, **kw)


def no_op(*args: Any, **kwargs: Any) -> None:
    """Function used to stub out the original structlog.configure method."""
    pass


def _name(obj: Callable) -> str:
    if isinstance(obj, functools.partial):
        obj = obj.func
    try:
        return obj.__qualname__
    except AttributeError:
        return type(obj).__name__


class Settings:
    """Configuration of pytest-structlog plugin from cmdline / config files"""

    def __init__(self) -> None:
        self.mode: str = "keep"  # or "evict"
        self.keep: dict[str, set[str]] = {
            "cmdline-arg": set(),
            "config-file": set(),
            "default-keep-list": {
                "add_log_level",
                "PositionalArgumentsFormatter",
                "ExceptionRenderer",
                "dict_tracebacks",
                "merge_contextvars",
            },
        }
        self.evict: dict[str, set[str]] = {
            "cmdline-arg": set(),
            "config-file": set(),
            "default-evict-list": {
                "filter_by_level",
                "TimeStamper",
                "ConsoleRenderer",
                "JSONRenderer",
                "ProcessorFormatter.wrap_for_formatter",
            },
        }
        self.report: str = "auto"

    def use_processor(self, name: str) -> tuple[bool, str]:
        """Should processor be used during test, according to plugin configuration?"""
        if self.mode == "evict":
            for reason, processor_names in self.evict.items():
                if name in processor_names:
                    return False, reason
            return True, ""
        else:
            assert self.mode == "keep"
            for reason, processor_names in self.keep.items():
                if name in processor_names:
                    return True, reason
            return False, ""

    def reset(self) -> None:
        """Resets the state of the plugin to default."""
        self.keep["config-file"].clear()
        self.evict["config-file"].clear()
        self.keep["cmdline-arg"].clear()
        self.evict["cmdline-arg"].clear()
        self.mode = "keep"
        self.report = "auto"


settings: Settings = Settings()


@pytest.fixture
def log(
    monkeypatch: MonkeyPatch, request: FixtureRequest
) -> Generator[StructuredLogCapture, None, None]:
    """Fixture providing access to captured structlog events. Interesting attributes:

        ``log.events`` a list of dicts, contains any events logged during the test
        ``log.has`` a helper method, return a bool for making simple assertions

    Example usage: ``assert log.has("some message", var1="extra context")``
    """
    capture = StructuredLogCapture()
    orig_processors = capture.original_config.get("processors", [])
    new_processors = [p for p in orig_processors if settings.use_processor(_name(p))[0]]
    new_processors.append(capture)
    structlog.configure(processors=new_processors, cache_logger_on_first_use=False)
    monkeypatch.setattr("structlog.configure", no_op)
    monkeypatch.setattr("structlog.configure_once", no_op)
    request.node.structlog_events = capture.events
    clear_contextvars()
    yield capture
    clear_contextvars()
    capture._reset()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None, None, None]:
    """Prints out a section of captured structlog events on test failures."""
    yield
    events = getattr(item, "structlog_events", [])
    content = os.linesep.join([str(e) for e in events])
    item.add_report_section("call", "structlog", content)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register argparse-style options and ini-style config values."""
    group = parser.getgroup("pytest-structlog")
    group.addoption(
        "--structlog-keep",
        action="append",
        metavar="PROCESSOR_NAME",
        help="Processors to keep if configured (may be specified multiple times).",
        default=[],
    )
    parser.addini(
        name="structlog_keep",
        help="Processors to keep if configured (list of names)",
        type="args",
        default=[],
    )
    group.addoption(
        "--structlog-evict",
        action="append",
        metavar="PROCESSOR_NAME",
        help="Processors to evict if configured (may be specified multiple times).",
        default=[],
    )
    parser.addini(
        name="structlog_evict",
        help="Processors to evict if configured (list of names)",
        type="args",
        default=[],
    )
    explicit_setting_help = (
        "Structlog processor list should be configured manually in test. Do not "
        "use default settings for 'keep' or 'evict' lists."
    )
    group.addoption(
        "--structlog-explicit",
        help=explicit_setting_help,
        action="store_true",
    )
    parser.addini(
        name="structlog_explicit",
        help=explicit_setting_help,
        type="bool",
    )
    settings_report_help = (
        "Display the configured pytest-structlog settings after test collection."
        "Default (auto) will display the report when pytest is running with increased "
        "verbosity (-v)."
    )
    group.addoption(
        "--structlog-settings-report",
        help=settings_report_help,
        choices=["always", "never", "auto"],
    )
    parser.addini(
        name="structlog_settings_report",
        help=settings_report_help,
        type="string",
        default="auto",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Perform initial plugin configuration."""
    user_keep = config.getoption("structlog_keep") or config.getini("structlog_keep")
    user_evict = config.getoption("structlog_evict") or config.getini("structlog_evict")
    settings_report = config.getoption("structlog_settings_report")
    if settings_report is None:
        settings_report = config.getini("structlog_settings_report")
        if settings_report not in ("always", "never", "auto"):
            raise pytest.UsageError(
                f"structlog_settings_report configuration value must be one of "
                f"'always', 'never', or 'auto' (got: {settings_report!r})"
            )
    settings.report = settings_report
    assert settings_report in ("always", "never", "auto"), settings_report
    if user_evict and user_keep:
        raise pytest.UsageError(
            "--structlog-keep and --structlog-evict settings are mutually "
            "exclusive. Specify one or the other, not both."
        )
    if config.getoption("structlog_explicit") or config.getini("structlog_explicit"):
        settings.keep["default-keep-list"].clear()
        settings.evict["default-evict-list"].clear()
    settings.keep["cmdline-arg"].update(config.getoption("structlog_keep"))
    settings.keep["config-file"].update(config.getini("structlog_keep"))
    settings.evict["cmdline-arg"].update(config.getoption("structlog_evict"))
    settings.evict["config-file"].update(config.getini("structlog_evict"))
    if user_evict:
        settings.mode = "evict"


def pytest_unconfigure() -> None:
    """Unconfigure the plugin before test process exits."""
    settings.reset()


def pytest_report_collectionfinish(config: pytest.Config) -> list[str]:
    """Add post-collection information about which pre-configured structlog processors
    are being used. These only show if verbosity is non-zero, i.e. the user passed -v
    or -vv when running pytest."""
    if settings.report == "never":
        return []
    verbosity = config.getoption("verbose", default=0)
    if settings.report == "auto" and not verbosity:
        return []
    tw = config.get_terminal_writer()
    lines = [" pytest-structlog settings ".center(tw.fullwidth, "=")]
    if settings.mode == "keep":
        col_mode = tw.markup("keep", green=True, bold=True)
    else:
        col_mode = tw.markup("evict", red=True, bold=True)
    lines.append(f"Plugin pytest-structlog is operating in {col_mode} mode.")
    if verbosity > 1:
        namelists = getattr(settings, settings.mode)
        for key, namelist in namelists.items():
            lines.append(f"- {key}:" + (" (empty)" if not namelist else ""))
            lines += [f"    {name}" for name in sorted(namelist)]
    for processor in structlog.get_config().get("processors", []):
        name = _name(processor)
        keep, reason = settings.use_processor(name)
        line = ["Structlog processor "]
        if keep:
            line.append(tw.markup(f"{name!r} is kept", green=True))
        else:
            line.append(tw.markup(f"{name!r} is evicted", red=True))
        if reason:
            line.append(f" due to {reason}")
        else:
            inverse_action = ["evicted", "kept"][not keep]
            line.append(f" because no configuration {inverse_action} it")
        if verbosity > 1:
            line.append(f" ({processor!r})")
        line.append(".")
        lines.append("".join(line))
    lines.append("=" * tw.fullwidth)
    return lines
