# Serial protocol — Teensy ⇄ dashboard

**Protocol version: 1** — spoken by firmware `v1.0` through `v1.4`.

Every token in this document was read out of the firmware source, not assumed.
The authoritative implementation is
[`firmware/latency_tester_oled_ldr_v1_4/latency_tester_oled_ldr_v1_4.ino`](../firmware/latency_tester_oled_ldr_v1_4/latency_tester_oled_ldr_v1_4.ino)
(whose measurement path is byte-identical to the v1.3 baseline);
the dashboard side is [`latency_tester/protocol.py`](../latency_tester/protocol.py).

> **Tokens are not translatable.** `TRIG`, `LAT`, `ARMED`, `REARM`, `CALIB_OK`
> and friends are the wire format. The user interface is translated; the
> protocol never is.

---

## 1. Transport

| Property | Value |
|---|---|
| Baud rate | `115200` |
| Framing | 8N1, USB CDC (the Teensy ignores the baud rate in practice) |
| Line ending, Teensy → PC | `\r\n` (`Serial.println`) |
| Line ending, PC → Teensy | the firmware reads **one byte** per command; the dashboard appends `\n`, which the firmware's `default:` branch discards |
| Encoding | 7-bit ASCII |
| Exclusivity | one process at a time — the Arduino Serial Monitor must be closed |

USB IDs used for auto-detection: VID `0x16C0`, PID `0x0482`, `0x0483`,
`0x0486`, `0x0487`.

---

## 2. Protocol versioning

The firmware does **not** transmit a numeric protocol version. It prints a
banner instead, and that banner is the compatibility signal:

```
LATENCY_TESTER v1.5 OLED+LDR+BTN+PHOTON
```

The dashboard parses the `vX.Y` from any line starting with `LATENCY_TESTER`
and shows it in the connection bar. `PROTOCOL_VERSION = 2` in `protocol.py` is
the revision of *this document*; it is bumped only if the wire format changes.
Version 1 was v1.0-v1.4; version 2 adds the Probe-to-Photon tokens.

**Backwards compatibility rule:** older firmware simply never sends the newer
tokens. `v1.0` has no `LIGHT:`, `v1.2` has no `ARMED`/`REARM`/`TESTMODE:*`.
Every unknown line decodes to a `log` event and is shown, never dropped. No
firmware change is required to use this dashboard.

### Token availability by firmware version

| Token / command | v1.0 | v1.1 | v1.2 | v1.3 | v1.4 | v1.5 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| `TRIG`, `H`, `X`, `LAT:`, `STATS:`, `CALIB_OK:`, `RESET`, `READY` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `C` `R` `S` `V` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `LIGHT:` / `L` | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| `SKIP:OLED_REFRESH` | — | — | ✅ | ✅ | ✅ | ✅ |
| `ARMED`, `REARM`, `ABORT:NO_CLICK`, `DROP:OUT_OF_RANGE:` | — | — | — | ✅ | ✅ | ✅ |
| `TESTMODE:ON` / `TESTMODE:OFF` / `T` `E` | — | — | — | ✅ | ✅ | ✅ |
| `BTN1:PRESS` / `BTN2:PRESS` | — | — | — | — | ✅ | ✅ |
| `OPT:`, `OPT_CAL:`, `OPT_ERR:`, `OPT_TIMEOUT`, `PHOTON:*` / `O` `N` `D` `W` `K` | — | — | — | — | — | ✅ |

---

## 3. Commands — PC → Teensy

One ASCII character each. Only accepted while the firmware is **not** inside a
measurement or a calibration (`measurementActive == false`).

| Byte | Name | Effect |
|---|---|---|
| `C` | calibrate | Enters `runCalibration()`; blocks until the PC syncs |
| `R` | reset | Clears firmware counters, replies `RESET` |
| `S` | stats | Replies `STATS:…` or `STATS:NO_DATA` |
| `V` | version | Replies with the banner string |
| `T` | test mode on | Freezes the OLED, replies `TESTMODE:ON` then `ARMED` or `REARM` |
| `E` | test mode off | Resumes the OLED, replies `TESTMODE:OFF` |
| `L` | light | Replies `LIGHT:<0..1023>` |

