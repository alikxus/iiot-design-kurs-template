import json
import random

import pytest

from iiot.security import (ExpiredError, InvalidSignature, NonceCache, ReplayError,
                           backoff_delays, generate_acl, sign, verify)

KEY = b"super-secret"
TOPIC = "plant/s/l/d/telemetry"
PAYLOAD = {"device_id": "d", "metrics": {"a": 1.5}}


def test_sign_verify_roundtrip():
    raw = sign(KEY, TOPIC, PAYLOAD, ts=1000.0)
    assert verify(KEY, TOPIC, raw, now=1005.0) == PAYLOAD


def test_tamper_detected():
    env = json.loads(sign(KEY, TOPIC, PAYLOAD, ts=1000.0))
    env["payload"]["metrics"]["a"] = 99
    with pytest.raises(InvalidSignature):
        verify(KEY, TOPIC, json.dumps(env), now=1000.0)


def test_wrong_key_wrong_topic_garbage():
    raw = sign(KEY, TOPIC, PAYLOAD, ts=1000.0)
    with pytest.raises(InvalidSignature):
        verify(b"other", TOPIC, raw, now=1000.0)
    with pytest.raises(InvalidSignature):
        verify(KEY, "plant/s/l/other/telemetry", raw, now=1000.0)
    with pytest.raises(InvalidSignature):
        verify(KEY, TOPIC, b"garbage", now=1000.0)


def test_expired():
    raw = sign(KEY, TOPIC, PAYLOAD, ts=1000.0)
    with pytest.raises(ExpiredError):
        verify(KEY, TOPIC, raw, max_age=30, now=1100.0)


def test_replay_blocked_and_cache_ttl():
    raw = sign(KEY, TOPIC, PAYLOAD, ts=1000.0, nonce="n1")
    cache = NonceCache(ttl=60)
    verify(KEY, TOPIC, raw, cache=cache, now=1001.0)
    with pytest.raises(ReplayError):
        verify(KEY, TOPIC, raw, cache=cache, now=1002.0)
    assert cache.check_and_add("n1", now=1200.0) is True  # TTL минув


def test_backoff():
    g = backoff_delays(base=1, factor=2, cap=10)
    assert [next(g) for _ in range(6)] == [1, 2, 4, 8, 10, 10]
    gj = backoff_delays(base=10, factor=1, cap=10, jitter=0.2, rng=random.Random(1))
    vals = [next(gj) for _ in range(50)]
    assert all(8 <= v <= 12 for v in vals) and len(set(vals)) > 1


def test_acl():
    acl = generate_acl(["pump-01", "pump-02"])
    assert "user pump-01\ntopic write plant/+/+/pump-01/#" in acl
    assert "user ingest\ntopic read plant/#" in acl
    assert "pump-02" in acl and "topic write plant/+/+/+/alerts" in acl
