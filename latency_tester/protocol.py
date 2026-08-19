"""Serial protocol between the Teensy firmware and the dashboard.

Pure parsing only: no serial, no threads, no GUI.  Every token here is part of
the wire format and must NOT be translated or renamed -- see
``docs/serial_protocol.md``.

The firmware does not announce a protocol version of its own; it only prints a
banner (``LATENCY_TESTER v1.3 OLED+LDR``).  ``PROTOCOL_VERSION`` below is the
dashboard-side revision of *this* document, and :func:`firmware_version` reads
the banner so old firmware keeps working unchanged.
"""

from __future__ import annotations

import re
from typing import Any, NamedTuple

# Revision of the protocol as implemented here.  Bump only when the wire format
# changes.  1 == the format spoken by firmware v1.0 through v1.3.
PROTOCOL_VERSION = 1

BAUD_RATE = 115200

TEENSY_VID = 0x16C0
TEENSY_PIDS = frozenset({0x0482, 0x0483, 0x0486, 0x0487})

# ---------------------------------------------------------------- commands --
# Single ASCII characters sent PC -> Teensy.  The firmware reads exactly one
# byte per command; the trailing newline the dashboard appends is swallowed by
# the firmware's `default:` branch.
CMD_CALIBRATE = "C"
CMD_RESET = "R"
CMD_STATS = "S"
CMD_VERSION = "V"
CMD_TEST_MODE_ON = "T"
CMD_TEST_MODE_OFF = "E"
CMD_LIGHT = "L"

# Handshake replies sent inside a measurement / calibration exchange.
REPLY_CLICK_SEEN = "H"     # OS click matched the TRIG -> firmware stops the clock
REPLY_NO_CLICK = "X"       # no matching click -> firmware aborts the sample
REPLY_CALIB_PING = "P"     # echo during the calibration round-trip loop
REPLY_CALIB_READY = "R"    # PC is synced and ready to be pinged

# ------------------------------------------------------------ replies/tokens -
TOK_TRIG = "TRIG"
TOK_READY = "READY"
TOK_RESET = "RESET"
TOK_ARMED = "ARMED"
TOK_REARM = "REARM"
TOK_AWAIT = "AWAIT"
TOK_PC_SYNCED = "PC_SYNCED"
TOK_CALIB_PING = "P"
TOK_TESTMODE_ON = "TESTMODE:ON"
TOK_TESTMODE_OFF = "TESTMODE:OFF"
TOK_SKIP_OLED = "SKIP:OLED_REFRESH"
TOK_ABORT_NO_CLICK = "ABORT:NO_CLICK"
TOK_STATS_NO_DATA = "STATS:NO_DATA"
TOK_OLED_FAIL = "OLED_FAIL"
PREFIX_OLED_OK = "OLED_OK:"
PREFIX_LIGHT = "LIGHT:"
PREFIX_DROP = "DROP:OUT_OF_RANGE:"
PREFIX_TIMEOUT = "TIMEOUT:"
PREFIX_CALIB_FAIL = "CALIB_FAIL"
PREFIX_CALIBRATING = "CALIBRATING"
PREFIX_BUTTON = "BTN"

LAT_RE = re.compile(
    r"^LAT:(?P<last>[\d.]+),min:(?P<min>[\d.]+),max:(?P<max>[\d.]+),"
    r"avg:(?P<avg>[\d.]+),n:(?P<n>\d+)$"
)
STATS_RE = re.compile(
    r"^STATS:samples:(?P<n>\d+),min:(?P<min>[\d.]+),max:(?P<max>[\d.]+),"
    r"avg:(?P<avg>[\d.]+),last:(?P<last>[\d.]+),calib:(?P<calib>\d+)$"
)
CAL_RE = re.compile(
    r"^CALIB_OK:(?P<calib>\d+),samples:(?P<samples>\d+),"
    r"min_us:(?P<min_us>\d+),max_us:(?P<max_us>\d+),avg_rt:(?P<avg_rt>\d+)$"
)
BANNER_RE = re.compile(r"^LATENCY_TESTER\s+(?P<version>v[\d.]+)")
# Firmware v1.4+. Parsed generically so a future BTNn:RELEASE needs no change
# on the dashboard side.
BUTTON_RE = re.compile(r"^BTN(?P<index>\d+):(?P<action>[A-Z_]+)$")


class Event(NamedTuple):
    """One decoded firmware line."""

    kind: str
    payload: Any = None


def firmware_version(line: str) -> str | None:
    """Return the firmware version from a banner line, else ``None``."""
    m = BANNER_RE.match(line.strip())
    return m.group("version") if m else None


def parse_line(line: str) -> Event:
    """Decode one firmware line into an :class:`Event`.

    ``TRIG`` and the calibration ping are returned as-is: they need a timed
    reply and are therefore handled by the serial service, not here.
    Unrecognised lines become ``Event("log", line)`` so nothing is ever lost.
    """
    line = line.strip()
    if not line:
        return Event("log", "")

    if line == TOK_TRIG:
        return Event("trig")
    if line == TOK_CALIB_PING:
        return Event("calib_ping")

    m = LAT_RE.match(line)
    if m:
        return Event("latency", {
            "latency_ms": float(m.group("last")),
            "firmware_min": float(m.group("min")),
            "firmware_max": float(m.group("max")),
            "firmware_avg": float(m.group("avg")),
            "firmware_n": int(m.group("n")),
        })

    m = STATS_RE.match(line)
    if m:
        return Event("stats", {
            "n": int(m.group("n")),
            "min": float(m.group("min")),
            "max": float(m.group("max")),
            "avg": float(m.group("avg")),
            "last": float(m.group("last")),
            "calib": int(m.group("calib")),
        })

    m = CAL_RE.match(line)
    if m:
        return Event("cal_ok", {k: int(v) for k, v in m.groupdict().items()})

    m = BUTTON_RE.match(line)
    if m:
        return Event("button", {
            "index": int(m.group("index")),
            "action": m.group("action"),
            "token": line,
        })

    if line.startswith(PREFIX_CALIB_FAIL):
        return Event("cal_fail", line)
    if line.startswith(PREFIX_LIGHT):
        try:
            return Event("light", int(line.split(":", 1)[1]))
        except ValueError:
            return Event("log", line)
    if line.startswith(PREFIX_DROP):
        try:
            return Event("drop", float(line.rsplit(":", 1)[1]))
        except ValueError:
            return Event("drop", None)
    if line.startswith(PREFIX_TIMEOUT):
        return Event("timeout", line)
    if line.startswith(PREFIX_OLED_OK):
        return Event("oled_ok", line.split(":", 1)[1])
    if line.startswith(PREFIX_CALIBRATING):
        return Event("calibrating")

    simple = {
        TOK_RESET: "reset",
        TOK_ARMED: "armed",
        TOK_REARM: "rearm",
        TOK_READY: "ready",
        TOK_AWAIT: "await_sync",
        TOK_PC_SYNCED: "pc_synced",
        TOK_TESTMODE_ON: "testmode_on",
        TOK_TESTMODE_OFF: "testmode_off",
        TOK_SKIP_OLED: "skip_oled",
        TOK_ABORT_NO_CLICK: "abort",
        TOK_STATS_NO_DATA: "stats_no_data",
        TOK_OLED_FAIL: "oled_fail",
    }
    if line in simple:
        return Event(simple[line])

    if firmware_version(line):
        return Event("banner", firmware_version(line))

    return Event("log", line)
