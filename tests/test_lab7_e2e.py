"""Наскрізний тест: gateway -> MQTT -> ingest (SQLite) + alerts. Потрібен брокер на localhost:1883."""
import json
import os
import socket
import subprocess
import sys
import time

import pytest

import iiot

SRC = os.path.dirname(os.path.dirname(iiot.__file__))


def _broker_up():
    try:
        socket.create_connection(("localhost", 1883), 0.3).close()
        return True
    except OSError:
        return False


@pytest.mark.skipif(not _broker_up(), reason="немає MQTT-брокера на localhost:1883")
def test_pipeline_end_to_end(tmp_path):
    import sqlite3
    import paho.mqtt.client as mqtt
    from iiot.security import verify

    key = "e2e-key"
    env = dict(os.environ, PYTHONPATH=SRC, SIGNING_KEY=key, INTERVAL="0.1", FAULT_AFTER="1",
               DB_PATH=str(tmp_path / "t.db"), SITE="e2e", HEALTH_FILE=str(tmp_path / "h"))
    alerts = []
    sub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="e2e-sub")
    sub.on_message = lambda c, u, m: alerts.append(verify(key.encode(), m.topic, m.payload, max_age=60))
    sub.connect("localhost")
    sub.subscribe("plant/e2e/+/+/alerts", qos=1)
    sub.loop_start()
    procs = [subprocess.Popen([sys.executable, "-m", f"iiot.services.{m}"], env=env, cwd=SRC,
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
             for m in ("ingest_service", "alert_service", "gateway_service")]
    try:
        deadline = time.time() + 15
        while time.time() < deadline and not any(a["state"] == "raised" for a in alerts):
            time.sleep(0.2)
        time.sleep(1.5)
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait(timeout=5)
        sub.loop_stop()
    assert any(a["rule"] == "high_vibration" and a["state"] == "raised" for a in alerts)
    n = sqlite3.connect(tmp_path / "t.db").execute("SELECT COUNT(*) FROM telemetry").fetchone()[0]
    assert n >= 20
