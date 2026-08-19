# Installation — Windows

Tested on Windows 11 with Python 3.11+.

## 1. Python

Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/)
or the Microsoft Store. Tick **"Add python.exe to PATH"**.

Check it:

```powershell
python --version
```

Tkinter ships with the python.org installer. If `import tkinter` fails, re-run
the installer and enable *tcl/tk and IDLE*.

## 2. Get the project

```powershell
git clone https://github.com/<your-user>/latency-tester.git
cd latency-tester
```

## 3. Virtual environment (recommended)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell refuses to run the activation script:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

## 4. Dependencies

```powershell
pip install -r requirements.txt
```

That installs `pyserial` (COM port), `pynput` (OS click detection) and
`matplotlib` (comparison charts). The app starts without matplotlib — the
Compare tab then shows statistics tables only.

## 5. Teensy driver

Windows 11 recognises the Teensy 2.0 as a USB serial device with no extra
driver. If it does not appear in Device Manager under *Ports (COM & LPT)*,
install the [Teensy driver](https://www.pjrc.com/teensy/td_download.html)
bundled with Teensyduino.

## 6. Run

```powershell
python run_dashboard.py
```

No hardware yet? Open **Settings → Demo mode → Start demo device**, or pick
`DEMO` in the port list.

## 7. Run the tests

```powershell
pip install pytest
python -m pytest tests -q
```

## Where your data lives

| What | Path |
|---|---|
| Archive | `%USERPROFILE%\Documents\LatencyTester\latency_tester.db` |
| Preferences | `%USERPROFILE%\Documents\LatencyTester\settings.json` |

Set the `LATENCY_TESTER_HOME` environment variable to move both elsewhere (for
example onto a USB stick).
