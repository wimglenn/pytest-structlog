[![actions](https://github.com/wimglenn/pytest-structlog/actions/workflows/tests.yml/badge.svg)](https://github.com/wimglenn/pytest-structlog/actions/workflows/tests.yml)
[![pypi](https://img.shields.io/pypi/v/pytest-structlog.svg)](https://pypi.org/project/pytest-structlog/)
![womm](https://cdn.rawgit.com/nikku/works-on-my-machine/v0.2.0/badge.svg)

# pytest-structlog

Structured logging assertions.
[pytest](https://docs.pytest.org/) + [structlog](https://www.structlog.org/) = `pytest-structlog`.

![pytest](https://user-images.githubusercontent.com/6615374/46903931-515eef00-cea2-11e8-8945-980ddbf0a053.png)
![structlog](https://user-images.githubusercontent.com/6615374/46903937-5b80ed80-cea2-11e8-9b85-d3f071180fe1.png)

## Installation:

``` bash
$ pip install pytest-structlog
```

## Usage:

The fixture name is `log`.
It has two attributes of interest: `log.events` is a list of events from captured log calls, and `log.has` is a helper function for asserting a single event was logged within the expected context.

Suppose you have some library module, `your_lib`, which is using
`structlog`:

``` python
# your_lib.py
from structlog import get_logger

logger = get_logger()

def spline_reticulator():
    logger.info("reticulating splines")
    for i in range(3):
        logger.debug("processing", spline=i)
    logger.info("reticulated splines", n_splines=3)
```

Then your test suite might use assertions such as shown below:

``` python
# test_your_lib.py
from your_lib import spline_reticulator
import pytest_structlog

def test_spline_reticulator(log: pytest_structlog.StructuredLogCapture):
    assert len(log.events) == 0
    spline_reticulator()
    assert len(log.events) == 5

    # can assert on the event only
    assert log.has("reticulating splines")

    # can assert with subcontext
    assert log.has("reticulated splines")
    assert log.has("reticulated splines", n_splines=3)
    assert log.has("reticulated splines", n_splines=3, level="info")

    # but not incorrect context
    assert not log.has("reticulated splines", n_splines=42)
    assert not log.has("reticulated splines", key="bogus")

    # can assert with the event dicts directly
    assert log.events == [
        {"event": "reticulating splines", "level": "info"},
        {"event": "processing", "level": "debug", "spline": 0},
        {"event": "processing", "level": "debug", "spline": 1},
        {"event": "processing", "level": "debug", "spline": 2},
        {"event": "reticulated splines", "level": "info", "n_splines": 3},
    ]

    # can use friendly factory methods for the events to assert on
    assert log.events == [
        log.info("reticulating splines"),
        log.debug("processing", spline=0),
        log.debug("processing", spline=1),
        log.debug("processing", spline=2),
        log.info("reticulated splines", n_splines=3),
    ]

    # can use membership to check for a single event's data
    assert {"event": "reticulating splines", "level": "info"} in log.events

    # can use >= to specify only the events you're interested in
    assert log.events >= [
        {"event": "processing", "level": "debug", "spline": 0},
        {"event": "processing", "level": "debug", "spline": 2},
    ]

    # or put the comparison the other way around if you prefer
    assert [
        {"event": "processing", "level": "debug", "spline": 0},
        {"event": "processing", "level": "debug", "spline": 2},
    ] <= log.events

    # note: comparisons are order sensitive!
    assert not [
        {"event": "processing", "level": "debug", "spline": 2},
        {"event": "processing", "level": "debug", "spline": 0},
    ] <= log.events
```

## Advanced configuration

By default, `pytest-structlog` attempts to nerf any pre-existing structlog configuration and set up a list of processors suitable for testing purposes.
Sometimes more control over this setup may be desired, for example if the code under test uses custom processors which should be kept even during testing.

For these purposes, the plugin provides options to override the testing processors:

``` bash
$ pytest --help | grep structlog --after=2
pytest-structlog:
  --structlog-keep=PROCESSOR_NAME
                        Processors to keep if configured (may be specified
                        multiple times).
  --structlog-evict=PROCESSOR_NAME
                        Processors to evict if configured (may be specified
                        multiple times).
...
  structlog_keep (args):
                        Processors to keep if configured (list of names)
  structlog_evict (args):
                        Processors to evict if configured (list of names)
```

Indicate that some specific processors should be kept during testing with:

``` bash
pytest --structlog-keep my_processor1 --structlog-keep MyProcessor2
```

Or write this directly in config files, e.g. in `pyproject.toml`:

``` toml
[tool.pytest.ini_options]
structlog_keep = ["my_processor1", "MyProcessor2"]
```

Sometimes, instead of listing processors to keep, it may be more convenient to list which processors to _exclude_ during testing. In this case you may specify an eviction list:

``` toml
[tool.pytest.ini_options]
structlog_evict = ["TimeStamper", "JSONRender"]
```

You may only use "keep" or "evict" mode. It is an error to specify both.

For complete control over which processors should be used in testing, the best way would be to add a `structlog.configure()` call directly in your `conftest.py` file and use `--structlog-explicit` (or set `structlog_explicit = true`) when running pytest to disable automatic processors selection entirely.

Using `pytest -v` or `pytest -vv` you can see more details about which processors `pytest-structlog` has included or excluded during the test startup.
The reporting of pytest-structlog's own settings can also be explicitly enabled/disabled independently of verbosity level by specifying `--structlog-settings-report always/never` (cmdline) or `structlog_settings_report` (ini).
