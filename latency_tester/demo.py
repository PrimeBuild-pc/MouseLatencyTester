"""Simulated Teensy, for using the app without hardware.

It speaks the same wire format as the firmware so the whole UI, the charts and
the archive can be exercised for development, screenshots and release testing.

It deliberately does **not** emit ``TRIG``: the click handshake needs a real
probe and a real OS click, so the demo produces finished ``LAT:`` lines
instead.  The measurement path is therefore never exercised -- and never
faked -- by demo mode.  Runs saved while the demo device is attached are stored
with ``is_demo = 1``.
"""

from __future__ import annotations

import queue
import random
import threading
import time

from . import protocol

PORT_NAME = "DEMO"

# A plausible wireless mouse: a tight main mode plus the occasional polling
# hiccup, so percentiles, jitter and the outlier markers all have something to
# show.
_BASE_MS = 6.4
_SIGMA_MS = 0.85
_SPIKE_CHANCE = 0.06
_SPIKE_EXTRA_MS = (3.0, 14.0)

_INTERVAL_S = 0.45      # simulated time between presses
_LIGHT_BASE = 620


class DemoDevice:
    """A :class:`~latency_tester.serial_service.Transport` backed by a thread."""

    def __init__(self, seed: int | None = None):
        self._out: queue.Queue[bytes] = queue.Queue()
        self._random = random.Random(seed)
        self._lock = threading.Lock()
        self._closed = threading.Event()

        self._test_mode = False
        self._calibrating = False
        self._sample_count = 0
        self._last = 0.0
        self._min = 0.0
        self._max = 0.0
        self._sum = 0.0
        self._calib_us = 250

        self._thread = threading.Thread(
            target=self._run, name="latency-demo", daemon=True)
        self._thread.start()
        self._emit("LATENCY_TESTER v1.3 DEMO")
        self._emit(protocol.TOK_READY)
        self._emit(protocol.PREFIX_OLED_OK + "0x3C")

    # ------------------------------------------------------- transport API --
    def write(self, data: bytes) -> int:
        for char in data.decode("ascii", errors="ignore"):
            self._command(char)
        return len(data)

    def flush(self) -> None:
        return None

    def readline(self) -> bytes:
        try:
            return self._out.get(timeout=0.1)
        except queue.Empty:
            return b""

    def close(self) -> None:
        self._closed.set()

    # ------------------------------------------------------------ internals --
    def _emit(self, line: str) -> None:
        self._out.put((line + "\n").encode("ascii"))

    def _command(self, char: str) -> None:
        # 'R' is both CMD_RESET and REPLY_CALIB_READY.  The firmware
        # disambiguates by being busy inside runCalibration(); do the same.
        if self._calibrating and char == protocol.REPLY_CALIB_READY:
            self._emit(protocol.TOK_PC_SYNCED)
            self._calib_us = self._random.randint(230, 300)
            self._calibrating = False
            self._emit(
                f"CALIB_OK:{self._calib_us},samples:50,min_us:120,"
                f"max_us:900,avg_rt:{self._calib_us * 2}"
            )
        elif char == protocol.CMD_VERSION:
            self._emit("LATENCY_TESTER v1.3 DEMO - simulated device")
        elif char == protocol.CMD_RESET:
            with self._lock:
                self._sample_count = 0
                self._last = self._min = self._max = self._sum = 0.0
            self._emit(protocol.TOK_RESET)
        elif char == protocol.CMD_LIGHT:
            self._emit(f"{protocol.PREFIX_LIGHT}{self._light()}")
        elif char == protocol.CMD_STATS:
            self._send_stats()
        elif char == protocol.CMD_TEST_MODE_ON:
            self._test_mode = True
            self._emit(protocol.TOK_TESTMODE_ON)
            self._emit(protocol.TOK_ARMED)
        elif char == protocol.CMD_TEST_MODE_OFF:
            self._test_mode = False
            self._emit(protocol.TOK_TESTMODE_OFF)
        elif char == protocol.CMD_CALIBRATE:
            self._calibrating = True
            self._emit("CALIBRATING...")

    def _light(self) -> int:
        return max(0, min(1023, _LIGHT_BASE + self._random.randint(-12, 12)))

    def _send_stats(self) -> None:
        with self._lock:
            if not self._sample_count:
                self._emit(protocol.TOK_STATS_NO_DATA)
                return
            avg = self._sum / self._sample_count
            self._emit(
                f"STATS:samples:{self._sample_count},min:{self._min:.3f},"
                f"max:{self._max:.3f},avg:{avg:.3f},last:{self._last:.3f},"
                f"calib:{self._calib_us}"
            )

    def _next_latency(self) -> float:
        value = self._random.gauss(_BASE_MS, _SIGMA_MS)
        if self._random.random() < _SPIKE_CHANCE:
            value += self._random.uniform(*_SPIKE_EXTRA_MS)
        return max(2.0, value)

    def _run(self) -> None:
        while not self._closed.wait(_INTERVAL_S):
            if not self._test_mode:
                continue
            latency = self._next_latency()
            with self._lock:
                self._last = latency
                if self._sample_count == 0:
                    self._min = self._max = latency
                self._min = min(self._min, latency)
                self._max = max(self._max, latency)
                self._sum += latency
                self._sample_count += 1
                count, low, high = self._sample_count, self._min, self._max
                avg = self._sum / count
            self._emit(
                f"LAT:{latency:.3f},min:{low:.3f},max:{high:.3f},"
                f"avg:{avg:.3f},n:{count}"
            )
            # Mirror the real arm/re-arm cycle so the overlay behaves normally.
            self._emit(protocol.TOK_REARM)
            time.sleep(0.12)
            if self._test_mode:
                self._emit(protocol.TOK_ARMED)
