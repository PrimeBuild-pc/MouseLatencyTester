# Contributing

Thanks for taking a look. This is a measurement tool, so the bar for anything
that touches the timing path is deliberately high — everywhere else, please
jump straight in.

## The one rule that matters

**Do not change the measurement pipeline without evidence.**

The following are verified against real hardware and are the reason the numbers
mean anything:

- the `TRIG` ↔ OS-click association and its grace/timeout windows
- `t₀` / `t₁` handling in the firmware ISR and measurement block
- the calibration offset
- the 2–100 ms firmware sample filter
- probe debounce and re-arm
- test mode and the OLED freeze
- the existing serial protocol tokens

A pull request that alters any of these must say **what** changes, **why**, and
**what was measured before and after** — ideally two saved runs compared in the
app with one as the baseline. "It looks cleaner" is not evidence.

Everything else — UI, charts, statistics, database, translations, docs,
packaging — is fair game.

## Getting set up

```powershell
git clone https://github.com/PrimeBuild-pc/MouseLatencyTester.git
cd MouseLatencyTester
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest tests -q
python run_dashboard.py
```

**No hardware? You don't need any.** Settings → Demo mode → Start demo device
gives you a simulated Teensy that speaks the real protocol, so the interface,
the charts and the archive are all usable.

## Before you open a pull request

- [ ] `python -m pytest tests -q` passes
- [ ] `python -m pytest tests --cov` stays at or above the 85% floor
- [ ] new logic has a test (see below)
- [ ] no new runtime dependency unless it genuinely earns its place
- [ ] the app still starts, in demo mode at minimum

## Testing

`pytest`, no other framework. The suite is fast and has no hardware or display
dependency — the measurement and serial layers deliberately never import
tkinter, which is what makes that possible.

Tkinter is **not** pixel-tested. Don't add tests that try.

Coverage is measured on the non-GUI modules only — the GUI is excluded rather
than padded with tests that assert nothing. CI fails below **85%**.

`tests/test_button_debounce.py` is a **mirror of the firmware**, not an import
of it: it transcribes `serviceButtons()` / `flushButtonEvents()` from the v1.4
sketch. If you change the corresponding `.ino`, change the mirror in the same
PR.

### The updater

`latency_tester/updater.py` downloads and runs an executable, so it is held to a
higher bar than the rest of the code:

- the repository is hard-coded; nothing configurable may redirect it;
- only HTTPS GitHub hosts are accepted;
- the installer is verified against the release's `SHA256SUMS.txt` **before** it
  is executed, and a mismatch deletes the file and aborts;
- a release without a published checksum is refused outright.

Any PR touching it must keep every one of those, and the tests that prove
them.

## Adding a language

The nicest small contribution, and it needs no Python:

1. Copy `latency_tester/locales/en.json` to `latency_tester/locales/xx.json`
   using the two-letter [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes)
   code.
2. Translate the **values**. Leave the keys alone.
3. Add the language's own name to `LANGUAGE_NAMES` in
   `latency_tester/i18n.py` (e.g. `"pt": "Português"`).
4. `python -m pytest tests/test_locales.py -q`

The locale tests check that your file has exactly the English key set, that
`{placeholders}` are unchanged, that nothing is empty, and that no protocol
token got translated. They will tell you precisely what is wrong.

**Never translate protocol tokens.** `TRIG`, `LAT`, `ARMED`, `REARM`,
`CALIB_OK`, `BTN1:PRESS` and friends are the wire format between the firmware
and the dashboard. Only the interface is translated.

## Firmware changes

Sketches are versioned as whole directories and **old versions are never
edited or deleted** — `latency_tester_oled_ldr_v1_3` is the measurement
baseline and stays byte-identical forever. Add `v1_5`, and keep the diff from
the previous version small enough to review line by line.

New serial tokens must be **additive**. Older dashboards treat unknown lines as
log output, so nothing breaks — but a renamed or repurposed token breaks
everyone. Document any addition in `docs/serial_protocol.md`, including the
version column in the compatibility table.

## Building the installer

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_installer.ps1
```

Needs [Inno Setup 6](https://jrsoftware.org/isdl.php). The script runs the
tests first and refuses to build if they fail.

## Style

Match the surrounding code. Type hints where they clarify, comments that
explain *why* rather than restating *what*, and no thread may touch tkinter —
the serial reader and the mouse callback communicate through the event queue.

## Reporting a bug

Please include the firmware version from the connection bar, what the event log
showed, and whether it reproduces in demo mode. A CSV export of the affected
run helps more than a screenshot.

Security issues go to [SECURITY.md](SECURITY.md), not the issue tracker.
