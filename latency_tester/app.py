"""Application shell: owns the services, the state and the event pump.

Threading rule: only this module's ``_pump`` touches tkinter.  The serial
reader thread and the mouse callback communicate exclusively through the event
queue in :mod:`latency_tester.serial_service`.
"""

from __future__ import annotations

import logging
import queue
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from . import (SUPPORTED_FIRMWARE, __version__, export, protocol,
               serial_service, theme)
from .database import LatencyDB
from .demo import PORT_NAME as DEMO_PORT
from .demo import DemoDevice
from .i18n import translator as tr
from .settings import Settings
from .stats import compute_stats, fmt_ms

log = logging.getLogger(__name__)

PUMP_INTERVAL_MS = 50
LIGHT_POLL_MS = 1000
RECONNECT_INTERVAL_MS = 3000

class LatencyTesterApp:
    def __init__(self, root: tk.Tk):
        self.root = root

        self.settings = Settings()
        tr.set_language(self.settings.get("language"))
        self.palette = theme.resolve(self.settings.get("theme"))

        self.db = LatencyDB(self.settings.db_path)
        if not self.db.list_devices():
            self.db.create_device(name="Mouse")

        self.serial = serial_service.SerialService()
        self.serial.accept_trig = self._accept_trig
        self.mouse = serial_service.MouseWatcher(self.serial.clicks)
        self.mouse.start()

        self.running = True
        self.test_mode = False
        self.test_complete = False
        self.overlay = None
        self._reconnect_port: str | None = None

        # Current, unsaved run.
        self.current_samples: list[dict] = []
        self.session_saved = False
        self.run_started_at: str | None = None
        self.run_ended_at: str | None = None
        self.test_start_index = 0
        self.current_light: int | None = None
        self.light_start: int | None = None
        self.light_end: int | None = None
        self._awaiting_light_end = False

        self._build_vars()
        self._build_shell()

        self.auto_select_device()
        self.refresh_ports(auto_connect=bool(self.settings.get("auto_connect")))
        # Tracked so shutdown can cancel them; a callback firing after the
        # interpreter is gone raises "invalid command name" out of Tk itself.
        self._timers = {
            "pump": self.root.after(PUMP_INTERVAL_MS, self._pump),
            "light": self.root.after(LIGHT_POLL_MS, self._poll_light),
            "watch": self.root.after(RECONNECT_INTERVAL_MS, self._watch_connection),
        }
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    # ================================================================ state ==
    def _build_vars(self) -> None:
        s = self.settings
        self.port_var = tk.StringVar()
        self.connection_var = tk.StringVar(value=tr("conn.disconnected"))
        self.firmware_var = tk.StringVar(value="—")
        self.state_var = tk.StringVar(value="READY")
        self.cal_var = tk.StringVar(value="0 µs")
        self.light_var = tk.StringVar(value="—")
        self.skipped_var = tk.StringVar(value="0")
        # Firmware v1.4 button test: counters make "10 presses -> 10 events"
        # verifiable at a glance.
        self.button_counts = {1: 0, 2: 0}
        self.button_vars = {1: tk.StringVar(value="0"), 2: tk.StringVar(value="0")}

        self.metric_vars = {
            key: tk.StringVar(value="—")
            for key in ("last", "mean", "median", "min", "max", "stdev",
                        "p5", "p95", "p99", "iqr", "mad", "jitter")
        }
        self.metric_vars["n"] = tk.StringVar(value="0")
        self.outlier_var = tk.StringVar(value="")

        self.device_var = tk.StringVar()
        self.run_name_var = tk.StringVar()
        self.polling_var = tk.StringVar(value=str(s.get("last_polling_rate")))
        self.mode_var = tk.StringVar(value=str(s.get("last_connection_mode")))
        self.dpi_var = tk.StringVar(value=str(s.get("last_dpi") or ""))
        self.mouse_fw_var = tk.StringVar()
        self.debounce_var = tk.StringVar()
        self.notes_var = tk.StringVar()
        self.target_var = tk.IntVar(value=int(s.get("target_samples") or 50))
        self.auto_reset_var = tk.BooleanVar(value=bool(s.get("auto_reset_on_test")))

        self.language_var = tk.StringVar(value=tr.language)
        self.theme_var = tk.StringVar(value=str(s.get("theme")))
        self.auto_connect_var = tk.BooleanVar(value=bool(s.get("auto_connect")))

        self.device_name_to_id: dict[str, int] = {}

    # ================================================================ shell ==
    def _build_shell(self) -> None:
        theme.apply(self.root, self.palette)
        self.root.title(f"{tr('app.title')} v{__version__}")
        geometry = str(self.settings.get("window_geometry") or "")
        self.root.geometry(geometry if geometry else "1380x900")
        self.root.minsize(1024, 680)

        self.shell = ttk.Frame(self.root, padding=12)
        self.shell.pack(fill="both", expand=True)

        self._build_connection_bar(self.shell)

        self.demo_banner = ttk.Label(self.shell, text=tr("app.demo_banner"),
                                     style="Demo.TLabel")
        # packed/unpacked by _update_connection_labels

        self.notebook = ttk.Notebook(self.shell)
        self.notebook.pack(fill="both", expand=True, pady=(10, 0))

        from .views.compare import CompareView
        from .views.devices import DevicesView
        from .views.live import LiveView
        from .views.preferences import PreferencesView
        from .views.sessions import SessionsView

        self.live_view = LiveView(self.notebook, self)
        self.sessions_view = SessionsView(self.notebook, self)
        self.compare_view = CompareView(self.notebook, self)
        self.devices_view = DevicesView(self.notebook, self)
        self.preferences_view = PreferencesView(self.notebook, self)

        self.notebook.add(self.live_view, text=tr("tab.live"))
        self.notebook.add(self.sessions_view, text=tr("tab.sessions"))
        self.notebook.add(self.compare_view, text=tr("tab.compare"))
        self.notebook.add(self.devices_view, text=tr("tab.devices"))
        self.notebook.add(self.preferences_view, text=tr("tab.settings"))

        self.refresh_devices()
        self.refresh_sessions()
        self._update_metrics()
        self._update_connection_labels()

    def _build_connection_bar(self, parent: ttk.Frame) -> None:
        bar = ttk.LabelFrame(parent, text=f" {tr('conn.title')} ", padding=10)
        bar.pack(fill="x")

        ttk.Label(bar, text=tr("conn.port")).pack(side="left")
        self.port_combo = ttk.Combobox(bar, textvariable=self.port_var,
                                       width=34, state="readonly")
        self.port_combo.pack(side="left", padx=(8, 8))
        ttk.Button(bar, text=tr("conn.refresh"),
                   command=lambda: self.refresh_ports(False)).pack(side="left", padx=3)
        self.connect_btn = ttk.Button(bar, text=tr("conn.connect"),
                                      command=self.toggle_connection,
                                      style="Accent.TButton")
        self.connect_btn.pack(side="left", padx=3)

        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=14)
        ttk.Label(bar, text=tr("conn.status")).pack(side="left", padx=(0, 6))
        self.connection_label = ttk.Label(bar, textvariable=self.connection_var,
                                          style="Error.TLabel")
        self.connection_label.pack(side="left")
        ttk.Label(bar, text=tr("conn.firmware"),
                  style="Muted.TLabel").pack(side="left", padx=(16, 6))
        ttk.Label(bar, textvariable=self.firmware_var).pack(side="left")

        ttk.Label(bar, text=f"{tr('conn.archive')}: {self.db.path}",
                  style="Muted.TLabel").pack(side="right")

    def rebuild_ui(self) -> None:
        """Re-create the interface after a theme or language change."""
        if self.test_mode:
            return
        self.settings.save()
        self.palette = theme.resolve(self.settings.get("theme"))
        self.shell.destroy()
        self._build_shell()
        self.live_view.set_samples(self._latencies())
        self._update_metrics()

    # =========================================================== connection ==
    def refresh_ports(self, auto_connect: bool = False) -> None:
        ports = serial_service.list_ports()
        labels = [p["label"] for p in ports]
        labels.append(DEMO_PORT)
        self.port_combo["values"] = labels

        detected = next((p["label"] for p in ports if p["is_teensy"]), None)
        if detected:
            self.port_var.set(detected)
        elif not self.port_var.get() and labels:
            self.port_var.set(labels[0])

        if auto_connect and detected and not self.serial.connected:
            self.root.after(250, self.connect)

    def _selected_port(self) -> str:
        value = self.port_var.get().strip()
        return value.split(" — ", 1)[0].strip()

    def toggle_connection(self) -> None:
        self.disconnect() if self.serial.connected else self.connect()

    def connect(self) -> None:
        if self.serial.connected:
            return
        device = self._selected_port()
        if not device:
            messagebox.showwarning(tr("conn.title"), tr("conn.no_port"))
            return

        if device == DEMO_PORT:
            self.serial.attach(DemoDevice(), DEMO_PORT, is_demo=True)
            self.log(tr("log.demo_on"))
        else:
            try:
                transport = serial_service.open_serial(device)
            except Exception as exc:
                messagebox.showerror(tr("conn.open_failed_title"),
                                     tr("conn.open_failed", error=exc))
                return
            self.serial.attach(transport, device)
            self.log(tr("log.connected", port=device))
            self._reconnect_port = device

        self._update_connection_labels()
        for delay, command in ((400, protocol.CMD_VERSION),
                               (650, protocol.CMD_STATS),
                               (900, protocol.CMD_LIGHT)):
            self.root.after(delay, lambda c=command: self.serial.send(c))

    def disconnect(self, keep_retrying: bool = False) -> None:
        was_demo = self.serial.is_demo
        self.serial.close()
        if not keep_retrying:
            self._reconnect_port = None
        if was_demo:
            self.log(tr("log.demo_off"))
        self.firmware_var.set("—")
        self._update_connection_labels()

    def _update_connection_labels(self) -> None:
        connected = self.serial.connected
        if connected and self.serial.is_demo:
            self.connection_var.set(tr("conn.demo"))
            self.connection_label.configure(style="Warn.TLabel")
        elif connected:
            self.connection_var.set(f"{tr('conn.connected')} — {self.serial.port_name}")
            self.connection_label.configure(style="Ok.TLabel")
        else:
            self.connection_var.set(tr("conn.disconnected"))
            self.connection_label.configure(style="Error.TLabel")

        self.connect_btn.configure(
            text=tr("conn.disconnect") if connected else tr("conn.connect"))

        if self.is_demo and not self.demo_banner.winfo_ismapped():
            self.demo_banner.pack(fill="x", pady=(10, 0), before=self.notebook)
        elif not self.is_demo and self.demo_banner.winfo_ismapped():
            self.demo_banner.pack_forget()

        self.live_view.set_connected(connected)

    def _watch_connection(self) -> None:
        """Reopen a port that came back after a cable hiccup.

        Runs on the Tk thread, so it can never race the reader thread; the
        current run's samples are kept either way.
        """
        if (self.running and self._reconnect_port and not self.serial.connected
                and self.auto_connect_var.get()):
            available = {p["device"] for p in serial_service.list_ports()}
            if self._reconnect_port in available:
                try:
                    transport = serial_service.open_serial(self._reconnect_port)
                except Exception:
                    transport = None
                if transport is not None:
                    self.serial.attach(transport, self._reconnect_port)
                    self.log(tr("conn.reconnected", port=self._reconnect_port))
                    self._update_connection_labels()
                    self.serial.send(protocol.CMD_VERSION)
        if self.running:
            self._timers["watch"] = self.root.after(
                RECONNECT_INTERVAL_MS, self._watch_connection)

    @property
    def is_demo(self) -> bool:
        return self.serial.connected and self.serial.is_demo

    # ============================================================== commands ==
    def send(self, command: str) -> bool:
        return self.serial.send(command)

    def calibrate(self) -> None:
        if not self.serial.connected or self.serial.calibrating or self.test_mode:
            return
        self.state_var.set("CALIBRATING")
        self.log(tr("log.calibrating"))
        if self.serial.start_calibration():
            self.root.after(800, self._calibration_ready)

    def _calibration_ready(self) -> None:
        if self.serial.connected and self.serial.calibrating:
            self.serial.send_calibration_ready()

    def reset_stats(self) -> None:
        if self.serial.connected and not self.test_mode:
            self.send(protocol.CMD_RESET)

    # ============================================================= test mode ==
    def _accept_trig(self) -> bool:
        """Called from the serial thread: refuse new samples past the target."""
        return not (self.test_mode and self.test_complete)

    def enter_test_mode(self) -> None:
        if not self.serial.connected or self.overlay is not None:
            return

        target = self.target_samples()
        if not self.run_name_var.get().strip():
            self.run_name_var.set(self.generate_run_name())

        self.test_mode = True
        self.test_complete = False
        self.run_started_at = datetime.now().isoformat(timespec="seconds")
        self.run_ended_at = None
        self.light_start = self.current_light
        self.light_end = None
        self._awaiting_light_end = False
        self.session_saved = False
        self.test_start_index = 0 if self.auto_reset_var.get() else len(self.current_samples)

        from .views.testmode import TestModeOverlay
        self.overlay = TestModeOverlay(self.root, self, target)

        # Same ordering as the verified v2 flow: clear the firmware counters
        # first, then freeze the OLED.
        if self.auto_reset_var.get():
            self.send(protocol.CMD_RESET)
            self.root.after(
                180,
                lambda: self.send(protocol.CMD_TEST_MODE_ON) if self.serial.connected else None)
        else:
            self.send(protocol.CMD_TEST_MODE_ON)

    def exit_test_mode(self) -> None:
        was_active = self.test_mode
        self.test_mode = False
        self.test_complete = False
        self.run_ended_at = datetime.now().isoformat(timespec="seconds")

        if was_active and self.serial.connected:
            self.send(protocol.CMD_TEST_MODE_OFF)

        if self.overlay is not None:
            self.overlay.close()
            self.overlay = None

        if self.serial.connected:
            self._awaiting_light_end = True
            self.root.after(200, lambda: self.send(protocol.CMD_LIGHT))

    def target_samples(self) -> int:
        try:
            return max(1, int(self.target_var.get()))
        except (tk.TclError, ValueError):
            self.target_var.set(50)
            return 50

    def test_sample_count(self) -> int:
        return max(0, len(self.current_samples) - self.test_start_index)

    # ================================================================== runs ==
    def generate_run_name(self) -> str:
        bits = []
        if self.polling_var.get().strip():
            bits.append(f"{self.polling_var.get().strip()} Hz")
        if self.mode_var.get().strip():
            bits.append(self.mode_var.get().strip())
        bits.append(datetime.now().strftime("%Y-%m-%d %H-%M"))
        return " - ".join(bits)

    def current_metadata(self) -> dict:
        device_name = self.device_var.get().strip()
        device_id = self.device_name_to_id.get(device_name)
        if not device_id:
            raise ValueError(tr("dlg.select_device"))

        name = self.run_name_var.get().strip() or self.generate_run_name()
        self.run_name_var.set(name)

        return {
            "device_id": device_id,
            "name": name,
            "polling_rate_hz": _as_int(self.polling_var.get()),
            "connection_mode": self.mode_var.get().strip(),
            "dpi": _as_int(self.dpi_var.get()),
            "mouse_firmware": self.mouse_fw_var.get().strip(),
            "debounce_setting": self.debounce_var.get().strip(),
            "notes": self.live_view.get_notes(),
            "target_samples": self.target_samples(),
            "calibration_us": self.calibration_us(),
            "teensy_firmware": self.serial.firmware_version or "",
            "is_demo": 1 if self.is_demo else 0,
            "light_start": self.light_start,
            "light_end": self.light_end if self.light_end is not None else self.current_light,
            "started_at": self.run_started_at or datetime.now().isoformat(timespec="seconds"),
            "ended_at": self.run_ended_at or datetime.now().isoformat(timespec="seconds"),
        }

    def calibration_us(self) -> int:
        try:
            return int(float(self.cal_var.get().replace("µs", "").strip()))
        except ValueError:
            return 0

    def save_current_run(self) -> None:
        if self.test_mode:
            messagebox.showinfo(tr("dlg.save_session"), tr("dlg.exit_test_first"))
            return
        if not self.current_samples:
            messagebox.showinfo(tr("dlg.save_session"), tr("dlg.no_samples"))
            return
        if self.session_saved:
            messagebox.showinfo(tr("dlg.save_session"), tr("dlg.already_saved"))
            return
        try:
            metadata = self.current_metadata()
        except ValueError as exc:
            messagebox.showwarning(tr("dlg.save_session"), str(exc))
            return

        run_id = self.db.save_run(metadata, self.current_samples)
        self.session_saved = True
        self.log(tr("log.saved", id=run_id))
        self.refresh_sessions()
        self.remember_last_run_settings()
        messagebox.showinfo(tr("dlg.save_session"), tr("dlg.saved", id=run_id))

    def new_run(self) -> None:
        if self.test_mode:
            return
        if self.current_samples and not self.session_saved:
            if not messagebox.askyesno(tr("dlg.new_run"), tr("dlg.discard_confirm")):
                return
        if self.serial.connected:
            self.send(protocol.CMD_RESET)
        else:
            self.clear_samples()
        self.run_name_var.set("")
        self.run_started_at = None
        self.run_ended_at = None
        self.light_start = self.current_light
        self.light_end = None
        self.session_saved = False
        self.remember_last_run_settings()

    def load_template(self, run) -> None:
        """Fill the live configuration from a stored run, samples excluded."""
        device = self.db.get_device(run["device_id"])
        if device:
            self.device_var.set(device["name"])
        self.run_name_var.set(f"{run['name']} (copy)")
        self.polling_var.set(str(run["polling_rate_hz"] or ""))
        self.mode_var.set(run["connection_mode"] or "")
        self.dpi_var.set(str(run["dpi"] or ""))
        self.mouse_fw_var.set(run["mouse_firmware"] or "")
        self.debounce_var.set(run["debounce_setting"] or "")
        self.target_var.set(int(run["target_samples"] or 50))
        self.live_view.set_notes(run["notes"] or "")
        self.notebook.select(self.live_view)
        messagebox.showinfo(tr("tab.sessions"), tr("sessions.template_loaded"))

    def remember_last_run_settings(self) -> None:
        self.settings.update(
            last_polling_rate=self.polling_var.get().strip(),
            last_connection_mode=self.mode_var.get().strip(),
            last_dpi=self.dpi_var.get().strip(),
            target_samples=self.target_samples(),
            auto_reset_on_test=bool(self.auto_reset_var.get()),
            last_device_id=self.device_name_to_id.get(self.device_var.get().strip()),
        )
        self.settings.save()

    def export_current_csv(self) -> None:
        if not self.current_samples:
            messagebox.showinfo(tr("dlg.csv"), tr("dlg.csv_empty"))
            return
        try:
            metadata = self.current_metadata()
        except ValueError:
            metadata = {"name": self.run_name_var.get()}
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"latency_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            filetypes=[(tr("dlg.csv"), "*.csv"), (tr("dlg.all_files"), "*.*")],
        )
        if not path:
            return
        export.write_csv(path, metadata, self.current_samples,
                         device_name=self.device_var.get().strip())
        self.log(tr("log.csv", path=path))

    # =============================================================== refresh ==
    def refresh_devices(self) -> None:
        devices = self.db.list_devices()
        if not devices:
            self.db.create_device(name="Mouse")
            devices = self.db.list_devices()

        previous = self.device_var.get()
        self.device_name_to_id = {row["name"]: row["id"] for row in devices}
        names = list(self.device_name_to_id)
        self.live_view.set_device_choices(names)

        remembered = self.settings.get("last_device_id")
        by_id = {row["id"]: row["name"] for row in devices}
        if previous in names:
            self.device_var.set(previous)
        elif remembered in by_id:
            self.device_var.set(by_id[remembered])
        elif names:
            self.device_var.set(names[0])

        self.devices_view.reload(devices)

    def auto_select_device(self) -> None:
        """Pick the profile saved for the mouse that is physically connected.

        Only ever *selects* an existing profile; it never creates or edits one.
        """
        try:
            from . import devices as hardware

            for mouse in hardware.detect_mice():
                row = self.db.find_device_by_hardware_id(mouse.hardware_id)
                if row is not None:
                    self.device_var.set(row["name"])
                    self.log(tr("devices.matched", name=row["name"]))
                    return
        except Exception:
            log.debug("device auto-selection failed", exc_info=True)

    def refresh_sessions(self) -> None:
        self.sessions_view.reload()
        self.compare_view.reload()

    def _latencies(self) -> list[float]:
        return [s["latency_ms"] for s in self.current_samples]

    def clear_samples(self) -> None:
        self.current_samples.clear()
        self.session_saved = False
        self._update_metrics()

    def _update_metrics(self) -> None:
        values = self._latencies()
        stats = compute_stats(values)
        self.metric_vars["n"].set(str(stats["n"]))
        if not values:
            for key, var in self.metric_vars.items():
                if key != "n":
                    var.set("—")
            self.outlier_var.set("")
        else:
            self.metric_vars["last"].set(fmt_ms(values[-1]))
            for key in ("mean", "median", "min", "max", "stdev",
                        "p5", "p95", "p99", "iqr", "mad", "jitter"):
                self.metric_vars[key].set(fmt_ms(stats[key]))
            from .stats import outlier_indices
            count = len(outlier_indices(values))
            self.outlier_var.set(tr("live.outliers", count=count) if count else "")
        self.live_view.set_samples(values)

    def log(self, message: str) -> None:
        self.live_view.log(f"[{datetime.now():%H:%M:%S}] {message}")

    # ============================================================ event pump ==
    def _pump(self) -> None:
        while True:
            try:
                event = self.serial.events.get_nowait()
            except queue.Empty:
                break
            try:
                self._handle(event)
            except Exception:
                log.exception("error while handling %s", event.kind)
        if self.overlay is not None:
            self.overlay.refresh()
        if self.running:
            self._timers["pump"] = self.root.after(PUMP_INTERVAL_MS, self._pump)

    def _handle(self, event: protocol.Event) -> None:
        kind, payload = event.kind, event.payload

        if kind == "latency":
            self.current_samples.append({
                "latency_ms": payload["latency_ms"],
                "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            })
            self.session_saved = False
            self._update_metrics()
            self.state_var.set("READY")
            self.log(tr("log.latency", value=f"{payload['latency_ms']:.3f}"))

            if self.test_mode:
                if self.test_sample_count() >= self.target_samples():
                    self.test_complete = True
                    if self.overlay:
                        self.overlay.set_mode("complete")
            else:
                self.root.after(
                    150, lambda: self.send(protocol.CMD_LIGHT) if self.serial.connected else None)

        elif kind == "stats":
            self.cal_var.set(f"{payload['calib']} µs")

        elif kind == "cal_ok":
            self.cal_var.set(f"{payload['calib']} µs")
            self.state_var.set("READY")
            self.log(tr("log.calibrated", calib=payload["calib"],
                        samples=payload["samples"], avg=payload["avg_rt"]))

        elif kind == "cal_fail":
            self.state_var.set("CAL FAIL")
            self.log(tr("log.calib_failed"))

        elif kind == "light":
            self.current_light = payload
            self.light_var.set(str(payload))
            if self.light_start is None and not self.test_mode:
                self.light_start = payload
            if self._awaiting_light_end:
                self.light_end = payload
                self._awaiting_light_end = False

        elif kind == "reset":
            self.clear_samples()
            self.state_var.set("READY")
            self.log(tr("log.reset"))

        elif kind == "skip_oled":
            self.skipped_var.set(str(_as_int(self.skipped_var.get(), 0) + 1))
            self.log(tr("log.skip"))
            if self.test_mode and not self.test_complete and self.overlay:
                self.overlay.set_mode("wait")

        elif kind == "armed":
            self.state_var.set("ARMED")
            if self.test_mode and not self.test_complete and self.overlay:
                self.overlay.set_mode("armed")

        elif kind == "rearm":
            self.state_var.set("REARM")
            if self.test_mode and not self.test_complete and self.overlay:
                self.overlay.set_mode("wait")

        elif kind == "trig":
            self.state_var.set("TRIG")
            if self.test_mode and not self.test_complete and self.overlay:
                self.overlay.set_mode("wait")

        elif kind == "trig_unmatched":
            self.log(tr("log.trig_unmatched"))

        elif kind == "testmode_on":
            self.state_var.set("TEST MODE")
            self.log(tr("log.testmode_on"))

        elif kind == "testmode_off":
            self.state_var.set("READY")
            self.log(tr("log.testmode_off"))

        elif kind == "abort":
            self.log(tr("log.abort"))

        elif kind == "drop":
            self.log(tr("log.drop", value=fmt_ms(payload)))

        elif kind == "button":
            # TEST PHASE: logged and counted only. No action is bound to the
            # buttons until the hardware has been verified.
            index = payload["index"]
            if index in self.button_counts:
                self.button_counts[index] += 1
                self.button_vars[index].set(str(self.button_counts[index]))
            self.log(payload["token"])

        elif kind == "banner":
            self.firmware_var.set(payload)
            if payload and payload not in SUPPORTED_FIRMWARE and not self.serial.is_demo:
                self.log(tr("conn.firmware_mismatch", found=payload,
                            expected="/".join(SUPPORTED_FIRMWARE)))

        elif kind == "ready":
            self.state_var.set("READY")

        elif kind == "timeout":
            self.state_var.set("TIMEOUT")
            self.log(payload)

        elif kind == "serial_error":
            self.log(tr("conn.lost", error=payload))
            self.disconnect(keep_retrying=True)

        elif kind in ("log", "oled_ok", "oled_fail", "stats_no_data",
                      "calibrating", "pc_synced", "await_sync"):
            if payload:
                self.log(str(payload))

    def _poll_light(self) -> None:
        if (self.running and self.serial.connected and not self.test_mode
                and not self.serial.calibrating):
            self.send(protocol.CMD_LIGHT)
        if self.running:
            self._timers["light"] = self.root.after(LIGHT_POLL_MS, self._poll_light)

    # ============================================================== shutdown ==
    def close(self) -> None:
        if self.current_samples and not self.session_saved:
            if not messagebox.askyesno(tr("dlg.close"), tr("dlg.close_confirm")):
                return
        self.running = False
        for timer_id in self._timers.values():
            try:
                self.root.after_cancel(timer_id)
            except tk.TclError:
                log.debug("timer %s was already gone", timer_id)
        self._timers.clear()
        if self.test_mode:
            self.exit_test_mode()

        try:
            self.settings.set("window_geometry", self.root.winfo_geometry())
        except tk.TclError:
            log.debug("no geometry to save; the window is already gone")
        self.remember_last_run_settings()

        self.disconnect()
        self.mouse.stop()
        try:
            self.db.close()
        except Exception:
            log.debug("database close failed", exc_info=True)
        self.root.after(50, self.root.destroy)


def _as_int(value, default=None):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    root = tk.Tk()
    LatencyTesterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
