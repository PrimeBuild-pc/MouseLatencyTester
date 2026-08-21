"""SQLite archive for device profiles, runs and raw samples.

The user's database is never recreated or dropped.  Schema changes are applied
as forward-only migrations keyed on ``PRAGMA user_version``; a database written
by dashboard v2 (which had no ``user_version``) reads as version 0 and is
upgraded in place with ``ALTER TABLE ... ADD COLUMN``.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from .constants import MODE_PROBE_PC

SCHEMA_VERSION = 3

# The v0 schema exactly as dashboard v2 created it.  Applied with IF NOT EXISTS
# so an existing archive is left untouched and a fresh one starts from the same
# baseline the migrations expect.
_BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    manufacturer TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
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

CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    seq INTEGER NOT NULL,
    latency_ms REAL NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_runs_device ON runs(device_id);
CREATE INDEX IF NOT EXISTS idx_samples_run ON samples(run_id);
"""

# Migration N upgrades user_version N-1 -> N.  Append only; never edit a
# migration that has already shipped.
_MIGRATIONS: list[list[str]] = [
    # -> 1 : optional device identity fields, richer run metadata, demo flag.
    [
        "ALTER TABLE devices ADD COLUMN serial_number TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE devices ADD COLUMN switch_type TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE devices ADD COLUMN default_firmware TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runs ADD COLUMN dpi INTEGER",
        "ALTER TABLE runs ADD COLUMN debounce_setting TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runs ADD COLUMN teensy_firmware TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runs ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0",
    ],
    # -> 2 : remember which physical mouse a profile belongs to, so the app can
    #        reselect it automatically. "VID:PID", e.g. "373B:11D9".
    [
        "ALTER TABLE devices ADD COLUMN hardware_id TEXT NOT NULL DEFAULT ''",
    ],
    # -> 3 : Probe-to-Photon.  Every run is labelled with the mode that produced
    #        it, so the two can be archived side by side and never averaged
    #        together by accident.  Existing rows are Probe-to-PC by definition:
    #        it was the only mode that existed when they were written.
    [
        "ALTER TABLE runs ADD COLUMN mode TEXT NOT NULL DEFAULT 'probe_to_pc'",
        "ALTER TABLE runs ADD COLUMN optical_dark INTEGER",
        "ALTER TABLE runs ADD COLUMN optical_bright INTEGER",
        "ALTER TABLE runs ADD COLUMN optical_threshold INTEGER",
        "ALTER TABLE samples ADD COLUMN raw_optical INTEGER",
    ],
]

DEVICE_FIELDS = ("name", "manufacturer", "model", "notes",
                 "serial_number", "switch_type", "default_firmware",
                 "hardware_id")

