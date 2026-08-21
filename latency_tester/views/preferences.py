"""Preferences: language, theme, updates, archive, demo mode, about."""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

from .. import __version__, updater
from ..i18n import LANGUAGE_NAMES
from ..i18n import translator as tr
from ..protocol import PROTOCOL_VERSION
from ..theme import THEMES
from ..widgets import attach_tooltip, form_row

if TYPE_CHECKING:
    from ..app import LatencyTesterApp

log = logging.getLogger(__name__)

THEME_LABELS = {
    "system": "settings.theme_system",
    "light": "settings.theme_light",
    "dark": "settings.theme_dark",
}


class PreferencesView(ttk.Frame):
    def __init__(self, parent: tk.Misc, app: "LatencyTesterApp"):
        super().__init__(parent, padding=10)
        self.app = app

        self.columnconfigure(0, weight=1, minsize=420)
        self.columnconfigure(1, weight=1)

        # Worker threads never touch tkinter: they post here and the poller
        # drains the queue on the Tk thread.
        self._update_events: queue.Queue = queue.Queue()
        self._update_release: updater.Release | None = None
        self._update_busy = False
        self._poll_id: str | None = None

        self._build_appearance()
        self._build_updates()
        self._build_archive()
        self._build_demo()
        self._build_about()

    # ---------------------------------------------------------- appearance --
    def _build_appearance(self) -> None:
        box = ttk.LabelFrame(self, text=f" {tr('settings.title')} ", padding=14)
        box.grid(row=0, column=0, sticky="new", padx=(0, 10))
        box.columnconfigure(1, weight=1)

        self.language_display = tk.StringVar(
            value=LANGUAGE_NAMES.get(tr.language, tr.language))
        language_combo = ttk.Combobox(
            box, textvariable=self.language_display, state="readonly",
            values=[LANGUAGE_NAMES[code] for code in tr.available()])
        language_combo.bind("<<ComboboxSelected>>", self._change_language)
        form_row(box, 0, tr("settings.language"), language_combo)

        self.theme_display = tk.StringVar(
            value=tr(THEME_LABELS[str(self.app.settings.get("theme"))]))
        theme_combo = ttk.Combobox(
            box, textvariable=self.theme_display, state="readonly",
            values=[tr(THEME_LABELS[key]) for key in THEMES])
        theme_combo.bind("<<ComboboxSelected>>", self._change_theme)
        form_row(box, 1, tr("settings.theme"), theme_combo)

        check = ttk.Checkbutton(box, text=tr("settings.auto_connect"),
                                variable=self.app.auto_connect_var,
                                command=self._change_auto_connect)
        check.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

        btn2 = ttk.Checkbutton(box, text=tr("settings.confirm_btn2"),
                               variable=self.app.confirm_btn2_var,
                               command=self._change_confirm_btn2)
        btn2.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))
        attach_tooltip(btn2, tr("tip.confirm_btn2"), self.app.palette)

        ttk.Label(box, text=tr("settings.restart_hint"), style="Muted.TLabel",
                  wraplength=420, justify="left").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _change_language(self, _event=None) -> None:
        chosen = self.language_display.get()
        for code, name in LANGUAGE_NAMES.items():
            if name == chosen:
                self.app.settings.set("language", code)
                tr.set_language(code)
                self.app.rebuild_ui()
                return

    def _change_theme(self, _event=None) -> None:
        chosen = self.theme_display.get()
        for key in THEMES:
            if tr(THEME_LABELS[key]) == chosen:
                self.app.settings.set("theme", key)
                self.app.rebuild_ui()
                return

    def _change_auto_connect(self) -> None:
        self.app.settings.set("auto_connect", bool(self.app.auto_connect_var.get()))
        self.app.settings.save()

    def _change_confirm_btn2(self) -> None:
        self.app.settings.set("confirm_btn2_reset",
                              bool(self.app.confirm_btn2_var.get()))
        self.app.settings.save()

    # ------------------------------------------------------------- updates --
    def _build_updates(self) -> None:
        box = ttk.LabelFrame(self, text=f" {tr('update.title')} ", padding=14)
        box.grid(row=1, column=0, sticky="new", padx=(0, 10), pady=(12, 0))

        ttk.Label(box, text=tr("update.current", version=__version__),
                  style="Muted.TLabel").pack(anchor="w")

        self.update_status = tk.StringVar(value="")
        ttk.Label(box, textvariable=self.update_status, wraplength=420,
                  justify="left").pack(anchor="w", pady=(8, 0))

        self.update_progress = ttk.Progressbar(box, mode="determinate", maximum=100)

        row = ttk.Frame(box)
        row.pack(anchor="w", pady=(10, 0))
        self.check_btn = ttk.Button(row, text=tr("update.check"),
                                    command=self.check_for_updates)
        self.check_btn.pack(side="left")
        # Shown only once an update is actually available.
        self.install_btn = ttk.Button(row, text=tr("update.install", version=""),
                                      style="Accent.TButton",
                                      command=self.install_update)
        self.page_btn = ttk.Button(row, text=tr("update.open_page"),
                                   command=self._open_release_page)

        ttk.Label(box, text=tr("update.hint"), wraplength=420, justify="left",
                  style="Muted.TLabel").pack(anchor="w", pady=(10, 0))

        if not updater.running_frozen():
            ttk.Label(box, text=tr("update.source_note"), wraplength=420,
                      justify="left", style="Warn.TLabel").pack(anchor="w", pady=(6, 0))

    def check_for_updates(self) -> None:
        if self._update_busy:
            return
        self._update_busy = True
        self.check_btn.configure(state="disabled")
        self.install_btn.pack_forget()
        self.page_btn.pack_forget()
        self.update_status.set(tr("update.checking"))

        def work() -> None:
            try:
                self._update_events.put(("result", updater.check_for_update()))
            except updater.UpdateError as exc:
                self._update_events.put(("error", str(exc)))
            except Exception as exc:            # pragma: no cover - defensive
                log.exception("update check failed")
                self._update_events.put(("error", str(exc)))

        threading.Thread(target=work, name="update-check", daemon=True).start()
        self._schedule_poll()

    def install_update(self) -> None:
        release = self._update_release
        if release is None or self._update_busy:
            return

        # An update must never silently discard measurements.
        if self.app.current_samples and not self.app.session_saved:
            messagebox.showwarning(tr("update.confirm_title"), tr("update.unsaved"))
            return
        if not messagebox.askyesno(
                tr("update.confirm_title"),
                tr("update.confirm", version=release.version, size=release.size_mb)):
            return

        self._update_busy = True
        self.check_btn.configure(state="disabled")
        self.install_btn.configure(state="disabled")
        self.update_progress.pack(fill="x", pady=(8, 0))
        self.update_progress["value"] = 0
        self.update_status.set(tr("update.downloading", percent=0))

        def work() -> None:
            def progress(done: int, total: int) -> None:
                if total:
                    self._update_events.put(("progress", int(done * 100 / total)))
            try:
                path = updater.download(release, progress=progress)
                self._update_events.put(("downloaded", path))
            except updater.UpdateError as exc:
                self._update_events.put(("error", str(exc)))
            except Exception as exc:            # pragma: no cover - defensive
                log.exception("update download failed")
                self._update_events.put(("error", str(exc)))

        threading.Thread(target=work, name="update-download", daemon=True).start()
        self._schedule_poll()

    def _open_release_page(self) -> None:
        release = self._update_release
        webbrowser.open(release.page_url if release else updater.RELEASES_PAGE)

    def _schedule_poll(self) -> None:
        if self._poll_id is None:
            self._poll_id = self.after(120, self._drain_update_events)

    def _drain_update_events(self) -> None:
        """Runs on the Tk thread: the only place update state touches widgets."""
        self._poll_id = None
        try:
            while True:
                try:
                    kind, payload = self._update_events.get_nowait()
                except queue.Empty:
                    break

                if kind == "progress":
                    self.update_progress["value"] = payload
                    self.update_status.set(tr("update.downloading", percent=payload))

                elif kind == "result":
                    self._update_busy = False
                    self.check_btn.configure(state="normal")
                    if payload is None:
                        self._update_release = None
                        self.update_status.set(tr("update.up_to_date"))
                    else:
                        self._update_release = payload
                        self.update_status.set(
                            tr("update.available", version=payload.version,
                               size=payload.size_mb))
                        self.install_btn.configure(
                            text=tr("update.install", version=payload.version),
                            state="normal")
                        self.install_btn.pack(side="left", padx=(8, 0))
                        self.page_btn.pack(side="left", padx=(8, 0))

                elif kind == "downloaded":
                    self.update_progress["value"] = 100
                    self.update_status.set(tr("update.verified"))
                    self.after(500, lambda p=payload: self._launch(p))
                    return

                elif kind == "error":
                    self._update_busy = False
                    self.check_btn.configure(state="normal")
                    self.install_btn.configure(state="normal")
                    self.update_progress.pack_forget()
                    self.update_status.set(tr("update.failed", error=payload))
                    self.page_btn.pack(side="left", padx=(8, 0))
        except tk.TclError:
            return

        if self._update_busy:
            self._schedule_poll()

    def _launch(self, path) -> None:
        """Start the verified installer, then close so it can replace files."""
        try:
            updater.launch_installer(path)
        except updater.UpdateError as exc:
            self._update_busy = False
            self.check_btn.configure(state="normal")
            self.update_status.set(tr("update.failed", error=str(exc)))
            return
        # install_update() already confirmed there is nothing unsaved to lose.
        self.app.session_saved = True
        self.app.close()

    # ------------------------------------------------------------- archive --
    def _build_archive(self) -> None:
        box = ttk.LabelFrame(self, text=f" {tr('settings.archive')} ", padding=14)
        box.grid(row=2, column=0, sticky="new", padx=(0, 10), pady=(12, 0))

        database = self.app.db
        info = [
            f"{database.path}",
            f"schema v{database.schema_version} · protocol v{PROTOCOL_VERSION}",
            f"{len(database.list_devices())} × {tr('tab.devices')} · "
            f"{len(database.list_runs())} × {tr('tab.sessions')} "
            f"({database.count_demo_runs()} demo)",
        ]
        for line in info:
            ttk.Label(box, text=line, style="Muted.TLabel",
                      wraplength=420, justify="left").pack(anchor="w")

        ttk.Button(box, text=tr("settings.backup"),
                   command=self.backup).pack(anchor="w", pady=(12, 0))

    def backup(self) -> None:
        default = f"latency_tester_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
        path = filedialog.asksaveasfilename(
            defaultextension=".db", initialfile=default,
            filetypes=[("SQLite", "*.db"), (tr("dlg.all_files"), "*.*")])
        if not path:
            return
        try:
            written = self.app.db.backup(path)
        except Exception as exc:
            messagebox.showerror(tr("dlg.error"), str(exc))
            return
        messagebox.showinfo(tr("settings.archive"),
                            tr("settings.backup_done", path=written))

    # ---------------------------------------------------------------- demo --
    def _build_demo(self) -> None:
        box = ttk.LabelFrame(self, text=f" {tr('settings.demo')} ", padding=14)
        box.grid(row=0, column=1, sticky="new")

        label = ttk.Label(box, text=tr("settings.demo_hint"), wraplength=440,
                          justify="left", style="Muted.TLabel")
        label.pack(anchor="w")
        attach_tooltip(label, tr("tip.demo"), self.app.palette)

        self.demo_btn = ttk.Button(box, text=self._demo_button_text(),
                                   command=self.toggle_demo)
        self.demo_btn.pack(anchor="w", pady=(12, 0))

    def _demo_button_text(self) -> str:
        return tr("settings.demo_stop") if self.app.is_demo else tr("settings.demo_start")

    def toggle_demo(self) -> None:
        from ..demo import PORT_NAME as DEMO_PORT

        if self.app.is_demo:
            self.app.disconnect()
        else:
            if self.app.serial.connected:
                self.app.disconnect()
            self.app.port_var.set(DEMO_PORT)
            self.app.connect()
        self.demo_btn.configure(text=self._demo_button_text())

    # --------------------------------------------------------------- about --
    def _build_about(self) -> None:
        box = ttk.LabelFrame(self, text=f" {tr('settings.about')} ", padding=14)
        box.grid(row=1, column=1, rowspan=2, sticky="new", pady=(12, 0))

        from .. import SUPPORTED_FIRMWARE

        lines = [
            f"{tr('app.title')} {__version__}",
            f"{tr('conn.firmware')}: {SUPPORTED_FIRMWARE} "
            f"(protocol v{PROTOCOL_VERSION})",
            f"{tr('settings.language')}: {LANGUAGE_NAMES.get(tr.language, tr.language)}",
            f"Config: {self.app.settings.path}",
        ]
        for line in lines:
            ttk.Label(box, text=line, style="Muted.TLabel", wraplength=440,
                      justify="left").pack(anchor="w")