Probe-to-Photon, firmware **v1.5+**. Older firmware ignores all five through its
`default:` branch, so a newer dashboard on older firmware degrades to
Probe-to-PC instead of misbehaving.

| Byte | Name | Effect |
|---|---|---|
| `O` | photon on | Selects the optical path, raises the ADC clock, clears the optical counters. Replies `PHOTON:ON` then `OPT_CAL:…` |
| `N` | photon off | Back to Probe-to-PC, restores the ADC clock. Replies `PHOTON:OFF` |
| `D` | calibrate dark | Samples `A0` as the black baseline, replies `OPT_CAL:…` |
| `W` | calibrate bright | Samples `A0` as the white baseline, replies `OPT_CAL:…` |
| `K` | report calibration | Replies `OPT_CAL:…` without changing anything |

Selecting the mode is always allowed; **measuring** without a usable calibration
is what gets refused. The dashboard sends `T` first and `O` second, so the OLED
is already frozen before the optical path is armed.

Two bytes are **replies inside an exchange**, not standalone commands:

| Byte | Meaning |
|---|---|
| `H` | "the OS click was seen" — stops the measurement clock |
| `X` | "no matching OS click" — aborts the sample |
| `P` | calibration ping echo |
| `R` | during calibration only: "PC is synced and ready" |

> `R` is overloaded. The firmware disambiguates by context: while
> `runCalibration()` is running, the main command `switch` is not reached, so
> the `R` is consumed by `waitForChar()` as the sync byte instead. The demo
> device reproduces this exact behaviour.

---

## 4. Responses — Teensy → PC

### Measurement

| Line | Meaning |
|---|---|
| `TRIG` | Probe contact detected. **t₀ is already recorded.** The firmware is now blocking on `waitForChar()` |
| `LAT:<ms>,min:<ms>,max:<ms>,avg:<ms>,n:<count>` | Valid sample; all values in milliseconds with 3 decimals |
| `DROP:OUT_OF_RANGE:<ms>` | Sample outside `[2 ms, 100 ms]`, discarded by the firmware |
| `ABORT:NO_CLICK` | The PC answered `X` |
| `TIMEOUT:No PC response. Is companion script running?` | No reply within 3 s |
| `REARM` | The measurement cycle is over; the probe will re-arm |
| `ARMED` | The probe returned HIGH for 80 ms and is armed again |
| `SKIP:OLED_REFRESH` | The press landed during an I²C display transfer and was **deliberately** discarded rather than reported as an inflated latency |

### Status

| Line | Meaning |
|---|---|
| `LATENCY_TESTER v1.5 OLED+LDR+BTN+PHOTON` | Boot banner |
| `LATENCY_TESTER v1.5 - Probe + OLED + KY-018 + Buttons + Photon` | Reply to `V` |
| `READY` | Idle |
| `RESET` | Counters cleared |
| `OLED_OK:0x3C` / `OLED_FAIL` | Display init result |
| `LIGHT:<0..1023>` | KY-018 reading, averaged over 16 ADC samples |
| `TESTMODE:ON` / `TESTMODE:OFF` | Display freeze state |
| `STATS:samples:<n>,min:<ms>,max:<ms>,avg:<ms>,last:<ms>,calib:<µs>` | Firmware-side statistics |
| `STATS:NO_DATA` | `S` requested with no samples |

### Buttons (firmware v1.4+)

| Line | Meaning |
|---|---|
| `BTN1:PRESS` | BTN1 (`B0` / digital 0) was pressed — exactly one line per physical press |
| `BTN2:PRESS` | BTN2 (`B1` / digital 1) was pressed |

