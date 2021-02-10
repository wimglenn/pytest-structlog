import structlog


logger = structlog.get_logger("test")


def spline_reticulator():
    logger.info("reticulating splines", n_splines=123)


def main_ish():
    structlog.configure(processors=[])
    # this configure call should be a no-op after fixture was injected
    logger.debug("yo")


def binding():
    log = logger.bind(k="v")
    log.debug("dbg")
    log.info("inf", kk="more context")
    log = log.unbind("k")
    log.warning("uh-oh")


def test_capture_creates_items(log):
    assert not log.events
    spline_reticulator()
    assert log.events


def test_assert_without_context(log):
    spline_reticulator()
    assert log.has("reticulating splines")


def test_assert_with_subcontext(log):
    spline_reticulator()
    assert log.has("reticulating splines", n_splines=123)


def test_assert_with_bogus_context(log):
    spline_reticulator()
    assert not log.has("reticulating splines", n_splines=0)


def test_assert_with_all_context(log):
    spline_reticulator()
    assert log.has("reticulating splines", n_splines=123, level="info")


def test_assert_with_super_context(log):
    spline_reticulator()
    assert not log.has("reticulating splines", n_splines=123, level="info", k="v")


def test_configurator(log):
    main_ish()
    assert log.has("yo", level="debug")


def test_multiple_events(log):
    binding()
    assert log.has("dbg", k="v", level="debug")
    assert log.has("inf", k="v", kk="more context", level="info")


def test_length(log):
    binding()
    assert len(log.events) == 3


d0, d1, d2 = [
    {"event": "dbg", "k": "v", "level": "debug"},
    {"event": "inf", "k": "v", "level": "info", "kk": "more context"},
    {"event": "uh-oh", "level": "warning"},
]


def test_membership(log):
    binding()
    assert d0 in log.events


def test_superset_single(log):
    binding()
    assert log.events >= [d0]


def test_superset_multi(log):
    binding()
    assert log.events >= [d0, d2]


def test_superset_respects_ordering(log):
    binding()
    assert not log.events >= [d2, d0]


def test_superset_multi_all(log):
    binding()
    assert log.events >= [d0, d1, d2]


def test_superset_multi_strict(log):
    binding()
    assert not log.events > [d0, d1, d2]


def test_equality(log):
    binding()
    assert log.events == [d0, d1, d2]


def test_inequality(log):
    binding()
    assert log.events != [d0, {}, d1, d2]


def test_total_ordering(log):
    binding()
    assert log.events <= [d0, d1, d2, {}]
    assert log.events < [d0, d1, d2, {}]
    assert log.events > [d0, d1]


def test_dupes(log):
    logger.info("a")
    logger.info("a")
    logger.info("b")
    assert log.events >= [{"event": "a", "level": "info"}]
    assert log.events >= [{"event": "a", "level": "info"}, {"event": "b", "level": "info"}]
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
