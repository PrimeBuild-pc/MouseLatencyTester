"""Every line the firmware can print must decode to the right event."""

import pytest

from latency_tester import protocol
from latency_tester.protocol import parse_line


def test_latency_line():
    event = parse_line("LAT:6.421,min:5.100,max:9.800,avg:6.900,n:12")
    assert event.kind == "latency"
    assert event.payload["latency_ms"] == pytest.approx(6.421)
    assert event.payload["firmware_n"] == 12
    assert event.payload["firmware_avg"] == pytest.approx(6.900)


def test_stats_line():
    event = parse_line(
        "STATS:samples:50,min:4.100,max:19.220,avg:6.700,last:6.100,calib:267")
    assert event.kind == "stats"
    assert event.payload == {
        "n": 50, "min": 4.1, "max": 19.22, "avg": 6.7, "last": 6.1, "calib": 267,
    }


def test_calibration_ok_line():
    event = parse_line(
        "CALIB_OK:267,samples:48,min_us:120,max_us:1500,avg_rt:534")
    assert event.kind == "cal_ok"
    assert event.payload["calib"] == 267
    assert event.payload["samples"] == 48
    assert event.payload["avg_rt"] == 534


def test_calibration_failure():
    assert parse_line("CALIB_FAIL:DEFAULT").kind == "cal_fail"


@pytest.mark.parametrize("line, kind", [
    ("TRIG", "trig"),
    ("P", "calib_ping"),
    ("READY", "ready"),
    ("RESET", "reset"),
    ("ARMED", "armed"),
    ("REARM", "rearm"),
    ("AWAIT", "await_sync"),
    ("PC_SYNCED", "pc_synced"),
    ("TESTMODE:ON", "testmode_on"),
    ("TESTMODE:OFF", "testmode_off"),
    ("SKIP:OLED_REFRESH", "skip_oled"),
    ("ABORT:NO_CLICK", "abort"),
    ("STATS:NO_DATA", "stats_no_data"),
    ("OLED_FAIL", "oled_fail"),
    ("CALIBRATING...", "calibrating"),
])
def test_simple_tokens(line, kind):
    assert parse_line(line).kind == kind


def test_light_line():
    event = parse_line("LIGHT:648")
    assert event.kind == "light"
    assert event.payload == 648


def test_light_line_with_garbage_is_not_lost():
    assert parse_line("LIGHT:xx").kind == "log"


def test_drop_line_carries_the_value():
    event = parse_line("DROP:OUT_OF_RANGE:0.412")
    assert event.kind == "drop"
    assert event.payload == pytest.approx(0.412)


def test_oled_ok_carries_the_address():
    assert parse_line("OLED_OK:0x3C").payload == "0x3C"


def test_timeout_line():
    line = "TIMEOUT:No PC response. Is companion script running?"
    assert parse_line(line).kind == "timeout"


def test_banner_and_firmware_version():
    assert protocol.firmware_version("LATENCY_TESTER v1.3 OLED+LDR") == "v1.3"
    assert protocol.firmware_version("LATENCY_TESTER v1.0 - Probe Method") == "v1.0"
    assert protocol.firmware_version("READY") is None
    assert parse_line("LATENCY_TESTER v1.3 OLED+LDR").payload == "v1.3"


def test_unknown_lines_become_log_events():
    event = parse_line("something the firmware said")
    assert event.kind == "log"
    assert event.payload == "something the firmware said"


def test_whitespace_is_tolerated():
    assert parse_line("  TRIG \r\n").kind == "trig"


def test_command_bytes_are_single_characters():
    commands = [protocol.CMD_CALIBRATE, protocol.CMD_RESET, protocol.CMD_STATS,
                protocol.CMD_VERSION, protocol.CMD_TEST_MODE_ON,
                protocol.CMD_TEST_MODE_OFF, protocol.CMD_LIGHT,
                protocol.REPLY_CLICK_SEEN, protocol.REPLY_NO_CLICK,
                protocol.REPLY_CALIB_PING, protocol.REPLY_CALIB_READY]
    assert all(len(c) == 1 for c in commands)
    # 'R' intentionally serves as both reset and calibration-ready; every other
    # command must stay unique or the firmware switch would be ambiguous.
    unique = [c for c in commands if c != "R"]
    assert len(set(unique)) == len(unique)


# ------------------------------------------------ firmware v1.4 buttons ----
@pytest.mark.parametrize("line, index", [("BTN1:PRESS", 1), ("BTN2:PRESS", 2)])
def test_button_press_events(line, index):
    event = parse_line(line)
    assert event.kind == "button"
    assert event.payload["index"] == index
    assert event.payload["action"] == "PRESS"
    # The raw token is preserved so the log shows exactly what the wire said.
    assert event.payload["token"] == line


def test_button_release_parses_without_a_dashboard_change():
    """v1.4 does not send RELEASE yet; the parser is ready for it anyway."""
    event = parse_line("BTN1:RELEASE")
    assert event.kind == "button"
    assert event.payload["action"] == "RELEASE"


def test_malformed_button_lines_are_not_button_events():
    for line in ("BTNX:PRESS", "BTN1PRESS", "BTN:PRESS", "BTN1:press"):
        assert parse_line(line).kind == "log"


def test_button_tokens_are_not_translated():
    """BTN1/BTN2 are protocol tokens and must never become UI strings."""
    from latency_tester import i18n
    for table in i18n.TRANSLATIONS.values():
        for value in table.values():
            assert "BTN1:PRESS" not in value
            assert "BTN2:PRESS" not in value
