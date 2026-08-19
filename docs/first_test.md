# Your first measurement

## Before you start

* The probe is clamped so it touches the copper tape **at the same instant**
  the switch actuates. Too early or too late and every sample is offset.
* The Arduino Serial Monitor is closed.
* No older `latency_companion.py` or dashboard is running.

## Steps

1. **Start the dashboard.**

   ```powershell
   python run_dashboard.py
   ```

   The Teensy is auto-detected; the status turns green with the COM port and
   the firmware version.

2. **Create a device profile.** *Devices* tab → fill in name, manufacturer,
   model → *Save / update*. Serial number, switch type and usual firmware are
   optional.

3. **Configure the run.** *Live test* tab: pick the device, set the polling
   rate, connection type, DPI and any notes. Leave the run name empty and it is
   generated for you (`1000 Hz - Wired - 2026-08-19 10-42`).

4. **Calibrate.** Press *Calibrate* and wait for `CALIB_OK` in the event log.
   Do this once per session — it measures the serial round-trip and subtracts
   it from every sample.

5. **Set a target** (50 samples is a good start) and press
   **ENTER TEST MODE**. The screen goes full-screen and the OLED freezes.

6. **Click only when the screen is green.**
   * 🟩 green — armed, press now
   * 🟥 red — wait, release the button
   * 🟦 blue — target reached

   Press once, release fully, wait for green, press again.

7. **Press ESC** when the screen is blue.

8. **Save session.** The run, its metadata and every raw sample go into the
   archive.

9. **Next configuration.** Change the polling rate, press *New run*, and repeat
   from step 5. You never need to restart the program.

## A typical benchmark session

```
Razer Viper → 1000 Hz → 50 samples → Save session → New run
Razer Viper → 2000 Hz → 50 samples → Save session → New run
Razer Viper → 4000 Hz → 50 samples → Save session → New run
Razer Viper → 8000 Hz → 50 samples → Save session
```

Then go to *Compare*, select all four, pick the 1000 Hz run as the baseline and
read the Δ median / Δ P95 table.

## Reading the numbers

| Metric | What it tells you |
|---|---|
| Median | The typical latency. Use this, not the mean, for comparisons |
| P95 / P99 | The bad cases — where a mouse actually feels inconsistent |
| Jitter (P95−P5) | Spread. Lower is more consistent |
| MAD | Spread that ignores a few wild samples |
| Std dev | Spread, but one 40 ms outlier wrecks it |

Circled points on the live chart are outliers by the Tukey rule. They are
**marked, never removed** — the raw sample stays in the database and in every
statistic. Deciding what they mean is your job, not the software's.

## What is actually being measured

Contact closure on the probe (t₀) → the OS reporting the click to a Python
callback (t₁), minus the calibrated serial round-trip. That covers the mouse's
switch debounce, its internal processing, the wireless or USB link, the polling
interval and the OS input stack. It does **not** cover display or render
latency.
