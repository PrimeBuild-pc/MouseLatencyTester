<div align="center">

<img src="docs/images/in-development.svg" alt="in development..." width="420">

<img src="docs/images/banner.png" alt="MouseLatencyTester" width="100%">

<br>

<a href="https://github.com/PrimeBuild-pc/MouseLatencyTester/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/PrimeBuild-pc/MouseLatencyTester?style=plastic&amp;logo=git&amp;logoColor=white"></a>
<a href="https://github.com/PrimeBuild-pc/MouseLatencyTester/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/PrimeBuild-pc/MouseLatencyTester?style=plastic&amp;logo=github"></a>
<a href="https://github.com/PrimeBuild-pc/MouseLatencyTester/issues"><img alt="Open issues" src="https://img.shields.io/github/issues/PrimeBuild-pc/MouseLatencyTester?style=plastic&amp;logo=github"></a>

<a href="https://github.com/PrimeBuild-pc/MouseLatencyTester/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/PrimeBuild-pc/MouseLatencyTester?style=plastic&amp;logo=github&amp;label=release"></a>
<a href="https://github.com/PrimeBuild-pc/MouseLatencyTester/releases"><img alt="Downloads" src="https://img.shields.io/github/downloads/PrimeBuild-pc/MouseLatencyTester/total?style=plastic&amp;logo=github&amp;label=downloads&amp;color=4ade80"></a>
<a href="https://github.com/PrimeBuild-pc/MouseLatencyTester/actions/workflows/tests.yml"><img alt="Tests" src="https://img.shields.io/github/actions/workflow/status/PrimeBuild-pc/MouseLatencyTester/tests.yml?branch=main&amp;style=plastic&amp;logo=githubactions&amp;label=tests"></a>
<a href="https://github.com/PrimeBuild-pc/MouseLatencyTester/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://img.shields.io/github/actions/workflow/status/PrimeBuild-pc/MouseLatencyTester/codeql.yml?branch=main&amp;style=plastic&amp;logo=github&amp;label=CodeQL"></a>
<a href="LICENSE"><img alt="License" src="https://img.shields.io/github/license/PrimeBuild-pc/MouseLatencyTester?style=plastic"></a>

<a href="pyproject.toml"><img alt="Python 3.10 or newer" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=plastic&amp;logo=python&amp;logoColor=white"></a>
<a href="docs/installation_windows.md"><img alt="Windows 10 and 11" src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?style=plastic&amp;logo=windows&amp;logoColor=white"></a>
<a href="#languages"><img alt="Eight UI languages" src="https://img.shields.io/badge/UI%20languages-8-a78bfa?style=plastic&amp;logo=googletranslate&amp;logoColor=white"></a>
<a href="firmware"><img alt="Firmware 1.4" src="https://img.shields.io/badge/firmware-v1.4-fbbf24?style=plastic&amp;logo=arduino&amp;logoColor=white"></a>
<a href="#hardware"><img alt="Hardware assembled and verified" src="https://img.shields.io/badge/hardware-assembled%20%26%20verified-4ade80?style=plastic"></a>

<br>

**Measure how long your mouse actually takes to click — to the microsecond.**

A Teensy 2.0 watches a probe touch the switch, the dashboard watches Windows report the click,<br>
and the difference is your real input latency. Archive it, chart it, compare it.

<br>

<a href="https://github.com/PrimeBuild-pc/MouseLatencyTester/releases/latest">
<img src="https://img.shields.io/badge/%E2%AC%87%20Download%20for%20Windows-5b9cff?style=plastic&amp;logoColor=white" alt="Download for Windows" height="32">
</a>

<sub>No hardware yet? The app ships a built-in simulator — <b>Settings → Demo mode</b>.</sub>

</div>

<br>

---

## Gallery

<div align="center">

<img src="docs/images/live-dark.png" alt="Live test tab, dark theme" width="92%">

<sub><b>Live test</b> — mean, median, P5/P95/P99, IQR, MAD and jitter, with outliers ringed on the chart.</sub>

</div>

<br>

