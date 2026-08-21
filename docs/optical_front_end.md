# Optical front-end v1 — photodiode variant

> [!WARNING]
> **In progress. Not built, not verified, not supported.** The tester that works
> and that every release ships is the **KY-018** build described in
> [wiring.md](wiring.md); it is finished and its numbers are real. This page is
> the design for a replacement front-end that has not been assembled yet.
> Nothing in the firmware or the dashboard talks to it. Do not follow this page
> expecting a working device at the end.

## Why replace the KY-018

A KY-018 is a photoresistor. Its own response time is in the **milliseconds** —
the same order as the quantity being measured — and it drifts with ambient light
and temperature. On a 360 Hz OLED, where the panel settles in microseconds and a
frame is 2.8 ms, the sensor is the largest unknown left in the chain: larger than
a frame at any refresh rate worth testing.

The design below replaces it with a **BPV10 PIN photodiode**, a transimpedance
amplifier and a comparator, so that:

- the sensor's own contribution drops from milliseconds to microseconds;
- `t₁` stops being a software threshold comparison on a sampled ADC value and
  becomes a **hardware interrupt**, timestamped in an ISR exactly like `t₀`.

That second point is the real change. Today the firmware polls `analogRead(A0)`
in a loop after `t₀`; each reading costs ~13 µs and the crossing is only detected
on a sample boundary. A comparator edge is timestamped the same way the probe is.

## What stays exactly as it is

- **Probe-to-PC is untouched.** Same ISR, same `t₀`, same `TRIG`/`H` handshake,
  same serial calibration, same filters. This front-end changes nothing about it.
- **`t₀` is untouched in both modes**: the physical probe on `D2`, in the same
  interrupt it has used since v1.0.
- **The mouse is untouched**: no opening it, no soldering to its PCB, no
  transistor across its microswitch. Removable copper tape on the outside of the
  left button remains the only mouse-side modification.
- **The 2N2222A and the old 220 Ω resistors stay unused.** This front-end does
  not use them either.

## Pins

| Signal | Teensy pad | Arduino pin | Change |
|---|:--:|:--:|---|
| BTN1 | `B0` | 0 | unchanged |
| BTN2 | `B1` | 1 | unchanged |
| OLED SCL | `D0` | 5 | unchanged |
| OLED SDA | `D1` | 6 | unchanged |
| Probe | `D2` | 7 | unchanged — still `t₀` |
| Analog optical | `F0` | A0 | **repurposed**: TIA output, calibration and telemetry only |
| **Optical trigger** | `D3` | **8** | **new** — comparator output, interrupt-capable, this is `t₁` |
| VCC / GND | — | — | unchanged, ~5 V |

The KY-018 is removed completely.

## Circuit

### Bias for the TIA non-inverting input

```
+5V ──┬── 10k ──┬── 10k ── GND
      │         │
      │         ├── 100nF ── GND
      │         ├── 10uF  ── GND
      │         │
      │         └── OPA380 pin 3 (+IN)
```

Half the supply, decoupled twice: the 100 nF for high frequency, the 10 µF to
hold the node still while the photodiode current steps.

### Photodiode and transimpedance amplifier

```
BPV10 anode   ── GND
BPV10 cathode ── OPA380 pin 2 (-IN)

OPA380 pin 6 (OUT) ── 10k  ── OPA380 pin 2   (transimpedance gain)
OPA380 pin 6 (OUT) ── 15pF ── OPA380 pin 2   (NP0/C0G, stability)
```

The photodiode runs in **photoconductive** mode into a virtual earth, which is
what keeps it fast: the junction capacitance never has to charge a load.

| OPA380 pin | Connection |
|:--:|---|
| 1 | NC |
| 2 | −IN ← BPV10 cathode |
| 3 | +IN ← VBIAS |
| 4 | V− → GND |
| 5 | NC |
| 6 | OUT |
| 7 | V+ → +5 V |
| 8 | NC |

The 15 pF is **NP0/C0G specifically**. An X7R of the same value drifts with
voltage and temperature and would turn a stable feedback pole into a variable
one.

### Comparator

```
OPA380 pin 6 (OUT) ── TLV3501 pin 2 (-IN)
10k multiturn trimmer across +5V and GND, wiper ── TLV3501 pin 3 (+IN)
TLV3501 pin 6 (OUT) ── 1M ── TLV3501 pin 3 (+IN)      (hysteresis)
TLV3501 pin 6 (OUT) ── 100R ── Teensy D3 / digital 8
```

| TLV3501 pin | Connection |
|:--:|---|
| 1 | NC |
| 2 | −IN ← OPA380 OUT |
| 3 | +IN ← threshold node |
| 4 | V− → GND |
| 5 | NC |
| 6 | OUT |
| 7 | V+ → +5 V |
| 8 | SHDN → GND (never shut down) |

The 1 MΩ from output back to the non-inverting input is what stops the comparator
chattering on the way through the threshold. The 100 Ω in series with the output
is there for the same reason it always is: it damps the edge into the Teensy pin
instead of ringing it.

### Decoupling

- 100 nF directly at the OPA380 `V+`/`GND` pins
- 100 nF directly at the TLV3501 `V+`/`GND` pins
- 10 µF ceramic across +5 V/GND near the front-end
- 100 nF **and** 10 µF on the VBIAS node

"Directly at the pins" is not a figure of speech here. A TLV3501 is fast enough
that a centimetre of extra lead on its decoupling changes how it behaves.

## Planned firmware architecture

```
Probe-to-PC          unchanged in every respect.

Probe-to-Photon      t0 = probe ISR on D2            (unchanged)
                     t1 = comparator ISR on D3/8,    (new)
                          FALLING when light crosses the threshold
                     A0 = calibration, debug and telemetry only.
                          Never read between t0 and t1.
```

Rules the implementation has to keep:

- **No I²C, no OLED, no `analogRead()` between `t₀` and `t₁`.** The comparator
  interrupt is the timestamp source and nothing else may run in that window.
- **No serial traffic between `t₀` and `t₁`**, as today.
- `calibOffset` stays out of the optical result: there is still no round-trip.
- The existing `OPT:` wire format can carry the result unchanged. `raw` becomes
  the last ADC reading taken *outside* the timing window, for debugging only.

Calibration changes shape: instead of deriving an ADC threshold in software, the
**trimmer** sets the threshold in hardware. The dashboard's black/white sequence
becomes an aid for setting that trimmer — show black, show white, read `A0`,
tell the operator where the midpoint is — rather than the thing that computes the
threshold.

## Bill of materials, one unit

| Qty | Part |
|:--:|---|
| 1 | BPV10 PIN photodiode |
| 1 | OPA380AID / OPA380AIDR |
| 1 | TLV3501AID / TLV3501AIDR |
| 2 | SOIC-8 to DIP adapter boards |
| 3 | 10 kΩ 1% resistors |
| 1 | 1 MΩ 1% resistor |
| 1 | 100 Ω 1% resistor |
| 1 | 15 pF NP0/C0G capacitor |
| 3 | 100 nF ceramic capacitors |
| 2 | 10 µF ceramic capacitors |
| 1 | 10 kΩ 3296W multiturn trimmer |
| 1 | small perfboard |
| — | 2.54 mm male headers as required |

Both ICs are SOIC-8, hence the adapters. Neither is hand-solderable onto
perfboard without one.

## Status

Design captured, nothing built. When it is assembled and verified the firmware
gains a sketch that uses `D3`/digital 8 as `OPTICAL_TRIGGER_PIN`, and this page
loses its warning banner. Until then the KY-018 build is the tester, and it
works.
