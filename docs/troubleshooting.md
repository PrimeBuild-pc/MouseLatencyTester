# Troubleshooting

## Connection

**"Cannot open the Teensy" / access denied**
Something else owns the COM port. Close the Arduino Serial Monitor, any older
`latency_companion.py` or dashboard window, and any terminal with the port
open. Then press *Refresh* and *Connect*.

**The Teensy does not appear in the port list**
Check Device Manager → *Ports (COM & LPT)*. If it is missing, try another USB
cable (many are charge-only), another port, and install the Teensyduino driver.

**The COM number changed and the app stopped**
It reconnects on its own within a few seconds if *Connect automatically on
start* is enabled. The samples of the current run are kept across a
disconnection — nothing is lost.

**Firmware shows as "unknown"**
The banner was missed at connect time. Press *Request stats*, or disconnect and
reconnect. It is cosmetic.

## Measurement

**No `TRIG` when I click**
The probe is not making contact. Check the clamp, the copper tape, and that the
tape is connected to Teensy `GND` and the probe to `D2`. The built-in LED on
pin 11 lights while a measurement is pending.

**"TRIG without a matching new OS click" in the log**
The probe closed but Windows reported no left-click. Usually the probe touched
before the switch actuated — nudge the probe so contact and click coincide.
It can also mean `pynput` is blocked; see below.

**Nothing is detected but the probe clearly works**
`pynput` needs to see global mouse events. Some anti-cheat and remote-desktop
software blocks that. Run the dashboard as a normal user on the local desktop.
If `pip install pynput` was skipped, clicks are never detected at all.

**`SKIP:OLED_REFRESH` keeps appearing**
The click landed while the OLED was being redrawn, so the firmware discarded it
rather than reporting an inflated number. This should not happen in test mode,
where the display is frozen. Outside test mode it is normal and harmless.

**`DROP:OUT_OF_RANGE`**
The sample fell outside the firmware's 2–100 ms window. A near-zero value
usually means the probe bounced; a very large one means the click was late or
the round-trip stalled.

**Latency values look implausibly low or high across the board**
Re-run *Calibrate*. Also read the calibration quirk section in
[serial_protocol.md](serial_protocol.md#6-calibration-sequence) — the offset is
known to sit close to 250 µs by construction, and that is deliberate and
unchanged from the verified setup.

**Duplicate samples from one press**
Should be impossible with firmware v1.3 (80 ms re-arm) plus the dashboard's
one-click-one-sample rule. If it happens, you are probably running older
firmware — check the version in the connection bar.

## Interface

**Text is unreadable after switching theme**
Switch again, or set *System*. If it persists, delete
`Documents\LatencyTester\settings.json` and restart; the archive is a separate
file and is untouched.

**The Compare tab shows tables but no charts**
Matplotlib is missing: `pip install matplotlib`.

**Controls are cut off on a small screen**
The window has a 1024×680 minimum. Below that, maximise the window; the panels
are all resizable and the tables scroll.

## Data

**Where is my database?**
`%USERPROFILE%\Documents\LatencyTester\latency_tester.db`. It is never
recreated or wiped by the app. Use *Settings → Back up the archive* before
experimenting.

**Can I still open the old dashboard?**
Yes. `LatencyTester_Dashboard_v2.py` is kept in `legacy/` and reads the same
database. It ignores the columns added in schema v1.

**A run is flagged \[DEMO\]**
It was recorded with the simulator, not with hardware. Demo runs are stored
with `is_demo = 1`, shown in a different colour and can be hidden with the
*Show demo runs* checkbox.
