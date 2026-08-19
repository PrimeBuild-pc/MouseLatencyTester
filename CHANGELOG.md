# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
versioning follows [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-08-19

**First public release.**

The dashboard went through several internal iterations before this point (see
*Pre-release history* below). Those were never published, so the public series
starts cleanly at 1.0.0.

**The measurement pipeline is the one that was verified on real hardware**: the
TRIG↔click association, t₀/t₁ handling, the calibration offset, the 2–100 ms
firmware filter, debounce/re-arm, test mode and the OLED freeze all behave
exactly as in the last known-good internal build.

### Application

- Modular package `latency_tester/` — protocol, statistics, database, serial
  service, settings, i18n, theming and views separated. The measurement and
  serial layers do not depend on the GUI, which is what makes them testable
  without a display.
- **Light / dark / system** themes, persisted. System detection reads the
  Windows personalisation setting.
- **Eight interface languages**: English, Italiano, Deutsch, Español, Français,
  日本語, Русский, 中文. Each is a JSON file in `latency_tester/locales/`, so
  adding one needs no Python.
- **One-click update** in Settings. Checks the project's GitHub releases,
  verifies the installer against the published SHA-256 before running it, and
  refuses to proceed on a mismatch or a missing checksum. The repository is
  hard-coded and only HTTPS GitHub hosts are accepted. Nothing is downloaded or
  launched without explicit confirmation, and an update is blocked outright
  while the current run has unsaved samples.
- **Demo mode**: a simulated Teensy that speaks the real protocol, for using the
  app without hardware. Runs saved in demo mode are stored with `is_demo = 1`,
  shown as `[DEMO]` and filterable. The demo never emits `TRIG`, so the
  measurement handshake is never faked.
- Statistics: **P5**, **MAD** and Tukey-fence **outlier marking**. Outliers are
  circled on the chart and never removed from the data or the statistics.
- Compare tab: selectable **baseline**, Δ median / mean / P95 / P99 in ms and
  percent, per-series marker and line style so charts stay readable without
  colour, and export to PNG / SVG / PDF.
- Sessions: search across run name, device, notes, mode and polling rate;
  rename; full metadata editor; **duplicate as template** for the next run.
- Device profiles with serial number, switch type and usual firmware.
- Runs carry DPI, debounce/switch setting, Teensy firmware version and the demo
  flag.
- Archive **backup** from the settings tab.
- Automatic reconnection when the COM port returns; the current run's samples
  survive a disconnection.
- Tooltips, resizable layout with a sensible minimum size, scrollable tables.
- Test mode overlay is vertically centred, so it stays readable on large
  displays instead of bunching at the top.

### Firmware

- **v1.4** adds `BTN1:PRESS` / `BTN2:PRESS` on pads `B0` / `B1`. Buttons are
  polled in `loop()` and never on an interrupt, debounced with a non-blocking
  30 ms `millis()` window, and their events are queued and only flushed while no
  measurement is pending — so nothing is ever written to the port between t₀ and
  t₁. **The measurement path is byte-identical to v1.3.**
- v1.3 remains the measurement baseline and is kept unmodified, as are v1.0–v1.2.

### Data

- Database schema versioned via `PRAGMA user_version`. An existing archive from
  an earlier internal build is migrated **in place** with
  `ALTER TABLE ADD COLUMN`; the database is never recreated or dropped.
- Preferences in `settings.json` next to the archive. Location overridable with
  `LATENCY_TESTER_HOME`.
- CSV export carries the full run metadata, including every raw sample.

### Distribution

- **Windows installer** built with PyInstaller + Inno Setup. Installs the
  dashboard, **the firmware sketches** and the documentation into one folder,
  defaults to a per-user install so no admin rights are needed, and never
  removes the measurement archive on uninstall.
  `packaging/build_installer.ps1` runs the tests, freezes the app, verifies all
  eight locales were bundled and emits the installer plus a SHA-256.
- MIT licence.

### Quality

- **217 tests**, **87% coverage of the non-GUI code**, with the floor enforced in
  CI so the badge cannot drift. Covers protocol parsing including the button
  tokens, the firmware button-debounce rules, statistics and percentiles, the
  database and its migration, run persistence, CSV export, settings, every
  locale, the updater's checksum and host allow-listing, and the TRIG↔click
  association. Tkinter is deliberately not pixel-tested.
- CI on Windows and Linux across Python 3.10 and 3.12, CodeQL, Dependabot,
  private vulnerability reporting, secret scanning with push protection.
- Documentation: serial protocol reference, Windows install, Teensy flashing,
  the ten-step bring-up with expected values, first measurement and
  troubleshooting.

### Documented, deliberately not changed

- The calibration ping echo is sent as `"P\n"` while the firmware reads a single
  byte, which desynchronises the round-trip loop and collapses the calibration
  offset towards its `+250 µs` constant. Every archived measurement was taken
  with this behaviour; changing it would shift all latency values and break
  comparability. See
  [docs/serial_protocol.md](docs/serial_protocol.md#6-calibration-sequence).

### Not implemented

- Physical button *behaviour* (BTN1 = test mode, BTN2 = reset the live run) —
  planned, gated on the 10-press hardware acceptance test.
- 2N2222A transistor and its 220 Ω resistor — physically present, deliberately
  **not connected**, no firmware, no protocol, purpose not specified.
- Any photoresistor-based measurement mode — does not exist.

---

## Pre-release history

These builds were internal and never published; they are kept in `legacy/` and
still run against the same database.

| Build | Notes |
|---|---|
| Dashboard v2 | Single-file `LatencyTester_Dashboard_v2.py`. Device profiles, named runs, SQLite archive, saved-session browser, comparison charts, full-screen test mode, mean/median/min/max/std dev/P95/P99/IQR/jitter |
| Dashboard v1.1 | Single-file `latency_dashboard_v1_1.py` with live charting |
| Companion | `companion/latency_companion.py`, the original command-line tool |

---

# Firmware changelog

## v1.4 — current
- BTN1 (`B0` / digital 0) and BTN2 (`B1` / digital 1), `INPUT_PULLUP`, wired
  directly to GND with no external resistors.
- One physical press emits exactly one `BTN1:PRESS` / `BTN2:PRESS`. A held
  button never repeats.
- **Timing-safe by construction:** polled in `loop()` and never on an interrupt;
  non-blocking 30 ms `millis()` debounce with no `delay()`; no serial output in
  any ISR; events queued in `pendingButtonPress` and flushed only while
  `measurementActive` and `probeFlag` are both clear; no display work triggered
  by a button.
- Debounce state is seeded from the real pin level in `setup()`, so a button
  held at power-on produces no phantom press.
- **The measurement path is byte-identical to v1.3.** The diff touches only the
  pin defines, the button state block, the two button functions, `setup()`, the
  two version strings and two added lines in `loop()`.
- Buttons currently change no firmware state.

## v1.3 — measurement baseline
- Probe debounce and re-arm: the ISR disarms itself and only re-arms after the
  pin reads HIGH continuously for 80 ms. One press, at most one sample.
- `ARMED` / `REARM` tokens so the desktop overlay can show the true state.
- `TESTMODE:ON` / `TESTMODE:OFF` (`T` / `E`): the OLED is frozen during a test so
  an I²C transfer can never overlap a press.
- `ABORT:NO_CLICK` and `DROP:OUT_OF_RANGE:<ms>`.

## v1.2
- `SKIP:OLED_REFRESH`: a press landing during a display transfer is discarded
  rather than reported as an inflated latency.

## v1.1
- SH1106 OLED and KY-018 support, `LIGHT:` / `L`.

## v1.0
- Probe method, calibration, `TRIG` / `H` / `LAT:` / `STATS:`.

---

## Licence

MIT, from 1.0.0 onward. Chosen because the surrounding ecosystem is permissive
(`pyserial`, `matplotlib`), and because the point of a measurement tool is for
other people to flash the firmware, adapt the wiring and publish their own
numbers without friction.
