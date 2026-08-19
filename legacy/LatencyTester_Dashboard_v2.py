"""
Latency Tester Dashboard v2.0
=============================

Desktop benchmark manager for the Teensy 2.0 latency tester.

Compatible firmware:
    latency_tester_oled_ldr_v1_3.ino

Features:
- Live measurement dashboard
- Full-screen Test Mode with ARMED / WAIT state
- Advanced statistics: mean, median, min, max, std dev, P95, P99,
  IQR and jitter (P95-P5)
- Device profiles
- Named test runs with polling rate / connection mode / firmware / notes
- Persistent SQLite archive
- Saved-session browser
- Multi-session comparison charts:
    raw samples, box plot, ECDF, histogram
- CSV export for current and archived sessions
- Calibration and light level stored with each run

Dependencies:
    pip install pyserial pynput matplotlib

Run:
    python latency_dashboard_v2.py

Important:
    Close Arduino Serial Monitor and any older latency_companion/dashboard
    before connecting, because only one process can own the Teensy COM port.
"""

import csv
import math
import queue
import re
import sqlite3
import statistics
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import serial
import serial.tools.list_ports
from pynput import mouse

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False


APP_NAME = "Latency Tester Dashboard v2.0"
BAUD_RATE = 115200
TEENSY_VID = 0x16C0
TEENSY_PIDS = {0x0482, 0x0483, 0x0486, 0x0487}

CLICK_GRACE_NS = int(0.200 * 1e9)
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


def default_data_dir():
    base = Path.home() / "Documents" / "LatencyTester"
    try:
        base.mkdir(parents=True, exist_ok=True)
        return base
    except Exception:
        fallback = Path(__file__).resolve().parent
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def percentile(values, p):
    """Linear-interpolated percentile, p in [0, 100]."""
    if not values:
        return math.nan
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * (p / 100.0)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def compute_stats(values):
    vals = [float(v) for v in values]
    if not vals:
        return {
            "n": 0, "mean": math.nan, "median": math.nan, "min": math.nan,
            "max": math.nan, "stdev": math.nan, "p95": math.nan, "p99": math.nan,
            "p5": math.nan, "q1": math.nan, "q3": math.nan, "iqr": math.nan,
            "jitter": math.nan,
        }

    q1 = percentile(vals, 25)
    q3 = percentile(vals, 75)
    p5 = percentile(vals, 5)
    p95 = percentile(vals, 95)
    return {
        "n": len(vals),
        "mean": statistics.fmean(vals),
        "median": statistics.median(vals),
        "min": min(vals),
        "max": max(vals),
        "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
        "p95": p95,
        "p99": percentile(vals, 99),
        "p5": p5,
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "jitter": p95 - p5,
    }


