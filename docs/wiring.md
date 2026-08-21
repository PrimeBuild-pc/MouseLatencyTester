# Bring-up and electrical notes

The **pin-by-pin wiring table, the BOM, the wire-colour convention and the
diagrams live in the [main README](../README.md#hardware)** — that is the
single source of truth, so it cannot drift from this file. This document covers
the procedure: what to test, in what order, and what you should actually see.

---

## Bring-up order

Do not skip ahead. Each step assumes the previous one passed.

### 1. Teensy alone

Flash `firmware/latency_tester_photon_v1_5/`, open the Arduino Serial Monitor
at `115200`.

**Expected:**
```
LATENCY_TESTER v1.5 OLED+LDR+BTN+PHOTON
READY
```
The board appears in Device Manager under *Ports (COM & LPT)*.

> [!IMPORTANT]
> **Opening the Serial Monitor does not reset a Teensy** — unlike an Uno. The
> banner is printed once at power-on, so by the time you open the monitor it has
> already gone. An empty monitor proves nothing. Type `V` and press Enter: the
> firmware answers with its version string, and that is how you know both the
> link and the flash are good. The baud rate is irrelevant on a Teensy: the USB
> is native and `115200` is a formality.
>
> **Only one program can hold the COM port.** If the dashboard is connected the
> Serial Monitor stays silent for ever, without any error. Close one before
> opening the other.

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

> [!IMPORTANT]
> **A 4-pin tactile button is two pairs, not four contacts.** The two legs on
> the *same side* are joined together permanently. Use **diagonally opposite**
> corners — one for the Teensy pin, one for GND — and straddle the breadboard's
> centre groove so the pairs land on different rows.
>
> Check with a continuity tester: **open at rest, closed when pressed.** If it
> beeps at rest you have picked two legs of the same pair; the pin then sits
> permanently at GND, the firmware records it as "already pressed" at boot, and
> **no event will ever appear**. That is the single most common cause of
> "the buttons do nothing".
>
> If nothing happens, take the button out of the circuit and bridge the Teensy's
> own `GND` pad to the `B0` pad with a jumper for an instant. If `BTN1:PRESS`
> appears, the pin and the firmware are fine and the fault is in the breadboard
> wiring.

The buttons are polled in `loop()` with a non-blocking 30 ms debounce, never on
an interrupt, and the event is queued and only transmitted while no measurement
is pending — so nothing is ever printed between t₀ and t₁. The firmware itself
changes no state: it reports, and the **dashboard decides**.

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

Once every box is ticked the buttons have real behaviour:

| Button | Action |
|---|---|
| `BTN1` | Enter / leave test mode |
| `BTN2` | Clear the live run, only while **not** in test mode |

The firmware reports the event; the **dashboard decides**. During a measurement
or during test mode, BTN2 is refused rather than allowed to destroy a run. No
long presses, double clicks or combinations.

---

### 10. Probe-to-Photon

**No new wiring.** `t₀` is still the probe on `D2` and the light transition is
read from the KY-018 already on `A0`. What changes is where you point the sensor.

1. *Live test → Measurement mode →* **Probe-to-Photon**. The optical panel
   appears.
2. Aim the KY-018 at the **centre of the screen** — that is where the
   full-screen target appears. Two or three centimetres away, facing it square
   on, taped or clamped so it cannot drift. Shade it from the room lamp if you
   can.
3. Press **Calibra sul bersaglio a schermo intero**. A centred full-screen
   target appears and takes both baselines by itself: black, 400 ms settle,
   sample; white, 400 ms settle, sample. **Do not move the sensor.** It shows
   the result and closes. About a second and a half.
4. If the two baselines are less than **60 counts** apart it stops at
   `CALIBRAZIONE FALLITA`, reports the numbers it measured, and stays on screen
   with a live `LUCE` reading. Move the sensor until that number swings between
   the black and the white phase, then press Enter to retry or Esc to give up.
   **If the reading barely moves, the sensor is not on the target** — that is
   what this readout is for.
5. **Enter test mode.** The calibration is repeated automatically, on the same
   target, so it can never be stale. Then the usual green/red/blue cycle.
6. Press ten times and expect ten `OPT:` lines, in the tens of milliseconds.

> [!TIP]
> **Shade the sensor.** A KY-018 sees the whole room, not just the screen. A
> centimetre of black tape rolled into a tube around it is the single biggest
> improvement you can make to the separation — often an order of magnitude.
> Aim for 200 counts or more between dark and bright; 60 is the bare minimum the
> firmware will accept.

Expected failures, and what they mean:

| Token | Meaning |
|---|---|
| `OPT_ERR:NO_CAL` | Test started without a usable calibration |
| `OPT_ERR:NOT_DARK` | The target was already bright at `t₀` — the sensor is seeing room light or the previous flash |
| `OPT_ERR:SEPARATION` | The two baselines are too close together |
| `OPT_TIMEOUT` | No transition within 400 ms — the sensor is not looking at the target |

The **2N2222A and the 220 Ω resistors are not used at all.** They were on an
early parts list and the finished tester has no role for them, in this mode or
any other. Leave them out.

Read [README → Probe-to-Photon](../README.md#probe-to-photon) before quoting any
number from this mode: the KY-018 is a photoresistor whose own response time is
in the milliseconds, so this is a relative indicator, not a precision
click-to-photon benchmark.

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
* **Never modify the mouse.** Do not open it, do not solder to its PCB, do not
  wire a transistor across its microswitch. The only mouse-side modification in
  this project is **removable** conductive copper tape on the outside of the left
  button.
* **The 2N2222A and the 220 Ω resistors are not used at all.** There is no
  wiring for them anywhere in this project. Leave them out.
* Measured supply on USB: **≈ 4.8 V** between `VCC` and `GND`. Both the OLED and
  the KY-018 are fine at that level.

## A note on the display count

An earlier version of this project's parts list mentioned **two** OLED displays
as a future upgrade. The build validated here uses **one**. A second display is
not required and is not supported by the firmware.
