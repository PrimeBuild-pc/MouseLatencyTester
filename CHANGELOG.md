# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
versioning follows [Semantic Versioning](https://semver.org/).

## [1.2.0] — 2026-08-21

### Added — a second way to measure

- **Probe-to-Photon.** A separate measurement mode, firmware **v1.5**. `t₀` is
  the same probe contact on `D2`, taken in the same ISR; `t₁` is the first
  KY-018 reading past a calibrated threshold. The dashboard's test mode shows a
  black target area that turns white the instant Windows reports the click, and
  the Teensy times the gap. Nothing is transmitted between t₀ and t₁, so the
  serial round-trip offset is **not** subtracted — there is no round-trip.
- **Optical calibration, automatic and in the right place.** Entering test mode
  in this mode calibrates first, inside the full-screen overlay, on the same
  target the measurement uses: black, settle, sample, white, settle, sample.
  A baseline taken anywhere else on the screen describes a different patch of
  backlight and is worthless, so it is not left to the operator to get right.
  The threshold is the midpoint and the direction is derived, so a module whose
  ADC value falls as light rises works with no setting. Baselines closer than
  60 ADC counts stop the run before it arms — a threshold inside the noise would
  make every sample a coin toss. Each reading is taken 400 ms after the target
  changes colour, because a photoresistor does not settle instantly. The side
  panel keeps manual black/white buttons as a bench check on the sensor.
- **The two modes never mix.** Different wire token (`OPT:` vs `LAT:`),
  different firmware statistics, `runs.mode` in the archive, and a warning in
  the Compare tab when a comparison spans both. They do not measure the same
  interval and the interface never pretends otherwise.
- **Schema v3.** `runs.mode`, `runs.optical_dark`, `runs.optical_bright`,
  `runs.optical_threshold` and `samples.raw_optical`, added in place. Existing
  runs read as `probe_to_pc`, which is what they are: it was the only mode that
  existed when they were written.
- **The demo device speaks both modes**, so the whole optical flow — calibration,
  target, samples, archive — can be exercised with no hardware attached.

### Honest about the sensor

- The KY-018 is a photoresistor. Its own response time is in the milliseconds,
  the same order as the quantity being measured, and it drifts with ambient
  light and temperature. Probe-to-Photon is documented as a **relative**
  indicator — one setup against itself — and explicitly **not** as an absolute
  click-to-photon benchmark. The dashboard says so in the optical panel, not
  only in the README.
- The dashboard's own repaint is inside the measured interval, driven by a 1 ms
  poll because touching a Tk widget from the input-listener thread is not safe.
  Documented rather than hidden: click-to-photon includes the application.
- The ADC prescaler goes from /128 to /16 while the optical mode is active
  (~13 µs per reading instead of ~112 µs), trading a little absolute accuracy
  for finer timing — the right way round for a threshold crossing.

### Added — buttons that do something

- **BTN1 / BTN2 now do something.** The 10-press hardware acceptance test
  passed, so the buttons are bound: `BTN1` enters and leaves test mode, `BTN2`
  clears the live run while test mode is **not** running. Entirely
  dashboard-side — the firmware is unchanged and still only *reports* the press,
  so the dashboard stays the authority on session state and refuses a press that
  would disturb a run (disconnected, calibrating, or `BTN2` during test mode).

### Fixed

- **The live tab's right-hand column scrolls.** With the optical panel showing it
  was taller than a laptop screen, which put *Enter test mode* below the bottom
  edge of the window with no way to reach it.
- **The optical target is large and in the same place in both windows.** It was
  a 260 px square that the calibration window and the test overlay positioned
  differently; a sensor held on the glass with elastic bands does not hit that,
  and both baselines then came back identical. It is now a 620 × 440 block dead
  centre, drawn by one function that both windows call. A failed calibration
  stays on screen with a live LIGHT reading, several times a second, so the
  sensor can be aimed by watching the number rather than by guessing; Enter
  retries, Esc gives up.
- **The optical calibration happens where the measurement happens.** It used to
  sample a small swatch in the side panel, then measure against a full-screen
  target somewhere else entirely — different patch of backlight, so the
  threshold described the wrong thing. There is now one button, it opens a
  centred full-screen target, and entering test mode repeats the calibration on
  that same target. The per-baseline buttons are gone: they only offered a way
  to get it wrong.
- **A failed calibration reports the numbers it measured**, not just the limit
  it missed — "dark 214, bright 226, 12 counts apart, at least 60 needed" tells
  you whether the setup is nearly right or nowhere near.
- **"Access denied" on the COM port at startup.** Two causes, both addressed:
  the serial reader thread is now joined when the port is closed, so Windows has
  really released the handle before the process exits; and the automatic
  connection at startup retries quietly instead of greeting the user with a
  modal error. A connection the *user* asks for still reports its errors.

### Preserved

- The Probe-to-PC path in the v1.5 sketch is **byte-identical** to v1.4 and
  v1.3: `probeISR()`, the t₀/t₁ block, the `TRIG`/`H` handshake,
  `runCalibration()`, `serviceProbeRearm()`, every filter and the OLED freeze.
  The diff from v1.4 removes six lines: three version strings, one comment, the
  `if (probeFlag)` that became `} else if (probeFlag)`, and the OLED refresh
  guard that now also checks the optical mode. Everything else is an addition.
- The mouse remains untouched: no opening it, no soldering to its PCB, no
  transistor across its microswitch. Removable copper tape on the outside of the
  button is still the only mouse-side modification, in this mode as in the other.

### Settled

- **The hardware is finished.** Every component is built, wired and verified;
  nothing is waiting on hardware. What is left is a 3D-printed enclosure, which
  changes no measurement.
- **The 2N2222A and the 220 Ω resistors are gone from the specification.** They
  were on an early parts list and never found a role — not in the probe method,
  which switches nothing, and not in Probe-to-Photon, which reads a sensor that
  was already wired. Removed from the BOM, the wiring tables, both diagrams and
  the bring-up rather than left as a dangling "reserved" row implying a plan
  that does not exist. This entry is the only record that keeps them.
- **Probe-to-Photon verified on hardware:** 40 clicks, ~16 ms median against
  ~3 ms for the same mouse in Probe-to-PC. The ~13 ms difference is the display
  pipeline *and* the KY-018's own response together, and is documented as such.

---

## [1.1.0] — 2026-08-19

### Added — knowing which mouse is plugged in

- **Mouse detection.** *Devices → Detect connected mouse* reads the USB string
  descriptors (`HidD_GetProductString` and friends) and fills in the profile
  name, manufacturer and serial. The Windows registry only ever reports the
  generic INF name "HID-compliant mouse", which is why the descriptors are read
  directly. When more than one device exposes a mouse collection — a keyboard
  with mouse emulation, for instance — a picker appears instead of guessing.
- **Profiles remember their hardware.** Schema v2 adds `devices.hardware_id`
  (`VID:PID`). Plugging a known mouse in selects its profile automatically at
  startup. The name is yours to change; the hardware ID is what does the
  matching.
- **Polling rate measurement.** *Live test → Measure* counts Raw Input movement
  reports for two seconds and fills the field with the nearest standard rate,
  while reporting the figure actually counted. It measures what the mouse
  achieves rather than what it is configured for, and refuses to produce a
  number when there was not enough movement. Blocked during test mode so it can
  never run next to the timing path.

### Not detectable, and not faked

- **DPI.** No Windows API exposes it: it lives inside the mouse and vendor
  software reads it over undocumented, per-manufacturer HID reports. The field
  stays manual, with a tooltip saying why. A guessed DPI in a benchmark's
  metadata is worse than a blank one.

### Fixed

- Every Win32 call in the new module declares its `restype`/`argtypes`.
  Without that, ctypes truncates 64-bit handles on x64 — a truncated
  `GetModuleHandleW` result made `RegisterClassW` fault with an access
  violation, which would have crashed the app.

### Quality

- 246 tests. The polling-rate formula is tested against steady streams from
  125 Hz to 8 kHz, against pauses in the movement, and against batched delivery
  — the counter was validated separately with synthetic input at known rates,
  where it matched to within 0.1% up to 4 kHz.

---

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

- 2N2222A transistor and the 220 Ω resistors — **not used at all**, settled: the
  finished tester has no role for them.
- **Probe-to-Photon mode** — specified, not implemented. Design recorded in the
  README; no firmware, no protocol token, no UI. It will be a separate mode from
  Probe-to-PC and will not alter the existing timing path.

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
