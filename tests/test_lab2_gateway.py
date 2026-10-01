import socket
import threading
import time

import pytest

from iiot.gateway import Gateway, OfflineBuffer, build_topic, decode, encode


class FakeClient:
    def __init__(self):
        self.published, self.will = [], None

    def will_set(self, topic, payload, qos=0, retain=False):
        self.will = (topic, payload, qos, retain)

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))


def test_topic():
    assert build_topic("kyiv", "line1", "pump-01") == "plant/kyiv/line1/pump-01/telemetry"
    assert build_topic("kyiv", "line1", "pump-01", "status").endswith("/status")


def test_roundtrip():
    msg = {"device_id": "p", "ts": 1.5, "metrics": {"a": 1}}
    assert decode(encode(msg)) == msg


def test_buffer_overflow_drops_oldest():
    b = OfflineBuffer(3)
    for i in range(5):
        b.push(i)
    assert len(b) == 3 and b.dropped == 2 and b.drain() == [2, 3, 4] and len(b) == 0


def test_gateway_lwt_set_on_init():
    c = FakeClient()
    Gateway(c, "s", "l", "d")
    topic, payload, qos, retain = c.will
    assert topic == "plant/s/l/d/status" and retain and qos == 1 and decode(payload)["state"] == "offline"


def test_gateway_buffers_then_flushes_in_order():
    c = FakeClient()
    gw = Gateway(c, "s", "l", "d")
    for i in range(3):
        gw.publish({"i": i})
    assert c.published == [] and len(gw.buffer) == 3
    gw.on_connect()
    kinds = [(t.split("/")[-1], retain) for t, _, _, retain in c.published]
    assert kinds[0] == ("status", True)
    assert [decode(p)["i"] for t, p, *_ in c.published if t.endswith("telemetry")] == [0, 1, 2]
    gw.publish({"i": 3})
    assert all(q == 1 for _, _, q, _ in c.published)
    assert decode(c.published[-1][1])["i"] == 3
    gw.on_disconnect()
    gw.publish({"i": 4})
    assert len(gw.buffer) == 1


def _broker_up():
    try:
        socket.create_connection(("localhost", 1883), 0.3).close()
        return True
    except OSError:
        return False


@pytest.mark.skipif(not _broker_up(), reason="немає MQTT-брокера на localhost:1883")
def test_integration_with_real_broker():
    import paho.mqtt.client as mqtt
    from iiot.gateway import make_client

    got = []
    sub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="t-sub")
    sub.on_message = lambda c, u, m: got.append((m.topic, decode(m.payload)))
    sub.connect("localhost")
    sub.subscribe("plant/#", qos=1)
    sub.loop_start()
    time.sleep(0.3)

    cl = make_client("t-gw")
    gw = Gateway(cl, "s", "l", "d1")
    cl.on_connect, cl.on_disconnect = gw.on_connect, gw.on_disconnect
    cl.connect("localhost")
    cl.loop_start()
    gw.publish({"i": 1})  # може піти у буфер, якщо ще не підключились
    time.sleep(1.0)
    gw.publish({"i": 2})
    time.sleep(0.5)
    cl.loop_stop(); sub.loop_stop()
    topics = [t for t, _ in got]
    assert "plant/s/l/d1/status" in topics
    assert [p["i"] for t, p in got if t.endswith("telemetry")] == [1, 2]
