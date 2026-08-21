"""Probe-to-Photon: wire format, threshold maths, and how a run is archived.

The optical mode is deliberately separate from Probe-to-PC everywhere, and the
tests here are what keeps it that way: an ``OPT:`` line must never decode as a
``LAT:`` one, and a stored run must always say which mode produced it.
"""

import importlib
import sqlite3

import pytest

from latency_tester import protocol
from latency_tester.constants import (
    FRAME_CAP_AUTO,
    FRAME_CAP_FALLBACK,
    FRAME_CAPS,
    MODE_PHOTON,
    MODE_PROBE_PC,
)
from latency_tester.database import SCHEMA_VERSION, LatencyDB, run_mode


# ------------------------------------------------------------------ parsing --
def test_an_optical_result_decodes_with_its_raw_reading():
    event = protocol.parse_line(
        "OPT:23.417,raw:851,min:19.200,max:31.008,avg:24.100,n:7")
    assert event.kind == "optical"
    assert event.payload["latency_ms"] == pytest.approx(23.417)
    assert event.payload["raw_optical"] == 851
    assert event.payload["firmware_n"] == 7


def test_an_optical_result_is_never_mistaken_for_a_serial_one():
    """The whole point of a separate token."""
    optical = protocol.parse_line(
        "OPT:23.417,raw:851,min:19.200,max:31.008,avg:24.100,n:7")
    serial = protocol.parse_line(
        "LAT:6.400,min:5.000,max:9.000,avg:6.500,n:3")
    assert optical.kind == "optical"
    assert serial.kind == "latency"
    assert optical.kind != serial.kind


def test_the_optical_calibration_decodes_including_its_direction():
    event = protocol.parse_line(
        "OPT_CAL:dark:118,bright:874,threshold:496,rising:1")
    assert event.kind == "optical_cal"
    assert event.payload == {"dark": 118, "bright": 874,
                             "threshold": 496, "rising": True}


def test_a_falling_sensor_is_reported_as_such():
    event = protocol.parse_line(
        "OPT_CAL:dark:900,bright:120,threshold:510,rising:0")
    assert event.payload["rising"] is False


@pytest.mark.parametrize("line, kind", [
    ("OPT_TIMEOUT", "optical_timeout"),
    ("OPT_ERR:NO_CAL", "optical_error"),
    ("OPT_ERR:NOT_DARK", "optical_error"),
    ("OPT_ERR:SEPARATION", "optical_error"),
    ("OPT_DROP:OUT_OF_RANGE:412.500", "optical_drop"),
    ("PHOTON:ON", "photon_on"),
    ("PHOTON:OFF", "photon_off"),
])
def test_the_optical_control_tokens_decode(line, kind):
    assert protocol.parse_line(line).kind == kind


def test_a_timeout_carries_no_sample():
    """A timeout must not reach the archive as a measurement."""
    assert protocol.parse_line("OPT_TIMEOUT").payload is None


def test_the_error_reason_survives():
    assert protocol.parse_line("OPT_ERR:NOT_DARK").payload == "NOT_DARK"


@pytest.mark.parametrize("line", [
    "OPT:23.417,raw:851,min:19.200,max:31.008,avg:24.100",   # no n
    "OPT:23.417,min:19.200,max:31.008,avg:24.100,n:7",       # no raw
    "OPT_CAL:dark:118,bright:874,threshold:496",             # no direction
    "OPT_CAL:dark:118,bright:874,threshold:496,rising:2",    # not a flag
])
def test_a_malformed_optical_line_is_logged_not_guessed(line):
    assert protocol.parse_line(line).kind == "log"


# ---------------------------------------------------------------- threshold --
def test_the_threshold_sits_between_the_two_baselines():
    threshold, rising = protocol.optical_threshold(100, 900)
    assert threshold == 500
    assert rising is True


def test_a_sensor_that_falls_with_light_is_handled():
    threshold, rising = protocol.optical_threshold(900, 100)
    assert threshold == 500
    assert rising is False


def test_baselines_that_are_too_close_have_no_usable_threshold():
    """Blocking the test is the point: a threshold inside the noise would turn
    every sample into a coin toss."""
    assert protocol.optical_threshold(500, 520) is None
    assert protocol.optical_threshold(520, 500) is None


def test_exactly_the_minimum_separation_is_accepted():
    gap = protocol.OPTICAL_MIN_SEPARATION
    assert protocol.optical_threshold(100, 100 + gap) is not None
    assert protocol.optical_threshold(100, 100 + gap - 1) is None


