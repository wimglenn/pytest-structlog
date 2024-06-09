from functools import partial

from pytest_structlog import _name


def proc1(logger, method_name, event_dict):
    return event_dict


class Processor:
    def proc2(self, logger, method_name, event_dict):
        return event_dict

    @classmethod
    def proc3(cls, logger, method_name, event_dict):
        return event_dict

    @staticmethod
    def proc4(logger, method_name, event_dict):
        return event_dict

    def __call__(self, logger, method_name, event_dict):
        return event_dict


proc5 = partial(proc1, method_name="info")


proc6 = lambda logger, method_name, event_dict: event_dict


def test_processor_name_function():
    assert _name(proc1) == "proc1"


def test_processor_name_method():
    assert _name(Processor().proc2) == "Processor.proc2"


def test_processor_name_classmethod():
    assert _name(Processor.proc3) == "Processor.proc3"
    assert _name(Processor().proc3) == "Processor.proc3"


def test_processor_name_staticmethod():
    assert _name(Processor.proc4) == "Processor.proc4"
    assert _name(Processor().proc4) == "Processor.proc4"


def test_processor_name_callable_class():
    assert _name(Processor()) == "Processor"


def test_processor_name_partial():
    assert _name(proc5) == "proc1"


def test_processor_name_anon():
    assert _name(proc6) == "<lambda>"