def fmt_ms(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{value:.3f}"


class LatencyDB:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()
        if not self.list_devices():
            self.create_device("Mouse non nominato", "", "", "")

    def _init_schema(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                manufacturer TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                polling_rate_hz INTEGER,
                connection_mode TEXT NOT NULL DEFAULT '',
                mouse_firmware TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                target_samples INTEGER NOT NULL DEFAULT 0,
                calibration_us INTEGER NOT NULL DEFAULT 0,
                light_start INTEGER,
                light_end INTEGER,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                seq INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_runs_device ON runs(device_id);
            CREATE INDEX IF NOT EXISTS idx_samples_run ON samples(run_id);
            """
        )
        self.conn.commit()

    def close(self):
        self.conn.close()

    def create_device(self, name, manufacturer="", model="", notes=""):
        cur = self.conn.execute(
            "INSERT INTO devices(name, manufacturer, model, notes, created_at) VALUES(?,?,?,?,?)",
            (name.strip(), manufacturer.strip(), model.strip(), notes.strip(),
             datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_device(self, device_id, name, manufacturer="", model="", notes=""):
        self.conn.execute(
            "UPDATE devices SET name=?, manufacturer=?, model=?, notes=? WHERE id=?",
            (name.strip(), manufacturer.strip(), model.strip(), notes.strip(), int(device_id)),
        )
        self.conn.commit()

    def delete_device(self, device_id):
        self.conn.execute("DELETE FROM devices WHERE id=?", (int(device_id),))
        self.conn.commit()

    def list_devices(self):
        return list(self.conn.execute("SELECT * FROM devices ORDER BY name COLLATE NOCASE"))

    def get_device(self, device_id):
        return self.conn.execute("SELECT * FROM devices WHERE id=?", (int(device_id),)).fetchone()

    def save_run(self, metadata, samples):
        cur = self.conn.execute(
            """
            INSERT INTO runs(
                device_id, name, polling_rate_hz, connection_mode, mouse_firmware,
                notes, target_samples, calibration_us, light_start, light_end,
                started_at, ended_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(metadata["device_id"]),
                metadata["name"],
                metadata.get("polling_rate_hz"),
                metadata.get("connection_mode", ""),
                metadata.get("mouse_firmware", ""),
                metadata.get("notes", ""),
                int(metadata.get("target_samples") or 0),
                int(metadata.get("calibration_us") or 0),
                metadata.get("light_start"),
                metadata.get("light_end"),
                metadata.get("started_at") or datetime.now().isoformat(timespec="seconds"),
                metadata.get("ended_at") or datetime.now().isoformat(timespec="seconds"),
            ),
        )
        run_id = cur.lastrowid
        self.conn.executemany(
            "INSERT INTO samples(run_id, seq, latency_ms, timestamp) VALUES(?,?,?,?)",
            [
                (
                    run_id,
                    i + 1,
                    float(sample["latency_ms"]),
                    sample.get("timestamp") or datetime.now().isoformat(timespec="milliseconds"),
                )
                for i, sample in enumerate(samples)
            ],
        )
        self.conn.commit()
        return run_id

    def list_runs(self):
        return list(
            self.conn.execute(
                """
                SELECT r.*, d.name AS device_name, d.manufacturer, d.model
                FROM runs r
                JOIN devices d ON d.id = r.device_id
                ORDER BY r.started_at DESC, r.id DESC
                """
            )
        )

    def get_run(self, run_id):
        return self.conn.execute(
            """
            SELECT r.*, d.name AS device_name, d.manufacturer, d.model
            FROM runs r
            JOIN devices d ON d.id = r.device_id
            WHERE r.id=?
            """,
            (int(run_id),),
        ).fetchone()

    def get_samples(self, run_id):
        return list(
            self.conn.execute(
                "SELECT * FROM samples WHERE run_id=? ORDER BY seq",
                (int(run_id),),
            )
        )

    def delete_run(self, run_id):
        self.conn.execute("DELETE FROM runs WHERE id=?", (int(run_id),))
        self.conn.commit()


class LatencyDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1360x860")
        self.root.minsize(1080, 700)

        self.data_dir = default_data_dir()
        self.db = LatencyDB(self.data_dir / "latency_tester.db")

        self.ser = None
        self.serial_thread = None
        self.running = True
        self.connected = False
        self.calibrating = False
        self.test_mode = False
        self.test_complete = False

        self.write_lock = threading.Lock()
        self.click_lock = threading.Lock()
        self.last_click_time = 0
        self.last_consumed_click_time = 0

        self.events = queue.Queue()

        # Current unsaved run
        self.current_samples = []
        self.current_run_started_at = None
        self.current_run_ended_at = None
        self.current_light = None
        self.light_start = None
        self.light_end = None
        self.awaiting_light_end = False
        self.session_saved = False
        self.test_start_sample_index = 0

        # Test overlay
        self.overlay = None
        self.overlay_frame = None
        self.overlay_hint_label = None
        self.overlay_state_label = None
        self.overlay_last_label = None
        self.overlay_median_label = None
        self.overlay_p95_label = None
        self.overlay_n_label = None

        # Connection vars
        self.connection_var = tk.StringVar(value="DISCONNESSO")
        self.port_var = tk.StringVar()
        self.state_var = tk.StringVar(value="READY")
        self.cal_var = tk.StringVar(value="0 µs")
        self.light_var = tk.StringVar(value="—")
        self.skipped_var = tk.StringVar(value="0")

        # Live stats vars
        self.last_var = tk.StringVar(value="—")
        self.mean_var = tk.StringVar(value="—")
        self.median_var = tk.StringVar(value="—")
        self.min_var = tk.StringVar(value="—")
        self.max_var = tk.StringVar(value="—")
        self.stdev_var = tk.StringVar(value="—")
        self.p95_var = tk.StringVar(value="—")
        self.p99_var = tk.StringVar(value="—")
        self.iqr_var = tk.StringVar(value="—")
        self.jitter_var = tk.StringVar(value="—")
        self.n_var = tk.StringVar(value="0")

        # Run metadata vars
        self.device_var = tk.StringVar()
        self.run_name_var = tk.StringVar()
        self.polling_var = tk.StringVar(value="1000")
        self.connection_mode_var = tk.StringVar(value="Wireless")
        self.mouse_firmware_var = tk.StringVar()
        self.target_samples_var = tk.IntVar(value=50)
        self.auto_reset_var = tk.BooleanVar(value=True)

        self.device_name_to_id = {}

        # Device editor vars
        self.dev_name_var = tk.StringVar()
        self.dev_manufacturer_var = tk.StringVar()
        self.dev_model_var = tk.StringVar()

        # Compare vars
        self.compare_chart_type = tk.StringVar(value="Campioni")
        self.compare_status_var = tk.StringVar(value="Seleziona almeno due sessioni per confrontarle.")

        self._build_ui()

        self.mouse_listener = mouse.Listener(on_click=self._on_click)
        self.mouse_listener.start()

        self.refresh_devices()
        self.refresh_sessions()
        self.refresh_ports(auto_connect=True)

        self.root.after(50, self._process_events)
        self.root.after(1000, self._idle_light_poll)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        conn = ttk.LabelFrame(outer, text=" Connessione Teensy ", padding=8)
        conn.pack(fill="x")

        ttk.Label(conn, text="Porta:").pack(side="left")
        self.port_combo = ttk.Combobox(conn, textvariable=self.port_var, width=35, state="readonly")
        self.port_combo.pack(side="left", padx=(6, 6))
        ttk.Button(conn, text="Aggiorna", command=lambda: self.refresh_ports(False)).pack(side="left", padx=3)
        self.connect_btn = ttk.Button(conn, text="Connetti", command=self.toggle_connection)
        self.connect_btn.pack(side="left", padx=3)
        ttk.Label(conn, text="Stato:").pack(side="left", padx=(20, 5))
        ttk.Label(conn, textvariable=self.connection_var).pack(side="left")

        ttk.Label(
            conn,
            text=f"Archivio: {self.db.path}",
        ).pack(side="right")

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True, pady=(8, 0))

        self.live_tab = ttk.Frame(self.notebook, padding=8)
        self.sessions_tab = ttk.Frame(self.notebook, padding=8)
        self.compare_tab = ttk.Frame(self.notebook, padding=8)
        self.devices_tab = ttk.Frame(self.notebook, padding=8)

        self.notebook.add(self.live_tab, text="LIVE TEST")
        self.notebook.add(self.sessions_tab, text="SESSIONI")
        self.notebook.add(self.compare_tab, text="CONFRONTA")
        self.notebook.add(self.devices_tab, text="DISPOSITIVI")

        self._build_live_tab()
        self._build_sessions_tab()
        self._build_compare_tab()
        self._build_devices_tab()

    def _build_live_tab(self):
        self.live_tab.columnconfigure(0, weight=3)
        self.live_tab.columnconfigure(1, weight=2)
        self.live_tab.rowconfigure(0, weight=1)

        left = ttk.Frame(self.live_tab)
        right = ttk.Frame(self.live_tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        metrics = ttk.LabelFrame(left, text=" Statistiche live ", padding=10)
        metrics.pack(fill="x")

        top = ttk.Frame(metrics)
        top.pack(fill="x")
        ttk.Label(top, text="ULTIMA", font=("Segoe UI", 10, "bold")).pack()
        ttk.Label(top, textvariable=self.last_var, font=("Segoe UI", 34, "bold")).pack()
        ttk.Label(top, text="ms").pack()

        grid = ttk.Frame(metrics)
        grid.pack(fill="x", pady=(8, 0))
        for c in range(5):
            grid.columnconfigure(c, weight=1)

        cells = [
            ("MEDIA", self.mean_var), ("MEDIANA", self.median_var),
            ("P95", self.p95_var), ("P99", self.p99_var), ("DEV.STD", self.stdev_var),
            ("MIN", self.min_var), ("MAX", self.max_var),
            ("IQR", self.iqr_var), ("JITTER P95-P5", self.jitter_var), ("N", self.n_var),
        ]
        for i, (title, var) in enumerate(cells):
            self._metric_cell(grid, i // 5, i % 5, title, var)

        chart_box = ttk.LabelFrame(left, text=" Campioni della run corrente ", padding=6)
        chart_box.pack(fill="both", expand=True, pady=(8, 0))
        self.live_chart = tk.Canvas(chart_box, height=300, highlightthickness=0)
        self.live_chart.pack(fill="both", expand=True)
        self.live_chart.bind("<Configure>", lambda _e: self._draw_live_chart())

        meta = ttk.LabelFrame(right, text=" Configurazione run ", padding=10)
        meta.pack(fill="x")
        meta.columnconfigure(1, weight=1)

        ttk.Label(meta, text="Dispositivo").grid(row=0, column=0, sticky="w", pady=3)
        self.device_combo = ttk.Combobox(meta, textvariable=self.device_var, state="readonly")
        self.device_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=3)

        ttk.Label(meta, text="Nome run").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(meta, textvariable=self.run_name_var).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=3)

        ttk.Label(meta, text="Polling rate (Hz)").grid(row=2, column=0, sticky="w", pady=3)
        self.poll_combo = ttk.Combobox(
            meta, textvariable=self.polling_var,
            values=("125", "250", "500", "1000", "2000", "4000", "8000"),
        )
        self.poll_combo.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=3)

        ttk.Label(meta, text="Connessione").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Combobox(
            meta, textvariable=self.connection_mode_var,
            values=("Wireless", "Wired", "Bluetooth", "Altro"),
        ).grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=3)

        ttk.Label(meta, text="Firmware mouse").grid(row=4, column=0, sticky="w", pady=3)
        ttk.Entry(meta, textvariable=self.mouse_firmware_var).grid(row=4, column=1, sticky="ew", padx=(8, 0), pady=3)

        ttk.Label(meta, text="Note").grid(row=5, column=0, sticky="nw", pady=3)
        self.run_notes = tk.Text(meta, height=4, wrap="word")
        self.run_notes.grid(row=5, column=1, sticky="ew", padx=(8, 0), pady=3)

        opts = ttk.Frame(meta)
        opts.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Label(opts, text="Target:").pack(side="left")
        ttk.Spinbox(opts, from_=1, to=10000, textvariable=self.target_samples_var, width=7).pack(
            side="left", padx=(5, 15)
        )
        ttk.Checkbutton(opts, text="Reset all'ingresso", variable=self.auto_reset_var).pack(side="left")

        control = ttk.LabelFrame(right, text=" Controlli ", padding=10)
        control.pack(fill="x", pady=(8, 0))

        info = ttk.Frame(control)
        info.pack(fill="x", pady=(0, 8))
        info.columnconfigure(1, weight=1)
        self._info_row(info, 0, "STATE", self.state_var)
        self._info_row(info, 1, "CAL", self.cal_var)
        self._info_row(info, 2, "LIGHT", self.light_var)
        self._info_row(info, 3, "SKIP OLED", self.skipped_var)

        buttons = ttk.Frame(control)
        buttons.pack(fill="x")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        self.cal_btn = ttk.Button(buttons, text="Calibra", command=self.calibrate)
        self.cal_btn.grid(row=0, column=0, sticky="ew", padx=(0, 3), pady=3)
        self.reset_btn = ttk.Button(buttons, text="Reset", command=self.reset_stats)
        self.reset_btn.grid(row=0, column=1, sticky="ew", padx=(3, 0), pady=3)

        ttk.Button(buttons, text="Richiedi stats", command=lambda: self.send_command("S")).grid(
            row=1, column=0, sticky="ew", padx=(0, 3), pady=3
        )
        ttk.Button(buttons, text="Leggi luce", command=lambda: self.send_command("L")).grid(
            row=1, column=1, sticky="ew", padx=(3, 0), pady=3
        )

        self.test_btn = ttk.Button(control, text="ENTRA IN TEST MODE", command=self.enter_test_mode)
        self.test_btn.pack(fill="x", pady=(10, 4), ipady=9)

        ttk.Label(
            control,
            text="VERDE = premi • ROSSO = attendi/rilascia • BLU = target completato\n"
                 "In Test Mode l'OLED rimane congelato per non disturbare il timing.",
            justify="center",
        ).pack(fill="x")

        session = ttk.LabelFrame(right, text=" Run corrente ", padding=10)
        session.pack(fill="x", pady=(8, 0))
        row = ttk.Frame(session)
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)
        self.save_run_btn = ttk.Button(row, text="Salva sessione", command=self.save_current_run)
        self.save_run_btn.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(row, text="Nuova run", command=self.new_run).grid(row=0, column=1, sticky="ew", padx=(3, 0))
        ttk.Button(session, text="Esporta run corrente CSV", command=self.export_current_csv).pack(
            fill="x", pady=(6, 0)
        )

        log_box = ttk.LabelFrame(right, text=" Eventi ", padding=6)
        log_box.pack(fill="both", expand=True, pady=(8, 0))
        self.log = tk.Text(log_box, height=10, wrap="word", state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)

        self._set_controls_state()

    def _build_sessions_tab(self):
        top = ttk.Frame(self.sessions_tab)
        top.pack(fill="x")
        ttk.Button(top, text="Aggiorna", command=self.refresh_sessions).pack(side="left")
        ttk.Button(top, text="Esporta CSV", command=self.export_selected_session_csv).pack(side="left", padx=5)
        ttk.Button(top, text="Elimina", command=self.delete_selected_session).pack(side="left", padx=5)
        ttk.Button(top, text="Confronta selezionate", command=self.compare_selected_from_sessions).pack(
            side="left", padx=5
        )

        columns = (
            "date", "device", "run", "poll", "mode", "n",
            "median", "mean", "p95", "p99", "stdev", "cal"
        )
        self.sessions_tree = ttk.Treeview(
            self.sessions_tab, columns=columns, show="headings", selectmode="extended"
        )
        headings = {
            "date": "Data", "device": "Dispositivo", "run": "Run",
            "poll": "Hz", "mode": "Modo", "n": "N",
            "median": "Mediana", "mean": "Media", "p95": "P95",
            "p99": "P99", "stdev": "Dev.Std", "cal": "Cal µs",
        }
        widths = {
            "date": 145, "device": 170, "run": 180, "poll": 60, "mode": 90, "n": 55,
            "median": 80, "mean": 80, "p95": 80, "p99": 80, "stdev": 80, "cal": 70,
        }
        for col in columns:
            self.sessions_tree.heading(col, text=headings[col])
            self.sessions_tree.column(col, width=widths[col], anchor="center")
        self.sessions_tree.pack(fill="both", expand=True, pady=(8, 0))
        self.sessions_tree.bind("<<TreeviewSelect>>", lambda _e: self._show_session_details())

        details = ttk.LabelFrame(self.sessions_tab, text=" Dettagli ", padding=8)
        details.pack(fill="x", pady=(8, 0))
        self.session_details = tk.Text(details, height=6, wrap="word", state="disabled")
        self.session_details.pack(fill="x")

    def _build_compare_tab(self):
        self.compare_tab.columnconfigure(0, weight=1)
        self.compare_tab.columnconfigure(1, weight=3)
        self.compare_tab.rowconfigure(0, weight=1)

        left = ttk.Frame(self.compare_tab)
        right = ttk.Frame(self.compare_tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        ttk.Label(left, text="Seleziona sessioni (Ctrl/Shift per più righe):").pack(anchor="w")
        columns = ("date", "device", "run", "poll", "n", "median")
        self.compare_tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="extended", height=20)
        for col, title, width in [
            ("date", "Data", 120), ("device", "Mouse", 130), ("run", "Run", 140),
            ("poll", "Hz", 55), ("n", "N", 45), ("median", "Med.", 65),
        ]:
            self.compare_tree.heading(col, text=title)
            self.compare_tree.column(col, width=width, anchor="center")
        self.compare_tree.pack(fill="both", expand=True, pady=(5, 6))

        controls = ttk.Frame(left)
        controls.pack(fill="x")
        ttk.Label(controls, text="Grafico:").pack(side="left")
        ttk.Combobox(
            controls,
            textvariable=self.compare_chart_type,
            state="readonly",
            values=("Campioni", "Box plot", "ECDF", "Istogramma"),
            width=15,
        ).pack(side="left", padx=5)
        ttk.Button(controls, text="Plot", command=self.plot_compare).pack(side="left")

        ttk.Label(left, textvariable=self.compare_status_var, wraplength=330).pack(
            fill="x", pady=(8, 0)
        )

        chart_frame = ttk.LabelFrame(right, text=" Grafico comparativo ", padding=4)
        chart_frame.pack(fill="both", expand=True)

        if MATPLOTLIB_AVAILABLE:
            self.compare_figure = Figure(figsize=(7.5, 4.8), dpi=100)
            self.compare_ax = self.compare_figure.add_subplot(111)
            self.compare_canvas = FigureCanvasTkAgg(self.compare_figure, master=chart_frame)
            self.compare_canvas.get_tk_widget().pack(fill="both", expand=True)
        else:
            self.compare_figure = None
            self.compare_ax = None
            self.compare_canvas = None
            ttk.Label(
                chart_frame,
                text="Matplotlib non installato.\nEsegui: pip install matplotlib",
                justify="center",
            ).pack(expand=True)

        table_frame = ttk.LabelFrame(right, text=" Statistiche selezionate ", padding=4)
        table_frame.pack(fill="x", pady=(8, 0))
        cols = ("session", "n", "mean", "median", "p95", "p99", "stdev", "min", "max", "jitter")
        self.compare_stats_tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=7)
        names = {
            "session": "Sessione", "n": "N", "mean": "Media", "median": "Mediana",
            "p95": "P95", "p99": "P99", "stdev": "Dev.Std",
            "min": "Min", "max": "Max", "jitter": "Jitter",
        }
        for col in cols:
            self.compare_stats_tree.heading(col, text=names[col])
            self.compare_stats_tree.column(col, width=85 if col != "session" else 220, anchor="center")
        self.compare_stats_tree.pack(fill="x")

    def _build_devices_tab(self):
        self.devices_tab.columnconfigure(0, weight=2)
        self.devices_tab.columnconfigure(1, weight=3)
        self.devices_tab.rowconfigure(0, weight=1)

        left = ttk.Frame(self.devices_tab)
        right = ttk.Frame(self.devices_tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.devices_tree = ttk.Treeview(
            left, columns=("name", "manufacturer", "model"), show="headings", selectmode="browse"
        )
        for col, title, width in [
            ("name", "Nome profilo", 180),
            ("manufacturer", "Produttore", 120),
            ("model", "Modello", 150),
        ]:
            self.devices_tree.heading(col, text=title)
            self.devices_tree.column(col, width=width)
        self.devices_tree.pack(fill="both", expand=True)
        self.devices_tree.bind("<<TreeviewSelect>>", lambda _e: self._load_selected_device())

        editor = ttk.LabelFrame(right, text=" Profilo dispositivo ", padding=10)
        editor.pack(fill="x")
        editor.columnconfigure(1, weight=1)

        ttk.Label(editor, text="Nome profilo").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(editor, textvariable=self.dev_name_var).grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=4)

        ttk.Label(editor, text="Produttore").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(editor, textvariable=self.dev_manufacturer_var).grid(
            row=1, column=1, sticky="ew", padx=(8, 0), pady=4
        )

        ttk.Label(editor, text="Modello").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(editor, textvariable=self.dev_model_var).grid(
            row=2, column=1, sticky="ew", padx=(8, 0), pady=4
        )

        ttk.Label(editor, text="Note").grid(row=3, column=0, sticky="nw", pady=4)
        self.dev_notes = tk.Text(editor, height=7, wrap="word")
        self.dev_notes.grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=4)

        buttons = ttk.Frame(editor)
        buttons.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        for c in range(3):
            buttons.columnconfigure(c, weight=1)
        ttk.Button(buttons, text="Nuovo", command=self.clear_device_editor).grid(
            row=0, column=0, sticky="ew", padx=(0, 3)
        )
        ttk.Button(buttons, text="Salva / aggiorna", command=self.save_device).grid(
            row=0, column=1, sticky="ew", padx=3
        )
        ttk.Button(buttons, text="Elimina", command=self.delete_device).grid(
            row=0, column=2, sticky="ew", padx=(3, 0)
        )

        ttk.Label(
            right,
            text="Ogni run viene collegata a un profilo dispositivo. "
                 "Puoi quindi salvare più configurazioni dello stesso mouse "
                 "(es. 1000/2000/4000/8000 Hz, wired/wireless) e confrontarle in seguito.",
            wraplength=600,
            justify="left",
        ).pack(fill="x", pady=(12, 0))

    def _metric_cell(self, parent, row, column, title, variable):
        frame = ttk.Frame(parent, padding=4)
        frame.grid(row=row, column=column, sticky="nsew")
        ttk.Label(frame, text=title, font=("Segoe UI", 8, "bold")).pack()
        ttk.Label(frame, textvariable=variable, font=("Segoe UI", 15, "bold")).pack()

    def _info_row(self, parent, row, name, variable):
        ttk.Label(parent, text=name, font=("Segoe UI", 9, "bold")).grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=2
        )
        ttk.Label(parent, textvariable=variable).grid(row=row, column=1, sticky="e", pady=2)

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

    # ------------------------------------------------------------------
    # Devices / metadata
    # ------------------------------------------------------------------

    def refresh_devices(self):
        devices = self.db.list_devices()
        if not devices:
            self.db.create_device("Mouse non nominato", "", "", "")
            devices = self.db.list_devices()
        current = self.device_var.get()

        self.device_name_to_id = {row["name"]: row["id"] for row in devices}
        names = list(self.device_name_to_id.keys())
        self.device_combo["values"] = names
        if current in names:
            self.device_var.set(current)
        elif names:
            self.device_var.set(names[0])

        for item in self.devices_tree.get_children():
            self.devices_tree.delete(item)
        for row in devices:
            self.devices_tree.insert(
                "", "end", iid=str(row["id"]),
                values=(row["name"], row["manufacturer"], row["model"])
            )

    def clear_device_editor(self):
        for item in self.devices_tree.selection():
            self.devices_tree.selection_remove(item)
        self.dev_name_var.set("")
        self.dev_manufacturer_var.set("")
        self.dev_model_var.set("")
        self.dev_notes.delete("1.0", "end")

    def _load_selected_device(self):
        sel = self.devices_tree.selection()
        if not sel:
            return
        row = self.db.get_device(int(sel[0]))
        if not row:
            return
        self.dev_name_var.set(row["name"])
        self.dev_manufacturer_var.set(row["manufacturer"])
        self.dev_model_var.set(row["model"])
        self.dev_notes.delete("1.0", "end")
        self.dev_notes.insert("1.0", row["notes"])

    def save_device(self):
        name = self.dev_name_var.get().strip()
        if not name:
            messagebox.showwarning("Dispositivo", "Inserisci un nome profilo.")
            return
        manufacturer = self.dev_manufacturer_var.get().strip()
        model = self.dev_model_var.get().strip()
        notes = self.dev_notes.get("1.0", "end").strip()
        sel = self.devices_tree.selection()
        try:
            if sel:
                self.db.update_device(int(sel[0]), name, manufacturer, model, notes)
            else:
                self.db.create_device(name, manufacturer, model, notes)
        except sqlite3.IntegrityError:
            messagebox.showerror("Dispositivo", "Esiste già un profilo con questo nome.")
            return
        self.refresh_devices()
        self.refresh_sessions()
        messagebox.showinfo("Dispositivo", "Profilo salvato.")

    def delete_device(self):
        sel = self.devices_tree.selection()
        if not sel:
            return
        row = self.db.get_device(int(sel[0]))
        if not row:
            return
        if not messagebox.askyesno(
            "Elimina dispositivo",
            f"Eliminare '{row['name']}'?\n\nSaranno eliminate anche tutte le sessioni associate.",
        ):
            return
        self.db.delete_device(int(sel[0]))
        self.clear_device_editor()
        self.refresh_devices()
        self.refresh_sessions()

    # ------------------------------------------------------------------
    # Ports / serial
    # ------------------------------------------------------------------

    def refresh_ports(self, auto_connect=False):
        ports = list(serial.tools.list_ports.comports())
        labels = []
        detected = None
        for p in ports:
            desc = p.description or ""
            label = f"{p.device} — {desc}"
            labels.append(label)
            if p.vid == TEENSY_VID and p.pid in TEENSY_PIDS:
                detected = label
            elif detected is None and ("teensy" in desc.lower() or "teensy" in str(p.hwid).lower()):
                detected = label

        self.port_combo["values"] = labels
        if detected:
            self.port_var.set(detected)
        elif labels and not self.port_var.get():
            self.port_var.set(labels[0])

        if auto_connect and detected:
            self.root.after(250, self.connect)

    def _selected_device_port(self):
        value = self.port_var.get().strip()
        return value.split(" — ", 1)[0].strip() if value else None

    def toggle_connection(self):
        self.disconnect() if self.connected else self.connect()

    def connect(self):
        if self.connected:
            return
        device = self._selected_device_port()
        if not device:
            messagebox.showwarning("Connessione", "Nessuna porta seriale selezionata.")
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
            self.root.after(500, lambda: self.send_command("V"))
            self.root.after(750, lambda: self.send_command("S"))
            self.root.after(1000, lambda: self.send_command("L"))
        except serial.SerialException as exc:
            messagebox.showerror(
                "Impossibile aprire la Teensy",
                f"{exc}\n\nChiudi Arduino Serial Monitor e le vecchie dashboard/companion e riprova.",
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
                if line:
                    self._handle_serial_line(line)
            except (serial.SerialException, OSError) as exc:
                if self.running and self.connected:
                    self.events.put(("serial_error", str(exc)))
                return

    def _handle_serial_line(self, line):
        if self.calibrating and line == "P":
            self.send_command("P")
            return

        if line == "TRIG":
            self.events.put(("state", "TRIG"))
            if self.test_mode and self.test_complete:
                self.send_command("X")
                return
            if self._wait_for_matching_click():
                self.send_command("H")
            else:
                self.send_command("X")
                self.events.put(("warning", "TRIG senza nuovo click OS associabile"))
            return

        m = LAT_RE.match(line)
        if m:
            self.events.put(("latency", {
                "latency_ms": float(m.group("last")),
                "firmware_n": int(m.group("n")),
                "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            }))
            return

        m = STATS_RE.match(line)
        if m:
            self.events.put(("stats", {
                "last": float(m.group("last")),
                "min": float(m.group("min")),
                "max": float(m.group("max")),
                "avg": float(m.group("avg")),
                "n": int(m.group("n")),
                "calib": int(m.group("calib")),
            }))
            return

        m = CAL_RE.match(line)
        if m:
            self.calibrating = False
            self.events.put(("cal_ok", {k: int(v) for k, v in m.groupdict().items()}))
            return

        if line.startswith("CALIB_FAIL"):
            self.calibrating = False
            self.events.put(("cal_fail", line))
        elif line.startswith("LIGHT:"):
            try:
                self.events.put(("light", int(line.split(":", 1)[1])))
            except ValueError:
                pass
        elif line == "RESET":
            self.events.put(("reset", None))
        elif line == "SKIP:OLED_REFRESH":
            self.events.put(("skip", None))
        elif line == "ARMED":
            self.events.put(("armed", None))
        elif line == "REARM":
            self.events.put(("rearm", None))
        elif line == "TESTMODE:ON":
            self.events.put(("testmode_on", None))
        elif line == "TESTMODE:OFF":
            self.events.put(("testmode_off", None))
        elif line == "ABORT:NO_CLICK":
            self.events.put(("abort", None))
        elif line.startswith("DROP:OUT_OF_RANGE:"):
            self.events.put(("drop", line))
        elif line.startswith("TIMEOUT:"):
            self.events.put(("state", "TIMEOUT"))
            self.events.put(("log", line))
        elif line == "READY":
            self.events.put(("state", "READY"))
        elif line.startswith("CALIBRATING"):
            self.events.put(("state", "CALIBRATING"))
        elif line.startswith("PC_SYNCED"):
            self.events.put(("log", "Calibrazione sincronizzata"))
        else:
            self.events.put(("log", line))

    # ------------------------------------------------------------------
    # Mouse click association
    # ------------------------------------------------------------------

    def _on_click(self, _x, _y, button, pressed):
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
                if current > self.last_consumed_click_time and current >= cutoff:
                    self.last_consumed_click_time = current
                    return True
            time.sleep(0.0002)
        return False

    # ------------------------------------------------------------------
    # Live actions
    # ------------------------------------------------------------------

    def calibrate(self):
        if not self.connected or self.calibrating or self.test_mode:
            return
        self.calibrating = True
        self.state_var.set("CALIBRATING")
        self.log_line("Avvio calibrazione…")
        if self.send_command("C"):
            self.root.after(800, self._send_calibration_ready)
        else:
            self.calibrating = False

    def _send_calibration_ready(self):
        if self.connected and self.calibrating:
            self.send_command("R")

    def reset_stats(self):
        if self.connected and not self.test_mode:
            self.send_command("R")

    def _generate_run_name(self):
        poll = self.polling_var.get().strip()
        mode = self.connection_mode_var.get().strip()
        bits = []
        if poll:
            bits.append(f"{poll} Hz")
        if mode:
            bits.append(mode)
        bits.append(datetime.now().strftime("%Y-%m-%d %H-%M"))
        return " - ".join(bits)

    def enter_test_mode(self):
        if not self.connected or self.overlay is not None:
            return

        try:
            target = max(1, int(self.target_samples_var.get()))
        except Exception:
            target = 50
            self.target_samples_var.set(target)

        if not self.run_name_var.get().strip():
            self.run_name_var.set(self._generate_run_name())

        self.test_mode = True
        self.test_complete = False
        self.current_run_started_at = datetime.now().isoformat(timespec="seconds")
        self.current_run_ended_at = None
        self.light_start = self.current_light
        self.light_end = None
        self.awaiting_light_end = False
        self.session_saved = False

        if self.auto_reset_var.get():
            self.test_start_sample_index = 0
        else:
            self.test_start_sample_index = len(self.current_samples)

        self._create_test_overlay(target)

        if self.auto_reset_var.get():
            self.send_command("R")
            self.root.after(180, lambda: self.send_command("T") if self.connected else None)
        else:
            self.send_command("T")

    def _create_test_overlay(self, target):
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

        device = self.device_var.get().strip() or "Mouse"
        run_name = self.run_name_var.get().strip()
        tk.Label(frame, text=f"{device} — {run_name}", font=("Segoe UI", 20, "bold"), name="run").pack(
            pady=(55, 8)
        )
        tk.Label(frame, text="TEST MODE", font=("Segoe UI", 30, "bold"), name="title").pack(pady=6)

        self.overlay_hint_label = tk.Label(
            frame,
            text="ATTENDI — preparazione",
            font=("Segoe UI", 17, "bold"),
            justify="center",
            name="hint",
        )
        self.overlay_hint_label.pack(pady=(8, 0))

        self.overlay_state_label = tk.Label(
            frame, text="PREPARAZIONE", font=("Segoe UI", 22, "bold"), name="state"
        )
        self.overlay_state_label.pack(pady=(35, 4))

        self.overlay_last_label = tk.Label(
            frame, text=self.last_var.get(), font=("Segoe UI", 82, "bold"), name="last"
        )
        self.overlay_last_label.pack()
        tk.Label(frame, text="ms", font=("Segoe UI", 18), name="units").pack()

        stat_row = tk.Frame(frame, name="statsrow")
        stat_row.pack(pady=28)

        self.overlay_median_label = tk.Label(
            stat_row, text=f"MED {self.median_var.get()} ms", font=("Segoe UI", 17, "bold"), name="median"
        )
        self.overlay_median_label.pack(side="left", padx=25)

        self.overlay_p95_label = tk.Label(
            stat_row, text=f"P95 {self.p95_var.get()} ms", font=("Segoe UI", 17, "bold"), name="p95"
        )
        self.overlay_p95_label.pack(side="left", padx=25)

        self.overlay_n_label = tk.Label(
            stat_row, text=f"N 0 / {target}", font=("Segoe UI", 17, "bold"), name="count"
        )
        self.overlay_n_label.pack(side="left", padx=25)

        tk.Label(frame, text="ESC per uscire", font=("Segoe UI", 11), name="esc").pack(pady=8)

        self._set_overlay_mode("wait")
        win.focus_force()

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
            hint = "Target raggiunto\nESC per tornare e salvare la sessione"
        else:
            bg = "#7f1d1d"
            state = "ATTENDI"
            hint = "ROSSO = non premere\nRilascia il tasto e attendi il verde"

        self.overlay_frame.configure(bg=bg)

        def recolor(widget):
            try:
                if isinstance(widget, (tk.Frame, tk.Label)):
                    widget.configure(bg=bg)
                if isinstance(widget, tk.Label):
                    widget.configure(fg="white")
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                recolor(child)

        recolor(self.overlay_frame)
        if self.overlay_state_label:
            self.overlay_state_label.configure(text=state)
        if self.overlay_hint_label:
            self.overlay_hint_label.configure(text=hint)

    def exit_test_mode(self):
        was_test = self.test_mode
        self.test_mode = False
        self.test_complete = False
        self.current_run_ended_at = datetime.now().isoformat(timespec="seconds")

        if was_test and self.connected:
            self.send_command("E")

        if self.overlay:
            try:
                self.overlay.destroy()
            except tk.TclError:
                pass

        self.overlay = None
        self.overlay_frame = None
        self.overlay_hint_label = None
        self.overlay_state_label = None
        self.overlay_last_label = None
        self.overlay_median_label = None
        self.overlay_p95_label = None
        self.overlay_n_label = None

        if self.connected:
            self.awaiting_light_end = True
            self.root.after(200, lambda: self.send_command("L"))

    def new_run(self):
        if self.test_mode:
            return
        if self.current_samples and not self.session_saved:
            if not messagebox.askyesno(
                "Nuova run",
                "La run corrente contiene campioni non salvati. Scartarli e iniziare una nuova run?",
            ):
                return
        if self.connected:
            self.send_command("R")
        else:
            self._clear_current_samples()
        self.run_name_var.set("")
        self.current_run_started_at = None
        self.current_run_ended_at = None
        self.light_start = self.current_light
        self.light_end = None
        self.session_saved = False

    def _current_calibration_us(self):
        text = self.cal_var.get().replace("µs", "").strip()
        try:
            return int(float(text))
        except ValueError:
            return 0

    def _current_metadata(self):
        device_name = self.device_var.get().strip()
        device_id = self.device_name_to_id.get(device_name)
        if not device_id:
            raise ValueError("Seleziona un dispositivo.")

        name = self.run_name_var.get().strip() or self._generate_run_name()
        self.run_name_var.set(name)

        try:
            poll = int(self.polling_var.get().strip()) if self.polling_var.get().strip() else None
        except ValueError:
            poll = None

        return {
            "device_id": device_id,
            "name": name,
            "polling_rate_hz": poll,
            "connection_mode": self.connection_mode_var.get().strip(),
            "mouse_firmware": self.mouse_firmware_var.get().strip(),
            "notes": self.run_notes.get("1.0", "end").strip(),
            "target_samples": int(self.target_samples_var.get()),
            "calibration_us": self._current_calibration_us(),
            "light_start": self.light_start,
            "light_end": self.light_end if self.light_end is not None else self.current_light,
            "started_at": self.current_run_started_at or datetime.now().isoformat(timespec="seconds"),
            "ended_at": self.current_run_ended_at or datetime.now().isoformat(timespec="seconds"),
        }

    def save_current_run(self):
        if self.test_mode:
            messagebox.showinfo("Salva sessione", "Esci prima dal Test Mode con ESC.")
            return
        if not self.current_samples:
            messagebox.showinfo("Salva sessione", "Non ci sono campioni da salvare.")
            return
        if self.session_saved:
            messagebox.showinfo("Salva sessione", "Questa versione della run è già stata salvata.")
            return
        try:
            metadata = self._current_metadata()
        except ValueError as exc:
            messagebox.showwarning("Salva sessione", str(exc))
            return

        run_id = self.db.save_run(metadata, self.current_samples)
        self.session_saved = True
        self.log_line(f"Sessione salvata nell'archivio (ID {run_id})")
        self.refresh_sessions()
        messagebox.showinfo("Salva sessione", f"Sessione salvata.\nID archivio: {run_id}")

    # ------------------------------------------------------------------
    # Current stats / chart
    # ------------------------------------------------------------------

    def _clear_current_samples(self):
        self.current_samples.clear()
        self.session_saved = False
        self._update_live_stats()
        self._draw_live_chart()

    def _update_live_stats(self):
        vals = [s["latency_ms"] for s in self.current_samples]
        st = compute_stats(vals)
        self.n_var.set(str(st["n"]))
        if not vals:
            for var in (
                self.last_var, self.mean_var, self.median_var, self.min_var, self.max_var,
                self.stdev_var, self.p95_var, self.p99_var, self.iqr_var, self.jitter_var
            ):
                var.set("—")
            return
        self.last_var.set(fmt_ms(vals[-1]))
        self.mean_var.set(fmt_ms(st["mean"]))
        self.median_var.set(fmt_ms(st["median"]))
        self.min_var.set(fmt_ms(st["min"]))
        self.max_var.set(fmt_ms(st["max"]))
        self.stdev_var.set(fmt_ms(st["stdev"]))
        self.p95_var.set(fmt_ms(st["p95"]))
        self.p99_var.set(fmt_ms(st["p99"]))
        self.iqr_var.set(fmt_ms(st["iqr"]))
        self.jitter_var.set(fmt_ms(st["jitter"]))

    def _draw_live_chart(self):
        c = self.live_chart
        c.delete("all")
        w = max(c.winfo_width(), 100)
        h = max(c.winfo_height(), 100)
        vals = [s["latency_ms"] for s in self.current_samples[-100:]]
        if not vals:
            c.create_text(w / 2, h / 2, text="Nessun campione", anchor="center")
            return

        st = compute_stats(vals)
        vmin = min(vals)
        vmax = max(vals)
        if vmax - vmin < 0.001:
            vmax = vmin + 1.0

        pad = 28
        pw = w - 2 * pad
        ph = h - 2 * pad

        c.create_line(pad, pad, pad, h - pad)
        c.create_line(pad, h - pad, w - pad, h - pad)

        points = []
        denom = max(len(vals) - 1, 1)
        for i, val in enumerate(vals):
            x = pad + (i / denom) * pw
            y = pad + (1 - (val - vmin) / (vmax - vmin)) * ph
            points.extend((x, y))
        if len(points) >= 4:
            c.create_line(*points, width=2)

        def y_for(value):
            return pad + (1 - (value - vmin) / (vmax - vmin)) * ph

        # Median and P95 reference lines use dashed patterns, no fixed colors.
        med_y = y_for(st["median"])
        p95_y = y_for(st["p95"])
        c.create_line(pad, med_y, w - pad, med_y, dash=(6, 4))
        c.create_line(pad, p95_y, w - pad, p95_y, dash=(2, 4))
        c.create_text(pad + 4, med_y - 4, text=f"MED {st['median']:.2f}", anchor="sw")
        c.create_text(w - pad - 4, p95_y - 4, text=f"P95 {st['p95']:.2f}", anchor="se")
        c.create_text(pad + 4, pad + 4, text=f"{vmax:.2f} ms", anchor="nw")
        c.create_text(pad + 4, h - pad - 4, text=f"{vmin:.2f} ms", anchor="sw")

    # ------------------------------------------------------------------
    # Persistence / exports
    # ------------------------------------------------------------------

    def export_current_csv(self):
        if not self.current_samples:
            messagebox.showinfo("CSV", "Non ci sono campioni nella run corrente.")
            return
        try:
            metadata = self._current_metadata()
        except ValueError:
            metadata = None
        default = f"latency_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile=default,
            filetypes=[("CSV", "*.csv"), ("Tutti i file", "*.*")]
        )
        if not path:
            return
        self._write_csv(path, metadata, self.current_samples)

    def _write_csv(self, path, metadata, samples):
        with open(path, "w", newline="", encoding="utf-8") as f:
            fields = [
                "seq", "timestamp", "latency_ms", "device", "run_name",
                "polling_rate_hz", "connection_mode", "mouse_firmware",
                "calibration_us", "light_start", "light_end", "notes"
            ]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()

            device_name = ""
            if metadata:
                d = self.db.get_device(metadata["device_id"])
                device_name = d["name"] if d else ""

            for i, sample in enumerate(samples):
                writer.writerow({
                    "seq": i + 1,
                    "timestamp": sample.get("timestamp", ""),
                    "latency_ms": f'{float(sample["latency_ms"]):.3f}',
                    "device": device_name,
                    "run_name": metadata["name"] if metadata else "",
                    "polling_rate_hz": metadata.get("polling_rate_hz", "") if metadata else "",
                    "connection_mode": metadata.get("connection_mode", "") if metadata else "",
                    "mouse_firmware": metadata.get("mouse_firmware", "") if metadata else "",
                    "calibration_us": metadata.get("calibration_us", "") if metadata else "",
                    "light_start": metadata.get("light_start", "") if metadata else "",
                    "light_end": metadata.get("light_end", "") if metadata else "",
                    "notes": metadata.get("notes", "") if metadata else "",
                })
        self.log_line(f"CSV esportato: {path}")

    def refresh_sessions(self):
        runs = self.db.list_runs()

        for tree in (self.sessions_tree, self.compare_tree):
            for item in tree.get_children():
                tree.delete(item)

        for run in runs:
            samples = self.db.get_samples(run["id"])
            vals = [row["latency_ms"] for row in samples]
            st = compute_stats(vals)
            dt = run["started_at"].replace("T", " ")[:16]
            poll = run["polling_rate_hz"] if run["polling_rate_hz"] is not None else ""

            self.sessions_tree.insert(
                "", "end", iid=str(run["id"]),
                values=(
                    dt, run["device_name"], run["name"], poll, run["connection_mode"],
                    st["n"], fmt_ms(st["median"]), fmt_ms(st["mean"]),
                    fmt_ms(st["p95"]), fmt_ms(st["p99"]), fmt_ms(st["stdev"]),
                    run["calibration_us"],
                )
            )
            self.compare_tree.insert(
                "", "end", iid=str(run["id"]),
                values=(dt, run["device_name"], run["name"], poll, st["n"], fmt_ms(st["median"]))
            )

    def _show_session_details(self):
        sel = self.sessions_tree.selection()
        if not sel:
            return
        run = self.db.get_run(int(sel[0]))
        samples = self.db.get_samples(int(sel[0]))
        st = compute_stats([s["latency_ms"] for s in samples])
        text = (
            f"Dispositivo: {run['device_name']}\n"
            f"Run: {run['name']} | Polling: {run['polling_rate_hz'] or '—'} Hz | "
            f"Connessione: {run['connection_mode'] or '—'} | Firmware mouse: {run['mouse_firmware'] or '—'}\n"
            f"N={st['n']}  Media={fmt_ms(st['mean'])} ms  Mediana={fmt_ms(st['median'])} ms  "
            f"P95={fmt_ms(st['p95'])} ms  P99={fmt_ms(st['p99'])} ms  "
            f"Dev.Std={fmt_ms(st['stdev'])} ms  IQR={fmt_ms(st['iqr'])} ms  "
            f"Jitter={fmt_ms(st['jitter'])} ms\n"
            f"Calibrazione={run['calibration_us']} µs | Luce start={run['light_start']} | Luce end={run['light_end']}\n"
            f"Note: {run['notes'] or '—'}"
        )
        self.session_details.configure(state="normal")
        self.session_details.delete("1.0", "end")
        self.session_details.insert("1.0", text)
        self.session_details.configure(state="disabled")

    def delete_selected_session(self):
        sel = self.sessions_tree.selection()
        if not sel:
            return
        if not messagebox.askyesno("Elimina sessione", f"Eliminare {len(sel)} sessione/i selezionata/e?"):
            return
        for iid in sel:
            self.db.delete_run(int(iid))
        self.refresh_sessions()

    def export_selected_session_csv(self):
        sel = self.sessions_tree.selection()
        if len(sel) != 1:
            messagebox.showinfo("CSV", "Seleziona una sola sessione.")
            return
        run_id = int(sel[0])
        run = self.db.get_run(run_id)
        samples = self.db.get_samples(run_id)
        default = f"{run['device_name']}_{run['name']}.csv".replace(" ", "_").replace("/", "-")
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile=default,
            filetypes=[("CSV", "*.csv"), ("Tutti i file", "*.*")]
        )
        if not path:
            return
        metadata = {
            "device_id": run["device_id"], "name": run["name"],
            "polling_rate_hz": run["polling_rate_hz"], "connection_mode": run["connection_mode"],
            "mouse_firmware": run["mouse_firmware"], "calibration_us": run["calibration_us"],
            "light_start": run["light_start"], "light_end": run["light_end"], "notes": run["notes"],
        }
        smp = [{"latency_ms": s["latency_ms"], "timestamp": s["timestamp"]} for s in samples]
        self._write_csv(path, metadata, smp)

    def compare_selected_from_sessions(self):
        sel = self.sessions_tree.selection()
        if not sel:
            return
        self.notebook.select(self.compare_tab)
        self.compare_tree.selection_set(*sel)
        self.compare_tree.see(sel[0])
        self.plot_compare()

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def plot_compare(self):
        selected = self.compare_tree.selection()
        if not selected:
            self.compare_status_var.set("Seleziona almeno una sessione.")
            return

        series = []
        for iid in selected:
            run = self.db.get_run(int(iid))
            samples = self.db.get_samples(int(iid))
            vals = [s["latency_ms"] for s in samples]
            if not vals:
                continue
            label_bits = [run["device_name"], run["name"]]
            if run["polling_rate_hz"]:
                label_bits.append(f"{run['polling_rate_hz']} Hz")
            label = " — ".join(label_bits)
            series.append((run, label, vals, compute_stats(vals)))

        if not series:
            self.compare_status_var.set("Le sessioni selezionate non contengono campioni.")
            return

        for item in self.compare_stats_tree.get_children():
            self.compare_stats_tree.delete(item)

        for run, label, vals, st in series:
            self.compare_stats_tree.insert(
                "", "end",
                values=(
                    label, st["n"], fmt_ms(st["mean"]), fmt_ms(st["median"]),
                    fmt_ms(st["p95"]), fmt_ms(st["p99"]), fmt_ms(st["stdev"]),
                    fmt_ms(st["min"]), fmt_ms(st["max"]), fmt_ms(st["jitter"]),
                ),
            )

        if not MATPLOTLIB_AVAILABLE:
            self.compare_status_var.set("Statistiche aggiornate. Installa matplotlib per i grafici.")
            return

        ax = self.compare_ax
        ax.clear()
        chart_type = self.compare_chart_type.get()

        if chart_type == "Campioni":
            styles = ["-", "--", "-.", ":"]
            for i, (_run, label, vals, _st) in enumerate(series):
                xs = list(range(1, len(vals) + 1))
                ax.plot(xs, vals, linestyle=styles[i % len(styles)], marker=".", label=label)
            ax.set_xlabel("Campione")
            ax.set_ylabel("Latenza (ms)")
            ax.set_title("Campioni grezzi")

        elif chart_type == "Box plot":
            ax.boxplot([vals for _run, _label, vals, _st in series],
                       tick_labels=[label for _run, label, _vals, _st in series],
                       showmeans=True)
            ax.set_ylabel("Latenza (ms)")
            ax.set_title("Distribuzione — box plot")
            ax.tick_params(axis="x", labelrotation=20)

        elif chart_type == "ECDF":
            for _run, label, vals, _st in series:
                ordered = sorted(vals)
                ys = [(i + 1) / len(ordered) for i in range(len(ordered))]
                ax.step(ordered, ys, where="post", label=label)
            ax.set_xlabel("Latenza (ms)")
            ax.set_ylabel("Quota campioni ≤ x")
            ax.set_title("ECDF")

        elif chart_type == "Istogramma":
            for _run, label, vals, _st in series:
                ax.hist(vals, bins="auto", histtype="step", linewidth=1.5, label=label)
            ax.set_xlabel("Latenza (ms)")
            ax.set_ylabel("Conteggio")
            ax.set_title("Istogramma")

        ax.grid(True, alpha=0.25)
        if chart_type != "Box plot":
            ax.legend(fontsize=8)
        self.compare_figure.tight_layout()
        self.compare_canvas.draw()

        if len(series) >= 2:
            base = series[0]
            med0 = base[3]["median"]
            p950 = base[3]["p95"]
            comparisons = []
            for _run, label, _vals, st in series[1:]:
                comparisons.append(
                    f"{label}: Δmediana {st['median'] - med0:+.3f} ms, "
                    f"ΔP95 {st['p95'] - p950:+.3f} ms"
                )
            self.compare_status_var.set(
                "Riferimento: " + base[1] + "\n" + "\n".join(comparisons)
            )
        else:
            self.compare_status_var.set("Una sessione selezionata.")

    # ------------------------------------------------------------------
    # Event processing
    # ------------------------------------------------------------------

    def _process_events(self):
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if kind == "latency":
                self.current_samples.append(payload)
                self.session_saved = False
                self._update_live_stats()
                self._draw_live_chart()
                self.state_var.set("READY")
                self.log_line(f"LAT {payload['latency_ms']:.3f} ms")

                if self.test_mode:
                    count = len(self.current_samples) - self.test_start_sample_index
                    target = max(1, int(self.target_samples_var.get()))
                    if count >= target:
                        self.test_complete = True
                        self._set_overlay_mode("complete")
                else:
                    self.root.after(150, lambda: self.send_command("L") if self.connected else None)

            elif kind == "stats":
                self.cal_var.set(f"{payload['calib']} µs")

            elif kind == "cal_ok":
                self.cal_var.set(f"{payload['calib']} µs")
                self.state_var.set("READY")
                self.log_line(
                    f"Calibrazione OK: {payload['calib']} µs "
                    f"({payload['samples']} campioni, RT medio {payload['avg_rt']} µs)"
                )

            elif kind == "cal_fail":
                self.state_var.set("CAL FAIL")
                self.log_line(payload)

            elif kind == "light":
                self.current_light = payload
                self.light_var.set(str(payload))
                if self.light_start is None and not self.test_mode:
                    self.light_start = payload
                if self.awaiting_light_end:
                    self.light_end = payload
                    self.awaiting_light_end = False

            elif kind == "reset":
                self._clear_current_samples()
                self.state_var.set("READY")
                self.log_line("Statistiche azzerate")

            elif kind == "skip":
                try:
                    self.skipped_var.set(str(int(self.skipped_var.get()) + 1))
                except ValueError:
                    self.skipped_var.set("1")
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

    def _refresh_overlay(self):
        if not self.overlay:
            return
        try:
            vals = [s["latency_ms"] for s in self.current_samples]
            st = compute_stats(vals)
            self.overlay_last_label.configure(text=self.last_var.get())
            self.overlay_median_label.configure(text=f"MED {fmt_ms(st['median'])} ms")
            self.overlay_p95_label.configure(text=f"P95 {fmt_ms(st['p95'])} ms")
            count = max(0, len(self.current_samples) - self.test_start_sample_index)
            target = max(1, int(self.target_samples_var.get()))
            self.overlay_n_label.configure(text=f"N {count} / {target}")
        except tk.TclError:
            pass

    def _idle_light_poll(self):
        if self.running and self.connected and not self.test_mode and not self.calibrating:
            self.send_command("L")
        if self.running:
            self.root.after(1000, self._idle_light_poll)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def close(self):
        if self.current_samples and not self.session_saved:
            if not messagebox.askyesno(
                "Chiudi",
                "La run corrente contiene campioni non salvati.\nChiudere comunque?",
            ):
                return
        self.running = False
        if self.test_mode:
            self.exit_test_mode()
        self.disconnect()
        try:
            self.mouse_listener.stop()
        except Exception:
            pass
        try:
            self.db.close()
        except Exception:
            pass
        self.root.after(50, self.root.destroy)


def main():
    root = tk.Tk()
    app = LatencyDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
