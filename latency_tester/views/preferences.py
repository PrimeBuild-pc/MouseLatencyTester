"""Preferences: language, theme, archive maintenance, demo mode, about."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

from .. import __version__
from ..i18n import LANGUAGE_NAMES
from ..i18n import translator as tr
from ..protocol import PROTOCOL_VERSION
from ..theme import THEMES
from ..widgets import attach_tooltip, form_row

if TYPE_CHECKING:
    from ..app import LatencyTesterApp

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

        self._build_appearance()
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

        ttk.Label(box, text=tr("settings.restart_hint"), style="Muted.TLabel",
                  wraplength=420, justify="left").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

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

    # ------------------------------------------------------------- archive --
    def _build_archive(self) -> None:
        box = ttk.LabelFrame(self, text=f" {tr('settings.archive')} ", padding=14)
        box.grid(row=1, column=0, sticky="new", padx=(0, 10), pady=(12, 0))

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
        box.grid(row=1, column=1, sticky="new", pady=(12, 0))

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
