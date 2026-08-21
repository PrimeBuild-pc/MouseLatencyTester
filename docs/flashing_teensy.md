# Flashing the Teensy 2.0

## What you need

* [Arduino IDE](https://www.arduino.cc/en/software) (1.8.x or 2.x)
* [Teensyduino](https://www.pjrc.com/teensy/td_download.html), matching your
  Arduino IDE version
* Libraries, installed through *Tools → Manage Libraries*:
  * `Adafruit GFX Library`
  * `Adafruit SH110X`

## Steps

1. Open `firmware/latency_tester_photon_v1_5/latency_tester_photon_v1_5.ino`.
2. *Tools → Board →* **Teensy 2.0**.
3. *Tools → USB Type →* **Serial** (or *Serial + Keyboard + Mouse + Joystick* —
   both work; only the serial endpoint is used).
4. *Tools → CPU Speed →* 16 MHz.
5. Click **Upload**. Press the physical button on the Teensy if the loader asks
   for it.

## Verifying the flash

Open the Arduino Serial Monitor at `115200` baud. You should see:

```
LATENCY_TESTER v1.5 OLED+LDR+BTN+PHOTON
READY
OLED_OK:0x3C
```

> [!IMPORTANT]
> **A Teensy does not reset when the Serial Monitor opens.** The banner is
> printed once at power-on, so an empty monitor is normal and proves nothing.
> Type `V` and press Enter — the reply is what tells you the flash worked. If
> nothing comes back at all, something else is holding the COM port (usually the
> dashboard, or another Serial Monitor).

Press BTN1 and BTN2 once each; you should see exactly one line per press:

```
BTN1:PRESS
BTN2:PRESS
```

If you get `OLED_FAIL`, the display was not found at `0x3C` — check `D0`/`D1`
and the power rails. The tester still measures latency without the OLED.

Type `V` and press Enter; the firmware replies with the version string. Type
`L` and it replies with `LIGHT:<value>`.

**Close the Serial Monitor before starting the dashboard.** Only one process
can own the COM port.

## Firmware versions in this repository

| Sketch | Notes |
|---|---|
| `latency_tester/` | v1.0 — probe only, no display |
| `latency_tester_oled_ldr/` | v1.1 — adds OLED + KY-018 |
| `latency_tester_oled_ldr_v1_2/` | v1.2 — adds `SKIP:OLED_REFRESH` |
| `latency_tester_oled_ldr_v1_3/` | v1.3 — debounce/re-arm, no duplicate triggers, OLED frozen during test mode. **Measurement baseline** |
| `latency_tester_oled_ldr_v1_4/` | v1.4 — v1.3 plus the BTN1/BTN2 events. The measurement path is byte-identical to v1.3 |
| **`latency_tester_photon_v1_5/`** | **v1.5 — current. v1.4 plus Probe-to-Photon. The Probe-to-PC path is byte-identical to v1.4** |
| `displayTester/` | standalone OLED check |

Older sketches are kept for reference and still work with this dashboard; see
the compatibility table in [serial_protocol.md](serial_protocol.md).
