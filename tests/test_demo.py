"""The demo device must speak the real protocol and never fake a measurement."""

import time

from latency_tester import protocol
from latency_tester.demo import DemoDevice
from latency_tester.serial_service import SerialService


def collect(service, seconds):
    deadline = time.time() + seconds
    events = []
    while time.time() < deadline:
        try:
            events.append(service.events.get(timeout=0.05))
        except Exception:
            pass
    return events


def test_demo_produces_samples_only_in_test_mode():
    service = SerialService()
    service.attach(DemoDevice(seed=7), "DEMO", is_demo=True)
    try:
        idle = collect(service, 0.8)
        assert not [e for e in idle if e.kind == "latency"]

        service.send(protocol.CMD_TEST_MODE_ON)
        active = collect(service, 1.6)
        assert [e for e in active if e.kind == "latency"]
    finally:
        service.close()


def test_demo_never_emits_TRIG():
    """TRIG needs a real probe and a real OS click; the demo must not simulate
    the handshake."""
    service = SerialService()
    service.attach(DemoDevice(seed=7), "DEMO", is_demo=True)
    try:
        service.send(protocol.CMD_TEST_MODE_ON)
        kinds = {e.kind for e in collect(service, 1.6)}
        assert "trig" not in kinds
    finally:
        service.close()


def test_demo_latencies_are_plausible_milliseconds():
    service = SerialService()
    service.attach(DemoDevice(seed=3), "DEMO", is_demo=True)
    try:
        service.send(protocol.CMD_TEST_MODE_ON)
        values = [e.payload["latency_ms"]
                  for e in collect(service, 2.2) if e.kind == "latency"]
    finally:
        service.close()
    assert values
    assert all(2.0 <= v <= 60.0 for v in values)


def test_demo_calibration_handshake():
    service = SerialService()
    service.attach(DemoDevice(seed=3), "DEMO", is_demo=True)
    try:
        service.start_calibration()
        collect(service, 0.3)
        service.send_calibration_ready()
        kinds = {e.kind for e in collect(service, 0.5)}
    finally:
        service.close()
    assert "cal_ok" in kinds
    assert service.calibrating is False


def test_demo_reports_light_and_is_flagged_as_demo():
    service = SerialService()
    service.attach(DemoDevice(seed=3), "DEMO", is_demo=True)
    try:
        assert service.is_demo is True
        service.send(protocol.CMD_LIGHT)
        lights = [e.payload for e in collect(service, 0.5) if e.kind == "light"]
    finally:
        service.close()
    assert lights and 0 <= lights[0] <= 1023