<table>
<tr>
<td width="50%" align="center">
<img src="docs/images/compare-box.png" alt="Compare tab with box plot" width="100%"><br>
<sub><b>Compare</b> — box plot with baseline deltas in ms and %</sub>
</td>
<td width="50%" align="center">
<img src="docs/images/compare-ecdf.png" alt="Compare tab with ECDF chart" width="100%"><br>
<sub><b>ECDF</b> — where the slow clicks actually live</sub>
</td>
</tr>
<tr>
<td width="50%" align="center">
<img src="docs/images/testmode-armed.png" alt="Test mode, armed" width="100%"><br>
<sub><b>Test mode</b> — 🟩 armed, press now</sub>
</td>
<td width="50%" align="center">
<img src="docs/images/testmode-wait.png" alt="Test mode, waiting" width="100%"><br>
<sub><b>Test mode</b> — 🟥 wait / release</sub>
</td>
</tr>
</table>

<details>
<summary><b>More screenshots</b> — light theme, sessions, devices, settings, raw samples, histogram</summary>
<br>
<table>
<tr>
<td width="50%" align="center">
<img src="docs/images/live-light.png" alt="Live test tab, light theme" width="100%"><br>
<sub>Live test — light theme</sub>
</td>
<td width="50%" align="center">
<img src="docs/images/sessions.png" alt="Sessions archive" width="100%"><br>
<sub>Sessions — searchable archive</sub>
</td>
</tr>
<tr>
<td width="50%" align="center">
<img src="docs/images/compare-samples.png" alt="Raw sample comparison" width="100%"><br>
<sub>Compare — raw samples</sub>
</td>
<td width="50%" align="center">
<img src="docs/images/compare-histogram.png" alt="Histogram comparison" width="100%"><br>
<sub>Compare — histogram</sub>
</td>
</tr>
<tr>
<td width="50%" align="center">
<img src="docs/images/devices.png" alt="Device profiles" width="100%"><br>
<sub>Devices — one profile per mouse</sub>
</td>
<td width="50%" align="center">
<img src="docs/images/settings.png" alt="Settings with one-click update" width="100%"><br>
<sub>Settings — theme, language, one-click update</sub>
</td>
</tr>
<tr>
<td colspan="2" align="center">
<img src="docs/images/testmode-complete.png" alt="Test mode, target reached" width="50%"><br>
<sub>Test mode — 🟦 target reached</sub>
</td>
</tr>
</table>
</details>

<sub>Screenshots are taken in demo mode, which is why they carry the simulated-data banner.</sub>

---

## What this actually measures

A metal probe is clamped so that it touches a strip of copper tape on the mouse button at the exact
instant the switch actuates. That contact closure is **t₀**, taken inside an interrupt on the Teensy.
The mouse then sends its HID report, Windows delivers the click, and the dashboard answers the
Teensy — **t₁**. The calibrated serial round-trip is subtracted from `t₁ − t₀`.

The result covers switch debounce, the mouse's internal processing, the wireless or USB link, the
polling interval and the OS input stack. It does **not** cover display or render latency.

### Feature maturity — read this first

| | Feature | Status |
|---|---|---|
| 1 | **Probe method** — the measurement above | ✅ **Working and verified on real hardware.** Every number the app produces comes from this path |
| 2 | **OLED SH1106** | ✅ Working. Frozen during test mode so I²C traffic cannot disturb the timing |
| 3 | **KY-018 light sensor** | ✅ Working, but **telemetry only**. Recorded with each run; it plays no part in any measurement |
| 4 | **BTN1 / BTN2 buttons** | 🧪 **Wired, firmware v1.4, test phase.** Each press emits exactly one `BTN1:PRESS` / `BTN2:PRESS`, counted and logged. **No action bound yet** |
| 5 | 2N2222A transistor + 220 Ω | ⛔ **Not connected, not supported.** Purpose not specified; nothing here anticipates it |
| 6 | Photoresistor / click-to-photon mode | ⛔ Does not exist and is not being faked |

Rows 5–6 are not implemented and no wiring for them is documented, on purpose.

---

## Install

