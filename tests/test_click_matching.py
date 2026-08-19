"""The TRIG <-> OS click association.

This is the rule that decides whether a physical press becomes a measurement,
so it is tested directly rather than through the serial thread.
"""

import queue
import time

import pytest

from latency_tester import protocol
from latency_tester.serial_service import (CLICK_GRACE_NS, ClickTracker,
                                           SerialService)

NS = 1_000_000_000


@pytest.fixture
def tracker():
    return ClickTracker()


def test_click_just_before_trig_matches(tracker):
    now = 10 * NS
    tracker.record(now - int(0.010 * NS))       # 10 ms before TRIG
    assert tracker.try_consume(now) is True


def test_click_after_trig_matches(tracker):
    now = 10 * NS
    tracker.record(now + int(0.005 * NS))       # HID arrived slightly later
    assert tracker.try_consume(now) is True


def test_no_click_at_all_does_not_match(tracker):
    assert tracker.try_consume(10 * NS) is False


def test_click_older_than_the_grace_window_does_not_match(tracker):
    now = 10 * NS
    tracker.record(now - CLICK_GRACE_NS - 1)
    assert tracker.try_consume(now) is False


def test_click_exactly_at_the_grace_boundary_matches(tracker):
    now = 10 * NS
    tracker.record(now - CLICK_GRACE_NS)
    assert tracker.try_consume(now) is True


def test_one_click_cannot_be_consumed_twice(tracker):
    """A duplicate TRIG must not turn one press into two samples."""
    now = 10 * NS
    tracker.record(now - int(0.01 * NS))
    assert tracker.try_consume(now) is True
    assert tracker.try_consume(now + int(0.05 * NS)) is False


def test_a_new_click_matches_the_next_trig(tracker):
    first = 10 * NS
    tracker.record(first - int(0.01 * NS))
    assert tracker.try_consume(first) is True

    second = 11 * NS
    tracker.record(second - int(0.01 * NS))
    assert tracker.try_consume(second) is True


def test_reset_forgets_history(tracker):
    tracker.record(10 * NS)
    assert tracker.try_consume(10 * NS) is True
    tracker.reset()
    tracker.record(10 * NS)
    assert tracker.try_consume(10 * NS) is True


# ----------------------------------------------------- service behaviour ----
class FakeTransport:
    """Replays scripted lines and records everything written back."""

    def __init__(self, lines):
        self.incoming = queue.Queue()
        for line in lines:
            self.incoming.put((line + "\n").encode())
        self.written = []
        self.closed = False

    def write(self, data):
        self.written.append(data.decode().strip())
        return len(data)

    def flush(self):
        pass

    def readline(self):
        try:
            return self.incoming.get(timeout=0.05)
        except queue.Empty:
            return b""

    def close(self):
        self.closed = True


def drain(service, timeout=1.5):
    kinds = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            kinds.append(service.events.get(timeout=0.05).kind)
        except queue.Empty:
            if not service.connected:
                break
    return kinds


def test_trig_with_a_matching_click_answers_H():
    transport = FakeTransport(["TRIG"])
    service = SerialService()
    service.attach(transport, "FAKE")
    service.clicks.record(time.perf_counter_ns())
    time.sleep(0.4)
    service.close()
    assert protocol.REPLY_CLICK_SEEN in transport.written
    assert protocol.REPLY_NO_CLICK not in transport.written


def test_trig_without_a_click_answers_X_and_reports_it():
    transport = FakeTransport(["TRIG"])
    service = SerialService()
    service.attach(transport, "FAKE")
    kinds = drain(service, timeout=2.0)
    service.close()
    assert protocol.REPLY_NO_CLICK in transport.written
    assert protocol.REPLY_CLICK_SEEN not in transport.written
    assert "trig_unmatched" in kinds


def test_trig_is_refused_without_waiting_when_the_target_is_reached():
    transport = FakeTransport(["TRIG"])
    service = SerialService()
    service.accept_trig = lambda: False
    service.clicks.record(time.perf_counter_ns())
    started = time.perf_counter()
    service.attach(transport, "FAKE")
    time.sleep(0.3)
    service.close()
    assert protocol.REPLY_NO_CLICK in transport.written
    # It must answer immediately instead of burning the 1 s click timeout.
    assert time.perf_counter() - started < 1.0


def test_calibration_ping_is_echoed_only_while_calibrating():
    transport = FakeTransport(["P", "P"])
    service = SerialService()
    service.attach(transport, "FAKE")
    time.sleep(0.3)
    service.close()
    assert transport.written == []

    transport = FakeTransport(["P", "P"])
    service = SerialService()
    service.calibrating = True
    service.attach(transport, "FAKE")
    time.sleep(0.3)
    service.close()
    assert transport.written == [protocol.REPLY_CALIB_PING] * 2


def test_calibration_flag_clears_on_result():
    transport = FakeTransport(
        ["CALIB_OK:267,samples:48,min_us:120,max_us:1500,avg_rt:534"])
    service = SerialService()
    service.calibrating = True
    service.attach(transport, "FAKE")
    drain(service, timeout=0.6)
    service.close()
    assert service.calibrating is False


def test_firmware_version_is_captured_from_the_banner():
    service = SerialService()
    service.attach(FakeTransport(["LATENCY_TESTER v1.3 OLED+LDR"]), "FAKE")
    drain(service, timeout=0.6)
    service.close()
    assert service.firmware_version == "v1.3"


def test_a_dead_port_becomes_an_event_instead_of_a_crash():
    class Dying(FakeTransport):
        def readline(self):
            raise OSError("device disconnected")

    service = SerialService()
    service.attach(Dying([]), "FAKE")
    kinds = drain(service, timeout=1.0)
    assert "serial_error" in kinds
    assert service.connected is False
    # Writing to a dead service is a no-op, not an exception.
    assert service.send(protocol.CMD_LIGHT) is False
