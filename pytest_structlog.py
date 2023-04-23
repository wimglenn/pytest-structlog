import logging
import os

import pytest
import structlog

try:
    from structlog.contextvars import merge_contextvars
    from structlog.contextvars import clear_contextvars
except ImportError:
    # structlog < 20.1.0
    # use a "missing" sentinel to avoid a NameError later on
    merge_contextvars = object()
    clear_contextvars = lambda *a, **kw: None  # noqa


__version__ = "0.6"


class EventList(list):
    """A list subclass that overrides ordering operations.
    Instead of A <= B being a lexicographical comparison,
    now it means every element of A is contained within B,
    in the same order, although there may be other items
    interspersed throughout (i.e. A is a subsequence of B)
    """

    def __ge__(self, other):
        return is_subseq(other, self)

    def __gt__(self, other):
        return len(self) > len(other) and is_subseq(other, self)

    def __le__(self, other):
        return is_subseq(self, other)

    def __lt__(self, other):
        return len(self) < len(other) and is_subseq(self, other)


absent = object()


def level_to_name(level):
    """Given the name or number for a log-leve, return the
    lower-case level name."""
    if isinstance(level, str):
        return level.lower()
    try:
        return logging._levelToName[level].lower()
    except KeyError:
        raise ValueError("Unknown level number " + str(level))


def is_submap(d1, d2):
    """is every pair from d1 also in d2? (unique and order insensitive)"""
    return all(d2.get(k, absent) == v for k, v in d1.items())


def is_subseq(l1, l2):
    """is every element of l1 also in l2? (non-unique and order sensitive)"""
    it = iter(l2)
    return all(d in it for d in l1)


class StructuredLogCapture(object):
    def __init__(self):
        self.events = EventList()

    def process(self, logger, method_name, event_dict):
        event_dict["level"] = method_name
        self.events.append(event_dict)
        raise structlog.DropEvent

    def has(self, message, **context):
        context["event"] = message
        return any(is_submap(context, e) for e in self.events)

    def log(self, level, event, **kw):
        """Create log event to assert against"""
        return {"level": level_to_name(level), "event": event, **kw}

    def debug(self, event, **kw):
        """Create debug-level log event to assert against"""
        return self.log(logging.DEBUG, event, **kw)

    def info(self, event, **kw):
        """Create info-level log event to assert against"""
        return self.log(logging.INFO, event, **kw)

    def warning(self, event, **kw):
        """Create warning-level log event to assert against"""
        return self.log(logging.WARNING, event, **kw)

    def error(self, event, **kw):
        """Create error-level log event to assert against"""
        return self.log(logging.ERROR, event, **kw)

    def critical(self, event, **kw):
        """Create critical-level log event to assert against"""
        return self.log(logging.CRITICAL, event, **kw)


def no_op(*args, **kwargs):
    pass


@pytest.fixture
def log(monkeypatch, request):
    """Fixture providing access to captured structlog events. Interesting attributes:

        ``log.events`` a list of dicts, contains any events logged during the test
        ``log.has`` a helper method, return a bool for making simple assertions

    Example usage: ``assert log.has("some message", var1="extra context")``
    """
    # save settings for later
    original_processors = structlog.get_config().get("processors", [])

    # redirect logging to log capture
    cap = StructuredLogCapture()
    new_processors = []
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
    cap.original_configure = configure = structlog.configure
    cap.configure_once = structlog.configure_once
    monkeypatch.setattr("structlog.configure", no_op)
    monkeypatch.setattr("structlog.configure_once", no_op)
    request.node.structlog_events = cap.events
    clear_contextvars()
    yield cap
    clear_contextvars()

    # back to original behavior
    configure(processors=original_processors)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_call(item):
    yield
    events = getattr(item, "structlog_events", [])
    content = os.linesep.join([str(e) for e in events])
    item.add_report_section("call", "structlog", content)
