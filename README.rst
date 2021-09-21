|actions|_ |pypi|_ |pyversions|_ |womm|_

.. |actions| image:: https://github.com/wimglenn/pytest-structlog/actions/workflows/tests.yml/badge.svg
.. _actions: https://github.com/wimglenn/pytest-structlog/actions/workflows/tests.yml/

.. |pypi| image:: https://img.shields.io/pypi/v/pytest-structlog.svg
.. _pypi: https://pypi.org/project/pytest-structlog

.. |pyversions| image:: https://img.shields.io/pypi/pyversions/pytest-structlog.svg
.. _pyversions:

.. |womm| image:: https://cdn.rawgit.com/nikku/works-on-my-machine/v0.2.0/badge.svg
.. _womm: https://github.com/nikku/works-on-my-machine


pytest-structlog
================

Structured logging assertions.  pytest_ + structlog_ = ``pytest-structlog``.

|pytest|    |structlog|


Installation:
-------------

.. code-block:: bash

   $ pip install pytest-structlog

Usage:
------

The fixture name is ``log``. It has two attributes of interest: ``log.events`` is a list of events from captured log calls, and ``log.has`` is a helper function for asserting a single event was logged within the expected context.

Suppose you have some library module, ``your_lib``, which is using ``structlog``:

.. code-block:: python

   # your_lib.py
   from structlog import get_logger

   logger = get_logger()

   def spline_reticulator():
       logger.info("reticulating splines")
       for i in range(3):
           logger.debug("processing", spline=i)
       logger.info("reticulated splines", n_splines=3)


Then your test suite might use assertions such as shown below:

.. code-block:: python

   # test_your_lib.py
   from your_lib import spline_reticulator

   def test_spline_reticulator(log):
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


.. _pytest: https://docs.pytest.org/
.. _structlog: https://www.structlog.org/
.. |pytest| image:: https://user-images.githubusercontent.com/6615374/46903931-515eef00-cea2-11e8-8945-980ddbf0a053.png
.. |structlog| image:: https://user-images.githubusercontent.com/6615374/46903937-5b80ed80-cea2-11e8-9b85-d3f071180fe1.png
