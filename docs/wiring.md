# Bring-up and electrical notes

The **pin-by-pin wiring table, the BOM, the wire-colour convention and the
diagrams live in the [main README](../README.md#hardware)** — that is the
single source of truth, so it cannot drift from this file. This document covers
the procedure: what to test, in what order, and what you should actually see.

---

## Bring-up order

Do not skip ahead. Each step assumes the previous one passed.

### 1. Teensy alone

Flash `firmware/latency_tester_oled_ldr_v1_4/`, open the Arduino Serial Monitor
at `115200`.

**Expected:**
```
LATENCY_TESTER v1.4 OLED+LDR+BTN
READY
```
The board appears in Device Manager under *Ports (COM & LPT)*.

**If not:** try another USB cable (many are charge-only), another port, and
install the Teensyduino driver.

---

### 2. Probe

Wire the probe to `D2` (digital 7) and the copper tape to `GND`. Touch them
together.

**Expected:** `TRIG` appears, the pin-11 LED lights, and about three seconds
later:
```
TIMEOUT:No PC response. Is companion script running?
```
That timeout is **correct** at this stage — no PC software is answering yet.

**If nothing happens:** the probe is not making contact, or the tape is not
actually connected to `GND`. Check continuity with a multimeter.

---

### 3. OLED I²C scan

Run any I²C scanner sketch (or `firmware/displayTester/`).

**Expected:** exactly **one** device found, at address `0x3C`.

**If two addresses appear:** you have something else on the bus. **If none
appear:** check `D0`→`SCL` (yellow) and `D1`→`SDA` (green), and that the module
has power.

---

### 4. OLED display test

Flash `firmware/displayTester/`.

**Expected:** readable text on the panel. Back on the main sketch, the boot
sequence prints `OLED_OK:0x3C` rather than `OLED_FAIL`.

The tester measures latency perfectly well without a working display — the OLED
is convenience, not a dependency.

---

### 5. KY-018 analog read

Wire `S`→`F0`/`A0` (blue), `+`→VCC (red), `−`→GND (black). Send `L`.

**Expected `LIGHT:` values, measured on this build:**

| Condition | Value |
|---|---|
| Sensor covered | ≈ 0 – 20 |
| Evening room lighting | ≈ 150 – 250 |
| Phone torch held close | ≈ 1000 |

**If the value never moves:** you probably have the pins in the wrong order.
Follow the `S` / `+` / `−` labels printed on the module — do **not** infer them
from physical position. Verify the supply with a multimeter (≈ 4.8 V on USB).

---

### 6. Probe + OLED + KY-018 together

**Expected:** the probe still triggers; the display refreshes about twice per
second; `LIGHT` tracks the room.

You may occasionally see:
```
SKIP:OLED_REFRESH
```
This is **correct behaviour**, not a fault. The press landed during an I²C
transfer, so the firmware discarded the sample rather than reporting an
inflated latency. It should not occur in test mode, where the display is
frozen.

---

### 7. Calibration

Start the dashboard, connect, press **Calibrate**.

**Expected:**
```
CALIB_OK:<offset>,samples:<n>,min_us:...,max_us:...,avg_rt:...
```
The offset lands close to 250 µs. That is expected and is explained in the
[calibration quirk section](serial_protocol.md#6-calibration-sequence) — it is
deliberate and unchanged from the verified setup.

---

### 8. Test mode

Set a target, press **ENTER TEST MODE**.

**Expected:** a full-screen overlay; `TESTMODE:ON` in the log; the OLED freezes
on a "TEST MODE / OLED PAUSED" screen; the overlay tracks 🟩 `ARMED` ⇄ 🟥
`REARM` and turns 🟦 at the target.

---

### 9. Buttons — BTN1 / BTN2

Wire `B0`(digital 0)→BTN1→GND (orange) and `B1`(digital 1)→BTN2→GND (purple).
**No external resistors** — `INPUT_PULLUP` supplies them. Not pressed = HIGH,
pressed = LOW.

Firmware v1.4 is a **test phase**: the buttons emit an event and nothing else.
They are polled in `loop()` with a non-blocking 30 ms debounce, never on an
interrupt, and the event is queued and only transmitted while no measurement is
pending — so nothing is ever printed between t₀ and t₁.

With the dashboard open, press **BTN1 ten times, slowly**:

```text
BTN1:PRESS
```

Then **BTN2 ten times**:

```text
BTN2:PRESS
```

The Live test tab's *Controls* panel keeps a running `BTN1` / `BTN2` counter,
so you can read the totals without counting log lines.

**Pass criteria — all of them:**

- [ ] 10 presses of BTN1 → exactly 10 `BTN1:PRESS`
- [ ] 10 presses of BTN2 → exactly 10 `BTN2:PRESS`
- [ ] no phantom events while nothing is touched
- [ ] no double event from a single press
- [ ] holding a button down does not repeat
- [ ] a normal 10-click mouse session still measures, with median and spread
      consistent with your previous runs

That last check matters: it is what proves adding the buttons did not disturb
the timing. Run it, compare against an earlier run in the **Compare** tab with
the old run as baseline, and confirm Δ median and Δ P95 are within your usual
run-to-run noise.

Only once every box is ticked do the buttons get real behaviour:

| Button | Planned action |
|---|---|
| `BTN1` | **Request** enter/exit test mode |
| `BTN2` | Reset the live run, only while **not** in test mode |

The firmware reports the event; the **dashboard decides**. During a measurement
or during test mode, BTN2 is refused rather than allowed to destroy a run. No
long presses, double clicks or combinations.

---

### 10. Transistor / light-sensing mode

⛔ **Not defined. Do not wire the 2N2222A.**

The transistor and its 220 Ω resistor are physically present but deliberately
unconnected. No firmware supports them, no protocol tokens exist, and no
measurement mode has been specified. This step stays blocked until a separate
specification for the click-to-photon / light-sensing mode exists.

---

## Electrical notes

* **Disconnect USB before soldering.** No exceptions.
* **Never connect VCC directly to the probe signal.** `D2` is an input with an
  internal pull-up; it expects to be shorted to **GND** and nothing else.
* **All modules share a common GND.** Teensy, OLED, KY-018 and both buttons
  must sit on the same ground rail, or readings make no sense.
* **Follow the printed `S` / `+` / `−` labels on the KY-018.** Do not deduce the
  order from pin position — it differs between manufacturers.
* **No external resistors on the buttons.** `INPUT_PULLUP` provides them; adding
  pull-downs breaks the logic.
* **Do not assume the 2N2222A pinout.** Both EBC and ECB orderings exist
  depending on package and manufacturer. Identify the exact part before wiring
  it — and it is not to be wired yet regardless.
* Measured supply on USB: **≈ 4.8 V** between `VCC` and `GND`. Both the OLED and
  the KY-018 are fine at that level.

## A note on the display count

An earlier version of this project's parts list mentioned **two** OLED displays
as a future upgrade. The build validated here uses **one**. A second display is
not required and is not supported by the firmware.