def test_the_threshold_matches_what_the_firmware_reports():
    """The dashboard pre-validates a calibration, so both must agree."""
    line = "OPT_CAL:dark:118,bright:874,threshold:496,rising:1"
    payload = protocol.parse_line(line).payload
    computed, rising = protocol.optical_threshold(payload["dark"],
                                                  payload["bright"])
    assert computed == payload["threshold"]
    assert rising is payload["rising"]


# ----------------------------------------------------------------- archive --
@pytest.fixture
def db(tmp_path):
    database = LatencyDB(tmp_path / "photon.db")
    yield database
    database.close()


@pytest.fixture
def device(db):
    return db.create_device(name="ATK F1")


def test_a_photon_run_keeps_its_mode_and_its_calibration(db, device):
    run_id = db.save_run(
        {
            "device_id": device, "name": "photon 1000 Hz",
            "polling_rate_hz": 1000, "connection_mode": "Wired",
            "calibration_us": 267, "notes": "curtains shut",
            "mode": MODE_PHOTON, "optical_dark": 118,
            "optical_bright": 874, "optical_threshold": 496,
        },
        [
            {"latency_ms": 23.4, "raw_optical": 851},
            {"latency_ms": 24.9, "raw_optical": 860},
        ],
    )
    run = db.get_run(run_id)
    assert run_mode(run) == MODE_PHOTON
    assert (run["optical_dark"], run["optical_bright"],
            run["optical_threshold"]) == (118, 874, 496)
    assert run["calibration_us"] == 267
    assert run["polling_rate_hz"] == 1000
    assert run["connection_mode"] == "Wired"
    assert run["notes"] == "curtains shut"
    assert [s["raw_optical"] for s in db.get_samples(run_id)] == [851, 860]
    assert db.get_latencies(run_id) == pytest.approx([23.4, 24.9])


def test_a_probe_to_pc_run_still_stores_nothing_optical(db, device):
    run_id = db.save_run({"device_id": device, "name": "serial"},
                         [{"latency_ms": 6.4}])
    run = db.get_run(run_id)
    assert run_mode(run) == MODE_PROBE_PC
    assert run["optical_dark"] is None
    assert run["optical_threshold"] is None
    assert db.get_samples(run_id)[0]["raw_optical"] is None


def test_both_modes_live_in_the_same_archive(db, device):
    serial_id = db.save_run({"device_id": device, "name": "serial"},
                            [{"latency_ms": 6.4}])
    photon_id = db.save_run(
        {"device_id": device, "name": "photon", "mode": MODE_PHOTON,
         "optical_dark": 100, "optical_bright": 900, "optical_threshold": 500},
        [{"latency_ms": 23.4, "raw_optical": 880}])

    modes = {run["id"]: run_mode(run) for run in db.list_runs()}
    assert modes == {serial_id: MODE_PROBE_PC, photon_id: MODE_PHOTON}


def test_an_unknown_mode_string_is_stored_verbatim(db, device):
    """No silent rewriting: an archive written by a newer build must survive a
    round trip through an older one."""
    run_id = db.save_run(
        {"device_id": device, "name": "future", "mode": "probe_to_something"},
        [{"latency_ms": 1.0}])
    assert db.get_run(run_id)["mode"] == "probe_to_something"


def test_run_mode_defaults_when_the_column_is_missing():
    assert run_mode({}) == MODE_PROBE_PC
    assert run_mode({"mode": ""}) == MODE_PROBE_PC
    assert run_mode({"mode": MODE_PHOTON}) == MODE_PHOTON


# --------------------------------------------------------------- migration --
# The schema exactly as it shipped at user_version 2, before Probe-to-Photon.
# Written out rather than produced by dropping columns, so the test does not
# depend on the SQLite build supporting ALTER TABLE ... DROP COLUMN.
V2_SCHEMA = """
CREATE TABLE devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    manufacturer TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    serial_number TEXT NOT NULL DEFAULT '',
    switch_type TEXT NOT NULL DEFAULT '',
    default_firmware TEXT NOT NULL DEFAULT '',
    hardware_id TEXT NOT NULL DEFAULT ''
);
CREATE TABLE runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    polling_rate_hz INTEGER,
    connection_mode TEXT NOT NULL DEFAULT '',
    mouse_firmware TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    target_samples INTEGER NOT NULL DEFAULT 0,
    calibration_us INTEGER NOT NULL DEFAULT 0,
    light_start INTEGER,
    light_end INTEGER,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    dpi INTEGER,
    debounce_setting TEXT NOT NULL DEFAULT '',
    teensy_firmware TEXT NOT NULL DEFAULT '',
    is_demo INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
);
CREATE TABLE samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    seq INTEGER NOT NULL,
    latency_ms REAL NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE CASCADE
);
"""



