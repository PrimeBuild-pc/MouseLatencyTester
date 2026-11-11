# Latency Tester Dashboard v2.0

Compatible with the firmware `latency_tester_oled_ldr_v1_3.ino`.

## Dependencies

```powershell
pip install pyserial pynput matplotlib
```

## Launch

1. Close the Arduino Serial Monitor, the old companion and the old dashboards.
2. Start:

```powershell
python LatencyTester_Dashboard_v2.py
```

## Recommended workflow

1. **DEVICES** → create the mouse profile.
2. **LIVE TEST** → set run name, polling rate, wired/wireless, mouse firmware and notes.
3. Press **Calibrate**.
4. Choose the target (e.g. 50 samples) and press **ENTER TEST MODE**.
5. Press only when the screen is green.
6. When the target is reached press `ESC`.
7. Press **Save session**.
8. Change polling rate/configuration, press **New run** and repeat.
9. **SESSIONS** holds the permanent history.
10. **COMPARE** lets you select several runs and view:
   - Raw samples
   - Box plot
   - ECDF
   - Histogram

## Statistics

The dashboard computes:
- Mean
- Median
- Min / Max
- Standard deviation
- P95 / P99
- IQR
- Jitter = P95 - P5

## Archive

Profiles, sessions and individual samples are saved automatically in an SQLite database:

`Documents/LatencyTester/latency_tester.db`

Each run also keeps:
- Teensy calibration
- polling rate
- wired/wireless mode
- mouse firmware
- notes
- initial/final light level
- timestamp of every sample

You can also export each run to CSV.
