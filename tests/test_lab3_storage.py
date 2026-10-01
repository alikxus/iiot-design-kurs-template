from types import SimpleNamespace

from iiot.storage import Ingestor, downsample_1m, init_db, insert_batch, last_n, purge_older_than


def msg(ts, vib=1.0, temp=50.0, dev="p1"):
    return {"device_id": dev, "ts": ts, "metrics": {"vibration_mm_s": vib, "temperature_c": temp}}


def test_insert_and_last_n():
    db = init_db()
    assert insert_batch(db, [msg(t, vib=t) for t in (3, 1, 2, 4)]) == 8
    assert last_n(db, "p1", "vibration_mm_s", 3) == [(2, 2.0), (3, 3.0), (4, 4.0)]
    assert last_n(db, "other", "vibration_mm_s", 3) == []


def test_downsample_and_idempotent():
    db = init_db()
    insert_batch(db, [msg(0, 1), msg(30, 3), msg(61, 10)])
    downsample_1m(db, before_ts=120)
    downsample_1m(db, before_ts=120)  # повторний виклик не дублює
    rows = db.execute("SELECT bucket, avg, min, max, n FROM telemetry_1m "
                      "WHERE metric='vibration_mm_s' ORDER BY bucket").fetchall()
    assert rows == [(0, 2.0, 1.0, 3.0, 2), (60, 10.0, 10.0, 10.0, 1)]


def test_purge():
    db = init_db()
    insert_batch(db, [msg(t) for t in (10, 20, 30)])
    assert purge_older_than(db, 25) == 4
    assert len(last_n(db, "p1", "vibration_mm_s", 10)) == 1


def test_ingestor_batches_and_skips_garbage():
    db = init_db()
    import json
    ing = Ingestor(db, decoder=lambda payload, topic: json.loads(payload), batch_size=2)
    mk = lambda body: SimpleNamespace(payload=body, topic="t")
    ing.on_message(None, None, mk(b"not json"))
    ing.on_message(None, None, mk(json.dumps(msg(1)).encode()))
    assert last_n(db, "p1", "vibration_mm_s", 5) == []
    ing.on_message(None, None, mk(json.dumps(msg(2)).encode()))
    assert len(last_n(db, "p1", "vibration_mm_s", 5)) == 2
    assert ing.flush() == 0
