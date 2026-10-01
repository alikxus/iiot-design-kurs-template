import math
import random

from iiot.analytics import RollingZ, detect_anomalies, estimate_rul, ewma, linear_trend


def test_ewma():
    assert ewma([10, 10, 10]) == [10, 10, 10]
    out = ewma([0, 10], alpha=0.5)
    assert out == [0, 5.0]


def test_rollingz_warmup_and_spike():
    rz = RollingZ(window=20, min_samples=10)
    rng = random.Random(1)
    zs = [rz.update(2 + rng.gauss(0, 0.1)) for _ in range(15)]
    assert all(z is None for z in zs[:10]) and all(z is not None for z in zs[10:])
    assert abs(rz.update(5.0)) > 10


def test_detect_anomalies_finds_spikes_only():
    rng = random.Random(3)
    data = [2 + rng.gauss(0, 0.1) for _ in range(100)]
    data[60] += 3
    data[85] -= 3
    assert detect_anomalies(data, window=30, threshold=4) == [60, 85]


def test_linear_trend():
    slope, icpt = linear_trend([0, 1, 2, 3], [1, 3, 5, 7])
    assert math.isclose(slope, 2) and math.isclose(icpt, 1)


def test_rul():
    ts = list(range(0, 100, 10))
    vals = [2 + 0.01 * t for t in ts]          # зростає на 0.01/с; у ts=90 значення 2.9
    rul = estimate_rul(ts, vals, limit=4.5)    # межа на t=250 => 160 с
    assert math.isclose(rul, 160, rel_tol=1e-6)
    assert estimate_rul(ts, vals, limit=2.5) == 0.0
    assert estimate_rul(ts, [3] * 10, limit=4.5) is None
    assert estimate_rul(ts, [3 - 0.01 * t for t in ts], limit=4.5) is None
