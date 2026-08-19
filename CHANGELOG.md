# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [3.0.0] — 2026-08-19

Full refactor of the dashboard. **The measurement pipeline is unchanged**: the
TRIG↔click association, t₀/t₁ handling, the calibration offset, the 2–100 ms
firmware filter, debounce/re-arm, test mode and the OLED freeze all behave
exactly as in v2.

### Added
- Modular package `latency_tester/` — protocol, statistics, database, serial
  service, settings, i18n, theming and views separated. The measurement and
  serial layers no longer depend on the GUI.
- Light / dark / **system** themes, persisted. System detection reads the
  Windows personalisation setting.
- **Italian and English** interface, switchable at runtime and persisted.
  Adding a language is one dictionary entry.
- **Demo mode**: a simulated Teensy that speaks the real protocol, for using
  the app without hardware. Runs saved in demo mode are stored with
  `is_demo = 1`, shown as `[DEMO]` and can be filtered out. The demo never
  emits `TRIG`, so the measurement handshake is never faked.
- Statistics: **P5**, **MAD** and Tukey-fence **outlier marking**. Outliers are
  circled on the chart and never removed from the data or the statistics.
- Compare tab: selectable **baseline**, Δ median / Δ mean / Δ P95 / Δ P99 in ms
  and percent, per-series marker and line style so charts stay readable without
  colour, and chart export to PNG / SVG / PDF.
- Sessions: search across run name, device, notes, mode and polling rate;
  rename; full metadata editor; **duplicate as template** for the next run.
- Device profiles gained serial number, switch type and usual firmware.
- Runs gained DPI, debounce/switch setting, Teensy firmware version and the
  demo flag.
- Archive **backup** from the settings tab.
- Automatic reconnection when the COM port comes back; the current run's
  samples survive a disconnection.
- Tooltips, resizable layout with a sensible minimum size, scrollable tables.
- pytest suite (110 tests) over protocol parsing, statistics, the database and
  its migration, run persistence, settings, i18n and the click-association
  rules.
- `docs/`: serial protocol reference, Windows install, Teensy flashing, wiring,
  first test, troubleshooting.

### Changed
- Database schema is now versioned via `PRAGMA user_version`. An existing v2
  archive is migrated **in place** with `ALTER TABLE ADD COLUMN`; the database
  is never recreated or dropped.
- Preferences moved to `settings.json` next to the archive. The location can be
  overridden with `LATENCY_TESTER_HOME`.
- CSV export gained the new metadata columns.
- The previous single-file dashboards moved to `legacy/` and still run against
  the same database.

### Documented, deliberately not changed
- The calibration ping echo is sent as `"P\n"` while the firmware reads a single
  byte, which desynchronises the round-trip loop and collapses the calibration
  offset towards its `+250 µs` constant. Every archived measurement was taken
  with this behaviour; changing it would shift all latency values and break
  comparability. See
  [docs/serial_protocol.md](docs/serial_protocol.md#6-calibration-sequence).

### Added — hardware integration (firmware v1.4)
- **BTN1 / BTN2 support, test phase only.** `BTN1:PRESS` and `BTN2:PRESS` are
  parsed, counted in the Live test tab and written to the event log. **No action
  is bound to the buttons yet** — the hardware is being verified first.
- Button token parsing is generic (`BTN<n>:<ACTION>`), so a future
  `BTNn:RELEASE` needs no dashboard change.
- The dashboard now accepts both `v1.3` and `v1.4` without a mismatch warning.
- README gained the full reproducible hardware schema: BOM, pin-by-pin wiring
  table, wire-colour convention, ASCII and Mermaid diagrams, 10-step bring-up
  with expected results, and electrical notes.
- `docs/wiring.md` became the bring-up and electrical-notes procedure, with the
  button acceptance checklist.

### Not implemented
- 2N2222A transistor and its 220 Ω resistor — physically present, deliberately
  **not connected**, no firmware, no protocol, purpose not specified.
- Any photoresistor-based measurement mode — does not exist.
- Button *behaviour* (BTN1 = test mode, BTN2 = reset the live run) — planned,
  gated on the 10/10 hardware test passing.

### Added — distribution and localisation
- **Windows installer** (`LatencyTester-<version>-Setup.exe`), built with
  PyInstaller + Inno Setup. It installs the dashboard, **the firmware sketches**
  and the documentation into one folder, defaults to a per-user install so no
  admin rights are needed, and never removes the measurement archive on
  uninstall. `packaging/build_installer.ps1` runs the tests, freezes the app and
  emits the installer plus a SHA-256.
- **Eight interface languages**: English, Italiano, Deutsch, Español, Français,
  日本語, Русский, 中文. Translations moved from Python into
  `latency_tester/locales/*.json`, so adding a language needs no code. 59 tests
  check every locale against the English key set, `{placeholder}` parity, empty
  values and untranslated protocol tokens.
- MIT licence.
- Community and security setup: `CONTRIBUTING.md`, `SECURITY.md` with private
  vulnerability reporting, `CODE_OF_CONDUCT.md`, issue and PR templates, CI on
  Windows and Linux across Python 3.10/3.12, CodeQL, Dependabot, and a tagged
  release workflow that builds the installer.

---

## [2.0.0] — earlier

- Single-file `LatencyTester_Dashboard_v2.py`.
- Device profiles, named runs, SQLite archive, saved-session browser.
- Comparison charts: raw samples, box plot, ECDF, histogram.
- Full-screen test mode with ARMED / WAIT states.
- Statistics: mean, median, min, max, std dev, P95, P99, IQR, jitter.

## [1.1.0] — earlier

- `latency_dashboard_v1_1.py`, live charting.

## [1.0.0] — earlier

- `companion/latency_companion.py`, command-line companion.

---

# Firmware changelog

## v1.4 — current
- BTN1 (`B0` / digital 0) and BTN2 (`B1` / digital 1), `INPUT_PULLUP`, wired
  directly to GND with no external resistors.
- One physical press emits exactly one `BTN1:PRESS` / `BTN2:PRESS`. A held
  button never repeats.
- **Timing-safe by construction:** polled in `loop()` and never on an interrupt;
  non-blocking 30 ms `millis()` debounce with no `delay()`; no serial output in
  any ISR; events are queued in `pendingButtonPress` and flushed only while
  `measurementActive` and `probeFlag` are both clear, so nothing is transmitted
  between t₀ and t₁; no display work is triggered by a button.
- The debounce state is seeded from the real pin level in `setup()`, so a button
  held at power-on produces no phantom press.
- **The measurement path is byte-identical to v1.3.** The diff touches only the
  pin defines, the button state block, the two button functions, `setup()`, the
  two version strings and two added lines in `loop()`. `probeISR()`, the
  measurement block, `runCalibration()` and `serviceProbeRearm()` are untouched.
- Buttons currently change no firmware state.

## v1.3 — measurement baseline
- Probe debounce and re-arm: the ISR disarms itself and only re-arms after the
  pin reads HIGH continuously for 80 ms. One press, at most one sample.
- `ARMED` / `REARM` tokens so the desktop overlay can show the true state.
- `TESTMODE:ON` / `TESTMODE:OFF` (`T` / `E`): the OLED is frozen during a test
  so an I²C transfer can never overlap a press.
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

MIT, from v3.0.0 onward. Chosen because the surrounding ecosystem is
permissive (`pyserial`, `matplotlib`), and because the point of a measurement
tool is for other people to flash the firmware, adapt the wiring and publish
their own numbers without friction.
