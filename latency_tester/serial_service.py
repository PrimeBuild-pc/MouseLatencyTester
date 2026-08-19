"""Serial transport, reader thread and TRIG/click association.

This module owns the measurement-critical path and deliberately mirrors the
behaviour of the known-good dashboard v2:

* the ``pynput`` callback only stores a timestamp -- no printing, no locking
  beyond one short critical section, no work that could delay the OS click;
* on ``TRIG`` the reader thread busy-waits for a *new* OS click within the
  grace window and answers ``H``; otherwise it answers ``X``;
* the calibration ping/echo runs inside the same reader thread.

Nothing here imports tkinter: the GUI consumes decoded events from a queue.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Any, Callable, Protocol

from . import protocol

log = logging.getLogger(__name__)

#: A click older than this (relative to TRIG) cannot belong to this trigger.
CLICK_GRACE_NS = int(0.200 * 1e9)
#: How long to wait for the OS click that belongs to a TRIG.
CLICK_TIMEOUT_S = 1.0
#: Busy-wait granularity while waiting for that click.
CLICK_POLL_S = 0.0002


class Transport(Protocol):
    """The subset of ``serial.Serial`` this service needs."""

    def write(self, data: bytes) -> int: ...
    def flush(self) -> None: ...
    def readline(self) -> bytes: ...
    def close(self) -> None: ...


class ClickTracker:
    """Associates OS mouse clicks with firmware ``TRIG`` events.

    A click counts for a trigger only if it is newer than the last click
    already consumed *and* not older than the grace window, so one physical
    press can never be counted twice.
    """

    def __init__(self, grace_ns: int = CLICK_GRACE_NS):
        self.grace_ns = grace_ns
        self._lock = threading.Lock()
        self._last_click_ns = 0
        self._last_consumed_ns = 0

    def record(self, timestamp_ns: int) -> None:
        """Called from the input callback. Keep this as short as possible."""
        with self._lock:
            self._last_click_ns = timestamp_ns

    def try_consume(self, trig_ns: int) -> bool:
        """Consume a click matching a TRIG seen at ``trig_ns``.  Pure enough to
        unit-test: no sleeping, no I/O."""
        cutoff = trig_ns - self.grace_ns
        with self._lock:
            current = self._last_click_ns
            if current > self._last_consumed_ns and current >= cutoff:
                self._last_consumed_ns = current
                return True
        return False

    def reset(self) -> None:
        with self._lock:
            self._last_click_ns = 0
            self._last_consumed_ns = 0


class SerialService:
    """Owns one transport and pushes decoded :class:`protocol.Event` items into
    ``events``."""

    def __init__(self, events: "queue.Queue[protocol.Event]" | None = None,
                 click_tracker: ClickTracker | None = None):
        self.events: queue.Queue = events or queue.Queue()
        self.clicks = click_tracker or ClickTracker()

        self._transport: Transport | None = None
        self._thread: threading.Thread | None = None
        self._write_lock = threading.Lock()
        self._running = False

        self.port_name: str = ""
        self.is_demo = False
        self.calibrating = False
        self.firmware_version: str | None = None

        #: Returning False makes the service answer ``X`` to a TRIG instead of
        #: waiting for a click (used once a test-mode target is reached).
        self.accept_trig: Callable[[], bool] = lambda: True

    # ---------------------------------------------------------- lifecycle --
    @property
    def connected(self) -> bool:
        return self._running and self._transport is not None

    def attach(self, transport: Transport, port_name: str, is_demo: bool = False) -> None:
        """Take ownership of an already-open transport and start reading."""
        if self.connected:
            self.close()
        self._transport = transport
        self.port_name = port_name
        self.is_demo = is_demo
        self.firmware_version = None
        self._running = True
        self._thread = threading.Thread(
            target=self._read_loop, name="latency-serial", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._running = False
        self.calibrating = False
        transport, self._transport = self._transport, None
        if transport is not None:
            try:
                transport.close()
            except Exception:  # a vanished COM port raises all sorts of things
                log.debug("error while closing %s", self.port_name, exc_info=True)
        self.port_name = ""
        self.is_demo = False

    # ------------------------------------------------------------ writing --
    def send(self, command: str) -> bool:
        """Write one command.  Never raises: a dead port becomes an event."""
        transport = self._transport
        if not self._running or transport is None:
            return False
        try:
            with self._write_lock:
                transport.write((command + "\n").encode("ascii"))
                transport.flush()
            return True
        except Exception as exc:
            self._fail(exc)
            return False

    def start_calibration(self) -> bool:
        """Send ``C`` and arm the ping/echo responder."""
        self.calibrating = True
        if not self.send(protocol.CMD_CALIBRATE):
            self.calibrating = False
            return False
        return True

    def send_calibration_ready(self) -> bool:
        return self.send(protocol.REPLY_CALIB_READY)

    # ------------------------------------------------------------ reading --
    def _read_loop(self) -> None:
        transport = self._transport
        while self._running and transport is not None:
            try:
                raw = transport.readline()
            except Exception as exc:
                if self._running:
                    self._fail(exc)
                return
            if not raw:
                continue
            line = raw.decode("ascii", errors="ignore").strip()
            if line:
                self._dispatch(line)

    def _dispatch(self, line: str) -> None:
        event = protocol.parse_line(line)

        if event.kind == "calib_ping":
            # Echo as fast as possible: this round-trip *is* the calibration.
            if self.calibrating:
                self.send(protocol.REPLY_CALIB_PING)
            return

        if event.kind == "trig":
            self.events.put(event)
            self._answer_trig()
            return

        if event.kind in ("cal_ok", "cal_fail"):
            self.calibrating = False
        elif event.kind == "banner":
            self.firmware_version = event.payload

        self.events.put(event)

    def _answer_trig(self) -> None:
        """Reply ``H`` (click matched) or ``X`` (no click) to a pending TRIG."""
        if not self.accept_trig():
            self.send(protocol.REPLY_NO_CLICK)
            return
        if self._wait_for_click():
            self.send(protocol.REPLY_CLICK_SEEN)
        else:
            self.send(protocol.REPLY_NO_CLICK)
            self.events.put(protocol.Event("trig_unmatched"))

    def _wait_for_click(self) -> bool:
        trig_ns = time.perf_counter_ns()
        deadline = time.perf_counter() + CLICK_TIMEOUT_S
        while self._running and time.perf_counter() < deadline:
            if self.clicks.try_consume(trig_ns):
                return True
            time.sleep(CLICK_POLL_S)
        return False

    def _fail(self, exc: BaseException) -> None:
        self._running = False
        self.calibrating = False
        self.events.put(protocol.Event("serial_error", str(exc)))


# ----------------------------------------------------------------- ports ----
def list_ports() -> list[dict[str, Any]]:
    """Available serial ports, Teensy ones flagged."""
    try:
        import serial.tools.list_ports
    except ImportError:
        return []
    found = []
    for port in serial.tools.list_ports.comports():
        description = port.description or ""
        is_teensy = (port.vid == protocol.TEENSY_VID
                     and port.pid in protocol.TEENSY_PIDS)
        if not is_teensy:
            is_teensy = "teensy" in f"{description} {port.hwid}".lower()
        found.append({
            "device": port.device,
            "description": description,
            "label": f"{port.device} — {description}" if description else port.device,
            "is_teensy": is_teensy,
        })
    return found


def open_serial(device: str, timeout: float = 0.10) -> Transport:
    """Open a real Teensy port.  Raises ``serial.SerialException`` on failure."""
    import serial

    return serial.Serial(device, protocol.BAUD_RATE, timeout=timeout)


# ---------------------------------------------------------------- clicks ----
class MouseWatcher:
    """Feeds :class:`ClickTracker` from ``pynput``.

    The callback does one comparison and one timestamp store -- no logging, no
    allocation, nothing that could add latency to the click being measured.
    """

    def __init__(self, tracker: ClickTracker):
        self.tracker = tracker
        self._listener = None

    def start(self) -> bool:
        try:
            from pynput import mouse
        except ImportError:
            log.warning("pynput is not installed: OS clicks cannot be detected")
            return False

        button_left = mouse.Button.left
        record = self.tracker.record
        perf_counter_ns = time.perf_counter_ns

        def on_click(_x, _y, button, pressed):
            if pressed and button is button_left:
                record(perf_counter_ns())

        self._listener = mouse.Listener(on_click=on_click)
        self._listener.start()
        return True

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                log.debug("mouse listener stop failed", exc_info=True)
            self._listener = None
