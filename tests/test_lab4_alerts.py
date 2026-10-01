from iiot.alerts import AlertEngine, Rule


def m(v, dev="p1", ts=0):
    return {"device_id": dev, "ts": ts, "metrics": {"vibration_mm_s": v}}


def engine():
    return AlertEngine([Rule("hv", "vibration_mm_s", high=4.5, hysteresis=0.5, debounce=3, severity="critical")])


def states(eng, values, dev="p1"):
    out = []
    for v in values:
        out += [e["state"] for e in eng.process(m(v, dev))]
    return out


def test_debounce_requires_consecutive_breaches():
    assert states(engine(), [5, 5, 1, 5, 5, 1]) == []
    assert states(engine(), [5, 5, 5]) == ["raised"]


def test_raised_only_once():
    assert states(engine(), [5] * 10) == ["raised"]


def test_hysteresis_clear():
    # 4.2 нижче порога, але не нижче high-hysteresis=4.0 => ще не знімаємо
    assert states(engine(), [5, 5, 5, 4.2, 4.2]) == ["raised"]
    assert states(engine(), [5, 5, 5, 4.2, 3.9]) == ["raised", "cleared"]


def test_event_fields_and_independent_devices():
    e = engine()
    ev = []
    for v in (5, 5, 5):
        ev += e.process(m(v, "a", ts=10))
    assert ev[0] == {"rule": "hv", "device_id": "a", "metric": "vibration_mm_s", "state": "raised",
                     "value": 5, "ts": 10, "severity": "critical"}
    assert states(e, [5, 5], dev="b") == []  # окремий стан для пристрою b


def test_unknown_metric_ignored():
    assert engine().process({"device_id": "a", "ts": 0, "metrics": {"x": 1}}) == []