RUN_FIELDS = ("name", "polling_rate_hz", "connection_mode", "mouse_firmware",
              "notes", "target_samples", "calibration_us", "light_start",
              "light_end", "dpi", "debounce_setting", "teensy_firmware",
              "is_demo", "mode", "optical_dark", "optical_bright",
              "optical_threshold")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class LatencyDB:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.migrate()

    # -------------------------------------------------------------- schema --
    @property
    def schema_version(self) -> int:
        return int(self.conn.execute("PRAGMA user_version").fetchone()[0])

    def migrate(self) -> int:
        """Bring the archive up to :data:`SCHEMA_VERSION`.  Idempotent."""
        self.conn.executescript(_BASE_SCHEMA)
        version = self.schema_version
        for index in range(version, len(_MIGRATIONS)):
            for statement in _MIGRATIONS[index]:
                try:
                    self.conn.execute(statement)
                except sqlite3.OperationalError as exc:
                    # A half-applied migration must still be able to finish;
                    # anything other than an already-present column is real.
                    if "duplicate column name" not in str(exc).lower():
                        raise
            self.conn.execute(f"PRAGMA user_version = {index + 1}")
        self.conn.commit()
        return self.schema_version

    def close(self) -> None:
        self.conn.close()

    def backup(self, destination: str | Path) -> Path:
        """Consistent copy of the archive, safe to call while the app runs."""
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        target = sqlite3.connect(destination)
        try:
            self.conn.backup(target)
        finally:
            target.close()
        return destination

    # ------------------------------------------------------------- devices --
    def create_device(self, **fields: Any) -> int:
        values = _clean(fields, DEVICE_FIELDS)
        if not values["name"]:
            raise ValueError("device name is required")
        columns = ", ".join(DEVICE_FIELDS)
        marks = ", ".join("?" * len(DEVICE_FIELDS))
        cur = self.conn.execute(
            f"INSERT INTO devices({columns}, created_at) VALUES({marks}, ?)",
            (*[values[k] for k in DEVICE_FIELDS], _now()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_device(self, device_id: int, **fields: Any) -> None:
        values = _clean(fields, DEVICE_FIELDS)
        if not values["name"]:
            raise ValueError("device name is required")
        assignments = ", ".join(f"{k}=?" for k in DEVICE_FIELDS)
        self.conn.execute(
            f"UPDATE devices SET {assignments} WHERE id=?",
            (*[values[k] for k in DEVICE_FIELDS], int(device_id)),
        )
        self.conn.commit()

    def delete_device(self, device_id: int) -> None:
        self.conn.execute("DELETE FROM devices WHERE id=?", (int(device_id),))
        self.conn.commit()

    def list_devices(self) -> list[sqlite3.Row]:
        return list(self.conn.execute(
            "SELECT * FROM devices ORDER BY name COLLATE NOCASE"))

    def get_device(self, device_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM devices WHERE id=?", (int(device_id),)).fetchone()

    def find_device_by_hardware_id(self, hardware_id: str) -> sqlite3.Row | None:
        """The profile saved for a physically connected mouse, if any."""
        hardware_id = (hardware_id or "").strip()
        if not hardware_id:
            return None
        return self.conn.execute(
            "SELECT * FROM devices WHERE hardware_id=? COLLATE NOCASE "
            "ORDER BY id LIMIT 1", (hardware_id,)).fetchone()

    # ---------------------------------------------------------------- runs --
    def save_run(self, metadata: dict, samples: Sequence[dict]) -> int:
        columns = ", ".join(RUN_FIELDS)
        marks = ", ".join("?" * len(RUN_FIELDS))
        cur = self.conn.execute(
            f"INSERT INTO runs(device_id, {columns}, started_at, ended_at) "
            f"VALUES(?, {marks}, ?, ?)",
            (
                int(metadata["device_id"]),
                *[_run_value(metadata, k) for k in RUN_FIELDS],
                metadata.get("started_at") or _now(),
                metadata.get("ended_at") or _now(),
            ),
        )
        run_id = int(cur.lastrowid)
        self.replace_samples(run_id, samples)
        return run_id

    def update_run(self, run_id: int, metadata: dict) -> None:
        """Edit the metadata of a stored run.  Samples are never touched."""
        assignments = ", ".join(f"{k}=?" for k in RUN_FIELDS)
        params: list[Any] = [_run_value(metadata, k) for k in RUN_FIELDS]
        if metadata.get("device_id") is not None:
            assignments += ", device_id=?"
            params.append(int(metadata["device_id"]))
        self.conn.execute(
            f"UPDATE runs SET {assignments} WHERE id=?", (*params, int(run_id)))
        self.conn.commit()

    def rename_run(self, run_id: int, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError("run name is required")
        self.conn.execute("UPDATE runs SET name=? WHERE id=?", (name, int(run_id)))
        self.conn.commit()

    def replace_samples(self, run_id: int, samples: Sequence[dict]) -> None:
        self.conn.execute("DELETE FROM samples WHERE run_id=?", (int(run_id),))
        self.conn.executemany(
            "INSERT INTO samples(run_id, seq, latency_ms, timestamp, raw_optical) "
            "VALUES(?,?,?,?,?)",
            [
                (
                    int(run_id),
                    i + 1,
                    float(s["latency_ms"]),
                    s.get("timestamp") or datetime.now().isoformat(timespec="milliseconds"),
                    _as_optional_int(s.get("raw_optical")),
                )
                for i, s in enumerate(samples)
            ],
        )
        self.conn.commit()

    def list_runs(self, search: str = "", device_id: int | None = None,
                  include_demo: bool = True) -> list[sqlite3.Row]:
        sql = [
            "SELECT r.*, d.name AS device_name, d.manufacturer, d.model",
            "FROM runs r JOIN devices d ON d.id = r.device_id",
        ]
        where: list[str] = []
        params: list[Any] = []
        if device_id is not None:
            where.append("r.device_id = ?")
            params.append(int(device_id))
        if not include_demo:
            where.append("r.is_demo = 0")
        if search.strip():
            like = f"%{search.strip()}%"
            where.append(
                "(r.name LIKE ? OR d.name LIKE ? OR r.notes LIKE ? "
                "OR r.connection_mode LIKE ? OR CAST(r.polling_rate_hz AS TEXT) LIKE ?)"
            )
            params.extend([like] * 5)
        if where:
            sql.append("WHERE " + " AND ".join(where))
        sql.append("ORDER BY r.started_at DESC, r.id DESC")
        return list(self.conn.execute("\n".join(sql), params))

    def get_run(self, run_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            """
            SELECT r.*, d.name AS device_name, d.manufacturer, d.model
            FROM runs r JOIN devices d ON d.id = r.device_id
            WHERE r.id=?
            """,
            (int(run_id),),
        ).fetchone()

    def get_samples(self, run_id: int) -> list[sqlite3.Row]:
        return list(self.conn.execute(
            "SELECT * FROM samples WHERE run_id=? ORDER BY seq", (int(run_id),)))

    def get_latencies(self, run_id: int) -> list[float]:
        return [row["latency_ms"] for row in self.get_samples(run_id)]

    def delete_run(self, run_id: int) -> None:
        self.conn.execute("DELETE FROM runs WHERE id=?", (int(run_id),))
        self.conn.commit()

    def count_demo_runs(self) -> int:
        return int(self.conn.execute(
            "SELECT COUNT(*) FROM runs WHERE is_demo=1").fetchone()[0])


def _as_optional_int(value: Any) -> int | None:
    """Raw ADC reading, or ``None`` for a Probe-to-PC sample that has none."""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean(fields: dict, keys: Sequence[str]) -> dict:
    out = {}
    for key in keys:
        value = fields.get(key) or ""
        out[key] = value.strip() if isinstance(value, str) else value
    return out


def _run_value(metadata: dict, key: str) -> Any:
    value = metadata.get(key)
    if key == "mode":
        # A run with no mode predates Probe-to-Photon, so it is Probe-to-PC.
        return str(value).strip() if value else MODE_PROBE_PC
    if key in ("target_samples", "calibration_us", "is_demo"):
        return int(value or 0)
    if key in ("polling_rate_hz", "light_start", "light_end", "dpi",
               "optical_dark", "optical_bright", "optical_threshold"):
        return int(value) if value not in (None, "") else None
    if value is None:
        return ""
    return value.strip() if isinstance(value, str) else value


def run_mode(run: sqlite3.Row | dict) -> str:
    """The measurement mode of a stored run, defaulting to Probe-to-PC.

    Tolerates a row that predates the column: an archive opened read-only by an
    older build, or a hand-made dict in a test.
    """
    try:
        value = run["mode"]
    except (IndexError, KeyError, TypeError):
        return MODE_PROBE_PC
    return str(value).strip() or MODE_PROBE_PC


def run_as_metadata(run: sqlite3.Row) -> dict:
    """Row -> metadata dict, ready for :meth:`LatencyDB.update_run` or to seed a
    duplicated run."""
    data = {key: run[key] for key in RUN_FIELDS}
    data["device_id"] = run["device_id"]
    return data
