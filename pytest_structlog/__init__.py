import logging
import os
from typing import Any
from typing import cast
from typing import Generator
from typing import List
from typing import Sequence
from typing import Union

import pytest
import structlog
from structlog.contextvars import clear_contextvars
from structlog.contextvars import merge_contextvars
from structlog.typing import EventDict
from structlog.typing import Processor
from structlog.typing import WrappedLogger


__version__ = "0.7"


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


absent = object()


def level_to_name(level: Union[str, int]) -> str:
    """Given the name or number for a log-level, return the lower-case level name."""
    if isinstance(level, str):
        return level.lower()
    return cast(str, logging.getLevelName(level)).lower()


def is_submap(d1: EventDict, d2: EventDict) -> bool:
    """is every pair from d1 also in d2? (unique and order insensitive)"""
    return all(d2.get(k, absent) == v for k, v in d1.items())


def is_subseq(l1: Sequence, l2: Sequence) -> bool:
    """is every element of l1 also in l2? (non-unique and order sensitive)"""
    it = iter(l2)
    return all(d in it for d in l1)


class StructuredLogCapture(object):
    def __init__(self) -> None:
        self.events = EventList()

    def process(self, logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
        event_dict["level"] = method_name
        self.events.append(event_dict)
        raise structlog.DropEvent

    def has(self, message: str, **context: Any) -> bool:
        context["event"] = message
        return any(is_submap(context, e) for e in self.events)

    def log(self, level: Union[int, str], event: str, **kw: Any) -> dict:
        """Create log event to assert against"""
        return dict(level=level_to_name(level), event=event, **kw)

    def debug(self, event: str, **kw: Any) -> dict:
        """Create debug-level log event to assert against"""
        return self.log(logging.DEBUG, event, **kw)

    def info(self, event: str, **kw: Any) -> dict:
        """Create info-level log event to assert against"""
        return self.log(logging.INFO, event, **kw)

    def warning(self, event: str, **kw: Any) -> dict:
        """Create warning-level log event to assert against"""
        return self.log(logging.WARNING, event, **kw)

    def error(self, event: str, **kw: Any) -> dict:
        """Create error-level log event to assert against"""
        return self.log(logging.ERROR, event, **kw)

    def critical(self, event: str, **kw: Any) -> dict:
        """Create critical-level log event to assert against"""
        return self.log(logging.CRITICAL, event, **kw)


def no_op(*args: Any, **kwargs: Any) -> None:
    pass


@pytest.fixture
def log(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> Generator[StructuredLogCapture, None, None]:
    """Fixture providing access to captured structlog events. Interesting attributes:

        ``log.events`` a list of dicts, contains any events logged during the test
        ``log.has`` a helper method, return a bool for making simple assertions

    Example usage: ``assert log.has("some message", var1="extra context")``
    """
    # save settings for later
    original_processors = structlog.get_config().get("processors", [])

    # redirect logging to log capture
    cap = StructuredLogCapture()
    new_processors: List[Processor] = []
    for processor in original_processors:
        if isinstance(processor, structlog.stdlib.PositionalArgumentsFormatter):
            # if there was a positional argument formatter in there, keep it there
            # see https://github.com/wimglenn/pytest-structlog/issues/18
            new_processors.append(processor)
        elif processor is merge_contextvars:
            # if merging contextvars, preserve
            # see https://github.com/wimglenn/pytest-structlog/issues/20
            new_processors.append(processor)
    new_processors.append(cap.process)
    structlog.configure(processors=new_processors, cache_logger_on_first_use=False)
    cap.original_configure = configure = structlog.configure # type:ignore[attr-defined]
    cap.configure_once = structlog.configure_once # type:ignore[attr-defined]
    monkeypatch.setattr("structlog.configure", no_op)
    monkeypatch.setattr("structlog.configure_once", no_op)
    request.node.structlog_events = cap.events
    clear_contextvars()
    yield cap
    clear_contextvars()

    # back to original behavior
    configure(processors=original_processors)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None, None, None]:
    yield
    events = getattr(item, "structlog_events", [])
    content = os.linesep.join([str(e) for e in events])
    item.add_report_section("call", "structlog", content)
