"""
Latency Tester - PC Companion
Listens for mouse clicks and communicates with Teensy 2.0 via serial.

Usage:
    pip install pyserial pynput
    python latency_companion.py

Steps:
    1. Connect Teensy, note the COM port (e.g. COM3)
    2. Run this script
    3. Type 'cal' to calibrate serial round-trip timing
    4. Press mouse left button — probe touches tape, Teensy measures
"""

import sys
import time
import threading
import serial
import serial.tools.list_ports
from pynput import mouse

# ── Configuration ──
BAUD_RATE = 115200
TEENSY_VID = 0x16C0
# Teensy 2.0 PIDs by USB Type:
#   0482 = Keyboard+Mouse+Joystick, 0483 = Serial only
#   0486 = ?, 0487 = Serial+Keyboard+Mouse+Joystick
TEENSY_PIDS = {0x0482, 0x0483, 0x0486, 0x0487}


def find_teensy_port():
    """Auto-detect Teensy serial port by VID/PID."""
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if port.vid == TEENSY_VID and port.pid in TEENSY_PIDS:
            return port.device
    # Fallback: look for "Teensy" in description
    for port in ports:
        if "teensy" in port.description.lower() or "teensy" in str(port.hwid).lower():
            return port.device
    # Last resort: list and ask
    if ports:
        print("Available serial ports:")
        for i, p in enumerate(ports):
            vid = f"{p.vid:04X}" if p.vid else "????"
            pid = f"{p.pid:04X}" if p.pid else "????"
            print(f"  [{i}] {p.device} - {p.description} (VID:{vid} PID:{pid})")
        try:
            idx = int(input("Select port number: "))
            return ports[idx].device
        except (ValueError, IndexError):
            pass
    return input("Enter COM port manually (e.g. COM3): ").strip()


class LatencyCompanion:
    def __init__(self, port):
        self.ser = serial.Serial(port, BAUD_RATE, timeout=0.1)
        self.running = True
        self.calibrating = threading.Event()  # True = calibration in progress
        self.last_click_time = 0
        self.click_lock = threading.Lock()

        # Start mouse listener
        self.listener = mouse.Listener(on_click=self._on_click)
        self.listener.start()

        # Give Teensy time to reset after serial open
        time.sleep(1.5)

    def _on_click(self, x, y, button, pressed):
        """Called by pynput on mouse events."""
        if button == mouse.Button.left and pressed:
            with self.click_lock:
                self.last_click_time = time.perf_counter_ns()

    def _wait_for_click(self, timeout_s=2.0):
        """Wait for a left click, also accepting one just before TRIG."""
        start = time.perf_counter_ns()
        timeout_ns = int(timeout_s * 1e9)
        grace_ns = int(0.2 * 1e9)  # accept clicks up to 200 ms before TRIG

        while (time.perf_counter_ns() - start) < timeout_ns:
            with self.click_lock:
                current = self.last_click_time

            if current >= start - grace_ns:
                return True

            time.sleep(0.0001)

        return False

    def calibration_mode(self):
        """Run serial round-trip calibration. Takes exclusive control of serial."""
        self.calibrating.set()  # Pause measurement_loop
        time.sleep(0.6)  # Let measurement_loop yield

        print("\n[CALIBRATION] Syncing with Teensy...")

        # Flush any stale data
        self.ser.reset_input_buffer()

        # Send 'R' to signal we're ready for calibration
        self.ser.write(b'R\n')
        self.ser.flush()

        # Wait for sync confirmation
        deadline = time.time() + 5
        while time.time() < deadline:
            line = self.ser.readline().decode(errors='ignore').strip()
            if line:
                print(f"  [sync] {line}")
            if "PC_SYNCED" in line:
                print("  Synced. Running calibration pings...")
                break

        # Echo mode: respond to 'P' with 'P'
        count = 0
        deadline = time.time() + 15
        while time.time() < deadline and count < 100:
            line = self.ser.readline().decode(errors='ignore').strip()
            if line == 'P':
                self.ser.write(b'P\n')
                self.ser.flush()
                count += 1
            elif "CALIB_OK" in line or "CALIB_FAIL" in line:
                print(f"  Result: {line}")
                self.calibrating.clear()
                return line

        print(f"  Calibration complete. {count} pings echoed.")
        self.calibrating.clear()

    def measurement_loop(self):
        """Main measurement loop: detect TRIG, wait for click, respond."""
        print("\n[MEASUREMENT] Ready. Press mouse left button to measure.")
        print("  Commands: 'cal' = calibrate, 'reset' = clear stats, 'stats' = show, 'quit' = exit")
        print()

        while self.running:
            # Yield serial reads during calibration
            if self.calibrating.is_set():
                time.sleep(0.05)
                continue

            line = self.ser.readline().decode(errors='ignore').strip()

            if not line:
                continue

            # Display all output; TRIG marked so we can see probe contact
            if line.startswith("TRIG"):
                print(f"  [PROBE] {line}")
            else:
                print(f"  [Teensy] {line}")

            # Probe contact detected — wait for actual mouse click
            if line == "TRIG":
                # The probe touched the tape. The physical mouse click should
                # arrive at the OS within the next few milliseconds.
                if self._wait_for_click(timeout_s=1.0):
                    self.ser.write(b'H\n')
                    self.ser.flush()
                else:
                    print("  [WARN] click non rilevato entro 1s — invio H comunque")
                    self.ser.write(b'H\n')
                    self.ser.flush()

    def send_command(self, cmd):
        """Send a single-char command to Teensy."""
        self.ser.write((cmd + '\n').encode())
        self.ser.flush()

    def command_loop(self):
        """Thread: handle user commands from stdin."""
        print("Type 'help' for commands.\n")
        while self.running:
            try:
                cmd = input().strip().lower()
                if cmd == 'quit' or cmd == 'q':
                    self.running = False
                elif cmd == 'cal':
                    self.send_command('C')
                    time.sleep(0.3)
                    self.calibration_mode()
                elif cmd == 'reset':
                    self.send_command('R')
                elif cmd == 'stats':
                    self.send_command('S')
                elif cmd == 'help':
                    print("Commands: cal, reset, stats, quit")
            except (EOFError, KeyboardInterrupt):
                self.running = False
                break

    def run(self):
        """Start measurement and command threads."""
        # Start measurement thread
        measure_thread = threading.Thread(target=self.measurement_loop, daemon=True)
        measure_thread.start()

        # Commands on main thread
        self.command_loop()

        # Cleanup
        self.listener.stop()
        self.ser.close()
        print("\nDone.")


def main():
    print("=" * 50)
    print("  Latency Tester - PC Companion v1.0")
    print("=" * 50)

    port = find_teensy_port()
    print(f"\nConnecting to {port}...")

    try:
        companion = LatencyCompanion(port)
        companion.run()
    except serial.SerialException as e:
        print(f"ERROR: Could not open serial port: {e}")
        print("Make sure Teensy is connected and not used by another program.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":
    main()
