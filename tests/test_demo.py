"""The demo device must speak the real protocol and never fake a measurement."""

import queue
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
        except queue.Empty:
            continue
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


def test_demo_reports_an_optical_calibration_on_request():
    service = SerialService()
    service.attach(DemoDevice(seed=7), "DEMO", is_demo=True)
    try:
        service.send(protocol.CMD_CAL_DARK)
        service.send(protocol.CMD_CAL_BRIGHT)
        service.send(protocol.CMD_CAL_REPORT)
        cals = [e for e in collect(service, 0.9) if e.kind == "optical_cal"]
        assert cals
        payload = cals[-1]
        # The demo must produce a calibration the dashboard would accept, or the
        # optical UI cannot be exercised without hardware.
        assert protocol.optical_threshold(payload.payload["dark"],
                                          payload.payload["bright"]) is not None
        assert payload.payload["rising"] is True
    finally:
        service.close()


def test_demo_switches_to_optical_samples():
    """Probe-to-Photon must be reachable without hardware, and must produce
    ``optical`` events rather than ``latency`` ones."""
    service = SerialService()
    service.attach(DemoDevice(seed=7), "DEMO", is_demo=True)
    try:
        service.send(protocol.CMD_PHOTON_ON)
        service.send(protocol.CMD_TEST_MODE_ON)
        events = collect(service, 1.8)
        kinds = [e.kind for e in events]
        assert "photon_on" in kinds
        optical = [e for e in events if e.kind == "optical"]
        assert optical
        assert "latency" not in kinds
        # Every optical sample carries the raw reading that produced it.
        assert all(e.payload["raw_optical"] > 0 for e in optical)
    finally:
        service.close()


def test_demo_optical_latencies_are_slower_than_serial_ones():
    """Click-to-photon includes the display, so it cannot be faster."""
    service = SerialService()
    service.attach(DemoDevice(seed=11), "DEMO", is_demo=True)
    try:
        service.send(protocol.CMD_PHOTON_ON)
        service.send(protocol.CMD_TEST_MODE_ON)
        values = [e.payload["latency_ms"]
                  for e in collect(service, 1.8) if e.kind == "optical"]
        assert values
        assert all(v > 8.0 for v in values)
    finally:
        service.close()


def test_demo_leaves_optical_mode_on_request():
    service = SerialService()
    service.attach(DemoDevice(seed=7), "DEMO", is_demo=True)
    try:
        service.send(protocol.CMD_PHOTON_ON)
        collect(service, 0.3)
        service.send(protocol.CMD_PHOTON_OFF)
        service.send(protocol.CMD_TEST_MODE_ON)
        events = collect(service, 1.6)
        assert "photon_off" in [e.kind for e in events]
        assert [e for e in events if e.kind == "latency"]
        assert not [e for e in events if e.kind == "optical"]
    finally:
        service.close()


def test_demo_reset_clears_the_optical_counter():
    service = SerialService()
    service.attach(DemoDevice(seed=7), "DEMO", is_demo=True)
    try:
        service.send(protocol.CMD_PHOTON_ON)
        service.send(protocol.CMD_TEST_MODE_ON)
        first = [e for e in collect(service, 1.6) if e.kind == "optical"]
        assert first
        service.send(protocol.CMD_RESET)
        after = [e for e in collect(service, 1.2) if e.kind == "optical"]
        assert after
        # Numbering restarts, so a reset really is a new run.
        assert after[0].payload["firmware_n"] < first[-1].payload["firmware_n"]
    finally:
        service.close()
