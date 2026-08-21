# Troubleshooting

## Connection

**"Cannot open the Teensy" / access denied**
Something else owns the COM port. Close the Arduino Serial Monitor, any older
`latency_companion.py` or dashboard window, and any terminal with the port
open. Then press *Refresh* and *Connect*.

The automatic connection at startup no longer raises this as a dialog: it
retries quietly four times before giving up, because Windows can still be
holding the port for a moment after a previous run. If a **manual** *Connect*
also fails, the port really is taken by another program.

**The Arduino Serial Monitor shows nothing at all**
Two different things, and both look identical:
- **The dashboard is connected.** One program at a time owns a COM port. The
  monitor then stays silent for ever without an error. Close one or the other.
- **You missed the banner.** A Teensy does not reset when the monitor opens, so
  the boot banner is long gone. Type `V` and press Enter; the version reply is
  the proof that the link works. The baud rate is irrelevant on a Teensy.

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

## Buttons

**Pressing BTN1 or BTN2 does nothing**
Almost always the wiring of the 4-pin button. Its legs are joined in **two
pairs**, one pair per side; you must use two **diagonally opposite** corners. If
you picked two legs of the same pair the pin is permanently at GND, the firmware
records it as "already pressed" at boot, and no event ever appears.

Test it with a continuity tester: **open at rest, closed when pressed.** If it
beeps at rest, rotate the button 90°.

If the button tests good and still nothing happens, take it out of the circuit
and bridge the Teensy's own `GND` pad to the `B0` pad with a jumper for an
instant. `BTN1:PRESS` appearing means the pin and firmware are fine and the
fault is in the breadboard wiring; nothing appearing means you are not touching
the pad you think you are.

**BTN2 asks before clearing the run**
By design, and it can be switched off: *Settings → Ask before BTN2 clears the
live run*. It is on by default because BTN2 sits on the same desk as the mouse
being measured.

**BTN2 does nothing during a test**
Also by design. The firmware reports the press; the dashboard refuses it so a
stray knock cannot destroy a running test. The refusal is written to the log.

## Probe-to-Photon

**The test will not start / "dark and bright are too close"**
The two baselines are less than 60 ADC counts apart, which would put the
threshold inside the sensor's own noise. Shade the KY-018 from the room light,
raise the screen brightness, or move the sensor closer to the target square.

**`OPT_ERR:NOT_DARK`**
The sensor was already above the threshold when the probe fired. Either it is
picking up room light rather than the target, or the target had not gone back to
black yet — give the previous cycle time to re-arm before pressing again.

**`OPT_TIMEOUT`**
No light change within 400 ms of the probe contact. The sensor is not pointed at
the target area, or the click never reached Windows at all — check the Live tab
log for the click.

**The optical numbers are much higher than the Probe-to-PC ones**
Expected. Probe-to-Photon includes the application, the compositor, the GPU
queue, the panel and the photoresistor's own response. Tens of milliseconds is
normal. See [README → Probe-to-Photon](../README.md#probe-to-photon) for why the
absolute figure is not a benchmark.

**The optical numbers move between sessions**
A photoresistor drifts with ambient light and temperature. Re-run the black and
white calibration whenever the room light, the screen brightness or the sensor
position changes — and compare only runs taken under the same conditions.

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
