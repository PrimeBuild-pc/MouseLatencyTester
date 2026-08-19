"""Persistent application preferences.

Stored as JSON next to the archive, under the user's own home directory --
nothing here is tied to a specific machine or account name.  Unknown keys in an
existing file are preserved so a downgrade does not lose settings.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

APP_DIR_NAME = "LatencyTester"
SETTINGS_FILE = "settings.json"
DB_FILE = "latency_tester.db"

DEFAULTS: dict[str, Any] = {
    "language": "it",
    "theme": "system",          # "system" | "light" | "dark"
    "last_device_id": None,
    "last_polling_rate": "1000",
    "last_connection_mode": "Wireless",
    "last_dpi": "",
    "target_samples": 50,
    "auto_connect": True,
    "auto_reset_on_test": True,
    "window_geometry": "",
    "data_dir": "",             # empty -> default_data_dir()
}


def default_data_dir() -> Path:
    """Where the archive and settings live.

    ``LATENCY_TESTER_HOME`` overrides everything (handy for tests and for
    running from a USB stick); otherwise ``~/Documents/LatencyTester``, which is
    where dashboard v2 already put the database.
    """
    override = os.environ.get("LATENCY_TESTER_HOME")
    if override:
        base = Path(override)
    else:
        documents = Path.home() / "Documents"
        base = (documents if documents.is_dir() else Path.home()) / APP_DIR_NAME
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        base = Path(__file__).resolve().parent.parent
        log.warning("cannot create %s, falling back to %s", base, base)
    return base


class Settings:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_data_dir() / SETTINGS_FILE
        self._data: dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            log.warning("cannot read %s (%s), using defaults", self.path, exc)
            return
        if isinstance(raw, dict):
            self._data.update(raw)

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            log.warning("cannot write %s: %s", self.path, exc)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def update(self, **values: Any) -> None:
        self._data.update(values)

    @property
    def data_dir(self) -> Path:
        configured = str(self.get("data_dir") or "").strip()
        return Path(configured) if configured else default_data_dir()

    @property
    def db_path(self) -> Path:
        return self.data_dir / DB_FILE
