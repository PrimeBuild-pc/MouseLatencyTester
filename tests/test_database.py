import sqlite3

import pytest

from latency_tester.database import (RUN_FIELDS, SCHEMA_VERSION, LatencyDB,
                                     run_as_metadata)

# The schema exactly as dashboard v2 wrote it: no user_version, no extra
# columns.  Migrating one of these in place is the case that must never lose
# a user's data.
V0_SCHEMA = """
CREATE TABLE devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    manufacturer TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
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


@pytest.fixture
def db(tmp_path):
    database = LatencyDB(tmp_path / "archive.db")
    yield database
    database.close()


@pytest.fixture
def device(db):
    return db.create_device(name="ATK F1", manufacturer="ATK", model="F1 v2")


def make_samples(values):
    return [{"latency_ms": v, "timestamp": f"2026-01-01T10:00:0{i}"}
            for i, v in enumerate(values)]


# --------------------------------------------------------------- schema ----
def test_fresh_database_is_at_the_current_version(db):
    assert db.schema_version == SCHEMA_VERSION


def test_migrate_is_idempotent(db):
    assert db.migrate() == SCHEMA_VERSION
    assert db.migrate() == SCHEMA_VERSION


def test_v0_database_is_upgraded_without_losing_data(tmp_path):
    path = tmp_path / "old.db"
    legacy = sqlite3.connect(path)
    legacy.executescript(V0_SCHEMA)
    legacy.execute(
        "INSERT INTO devices(name, manufacturer, model, notes, created_at) "
        "VALUES('Old Mouse','Acme','M1','keep me','2025-01-01T00:00:00')")
    legacy.execute(
        "INSERT INTO runs(device_id, name, polling_rate_hz, connection_mode, "
        "mouse_firmware, notes, target_samples, calibration_us, light_start, "
        "light_end, started_at, ended_at) "
        "VALUES(1,'1000 Hz run',1000,'Wired','fw1','n',50,267,600,610,"
        "'2025-01-02T10:00:00','2025-01-02T10:05:00')")
    legacy.executemany(
        "INSERT INTO samples(run_id, seq, latency_ms, timestamp) VALUES(1,?,?,?)",
        [(i + 1, 5.0 + i / 10, "2025-01-02T10:00:00") for i in range(20)])
    legacy.commit()
    assert legacy.execute("PRAGMA user_version").fetchone()[0] == 0
    legacy.close()

    upgraded = LatencyDB(path)
    try:
        assert upgraded.schema_version == SCHEMA_VERSION
        run = upgraded.get_run(1)
        assert run["name"] == "1000 Hz run"
        assert run["calibration_us"] == 267
        assert run["device_name"] == "Old Mouse"
        assert len(upgraded.get_latencies(1)) == 20
        # New columns exist with usable defaults.
        assert run["is_demo"] == 0
        assert run["dpi"] is None
        assert upgraded.get_device(1)["serial_number"] == ""
    finally:
        upgraded.close()


def test_opening_an_existing_archive_never_drops_tables(tmp_path):
    path = tmp_path / "archive.db"
    first = LatencyDB(path)
    device_id = first.create_device(name="Keep")
    first.save_run({"device_id": device_id, "name": "r1"}, make_samples([1.0, 2.0]))
    first.close()

    second = LatencyDB(path)
    try:
        assert len(second.list_runs()) == 1
        assert len(second.list_devices()) == 1
    finally:
        second.close()


# -------------------------------------------------------------- devices ----
def test_device_crud(db):
    device_id = db.create_device(name="Viper", manufacturer="Razer",
                                 model="V3 Pro", serial_number="SN-1",
                                 switch_type="optical gen3")
    row = db.get_device(device_id)
    assert row["name"] == "Viper"
    assert row["serial_number"] == "SN-1"
    assert row["switch_type"] == "optical gen3"

    db.update_device(device_id, name="Viper V3", manufacturer="Razer",
                     model="V3 Pro", notes="8k dongle")
    row = db.get_device(device_id)
    assert row["name"] == "Viper V3"
    assert row["notes"] == "8k dongle"
    # Fields omitted from an update are cleared, not left stale.
    assert row["serial_number"] == ""

    db.delete_device(device_id)
    assert db.get_device(device_id) is None


def test_device_name_is_required(db):
    with pytest.raises(ValueError):
        db.create_device(name="   ")


def test_duplicate_device_name_is_rejected(db):
    db.create_device(name="Dup")
    with pytest.raises(sqlite3.IntegrityError):
        db.create_device(name="Dup")


def test_deleting_a_device_cascades_to_runs_and_samples(db, device):
    run_id = db.save_run({"device_id": device, "name": "r"}, make_samples([1.0, 2.0]))
    db.delete_device(device)
    assert db.get_run(run_id) is None
    assert db.get_samples(run_id) == []


# ----------------------------------------------------------------- runs ----
def test_save_and_reload_a_run_with_all_metadata(db, device):
    metadata = {
        "device_id": device, "name": "8000 Hz wired", "polling_rate_hz": 8000,
        "connection_mode": "Wired", "mouse_firmware": "1.02.00", "notes": "cold",
        "target_samples": 50, "calibration_us": 267, "light_start": 640,
        "light_end": 651, "dpi": 1600, "debounce_setting": "0 ms",
        "teensy_firmware": "v1.3", "is_demo": 0,
        "mode": "probe_to_pc", "optical_dark": None, "optical_bright": None,
        "optical_threshold": None, "target_fps": None,
        "started_at": "2026-02-01T10:00:00", "ended_at": "2026-02-01T10:04:00",
    }
    values = [5.1, 5.4, 6.0, 5.2]
    run_id = db.save_run(metadata, make_samples(values))

    run = db.get_run(run_id)
    for key in RUN_FIELDS:
        assert run[key] == metadata[key], key
    assert run["device_name"] == "ATK F1"
    assert db.get_latencies(run_id) == pytest.approx(values)
    # Raw samples keep their order and their sequence numbers.
    assert [s["seq"] for s in db.get_samples(run_id)] == [1, 2, 3, 4]


def test_empty_optional_numbers_become_null(db, device):
    run_id = db.save_run(
        {"device_id": device, "name": "r", "polling_rate_hz": "", "dpi": None},
        make_samples([1.0]))
    run = db.get_run(run_id)
    assert run["polling_rate_hz"] is None
    assert run["dpi"] is None


def test_rename_run(db, device):
    run_id = db.save_run({"device_id": device, "name": "old"}, make_samples([1.0]))
    db.rename_run(run_id, "  new name  ")
    assert db.get_run(run_id)["name"] == "new name"
    with pytest.raises(ValueError):
        db.rename_run(run_id, "  ")


def test_update_run_metadata_keeps_samples(db, device):
    run_id = db.save_run({"device_id": device, "name": "r", "polling_rate_hz": 1000},
                         make_samples([1.0, 2.0, 3.0]))
    metadata = run_as_metadata(db.get_run(run_id))
    metadata.update(polling_rate_hz=4000, notes="re-tagged", dpi=800)
    db.update_run(run_id, metadata)

    run = db.get_run(run_id)
    assert run["polling_rate_hz"] == 4000
    assert run["notes"] == "re-tagged"
    assert run["dpi"] == 800
    assert db.get_latencies(run_id) == [1.0, 2.0, 3.0]


def test_run_as_metadata_round_trips_into_a_duplicate(db, device):
    run_id = db.save_run(
        {"device_id": device, "name": "template", "polling_rate_hz": 2000,
         "connection_mode": "Wired", "dpi": 1600},
        make_samples([1.0]))
    template = run_as_metadata(db.get_run(run_id))
    template["name"] = "copy"
    copy_id = db.save_run(template, make_samples([9.9]))

    copy = db.get_run(copy_id)
    assert copy["name"] == "copy"
    assert copy["polling_rate_hz"] == 2000
    assert copy["dpi"] == 1600
    assert db.get_latencies(copy_id) == [9.9]
    # The original is untouched.
    assert db.get_latencies(run_id) == [1.0]


def test_delete_run_removes_its_samples(db, device):
    run_id = db.save_run({"device_id": device, "name": "r"}, make_samples([1.0]))
    db.delete_run(run_id)
    assert db.get_run(run_id) is None
    assert db.get_samples(run_id) == []


# -------------------------------------------------------------- queries ----
def test_search_matches_run_name_device_notes_and_polling(db, device):
    db.save_run({"device_id": device, "name": "morning", "polling_rate_hz": 1000,
                 "notes": "cold desk"}, make_samples([1.0]))
    db.save_run({"device_id": device, "name": "evening", "polling_rate_hz": 8000},
                make_samples([1.0]))

    assert len(db.list_runs(search="morning")) == 1
    assert len(db.list_runs(search="cold")) == 1
    assert len(db.list_runs(search="8000")) == 1
    assert len(db.list_runs(search="ATK")) == 2
    assert len(db.list_runs(search="nothing here")) == 0


def test_filter_by_device(db, device):
    other = db.create_device(name="Other")
    db.save_run({"device_id": device, "name": "a"}, make_samples([1.0]))
    db.save_run({"device_id": other, "name": "b"}, make_samples([1.0]))
    assert len(db.list_runs(device_id=device)) == 1
    assert len(db.list_runs()) == 2


def test_demo_runs_can_be_hidden_and_counted(db, device):
    db.save_run({"device_id": device, "name": "real", "is_demo": 0}, make_samples([1.0]))
    db.save_run({"device_id": device, "name": "sim", "is_demo": 1}, make_samples([1.0]))
    assert db.count_demo_runs() == 1
    assert len(db.list_runs(include_demo=False)) == 1
    assert len(db.list_runs(include_demo=True)) == 2


# --------------------------------------------------------------- backup ----
def test_backup_is_a_readable_copy(db, device, tmp_path):
    db.save_run({"device_id": device, "name": "r"}, make_samples([1.0, 2.0]))
    destination = db.backup(tmp_path / "backups" / "copy.db")
    assert destination.exists()

    restored = LatencyDB(destination)
    try:
        assert len(restored.list_runs()) == 1
        assert restored.get_latencies(1) == [1.0, 2.0]
    finally:
        restored.close()