Parsed by the dashboard with `^BTN(\d+):([A-Z_]+)$`, so a future
`BTN1:RELEASE` or `BTN2:LONG_PRESS` needs no dashboard change. See
[§10](#10-buttons--firmware-v14).

### Probe-to-Photon (firmware v1.5+)

| Line | Meaning |
|---|---|
| `PHOTON:ON` / `PHOTON:OFF` | Optical path selected / released |
| `OPT_CAL:dark:<n>,bright:<n>,threshold:<n>,rising:<0\|1>` | The stored optical calibration. `rising` is `0` when the module's ADC value *falls* as light rises |
| `OPT:<ms>,raw:<adc>,min:<ms>,max:<ms>,avg:<ms>,n:<count>` | Valid optical sample. `raw` is the reading that crossed the threshold |
| `OPT_TIMEOUT` | No transition within 400 ms of t₀ |
| `OPT_ERR:NO_CAL` | A press arrived with no usable calibration |
| `OPT_ERR:NOT_DARK` | The sensor was already past the threshold at t₀ |
| `OPT_ERR:SEPARATION` | `D`/`W` produced baselines less than 60 counts apart |
| `OPT_DROP:OUT_OF_RANGE:<ms>` | Sample outside `[0.5 ms, 350 ms]`, discarded by the firmware |

`OPT:` is a **different token from `LAT:` on purpose.** The two modes do not
measure the same interval, and a parser that treated them alike would let an
optical sample into a Probe-to-PC mean. The optical statistics are kept in
separate firmware variables for the same reason.

**Nothing is transmitted between t₀ and t₁ in this mode**, so `calibOffset` — the
serial round-trip — is **not** subtracted from an optical latency. There is no
round-trip to subtract.

### Calibration

| Line | Meaning |
|---|---|
| `CALIBRATING...` | Calibration started |
| `Please run the companion script.` / `Waiting for PC to sync...` | Human-readable prompts |
| `AWAIT` | Repeated every 250 ms until the PC sends `R` |
| `PC_SYNCED` | Sync received |
| `P` | One ping; the PC must echo `P` |
| `CALIB_OK:<µs>,samples:<n>,min_us:<n>,max_us:<n>,avg_rt:<n>` | Result |
| `CALIB_FAIL:DEFAULT` | No valid round-trips; offset defaults to 500 µs |

---

## 5. Measurement sequence

```
Teensy                                  PC (dashboard)
  |                                          |
  |-- probe falls LOW -> ISR: t0 = micros()  |
  |     (rejected if an OLED transfer is in flight -> SKIP:OLED_REFRESH)
  |                                          |
  |------------------ "TRIG" --------------->|
  |                                          |-- look for an OS left-click that is
  |   (blocked in waitForChar, 3 s timeout)   |   newer than the last consumed one and
  |                                          |   not older than 200 ms; wait up to 1 s
  |<----------------- 'H' -------------------|
  |-- t1 = micros()   <-- CLOCK STOPS HERE   |
  |   raw = t1 - t0                          |
  |   latency = raw - calibOffset            |
  |   accept only if 2 ms <= latency <= 100 ms
  |------- "LAT:6.421,min:...,n:12" -------->|
  |------------------ "REARM" -------------->|
  |-- probe HIGH for 80 ms                   |
  |------------------ "ARMED" -------------->|   (green screen in test mode)
```

**Timing invariants — do not break these:**

1. `t0` is taken inside the ISR, before anything else.
2. Between a valid `TRIG` and `t1` the firmware does **no** OLED or LDR work.
3. A press that overlaps an I²C transfer is discarded, never reported.
4. In test mode the OLED is frozen, so invariant 3 should never trigger.
5. One physical press produces at most one sample: the ISR disarms itself and
   only re-arms after the pin has read HIGH continuously for 80 ms.
6. The dashboard consumes each OS click once, so a duplicate `TRIG` cannot turn
   one press into two samples.

### Click association rules (dashboard side)

A click matches a `TRIG` when **both** hold:

* it is newer than the last click already consumed, and
* it is not older than `TRIG − 200 ms` (`CLICK_GRACE_NS`).

The dashboard waits up to 1 s (`CLICK_TIMEOUT_S`), polling every 0.2 ms, then
answers `X`. The `pynput` callback stores a `perf_counter_ns()` timestamp and
does nothing else — no logging, no allocation — so it cannot add latency to the
click being measured.

---

## 6. Calibration sequence

```
PC: 'C'
Teensy: "CALIBRATING..." / "Please run the companion script." / "Waiting for PC to sync..."
Teensy: "AWAIT" every 250 ms
PC: 'R'
Teensy: "PC_SYNCED"
   repeat 50 times:
       t0 = micros(); print "P"; wait for a byte; t1 = micros()
       if the byte is 'P' and (t1-t0) < 50 ms -> count it
       delayMicroseconds(20000)
Teensy: "CALIB_OK:<offset>,samples:<n>,min_us:…,max_us:…,avg_rt:…"
```

The offset is `avg_round_trip / 2 + 250` µs and is subtracted from every raw
measurement.

> ### ⚠️ Known quirk — do not "fix" without a hardware re-validation
>
> Both the PC sides (the original `latency_companion.py` and every dashboard)
> send the echo as `b"P\n"`, i.e. **two** bytes, while `waitForChar()` reads
> **one**. The leftover `\n` desynchronises the ping loop: roughly half of the
> iterations read the stale newline (rejected, `c != 'P'`) and the other half
> read an already-buffered `P` (counted, but with a near-zero round-trip).
>
> The practical effect is that `calibOffset` collapses towards the `+250` µs
> constant — the archived runs show `calibration_us = 267`, consistent with
> this. It is stable and it is what every existing measurement in the archive
> was taken with.
>
> Fixing it (sending a bare `P`, or draining the buffer in the firmware) would
> change the offset and therefore shift **every** latency value, making new
> runs incomparable with the stored ones. It is documented here rather than
> silently changed. If you do fix it, treat it as a new protocol revision and
> re-baseline the archive.

---

## 7. Test mode

```
PC: 'R'          (optional, when "reset on entering test mode" is on)
PC: 'T'
Teensy: "TESTMODE:ON"
Teensy: "ARMED" or "REARM"
   ... normal measurement cycles, with the OLED frozen ...
PC: 'E'
Teensy: "TESTMODE:OFF"
```

The overlay colour is driven purely by these tokens:

| Firmware state | Overlay |
|---|---|
| `ARMED` | 🟩 green — you may press |
| `REARM`, `TRIG`, `SKIP:OLED_REFRESH` | 🟥 red — wait / release |
| target reached (dashboard-side) | 🟦 blue — done, press ESC |

Once the target sample count is reached the dashboard answers `X` to any
further `TRIG` **immediately**, without waiting for a click, so no extra
samples enter the run.

---

## 8. Light sensor (KY-018)

`LIGHT:<0..1023>` is **telemetry only**. It is polled once a second while idle,
recorded as `light_start` / `light_end` on each run, and displayed. It takes no
part in the latency measurement and is never read between `TRIG` and `t1`.

---

## 10. Buttons — firmware v1.4

Two momentary buttons: **BTN1** on `B0` / digital `0`, **BTN2** on `B1` /
digital `1`, each wired straight to `GND` with no external resistor and read
with `INPUT_PULLUP` (not pressed = HIGH, pressed = LOW).

### Timing guarantees

The buttons were added under the rule that the measurement path must not
change. Concretely:

1. **No interrupt.** They are polled in `loop()`. A button can never preempt
   the probe ISR.
2. **Non-blocking debounce.** A 30 ms `millis()` window, no `delay()`.
3. **No serial output inside any ISR.**
4. **Events are queued, not printed immediately.** `serviceButtons()` sets a
   bit in `pendingButtonPress`; `flushButtonEvents()` is the only thing that
   writes to the port, and it returns early while `measurementActive` or
   `probeFlag` is set. Nothing is ever transmitted between t₀ and t₁.
5. **No display work** is triggered by a button.

The diff from v1.3 to v1.4 touches only: the pin defines, the button state
block, the two button functions, `setup()`, the two version strings, and two
added lines in `loop()`. `probeISR()`, the measurement block, `runCalibration()`
and `serviceProbeRearm()` are untouched.

### Firmware semantics: still none

The buttons **change no firmware state**, in v1.4 and by design. They emit an
event; every decision happens on the PC.

**Acceptance test** (passed on hardware): 10 slow presses of a button produce
exactly 10 events, with no phantom events, no doubles, no repeat while held,
and no effect on a normal mouse measurement.

### Dashboard semantics

| Button | Action |
|---|---|
| `BTN1` | Enter / leave test mode |
| `BTN2` | Clear the live run, only while **not** in test mode |

A press is **refused** — logged, never obeyed — while disconnected, while
calibrating, and for `BTN2` while test mode is running.

The firmware reports; the **dashboard decides**. It stays the authority on
session state, so a button press during a measurement or during test mode is
ignored or refused rather than being allowed to destroy a run. Long presses,
double clicks and chords are out of scope.

Calibration still requires the PC. There is no standalone calibration and none
is planned.

## 11. Not implemented

* **2N2222A transistor and its 220 Ω resistor** — **unused / reserved**, not
  used by the current validated build: not connected, no protocol, no firmware,
  no measurement mode.
* **Probe-to-Photon mode** — specified, **not implemented**. No command byte, no
  result token and no calibration exchange exist for it yet. Today the KY-018
  provides the `LIGHT` telemetry value and nothing else.

  The design is fixed (see
  [README → Planned — Probe-to-Photon mode](../README.md#planned--probe-to-photon-mode)):
  `t₀` is the same probe contact on `D2` as the Probe-to-PC path, `t₁` is the
  first `A0` sample past a calibrated threshold, and latency is `t₁ − t₀`. It
  will be a **separate mode** with its own commands and its own stored metric —
  results are never mixed with Probe-to-PC — and it may not alter `probeISR()`
  or the existing measurement block. The KY-018 is a prototype-grade LDR whose
  response time is itself in the milliseconds, so this mode is a relative
  indicator rather than a precision click-to-photon benchmark.

## 12. Probe-to-Photon sequence

```
Teensy                                  PC (dashboard)
  |                                          |
  |<--------------- "T" then "O" ------------|  OLED frozen, then optical armed
  |---------- "PHOTON:ON", "OPT_CAL:..." --->|
  |                                          |
  |-- probe falls LOW -> ISR: t0 = micros()  |
  |                                          |
  |   NOTHING IS TRANSMITTED HERE.           |
  |   analogRead(A0) in a tight loop.        |
  |                                          |-- Windows reports the click
  |                                          |-- target area repainted WHITE
  |   first sample past the threshold        |
  |   -> t1 = micros()   TIMING STOPS        |
  |                                          |
  |------------- "OPT:<ms>,raw:<adc>,..." -->|
  |------------------ "REARM" -------------->|-- target area repainted BLACK
  |------------------ "ARMED" -------------->|
```

The PC is never asked for anything during the measurement: it flips its own
target because Windows told it about the click, and the Teensy finds out by
looking at the light. That is why no round-trip offset is subtracted here.

**The dashboard's repaint is inside the measured interval**, and so is the 1 ms
poll that triggers it — touching a Tk widget from the input-listener thread is
not safe, so the flip cannot be done in the callback. This is not hidden: a
click-to-photon measurement legitimately includes the application, and this one
is honest about where its floor comes from.

---

## 13. Never in scope: modifying the mouse

The mouse is never opened, nothing is soldered to its PCB, and no transistor is
wired across its microswitch. `t₀` comes from a probe touching **removable**
conductive copper tape on the outside of the left button. Any future mode,
Probe-to-Photon included, keeps that constraint.
