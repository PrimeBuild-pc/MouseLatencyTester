"""CSV export shared by the live view and the archive."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

FIELDS = [
    "seq", "timestamp", "latency_ms", "device", "run_name", "polling_rate_hz",
    "connection_mode", "dpi", "mouse_firmware", "debounce_setting",
    "calibration_us", "teensy_firmware", "light_start", "light_end",
    "is_demo", "notes",
]


def write_csv(path: str | Path, metadata: dict, samples: Sequence[dict],
              device_name: str = "") -> Path:
    """One row per raw sample, run metadata repeated on every row.

    Every sample is written, including the ones flagged as outliers.
    """
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for index, sample in enumerate(samples):
            writer.writerow({
                "seq": index + 1,
                "timestamp": sample.get("timestamp", ""),
                "latency_ms": f'{float(sample["latency_ms"]):.3f}',
                "device": device_name,
                "run_name": metadata.get("name", ""),
                "polling_rate_hz": _blank(metadata.get("polling_rate_hz")),
                "connection_mode": metadata.get("connection_mode", ""),
                "dpi": _blank(metadata.get("dpi")),
                "mouse_firmware": metadata.get("mouse_firmware", ""),
                "debounce_setting": metadata.get("debounce_setting", ""),
                "calibration_us": _blank(metadata.get("calibration_us")),
                "teensy_firmware": metadata.get("teensy_firmware", ""),
                "light_start": _blank(metadata.get("light_start")),
                "light_end": _blank(metadata.get("light_end")),
                "is_demo": int(metadata.get("is_demo") or 0),
                "notes": (metadata.get("notes") or "").replace("\n", " "),
            })
    return path


def _blank(value) -> str:
    return "" if value is None else str(value)