def test_a_v2_archive_is_upgraded_without_losing_runs(tmp_path):
    """The user's archive is never recreated: the optical columns are added to
    the rows that are already there, and every old run reads as Probe-to-PC."""
    path = tmp_path / "v2.db"
    legacy = sqlite3.connect(path)
    legacy.executescript(V2_SCHEMA)
    legacy.execute(
        "INSERT INTO devices(name, manufacturer, model, notes, created_at, "
        "serial_number, switch_type, default_firmware, hardware_id) "
        "VALUES('Old Mouse','Acme','M1','keep me','2025-01-01T00:00:00',"
        "'','','','373B:11D9')")
    legacy.execute(
        "INSERT INTO runs(device_id, name, polling_rate_hz, connection_mode, "
        "mouse_firmware, notes, target_samples, calibration_us, light_start, "
        "light_end, started_at, ended_at, dpi, debounce_setting, "
        "teensy_firmware, is_demo) "
        "VALUES(1,'1000 Hz',1000,'Wired','fw1','n',50,267,600,610,"
        "'2025-01-02T10:00:00','2025-01-02T10:05:00',1600,'0 ms','v1.4',0)")
    legacy.executemany(
        "INSERT INTO samples(run_id, seq, latency_ms, timestamp) VALUES(1,?,?,?)",
        [(i + 1, 5.0 + i / 10, "2025-01-02T10:00:00") for i in range(20)])
    legacy.execute("PRAGMA user_version = 2")
    legacy.commit()
    legacy.close()

    run_id = 1
    upgraded = LatencyDB(path)
    try:
        assert upgraded.schema_version == SCHEMA_VERSION
        run = upgraded.get_run(run_id)
        assert run["name"] == "1000 Hz"
        assert run["calibration_us"] == 267
        assert len(upgraded.get_latencies(run_id)) == 20
        assert run_mode(run) == MODE_PROBE_PC
        assert run["optical_threshold"] is None
        assert upgraded.get_samples(run_id)[0]["raw_optical"] is None
    finally:
        upgraded.close()


def test_migrating_twice_changes_nothing(tmp_path):
    database = LatencyDB(tmp_path / "twice.db")
    try:
        assert database.migrate() == SCHEMA_VERSION
        assert database.migrate() == SCHEMA_VERSION
    finally:
        database.close()


# ---------------------------------------------------------------- frame cap --
pytest.importorskip("tkinter")

_app = importlib.import_module("latency_tester.app")
LatencyTesterApp = _app.LatencyTesterApp


class _CapApp:
    """The frame-cap resolution, without a window around it."""

    effective_frame_cap = LatencyTesterApp.effective_frame_cap

    def __init__(self, frame_cap, monitor):
        self.frame_cap = frame_cap
        self._monitor = monitor

    def monitor_hz(self):
        return self._monitor


@pytest.mark.parametrize("fps", FRAME_CAPS)
def test_an_explicit_cap_is_used_as_is(fps):
    assert _CapApp(fps, 144).effective_frame_cap() == fps


def test_auto_follows_the_monitor():
    assert _CapApp(FRAME_CAP_AUTO, 360).effective_frame_cap() == 360


def test_auto_falls_back_when_the_refresh_rate_is_unknown():
    """A run must always record a real number, so 'auto' can never stay auto."""
    assert _CapApp(FRAME_CAP_AUTO, None).effective_frame_cap() == FRAME_CAP_FALLBACK


def test_an_explicit_cap_ignores_the_monitor():
    assert _CapApp(60, 360).effective_frame_cap() == 60


def test_the_frame_cap_reaches_the_archive(db, device):
    """Half a frame of quantisation is the difference between 30 and 360 fps;
    an archived optical run without its cap cannot be interpreted."""
    run_id = db.save_run(
        {"device_id": device, "name": "capped", "mode": MODE_PHOTON,
         "optical_dark": 100, "optical_bright": 900, "optical_threshold": 500,
         "target_fps": 240},
        [{"latency_ms": 12.0, "raw_optical": 880}])
    assert db.get_run(run_id)["target_fps"] == 240


def test_a_probe_to_pc_run_has_no_frame_cap(db, device):
    run_id = db.save_run({"device_id": device, "name": "serial"},
                         [{"latency_ms": 6.4}])
    assert db.get_run(run_id)["target_fps"] is None
