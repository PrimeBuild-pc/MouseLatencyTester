"""Mouse identification and report-rate maths.

The Win32 calls themselves are only exercised on Windows; everything that can
be reasoned about — the naming rules and the rate formula — is tested
everywhere, because a wrong polling rate silently written into a run's metadata
is worse than an empty field.
"""

import sys

import pytest

from latency_tester import devices
from latency_tester.devices import DetectedMouse, RateResult, compute_rate


def mouse(**overrides):
    defaults = dict(vendor_id="373B", product_id="11D9",
                    product="Wireless mouse 8k dongle-L", manufacturer="Compx",
                    serial="541505796617", path=r"\\?\HID#VID_373B&PID_11D9")
    defaults.update(overrides)
    return DetectedMouse(**defaults)


# ------------------------------------------------------------- identity ----
def test_hardware_id_is_vid_colon_pid():
    assert mouse().hardware_id == "373B:11D9"


def test_display_name_prefixes_the_manufacturer():
    assert mouse().display_name == "Compx Wireless mouse 8k dongle-L"


def test_display_name_does_not_repeat_the_manufacturer():
    """"Razer Razer Viper" would be silly."""
    assert mouse(manufacturer="Razer",
                 product="Razer Viper V3 Pro").display_name == "Razer Viper V3 Pro"


def test_display_name_ignores_case_when_deduplicating():
    assert mouse(manufacturer="RAZER",
                 product="Razer Viper").display_name == "Razer Viper"


def test_display_name_falls_back_to_the_manufacturer():
    assert mouse(product="", manufacturer="Logitech").display_name == "Logitech"


def test_display_name_falls_back_to_the_hardware_id():
    assert mouse(product="", manufacturer="").display_name == "Mouse 373B:11D9"


def test_display_name_strips_whitespace():
    assert mouse(product="  Viper  ", manufacturer=" Razer ").display_name == \
        "Razer Viper"


# ----------------------------------------------------------------- rate ----
def stamps_at(hertz, count, start_ns=0):
    step = 1e9 / hertz
    return [int(start_ns + i * step) for i in range(count)]


@pytest.mark.parametrize("hertz", [125, 250, 500, 1000, 2000, 4000, 8000])
def test_rate_matches_a_steady_stream(hertz):
    result = compute_rate(stamps_at(hertz, 500))
    assert result is not None
    assert result.hertz == pytest.approx(hertz, rel=0.02)
    assert result.nominal == hertz


def test_rate_ignores_pauses():
    """A hand that stops moving must not drag the measured rate down."""
    first = stamps_at(1000, 300)
    # 400 ms of nothing, then more movement.
    second = stamps_at(1000, 300, start_ns=first[-1] + int(0.4e9))
    result = compute_rate(first + second)
    assert result is not None
    assert result.hertz == pytest.approx(1000, rel=0.05)


def test_rate_survives_batched_delivery():
    """Windows sometimes delivers several reports at once; the median interval
    collapses to zero there, which is why the formula uses total active time."""
    stamps = []
    now = 0
    for _ in range(150):
        # Four reports delivered together, then a 4 ms wait: 1000 Hz overall.
        for _ in range(4):
            stamps.append(now)
            now += 1_000            # 1 µs apart
        now += 4_000_000 - 4_000
    result = compute_rate(stamps)
    assert result is not None
    assert result.hertz == pytest.approx(1000, rel=0.1)


def test_too_few_samples_is_none():
    assert compute_rate([]) is None
    assert compute_rate(stamps_at(1000, 5)) is None


def test_only_idle_gaps_is_none():
    """Slow, sporadic movement must refuse to produce a number."""
    assert compute_rate([int(i * 0.5e9) for i in range(100)]) is None


def test_non_monotonic_timestamps_do_not_crash():
    stamps = stamps_at(1000, 200)
    stamps[50] = stamps[49] - 1_000_000      # a backwards step
    assert compute_rate(stamps) is not None


@pytest.mark.parametrize("measured, expected", [
    (999.4, 1000), (1012.0, 1000), (7850.0, 8000), (126.0, 125),
    (3980.0, 4000), (2050.0, 2000),
])
def test_nominal_snaps_to_standard_rates(measured, expected):
    assert RateResult(hertz=measured, reports=900, seconds=1.0).nominal == expected


def test_nominal_does_not_invent_a_standard_rate():
    """An unusual rate is reported as itself, not forced into the table."""
    assert RateResult(hertz=1500.0, reports=900, seconds=1.0).nominal == 1500


# --------------------------------------------------------- platform ----
def test_detect_mice_never_raises():
    assert isinstance(devices.detect_mice(), list)


@pytest.mark.skipif(sys.platform == "win32", reason="non-Windows behaviour")
def test_detection_is_empty_off_windows():
    assert devices.detect_mice() == []
    assert devices.measure_report_rate(seconds=0.01) is None


@pytest.mark.skipif(sys.platform != "win32", reason="needs Windows")
def test_detected_mice_look_sane_on_windows():
    for found in devices.detect_mice():
        assert len(found.vendor_id) == 4
        assert len(found.product_id) == 4
        assert found.hardware_id == f"{found.vendor_id}:{found.product_id}"
        assert found.display_name


@pytest.mark.skipif(sys.platform != "win32", reason="needs Windows")
def test_measuring_without_moving_the_mouse_returns_none():
    """No movement must produce no number rather than a fabricated one."""
    assert devices.measure_report_rate(seconds=0.3) is None