<table>
<tr>
<td width="55%" valign="top">

### Windows installer &nbsp;<sub>recommended</sub>

Grab **`LatencyTester-<version>-Setup.exe`** from the
[latest release](https://github.com/PrimeBuild-pc/MouseLatencyTester/releases/latest).

It installs the dashboard, **the firmware sketches** and the full documentation
into a single folder, so you can flash the Teensy without cloning anything.

- Per-user install by default — **no admin rights needed**
- Your archive lives in `Documents\LatencyTester\` and is **never** touched by the uninstaller
- Built-in **one-click updater**: *Settings → Check for updates*

<sub>The installer is not code-signed, so SmartScreen warns on first run.
Verify <code>SHA256SUMS.txt</code> from the release.</sub>

</td>
<td width="45%" valign="top">

### From source

```powershell
git clone https://github.com/PrimeBuild-pc/MouseLatencyTester.git
cd MouseLatencyTester
pip install -r requirements.txt
python run_dashboard.py
```

### No hardware?

**Settings → Demo mode → Start demo device.**

A simulator that speaks the real serial protocol drives the whole interface,
the charts and the archive. Runs saved that way are flagged `[DEMO]` and never
mixed with real measurements.

</td>
</tr>
</table>

### Languages

<div align="center">

🇬🇧 English &nbsp;·&nbsp; 🇮🇹 Italiano &nbsp;·&nbsp; 🇩🇪 Deutsch &nbsp;·&nbsp; 🇪🇸 Español &nbsp;·&nbsp; 🇫🇷 Français &nbsp;·&nbsp; 🇯🇵 日本語 &nbsp;·&nbsp; 🇷🇺 Русский &nbsp;·&nbsp; 🇨🇳 中文

</div>

Switch under *Settings → Language*; the choice persists. Adding another is a single JSON file and
**no Python at all** — see [CONTRIBUTING.md](CONTRIBUTING.md#adding-a-language).

### Documentation

[Installation](docs/installation_windows.md) &nbsp;·&nbsp;
[Flashing the Teensy](docs/flashing_teensy.md) &nbsp;·&nbsp;
[Bring-up & electrical notes](docs/wiring.md) &nbsp;·&nbsp;
[First measurement](docs/first_test.md) &nbsp;·&nbsp;
[Troubleshooting](docs/troubleshooting.md) &nbsp;·&nbsp;
[Serial protocol](docs/serial_protocol.md)

---

## The dashboard

<table>
<tr>
<td width="33%" valign="top">

#### 📊 Live test
Mean, median, min, max, std dev, P5/P95/P99, IQR, MAD and jitter (P95−P5).
Live chart with outliers ringed, `BTN1`/`BTN2` counters, and a **Measure**
button for the real polling rate.

</td>
<td width="33%" valign="top">

#### 🗂 Sessions
Searchable archive. Rename, edit metadata, **duplicate as a template** for the
next configuration, export to CSV.

</td>
<td width="33%" valign="top">

#### 📈 Compare
Raw samples, box plot, ECDF or histogram. Selectable **baseline** with
Δ median / mean / P95 / P99 in ms and %. Export to PNG, SVG, PDF.

</td>
</tr>
<tr>
<td valign="top">

#### 🖱 Devices
One profile per mouse: manufacturer, model, serial, switch type, usual
firmware, notes. **Detects the connected mouse** and reconnects it to its
saved profile automatically.

</td>
<td valign="top">

#### ⚙️ Settings
Eight languages, light / dark / system theme, archive backup, demo mode and
**one-click update**. Preferences persist.

</td>
<td valign="top">

#### 🎯 Test mode
Full screen, colour-coded: 🟩 press · 🟥 wait · 🟦 done. The OLED is frozen so
the display never disturbs the timing.

</td>
</tr>
</table>

> [!IMPORTANT]
> **Raw data is never discarded.** Outliers are detected with the Tukey fence and **marked**, not
> removed. They stay in the database, in the CSV export and in every statistic. Deciding what an
> outlier means is the operator's job, not the software's.

### Knowing your mouse

**Name** — *Devices → Detect connected mouse* reads the USB descriptor and fills in the name,
manufacturer and serial. That name is often the internal or dongle name rather than the marketing
one (an ATK F1 reports as `Compx Wireless mouse 8k dongle-L`), so **rename it to whatever you
like** — the profile is linked to the device by its `VID:PID` hardware ID, not by its name. Once
linked, plugging that mouse in selects its profile automatically.

**Polling rate** — *Live test → Measure* counts the mouse's actual Raw Input reports for two
seconds while you move it, and fills the field with the nearest standard rate while reporting what
was really counted. It measures what the mouse **achieves**, which is not always what it is
configured for. If you do not move enough, it says so rather than guessing.

**DPI** — not detectable, and not faked. No Windows API exposes it: DPI lives inside the mouse and
vendor software reads it over undocumented, per-manufacturer HID reports. Type it in from your
mouse's own software.

### A typical session

```
Razer Viper → 1000 Hz → 50 samples → Save → New run
Razer Viper → 2000 Hz → 50 samples → Save → New run
Razer Viper → 4000 Hz → 50 samples → Save → New run
Razer Viper → 8000 Hz → 50 samples → Save
→ Compare, baseline = 1000 Hz
```

All without restarting the program.

---

## Hardware

Everything below describes the build that is **physically assembled and verified**, so it can be
reproduced without any prior context.

<details open>
<summary><b>BOM / parts list</b></summary>
<br>

| Qty | Component | Function | Notes |
|:--:|---|---|---|
| 1 | **Teensy 2.0** (ATmega32U4, 16 MHz) | Takes t₀ in an ISR, computes latency, talks to the PC | The whole measurement lives here |
| 1 | **OLED 1.30", 128×64, SH1106, I²C, 4-pin** | Local status display | Address `0x3C`. **One** display — see note below |
| 1 | **KY-018 photoresistor module** | `LIGHT` telemetry recorded with each run | Analog output. Not part of the measurement |
| 2 | **Momentary push buttons** | `BTN1` / `BTN2` events | No external resistors — `INPUT_PULLUP` is used |
| 1 | **Breadboard** (400 or 830 points) | Power rails and module mounting | |
| 1 | **Conductive copper tape**, 5 mm | Contact pad on the mouse button | Aluminium foil + tape works too |
| 1 | **Metal probe / multimeter tip** | Closes the circuit at the instant of the click | A stiff bare wire also works |
| 1 | **Helping hands / third hand** | Holds the probe steady | Not optional in practice — probe alignment is the biggest error source |
| — | **Jumper wires M-M and M-F** | Wiring | Both types needed |
| — | **Solid-core wire** | Short, tidy breadboard runs | |
| — | **Soldering iron + solder** | Permanent joints on the probe and tape | |
| — | **Insulating tape** | Strain relief and shorts prevention | |
| 1 | **Micro USB cable** | Power and serial | A data cable, not charge-only |
| 1 | 2N2222A NPN transistor | — | ⛔ **Present but NOT connected and NOT supported by the firmware** |
| 1 | 220 Ω resistor | — | ⛔ **Present but NOT connected** |

> [!NOTE]
> An earlier version of this project's parts list mentioned *two* OLED displays as a future upgrade.
> **The validated build uses exactly one.** A second display is not required and is not supported.

Measured on USB power: **≈ 4.8 V** between `VCC` and `GND` at the breadboard rails.

</details>

<details open>
<summary><b>Wiring — pin by pin</b></summary>
<br>

| Component | Component pin | Teensy pad | Arduino pin | Wire colour | Function |
|---|---|:--:|:--:|---|---|
| Breadboard rail | + | `VCC` | — | 🔴 Red | Power to OLED and KY-018 (~4.8 V on USB) |
| Breadboard rail | − | `GND` | — | ⚫ Black | Common ground for everything |
| Probe | tip | `D2` | **7** | ⚪ White | Probe input, `INPUT_PULLUP`, trigger on `FALLING` |
| Copper tape | on left mouse button | `GND` | — | ⚫ Black | Return path — closing to GND is the t₀ event |
| OLED SH1106 | `GND` | `GND` | — | ⚫ Black | Ground |
| OLED SH1106 | `VCC` / `VDD` | `VCC` | — | 🔴 Red | Power |
| OLED SH1106 | `SCL` / `SCK` | `D0` | **5** | 🟡 Yellow | I²C clock |
| OLED SH1106 | `SDA` | `D1` | **6** | 🟢 Green | I²C data |
| KY-018 | `S` | `F0` | **A0** | 🔵 Blue | Analog light level, 0–1023 |
| KY-018 | `+` | `VCC` | — | 🔴 Red | Power |
| KY-018 | `−` | `GND` | — | ⚫ Black | Ground |
| BTN1 | leg A | `B0` | **0** | 🟠 Orange | Button input, `INPUT_PULLUP` |
| BTN1 | leg B | `GND` | — | ⚫ Black | Pressed = LOW |
| BTN2 | leg A | `B1` | **1** | 🟣 Purple | Button input, `INPUT_PULLUP` |
| BTN2 | leg B | `GND` | — | ⚫ Black | Pressed = LOW |
| Built-in LED | — | `D6` | **11** | — | Lit while a measurement is pending |

> [!WARNING]
> **KY-018 pin order:** always follow the `S` / `+` / `−` markings printed on the module.
> **Do not infer the order from the physical pin positions** — it varies between manufacturers.

> [!TIP]
> **`A0` on a Teensy 2.0** resolves to pad `F0` (digital 21) in Teensyduino. That is why the
> sketch's `analogRead(A0)` reads the pad labelled `F0`.

</details>

<details>
<summary><b>Wire colour convention</b></summary>
<br>

| Colour | Use |
|---|---|
| ⚫ Black | GND |
| 🔴 Red | VCC / ≈ 5 V |
| 🟡 Yellow | OLED `SCL` |
| 🟢 Green | OLED `SDA` |
| 🔵 Blue | KY-018 analog signal |
| ⚪ White | Probe |
| 🟠 Orange | BTN1 |
| 🟣 Purple | BTN2 |

**These colours are a project convention for readability, not an electrical requirement.** Any
colour works electrically; keeping to the table makes the photos, the diagrams and the physical
build agree with each other.

</details>

<details>
<summary><b>Diagram</b></summary>
<br>

```text
                    TEENSY 2.0  (ATmega32U4, 16 MHz)
                  +--------------------------------+
   metal probe ---|  D2   (7)   probe in    [WHT]  |
        :         |                                |
        :         |  D0   (5)   I2C SCL     [YEL] -+--------> OLED SCL
        :         |  D1   (6)   I2C SDA     [GRN] -+--------> OLED SDA
        :         |                                |
        :         |  F0   (A0)  analog in   [BLU] <+--------- KY-018  S
        :         |                                |
        :         |  B0   (0)   BTN1 in     [ORG] <+--------- BTN1 --+
        :         |  B1   (1)   BTN2 in     [PUR] <+--------- BTN2 --+
        :         |                                |                 |
        :         |  D6   (11)  built-in LED       |                 |
        :         |                                |                 |
        :         |  VCC                    [RED] -+---+--> OLED VCC |
        :         |  GND                    [BLK] -+-+ +--> KY-018 + |
        :         +--------------------------------+ |               |
        :                                            |               |
        v                                            +--> OLED GND   |
  +------------------------+                         +--> KY-018 -   |
  |  copper tape on the    |                         +---------------+
  |  LEFT mouse button     |---------[BLK]-----------+  (BTN1/BTN2 other leg)
  +------------------------+
                                    GND rail

  The probe touches the tape at the exact instant the switch actuates -> t0.

  Colour codes: BLK=GND  RED=VCC  YEL=SCL  GRN=SDA
                BLU=KY-018 signal  WHT=probe  ORG=BTN1  PUR=BTN2

  NOT CONNECTED: 2N2222A transistor, 220 ohm resistor.
```

```mermaid
graph LR
    subgraph Teensy["Teensy 2.0 · ATmega32U4"]
        VCC["VCC"]
        GND["GND"]
        D2["D2 · pin 7"]
        D0["D0 · pin 5"]
        D1["D1 · pin 6"]
        F0["F0 · A0"]
        B0["B0 · pin 0"]
        B1["B1 · pin 1"]
        LED["D6 · pin 11 · LED"]
    end

    PROBE["Metal probe"] -->|white| D2
    TAPE["Copper tape<br/>on left mouse button"] -->|black| GND

    D0 -->|yellow · SCL| OLED["OLED SH1106<br/>128x64 I2C 0x3C"]
    D1 -->|green · SDA| OLED
    VCC -->|red| OLED
    GND -->|black| OLED

    KY["KY-018 LDR module"] -->|blue · S| F0
    VCC -->|red · +| KY
    GND -->|black · −| KY

    BTN1["BTN1"] -->|orange| B0
    BTN1 -->|black| GND
    BTN2["BTN2"] -->|purple| B1
    BTN2 -->|black| GND

    TRANSISTOR["2N2222A + 220 Ω<br/>NOT CONNECTED"]:::todo

    classDef todo fill:#2a2a2a,stroke:#b45309,stroke-dasharray: 5 4,color:#fbbf24
```

The 2N2222A and its resistor appear only to record that they exist and are **deliberately
unconnected**. No connection for them is invented here.

</details>

<details>
<summary><b>Bring-up — test in this order</b></summary>
<br>

Each step must pass before moving to the next.

| # | Step | Expected result |
|:--:|---|---|
| 1 | **Teensy alone.** Flash, open Serial Monitor at 115200 | `LATENCY_TESTER v1.4 OLED+LDR+BTN` then `READY` |
| 2 | **Probe.** Touch the probe to the copper tape | `TRIG` appears, pin-11 LED lights. Without the dashboard you then get `TIMEOUT:…` — that is correct |
| 3 | **OLED I²C scan** | Exactly one device at `0x3C` |
| 4 | **OLED display test** — `firmware/displayTester/` | Text on the panel; the main sketch prints `OLED_OK:0x3C` |
| 5 | **KY-018.** Send `L` | Covered ≈ **0–20**, evening room ≈ **150–250**, phone torch ≈ **1000** |
| 6 | **All three together** | Probe still triggers; display refreshes ~2×/s. Occasional `SKIP:OLED_REFRESH` outside test mode is normal and correct |
| 7 | **Calibration** | `CALIB_OK:<offset>,…`. Lands near 250 µs — see the [known quirk](docs/serial_protocol.md#6-calibration-sequence) |
| 8 | **Test mode** | Overlay appears, `TESTMODE:ON`, OLED freezes, green ⇄ red tracks `ARMED`/`REARM` |
| 9 | **BTN1 / BTN2** | 10 presses → **exactly 10** events, no phantoms, no doubles, no repeat while held |
| 10 | Transistor / light mode | ⛔ Not defined. Do not wire the 2N2222A |

Full detail with expected values: **[docs/wiring.md](docs/wiring.md)**.

</details>

<details>
<summary><b>Electrical notes</b></summary>
<br>

- **Disconnect USB before soldering.** No exceptions.
- **Never connect VCC directly to the probe signal.** `D2` is an input with an internal pull-up; it
  expects to be shorted to **GND** and nothing else.
- **All modules share a common GND.** Teensy, OLED, KY-018 and both buttons on the same rail.
- **Follow the printed `S` / `+` / `−` labels on the KY-018.** Do not deduce from pin position.
- **No external resistors on the buttons.** `INPUT_PULLUP` provides them; pull-downs break the logic.
- **Do not assume the 2N2222A pinout.** EBC and ECB both exist depending on package and
  manufacturer — and it is not to be wired yet regardless.
- Measured supply on USB: **≈ 4.8 V**. Both the OLED and the KY-018 are fine at that level.

</details>

---

## Firmware

| Sketch | Notes |
|---|---|
| `latency_tester/` | v1.0 — probe only |
| `latency_tester_oled_ldr/` | v1.1 — adds OLED + KY-018 |
| `latency_tester_oled_ldr_v1_2/` | v1.2 — adds `SKIP:OLED_REFRESH` |
| `latency_tester_oled_ldr_v1_3/` | v1.3 — debounce/re-arm, test mode, OLED freeze. **Measurement baseline** |
| **`latency_tester_oled_ldr_v1_4/`** | **v1.4 — current. v1.3 plus BTN1/BTN2 test events. Measurement path byte-identical to v1.3** |
| `displayTester/` | Standalone OLED check |

Older sketches still work; unknown tokens are logged, never dropped. Compatibility table in
[docs/serial_protocol.md](docs/serial_protocol.md).

---

## Repository layout

```
latency_tester/          the dashboard, as a package
  protocol.py            wire format: tokens, parsing        (no GUI, no serial)
  stats.py               percentiles, MAD, outliers, deltas  (pure functions)
  database.py            SQLite archive + schema migrations
  serial_service.py      reader thread, TRIG/click association
  devices.py             mouse identification + report-rate measurement
  updater.py             checksum-verified one-click update
  demo.py                simulated Teensy
  settings.py            persisted preferences
  i18n.py                translation loader
  locales/               one JSON file per language
  theme.py               light / dark / system palettes
  widgets.py             tooltips, metric cards, live chart
  export.py              CSV
  app.py                 shell, state, event pump
  views/                 live · sessions · compare · devices · preferences · testmode
firmware/                Arduino sketches, v1.0 → v1.4
packaging/               PyInstaller spec, Inno Setup script, build script
tests/                   pytest suite
docs/                    protocol, install, bring-up, first test, troubleshooting
legacy/                  the previous single-file dashboards, still runnable
```

The measurement and serial logic never imports tkinter, which is what lets it be tested headlessly.

## Development

```powershell
pip install -r requirements-dev.txt
python -m pytest tests -q
```

**246 tests**, **87% coverage of the non-GUI code** — the GUI is deliberately excluded rather than
padded with tests that assert nothing. CI enforces the coverage floor, so the badge cannot drift
down silently.

Covered: protocol parsing including the button tokens, the firmware button-debounce rules,
statistics and percentiles, the database and its migrations, run save/load/duplicate, CSV export,
settings, every locale, the updater's checksum verification and host allow-listing, mouse naming
rules and the polling-rate formula, the TRIG↔click association, and the demo device.

`tests/test_button_debounce.py` mirrors `serviceButtons()` / `flushButtonEvents()` from the v1.4
sketch line for line, so the bench acceptance rules are checked in CI. It is a **mirror, not an
import**: if the `.ino` changes, change the test too.

### Building the installer

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_installer.ps1
```

Requires [Inno Setup 6](https://jrsoftware.org/isdl.php). The script runs the tests first and
refuses to build if anything fails, then emits the installer and its SHA-256 into
`build\installer\`.

---

## Contributing

Pull requests are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) covers setup, testing rules and how to
add a language — the last of which needs no Python and is the easiest place to start.

One rule matters above the others: **changes to the measurement pipeline need before/after
numbers**, not opinions. Everything else is fair game.

Security issues go through
[private reporting](https://github.com/PrimeBuild-pc/MouseLatencyTester/security/advisories/new),
never a public issue — see [SECURITY.md](SECURITY.md).

## Support the project

If MouseLatencyTester is useful to you, you can support its development here:

[![PayPal](https://img.shields.io/badge/Support-PayPal-0070BA?style=plastic&logo=paypal&logoColor=white)](https://paypal.me/PrimeBuildOfficial?country.x=IT&locale.x=it_IT)

## Privacy

No telemetry, no analytics, no background network activity. Every measurement stays in a local
SQLite file under your Documents folder. The only network request the app ever makes is the update
check, and only when **you** press the button.

## Licence

[MIT](LICENSE) © 2026 PrimeBuild.

<div align="center">
<sub>Built around a Teensy 2.0 (PJRC), with <code>pyserial</code>, <code>pynput</code> and <code>matplotlib</code>.</sub>
</div>
