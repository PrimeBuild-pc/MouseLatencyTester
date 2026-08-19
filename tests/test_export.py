"""CSV export: every raw sample must survive the round trip."""

import csv

import pytest

from latency_tester.export import FIELDS, write_csv


@pytest.fixture
def metadata():
    return {
        "name": "8000 Hz wired",
        "polling_rate_hz": 8000,
        "connection_mode": "Wired",
        "dpi": 1600,
        "mouse_firmware": "1.02.00",
        "debounce_setting": "0 ms",
        "calibration_us": 267,
        "teensy_firmware": "v1.4",
        "light_start": 640,
        "light_end": 651,
        "is_demo": 0,
        "notes": "cold desk",
    }


def samples(values):
    return [{"latency_ms": v, "timestamp": f"2026-02-01T10:00:0{i}"}
            for i, v in enumerate(values)]


def read(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_every_sample_is_written(tmp_path, metadata):
    values = [5.1, 5.4, 6.0, 5.2, 40.0]      # the 40.0 is an outlier
    path = write_csv(tmp_path / "out.csv", metadata, samples(values), "ATK F1")
    rows = read(path)

    assert len(rows) == len(values)
    # Outliers are exported like any other sample: nothing is filtered.
    assert [float(r["latency_ms"]) for r in rows] == pytest.approx(values)
    assert [int(r["seq"]) for r in rows] == [1, 2, 3, 4, 5]


def test_header_matches_the_declared_fields(tmp_path, metadata):
    path = write_csv(tmp_path / "out.csv", metadata, samples([1.0]), "M")
    with open(path, newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == list(FIELDS)


def test_metadata_is_repeated_on_every_row(tmp_path, metadata):
    path = write_csv(tmp_path / "out.csv", metadata, samples([1.0, 2.0]), "ATK F1")
    for row in read(path):
        assert row["device"] == "ATK F1"
        assert row["run_name"] == "8000 Hz wired"
        assert row["polling_rate_hz"] == "8000"
        assert row["dpi"] == "1600"
        assert row["calibration_us"] == "267"
        assert row["teensy_firmware"] == "v1.4"


def test_latency_keeps_three_decimals(tmp_path, metadata):
    path = write_csv(tmp_path / "out.csv", metadata, samples([6.4213]), "M")
    assert read(path)[0]["latency_ms"] == "6.421"


def test_missing_optional_values_become_empty_not_none(tmp_path):
    path = write_csv(tmp_path / "out.csv", {"name": "bare"}, samples([1.0]), "")
    row = read(path)[0]
    assert row["polling_rate_hz"] == ""
    assert row["dpi"] == ""
    assert row["light_start"] == ""
    assert row["notes"] == ""
    assert row["is_demo"] == "0"


def test_newlines_in_notes_do_not_break_rows(tmp_path, metadata):
    metadata["notes"] = "line one\nline two"
    path = write_csv(tmp_path / "out.csv", metadata, samples([1.0, 2.0]), "M")
    rows = read(path)
    assert len(rows) == 2
    assert "\n" not in rows[0]["notes"]


def test_demo_runs_are_flagged_in_the_export(tmp_path, metadata):
    metadata["is_demo"] = 1
    path = write_csv(tmp_path / "out.csv", metadata, samples([1.0]), "M")
    assert read(path)[0]["is_demo"] == "1"


def test_timestamps_are_preserved(tmp_path, metadata):
    path = write_csv(tmp_path / "out.csv", metadata, samples([1.0, 2.0]), "M")
    assert [r["timestamp"] for r in read(path)] == \
        ["2026-02-01T10:00:00", "2026-02-01T10:00:01"]


def test_empty_sample_list_still_writes_a_header(tmp_path, metadata):
    path = write_csv(tmp_path / "out.csv", metadata, [], "M")
    assert read(path) == []
    assert path.read_text(encoding="utf-8").startswith("seq,")
