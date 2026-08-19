"""
Latency Tester Dashboard v1.1
Compatible with Teensy 2.0 firmware:
  latency_tester_oled_ldr_v1_3.ino

Dependencies:
    pip install pyserial pynput

Run:
    python latency_dashboard.py

Important:
    Close Arduino Serial Monitor and the old latency_companion.py before connecting.
"""

import csv
import queue
import re
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import serial
import serial.tools.list_ports
from pynput import mouse


BAUD_RATE = 115200
TEENSY_VID = 0x16C0
TEENSY_PIDS = {0x0482, 0x0483, 0x0486, 0x0487}

CLICK_GRACE_NS = int(0.200 * 1e9)   # accept OS click up to 200 ms before TRIG
CLICK_TIMEOUT_S = 1.0


LAT_RE = re.compile(
    r"^LAT:(?P<last>[\d.]+),min:(?P<min>[\d.]+),max:(?P<max>[\d.]+),"
    r"avg:(?P<avg>[\d.]+),n:(?P<n>\d+)$"
)

STATS_RE = re.compile(
    r"^STATS:samples:(?P<n>\d+),min:(?P<min>[\d.]+),max:(?P<max>[\d.]+),"
    r"avg:(?P<avg>[\d.]+),last:(?P<last>[\d.]+),calib:(?P<calib>\d+)$"
)

CAL_RE = re.compile(
    r"^CALIB_OK:(?P<calib>\d+),samples:(?P<samples>\d+),"
    r"min_us:(?P<min_us>\d+),max_us:(?P<max_us>\d+),avg_rt:(?P<avg_rt>\d+)$"
)


class LatencyDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Latency Tester Dashboard v1.1")
        self.root.geometry("1120x760")
        self.root.minsize(940, 650)

        self.ser = None
        self.serial_thread = None
        self.running = True
        self.connected = False
        self.calibrating = False
        self.test_mode = False

        self.write_lock = threading.Lock()
        self.click_lock = threading.Lock()
        self.last_click_time = 0
        self.last_consumed_click_time = 0

        self.events = queue.Queue()
        self.samples = []
        self.overlay = None
        self.overlay_last_label = None
        self.overlay_avg_label = None
        self.overlay_n_label = None
        self.overlay_state_label = None
        self.overlay_frame = None
        self.overlay_hint_label = None
        self.test_session_count = 0
        self.test_complete = False

        self.connection_var = tk.StringVar(value="DISCONNESSO")
        self.state_var = tk.StringVar(value="READY")
        self.port_var = tk.StringVar()
        self.last_var = tk.StringVar(value="—")
        self.avg_var = tk.StringVar(value="—")
        self.min_var = tk.StringVar(value="—")
        self.max_var = tk.StringVar(value="—")
        self.n_var = tk.StringVar(value="0")
        self.cal_var = tk.StringVar(value="0 µs")
        self.light_var = tk.StringVar(value="—")
        self.skipped_var = tk.StringVar(value="0")
        self.log_enabled = tk.BooleanVar(value=True)
        self.target_samples_var = tk.IntVar(value=10)
        self.auto_reset_var = tk.BooleanVar(value=True)

        self._build_ui()

        self.mouse_listener = mouse.Listener(on_click=self._on_click)
        self.mouse_listener.start()

        self.refresh_ports(auto_connect=True)
        self.root.after(50, self._process_events)
        self.root.after(1000, self._idle_light_poll)

        self.root.protocol("WM_DELETE_WINDOW", self.close)

    # ---------------- UI ----------------

    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)

        # Connection bar
        conn = ttk.LabelFrame(outer, text=" Connessione ", padding=10)
        conn.pack(fill="x")

        ttk.Label(conn, text="Porta:").pack(side="left")
        self.port_combo = ttk.Combobox(conn, textvariable=self.port_var, width=34, state="readonly")
        self.port_combo.pack(side="left", padx=(8, 8))

        ttk.Button(conn, text="Aggiorna", command=lambda: self.refresh_ports(False)).pack(side="left", padx=4)
        self.connect_btn = ttk.Button(conn, text="Connetti", command=self.toggle_connection)
        self.connect_btn.pack(side="left", padx=4)

        ttk.Label(conn, text="Stato:").pack(side="left", padx=(24, 6))
        self.conn_status = ttk.Label(conn, textvariable=self.connection_var)
        self.conn_status.pack(side="left")

        # Main area
        content = ttk.Frame(outer)
        content.pack(fill="both", expand=True, pady=(12, 0))
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        left = ttk.Frame(content)
        right = ttk.Frame(content)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # Metrics
        metrics = ttk.LabelFrame(left, text=" Misure ", padding=12)
        metrics.pack(fill="x")

        top_metric = ttk.Frame(metrics)
        top_metric.pack(fill="x")
        ttk.Label(top_metric, text="ULTIMA", font=("Segoe UI", 11, "bold")).pack(anchor="center")
        ttk.Label(top_metric, textvariable=self.last_var, font=("Segoe UI", 34, "bold")).pack(anchor="center")
        ttk.Label(top_metric, text="ms").pack(anchor="center")

        grid = ttk.Frame(metrics)
        grid.pack(fill="x", pady=(12, 4))
        for c in range(4):
            grid.columnconfigure(c, weight=1)

        self._metric_cell(grid, 0, "MEDIA", self.avg_var)
        self._metric_cell(grid, 1, "MIN", self.min_var)
        self._metric_cell(grid, 2, "MAX", self.max_var)
        self._metric_cell(grid, 3, "CAMPIONI", self.n_var)

        # Sparkline
        chart_box = ttk.LabelFrame(left, text=" Ultimi campioni ", padding=8)
        chart_box.pack(fill="both", expand=True, pady=(12, 0))
        self.chart = tk.Canvas(chart_box, height=220, highlightthickness=0)
        self.chart.pack(fill="both", expand=True)
        self.chart.bind("<Configure>", lambda _e: self._draw_chart())

        # Controls / status
        status = ttk.LabelFrame(right, text=" Controlli ", padding=12)
        status.pack(fill="x")

        info = ttk.Frame(status)
        info.pack(fill="x", pady=(0, 10))
        info.columnconfigure(1, weight=1)

        self._info_row(info, 0, "STATE", self.state_var)
        self._info_row(info, 1, "CAL", self.cal_var)
        self._info_row(info, 2, "LIGHT", self.light_var)
        self._info_row(info, 3, "SKIP OLED", self.skipped_var)

        buttons = ttk.Frame(status)
        buttons.pack(fill="x")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        self.cal_btn = ttk.Button(buttons, text="Calibra", command=self.calibrate)
        self.cal_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=4)

        self.reset_btn = ttk.Button(buttons, text="Reset", command=self.reset_stats)
        self.reset_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=4)

        ttk.Button(buttons, text="Richiedi stats", command=lambda: self.send_command("S")).grid(
            row=1, column=0, sticky="ew", padx=(0, 4), pady=4
        )
        ttk.Button(buttons, text="Leggi luce", command=lambda: self.send_command("L")).grid(
            row=1, column=1, sticky="ew", padx=(4, 0), pady=4
        )

        test_opts = ttk.Frame(status)
        test_opts.pack(fill="x", pady=(10, 0))
        ttk.Label(test_opts, text="Target campioni:").pack(side="left")
        ttk.Spinbox(test_opts, from_=1, to=500, textvariable=self.target_samples_var, width=6).pack(side="left", padx=(6, 16))
        ttk.Checkbutton(test_opts, text="Reset all'ingresso", variable=self.auto_reset_var).pack(side="left")

        self.test_btn = ttk.Button(status, text="ENTRA IN TEST MODE", command=self.enter_test_mode)
        self.test_btn.pack(fill="x", pady=(10, 6), ipady=10)

        ttk.Label(
            status,
            text="In Test Mode l'OLED viene congelato: niente campioni persi per refresh.\n"
                 "VERDE = puoi premere, ROSSO = attendi/rilascia.\n"
                 "Premi ESC per uscire.",
            justify="center",
        ).pack(fill="x", pady=(0, 8))

        export_box = ttk.LabelFrame(right, text=" Sessione ", padding=10)
        export_box.pack(fill="x", pady=(12, 0))
        ttk.Button(export_box, text="Esporta CSV", command=self.export_csv).pack(fill="x")

        # Log
        log_box = ttk.LabelFrame(right, text=" Eventi ", padding=8)
        log_box.pack(fill="both", expand=True, pady=(12, 0))

        self.log = tk.Text(log_box, height=12, wrap="word", state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)

        self._set_controls_state()

    def _metric_cell(self, parent, column, title, variable):
        frame = ttk.Frame(parent, padding=6)
        frame.grid(row=0, column=column, sticky="nsew")
        ttk.Label(frame, text=title, font=("Segoe UI", 9, "bold")).pack()
        ttk.Label(frame, textvariable=variable, font=("Segoe UI", 17, "bold")).pack()

    def _info_row(self, parent, row, name, variable):
        ttk.Label(parent, text=name, font=("Segoe UI", 9, "bold")).grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=3
        )
        ttk.Label(parent, textvariable=variable).grid(row=row, column=1, sticky="e", pady=3)

    def _set_controls_state(self):
        state = "normal" if self.connected else "disabled"
        self.cal_btn.configure(state=state)
        self.reset_btn.configure(state=state)
        self.test_btn.configure(state=state)

    def log_line(self, text):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.configure(state="normal")
        self.log.insert("end", f"[{timestamp}] {text}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ---------------- Ports / serial ----------------

    def refresh_ports(self, auto_connect=False):
        ports = list(serial.tools.list_ports.comports())
        labels = []
        detected_label = None

        for p in ports:
            desc = p.description or ""
            label = f"{p.device} — {desc}"
            labels.append(label)

            if p.vid == TEENSY_VID and p.pid in TEENSY_PIDS:
                detected_label = label
            elif detected_label is None and ("teensy" in desc.lower() or "teensy" in str(p.hwid).lower()):
                detected_label = label

        self.port_combo["values"] = labels

        if detected_label:
            self.port_var.set(detected_label)
        elif labels and not self.port_var.get():
            self.port_var.set(labels[0])

        if auto_connect and detected_label:
            self.root.after(250, self.connect)

    def _selected_device(self):
        value = self.port_var.get().strip()
        if not value:
            return None
        return value.split(" — ", 1)[0].strip()

    def toggle_connection(self):
        if self.connected:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        if self.connected:
            return

        device = self._selected_device()
        if not device:
            messagebox.showwarning("Latency Tester", "Nessuna porta seriale selezionata.")
            return

        try:
            self.ser = serial.Serial(device, BAUD_RATE, timeout=0.10)
            self.connected = True
            self.connection_var.set(f"CONNESSO — {device}")
            self.connect_btn.configure(text="Disconnetti")
            self._set_controls_state()
            self.log_line(f"Connesso a {device}")

            self.serial_thread = threading.Thread(target=self._serial_loop, daemon=True)
            self.serial_thread.start()

            # Ask firmware version and current stats.
            self.root.after(500, lambda: self.send_command("V"))
            self.root.after(750, lambda: self.send_command("S"))
            self.root.after(1000, lambda: self.send_command("L"))

        except serial.SerialException as exc:
            self.connection_var.set("PORTA OCCUPATA / ERRORE")
            messagebox.showerror(
                "Impossibile aprire la Teensy",
                f"{exc}\n\n"
                "Chiudi Arduino Serial Monitor e il vecchio latency_companion.py,\n"
                "poi premi Aggiorna e riprova."
            )

    def disconnect(self):
        self.connected = False
        self.calibrating = False
        self.connection_var.set("DISCONNESSO")
        self.connect_btn.configure(text="Connetti")
        self._set_controls_state()

        ser = self.ser
        self.ser = None
        if ser:
            try:
                ser.close()
            except Exception:
                pass

        self.log_line("Disconnesso")

    def send_command(self, command):
        if not self.connected or not self.ser:
            return False
        try:
            with self.write_lock:
                self.ser.write((command + "\n").encode("ascii"))
                self.ser.flush()
            return True
        except (serial.SerialException, OSError) as exc:
            self.events.put(("serial_error", str(exc)))
            return False

    def _serial_loop(self):
        while self.running and self.connected and self.ser:
            try:
                raw = self.ser.readline()
                if not raw:
                    continue

                line = raw.decode(errors="ignore").strip()
                if not line:
                    continue

                self._handle_serial_line(line)

            except (serial.SerialException, OSError) as exc:
                if self.running and self.connected:
                    self.events.put(("serial_error", str(exc)))
                return

    def _handle_serial_line(self, line):
        # Calibration ping: reply immediately from this single serial-reader thread.
        if self.calibrating and line == "P":
            self.send_command("P")
            return

        if line == "TRIG":
            self.events.put(("state", "TRIG"))

            # Once the requested test count is complete, abort any accidental
            # extra press instead of adding another sample.
            if self.test_mode and self.test_complete:
                self.send_command("X")
                return

            got_click = self._wait_for_matching_click()
            if got_click:
                self.send_command("H")
            else:
                # Never manufacture a measurement when there was no fresh OS
                # click.  v1.3 firmware treats X as a clean abort.
                self.send_command("X")
                self.events.put(("warning", "TRIG ricevuto ma nessun nuovo click OS associabile"))
            return

        m = LAT_RE.match(line)
        if m:
            data = {
                "last": float(m.group("last")),
                "min": float(m.group("min")),
                "max": float(m.group("max")),
                "avg": float(m.group("avg")),
                "n": int(m.group("n")),
                "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            }
            self.events.put(("latency", data))
            return

        m = STATS_RE.match(line)
        if m:
            data = {
                "last": float(m.group("last")),
                "min": float(m.group("min")),
                "max": float(m.group("max")),
                "avg": float(m.group("avg")),
                "n": int(m.group("n")),
                "calib": int(m.group("calib")),
            }
            self.events.put(("stats", data))
            return

        m = CAL_RE.match(line)
        if m:
            self.calibrating = False
            data = {k: int(v) for k, v in m.groupdict().items()}
            self.events.put(("cal_ok", data))
            return

        if line.startswith("CALIB_FAIL"):
            self.calibrating = False
            self.events.put(("cal_fail", line))
            return

        if line.startswith("LIGHT:"):
            try:
                self.events.put(("light", int(line.split(":", 1)[1])))
            except ValueError:
                pass
            return

        if line == "RESET":
            self.events.put(("reset", None))
            return

        if line == "SKIP:OLED_REFRESH":
            self.events.put(("skip", None))
            return

        if line == "ARMED":
            self.events.put(("armed", None))
            return

        if line == "REARM":
            self.events.put(("rearm", None))
            return

        if line == "TESTMODE:ON":
            self.events.put(("testmode_on", None))
            return

        if line == "TESTMODE:OFF":
            self.events.put(("testmode_off", None))
            return

        if line == "ABORT:NO_CLICK":
            self.events.put(("abort", None))
            return

        if line.startswith("DROP:OUT_OF_RANGE:"):
            self.events.put(("drop", line))
            return

        if line.startswith("TIMEOUT:"):
            self.events.put(("state", "TIMEOUT"))
            self.events.put(("log", line))
            return

        if line == "READY":
            self.events.put(("state", "READY"))
            return

        if line.startswith("CALIBRATING"):
            self.events.put(("state", "CALIBRATING"))
            return

        if line.startswith("PC_SYNCED"):
            self.events.put(("log", "Calibrazione sincronizzata"))
            return

        self.events.put(("log", line))

    # ---------------- Mouse matching ----------------

    def _on_click(self, _x, _y, button, pressed):
        # Keep this callback intentionally tiny. Printing or GUI work here can
        # make Windows mouse input stutter.
        if button == mouse.Button.left and pressed:
            with self.click_lock:
                self.last_click_time = time.perf_counter_ns()

    def _wait_for_matching_click(self):
        trig_seen = time.perf_counter_ns()
        cutoff = trig_seen - CLICK_GRACE_NS

        deadline = time.perf_counter() + CLICK_TIMEOUT_S
        while time.perf_counter() < deadline and self.running:
            with self.click_lock:
                current = self.last_click_time
                # A single OS click may be consumed only once.  This prevents
                # contact bounce / repeated TRIG lines from reusing the same
                # mouse click and creating fake extra samples.
                if current > self.last_consumed_click_time and current >= cutoff:
                    self.last_consumed_click_time = current
                    return True
            time.sleep(0.0002)

        return False

    # ---------------- Actions ----------------

    def calibrate(self):
        if not self.connected or self.calibrating:
            return

        self.calibrating = True
        self.state_var.set("CALIBRATING")
        self.log_line("Avvio calibrazione…")

        if not self.send_command("C"):
            self.calibrating = False
            return

        # Firmware waits for R after announcing calibration mode.
        self.root.after(800, self._send_calibration_ready)

    def _send_calibration_ready(self):
        if self.connected and self.calibrating:
            self.send_command("R")

    def reset_stats(self):
        if self.connected:
            self.send_command("R")

    def enter_test_mode(self):
        if not self.connected or self.overlay is not None:
            return

        try:
            target = max(1, int(self.target_samples_var.get()))
        except (ValueError, tk.TclError):
            target = 10
            self.target_samples_var.set(target)

        self.test_mode = True
        self.test_complete = False
        self.test_session_count = 0

        win = tk.Toplevel(self.root)
        self.overlay = win
        win.title("Latency Tester — TEST MODE")
        win.attributes("-fullscreen", True)
        win.attributes("-topmost", True)
        win.bind("<Escape>", lambda _e: self.exit_test_mode())
        win.protocol("WM_DELETE_WINDOW", self.exit_test_mode)

        frame = tk.Frame(win)
        self.overlay_frame = frame
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="TEST MODE", font=("Segoe UI", 28, "bold"), name="title").pack(pady=(70, 12))

        self.overlay_hint_label = tk.Label(
            frame,
            text="ATTENDI — preparazione\nVERDE = premi  •  ROSSO = attendi",
            font=("Segoe UI", 16, "bold"),
            justify="center",
            name="hint",
        )
        self.overlay_hint_label.pack()

        self.overlay_state_label = tk.Label(
            frame, text="PREPARAZIONE", font=("Segoe UI", 20, "bold"), name="state"
        )
        self.overlay_state_label.pack(pady=(45, 8))

        self.overlay_last_label = tk.Label(
            frame, text=self.last_var.get(), font=("Segoe UI", 84, "bold"), name="last"
        )
        self.overlay_last_label.pack()

        tk.Label(frame, text="ms", font=("Segoe UI", 20), name="units").pack()

        stats_row = tk.Frame(frame, name="statsrow")
        stats_row.pack(pady=35)

        self.overlay_avg_label = tk.Label(
            stats_row, text=f"AVG {self.avg_var.get()} ms", font=("Segoe UI", 18, "bold"), name="avg"
        )
        self.overlay_avg_label.pack(side="left", padx=30)

        self.overlay_n_label = tk.Label(
            stats_row, text=f"N 0 / {target}", font=("Segoe UI", 18, "bold"), name="count"
        )
        self.overlay_n_label.pack(side="left", padx=30)

        tk.Label(frame, text="ESC per uscire", font=("Segoe UI", 12), name="esc").pack(pady=12)

        self._set_overlay_mode("wait")
        win.focus_force()

        # Resetting statistics does NOT erase calibration.  Then tell firmware
        # to enter TEST MODE, which freezes OLED refresh traffic.
        if self.auto_reset_var.get():
            self.send_command("R")
            self.root.after(180, lambda: self.send_command("T") if self.connected else None)
        else:
            self.send_command("T")

    def _set_overlay_mode(self, mode):
        if self.overlay_frame is None:
            return

        if mode == "armed":
            bg = "#14532d"
            state = "PRONTO — PREMI"
            hint = "VERDE = puoi premere\nUn click alla volta"
        elif mode == "complete":
            bg = "#1e3a8a"
            state = "TEST COMPLETATO"
            hint = "Target raggiunto — non premere ancora\nESC per tornare alla dashboard"
        else:
            bg = "#7f1d1d"
            state = "ATTENDI"
            hint = "ROSSO = non premere\nRilascia il tasto e attendi il verde"

        fg = "white"
        self.overlay_frame.configure(bg=bg)

        def recolor(widget):
            try:
                if isinstance(widget, (tk.Frame, tk.Label)):
                    widget.configure(bg=bg)
                if isinstance(widget, tk.Label):
                    widget.configure(fg=fg)
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                recolor(child)

        recolor(self.overlay_frame)
        if self.overlay_state_label is not None:
            self.overlay_state_label.configure(text=state)
        if self.overlay_hint_label is not None:
            self.overlay_hint_label.configure(text=hint)

    def exit_test_mode(self):
        was_test_mode = self.test_mode
        self.test_mode = False
        self.test_complete = False

        if was_test_mode and self.connected:
            self.send_command("E")

        if self.overlay is not None:
            try:
                self.overlay.destroy()
            except tk.TclError:
                pass
        self.overlay = None
        self.overlay_frame = None
        self.overlay_hint_label = None
        self.overlay_last_label = None
        self.overlay_avg_label = None
        self.overlay_n_label = None
        self.overlay_state_label = None

        if self.connected:
            self.root.after(200, lambda: self.send_command("L"))

    def export_csv(self):
        if not self.samples:
            messagebox.showinfo("Esporta CSV", "Non ci sono ancora misure nella sessione.")
            return

        default_name = f"latency_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = filedialog.asksaveasfilename(
            title="Esporta sessione",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV", "*.csv"), ("Tutti i file", "*.*")],
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["timestamp", "latency_ms", "min_ms", "max_ms", "avg_ms", "sample_n"],
            )
            writer.writeheader()
            for sample in self.samples:
                writer.writerow({
                    "timestamp": sample["timestamp"],
                    "latency_ms": f'{sample["last"]:.3f}',
                    "min_ms": f'{sample["min"]:.3f}',
                    "max_ms": f'{sample["max"]:.3f}',
                    "avg_ms": f'{sample["avg"]:.3f}',
                    "sample_n": sample["n"],
                })

        self.log_line(f"CSV esportato: {path}")

    # ---------------- Event -> GUI ----------------

    def _process_events(self):
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if kind == "latency":
                self.last_var.set(f'{payload["last"]:.3f}')
                self.min_var.set(f'{payload["min"]:.3f}')
                self.max_var.set(f'{payload["max"]:.3f}')
                self.avg_var.set(f'{payload["avg"]:.3f}')
                self.n_var.set(str(payload["n"]))
                self.state_var.set("READY")
                self.samples.append(payload)
                self.log_line(f'LAT {payload["last"]:.3f} ms')
                self._draw_chart()

                if self.test_mode:
                    self.test_session_count += 1
                    try:
                        target = max(1, int(self.target_samples_var.get()))
                    except (ValueError, tk.TclError):
                        target = 10
                    if self.test_session_count >= target:
                        self.test_complete = True
                        self._set_overlay_mode("complete")
                else:
                    # Safe: timing has already stopped at t1 before LAT is emitted.
                    self.root.after(150, lambda: self.send_command("L") if self.connected else None)

            elif kind == "stats":
                self.last_var.set(f'{payload["last"]:.3f}')
                self.min_var.set(f'{payload["min"]:.3f}')
                self.max_var.set(f'{payload["max"]:.3f}')
                self.avg_var.set(f'{payload["avg"]:.3f}')
                self.n_var.set(str(payload["n"]))
                self.cal_var.set(f'{payload["calib"]} µs')

            elif kind == "cal_ok":
                self.cal_var.set(f'{payload["calib"]} µs')
                self.state_var.set("READY")
                self.log_line(
                    f'Calibrazione OK: {payload["calib"]} µs '
                    f'({payload["samples"]} campioni, RT medio {payload["avg_rt"]} µs)'
                )

            elif kind == "cal_fail":
                self.state_var.set("CAL FAIL")
                self.log_line(payload)

            elif kind == "light":
                self.light_var.set(str(payload))

            elif kind == "reset":
                self.samples.clear()
                if self.test_mode:
                    self.test_session_count = 0
                self.last_var.set("—")
                self.avg_var.set("—")
                self.min_var.set("—")
                self.max_var.set("—")
                self.n_var.set("0")
                self.state_var.set("READY")
                self.log_line("Statistiche azzerate")
                self._draw_chart()

            elif kind == "skip":
                try:
                    count = int(self.skipped_var.get()) + 1
                except ValueError:
                    count = 1
                self.skipped_var.set(str(count))
                self.state_var.set("SKIP OLED — RIPROVA")
                self.log_line("Campione scartato: click durante refresh OLED")
                if self.test_mode and not self.test_complete:
                    self._set_overlay_mode("wait")

            elif kind == "armed":
                self.state_var.set("ARMED")
                if self.test_mode and not self.test_complete:
                    self._set_overlay_mode("armed")

            elif kind == "rearm":
                self.state_var.set("REARM")
                if self.test_mode and not self.test_complete:
                    self._set_overlay_mode("wait")

            elif kind == "testmode_on":
                self.state_var.set("TEST MODE")
                if self.test_mode and not self.test_complete:
                    self._set_overlay_mode("wait")
                self.log_line("Test Mode: OLED congelato")

            elif kind == "testmode_off":
                self.state_var.set("READY")
                self.log_line("Test Mode terminato: OLED riattivato")

            elif kind == "abort":
                self.log_line("Pressione annullata: nessun nuovo click OS")

            elif kind == "drop":
                self.log_line(payload)

            elif kind == "state":
                self.state_var.set(payload)
                if payload == "TRIG" and self.test_mode and not self.test_complete:
                    self._set_overlay_mode("wait")

            elif kind == "warning":
                self.log_line("WARN: " + payload)

            elif kind == "log":
                self.log_line(payload)

            elif kind == "serial_error":
                self.log_line("Errore seriale: " + payload)
                self.disconnect()

            self._refresh_overlay()

        if self.running:
            self.root.after(50, self._process_events)

    def _idle_light_poll(self):
        # Never inject L commands while the full-screen test is active or during
        # calibration. In normal dashboard idle mode it is safe and convenient.
        if self.running and self.connected and not self.test_mode and not self.calibrating:
            self.send_command("L")

        if self.running:
            self.root.after(1000, self._idle_light_poll)

    def _refresh_overlay(self):
        if self.overlay is None:
            return
        try:
            self.overlay_last_label.configure(text=self.last_var.get())
            self.overlay_avg_label.configure(text=f"AVG {self.avg_var.get()} ms")
            try:
                target = max(1, int(self.target_samples_var.get()))
            except (ValueError, tk.TclError):
                target = 10
            self.overlay_n_label.configure(text=f"N {self.test_session_count} / {target}")
            if not self.test_complete:
                # ARMED/REARM handlers own the large state text/color.
                pass
        except tk.TclError:
            pass

    def _draw_chart(self):
        c = self.chart
        c.delete("all")
        width = max(c.winfo_width(), 100)
        height = max(c.winfo_height(), 100)

        vals = [s["last"] for s in self.samples[-60:]]
        if not vals:
            c.create_text(width / 2, height / 2, text="Nessun campione", anchor="center")
            return

        vmin = min(vals)
        vmax = max(vals)
        if vmax - vmin < 0.001:
            vmax = vmin + 1.0

        pad = 18
        plot_w = width - 2 * pad
        plot_h = height - 2 * pad

        # Axes
        c.create_line(pad, pad, pad, height - pad)
        c.create_line(pad, height - pad, width - pad, height - pad)

        points = []
        denom = max(len(vals) - 1, 1)
        for i, value in enumerate(vals):
            x = pad + (i / denom) * plot_w
            y = pad + (1 - (value - vmin) / (vmax - vmin)) * plot_h
            points.extend([x, y])

        if len(points) >= 4:
            c.create_line(*points, width=2)
        else:
            x, y = points[0], points[1]
            c.create_oval(x - 2, y - 2, x + 2, y + 2)

        c.create_text(pad + 4, pad + 4, text=f"{vmax:.2f} ms", anchor="nw")
        c.create_text(pad + 4, height - pad - 4, text=f"{vmin:.2f} ms", anchor="sw")

    # ---------------- Shutdown ----------------

    def close(self):
        self.running = False
        self.exit_test_mode()
        self.disconnect()
        try:
            self.mouse_listener.stop()
        except Exception:
            pass
        self.root.after(50, self.root.destroy)


def main():
    root = tk.Tk()
    app = LatencyDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
