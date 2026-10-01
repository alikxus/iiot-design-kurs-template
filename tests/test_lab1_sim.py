from statistics import mean

import pytest

from iiot.sim import PumpSimulator


def test_message_schema():
    msg = PumpSimulator("p1", seed=1).step(now=1000.0)
    assert msg["device_id"] == "p1" and msg["ts"] == 1000.0 and msg["running"] is True
    assert set(msg["metrics"]) == {"vibration_mm_s", "temperature_c", "pressure_bar", "current_a"}


def test_seed_is_deterministic():
    a, b = PumpSimulator(seed=7), PumpSimulator(seed=7)
    assert [a.step(now=0)["metrics"] for _ in range(20)] == [b.step(now=0)["metrics"] for _ in range(20)]


def test_healthy_ranges():
    sim = PumpSimulator(seed=2)
    vib = [sim.step(now=0)["metrics"]["vibration_mm_s"] for _ in range(100)]
    assert 1.0 < mean(vib) < 2.8


def test_stopped_pump():
    sim = PumpSimulator(seed=3)
    sim.running = False
    m = sim.step(now=0)["metrics"]
    assert m["pressure_bar"] == 0 and m["current_a"] == 0 and m["vibration_mm_s"] < 0.2


def test_wear_increases_vibration():
    sim = PumpSimulator(seed=4, wear_rate=0.004)
    v = [sim.step(now=0)["metrics"]["vibration_mm_s"] for _ in range(200)]
    assert mean(v[-20:]) > mean(v[:20]) + 2


def test_faults():
    sim = PumpSimulator(seed=5)
    sim.inject_fault("bearing")
    assert sim.wear >= 0.6
    sim2 = PumpSimulator(seed=5)
    base = sim2.step(now=0)["metrics"]["pressure_bar"]
    sim2.inject_fault("clog")
    assert sim2.step(now=0)["metrics"]["pressure_bar"] < base - 0.5
    with pytest.raises(ValueError):
        sim.inject_fault("magic")
