"""Device profiles: the mouse or peripheral every run is attached to."""

from __future__ import annotations

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from .. import devices as hardware
from ..i18n import translator as tr
from ..widgets import attach_tooltip, form_row, tree_with_scrollbar

if TYPE_CHECKING:
    from ..app import LatencyTesterApp

FIELDS = (
    ("name", "devices.name"),
    ("manufacturer", "devices.manufacturer"),
    ("model", "devices.model"),
    ("serial_number", "devices.serial"),
    ("switch_type", "devices.switch"),
    ("default_firmware", "devices.default_firmware"),
    ("hardware_id", "devices.hardware_id"),
)


class DevicesView(ttk.Frame):
    def __init__(self, parent: tk.Misc, app: "LatencyTesterApp"):
        super().__init__(parent, padding=10)
        self.app = app
        self.vars = {key: tk.StringVar() for key, _ in FIELDS}

        self.columnconfigure(0, weight=2, minsize=340)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(0, weight=1)

        holder, self.tree = tree_with_scrollbar(
            self, columns=("name", "manufacturer", "model", "runs"),
            show="headings", selectmode="browse")
        for key, label, width in (
            ("name", "devices.name", 170), ("manufacturer", "devices.manufacturer", 110),
            ("model", "devices.model", 130), ("runs", "tab.sessions", 70),
        ):
            self.tree.heading(key, text=tr(label))
            self.tree.column(key, width=width,
                             anchor="center" if key == "runs" else "w")
        holder.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._load_selected())

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        editor = ttk.LabelFrame(right, text=f" {tr('devices.profile')} ", padding=14)
        editor.grid(row=0, column=0, sticky="ew")
        editor.columnconfigure(1, weight=1)

        for index, (key, label) in enumerate(FIELDS):
            form_row(editor, index, tr(label),
                     ttk.Entry(editor, textvariable=self.vars[key]))

        notes_row = len(FIELDS)
        ttk.Label(editor, text=tr("devices.notes")).grid(
            row=notes_row, column=0, sticky="nw", pady=4)
        palette = app.palette
        self.notes = tk.Text(editor, height=6, wrap="word", relief="flat",
                             background=palette.surface_alt, foreground=palette.fg,
                             insertbackground=palette.fg)
        self.notes.grid(row=notes_row, column=1, sticky="ew", pady=4)

        detect_row = ttk.Frame(editor)
        detect_row.grid(row=notes_row + 1, column=0, columnspan=2, sticky="ew",
                        pady=(12, 0))
        self.detect_btn = ttk.Button(detect_row, text=tr("devices.detect"),
                                     command=self.detect)
        self.detect_btn.pack(side="left")
        attach_tooltip(self.detect_btn, tr("tip.detect"), app.palette)
        self.detect_status = tk.StringVar(value="")
        ttk.Label(detect_row, textvariable=self.detect_status,
                  style="Muted.TLabel").pack(side="left", padx=(10, 0))

        buttons = ttk.Frame(editor)
        buttons.grid(row=notes_row + 2, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        for column in range(3):
            buttons.columnconfigure(column, weight=1)
        ttk.Button(buttons, text=tr("devices.new"), command=self.clear).grid(
            row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(buttons, text=tr("devices.save"), style="Accent.TButton",
                   command=self.save).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(buttons, text=tr("devices.delete"), command=self.delete).grid(
            row=0, column=2, sticky="ew", padx=(4, 0))

        ttk.Label(right, text=tr("devices.hint"), wraplength=560, justify="left",
                  style="Muted.TLabel").grid(row=1, column=0, sticky="ew", pady=(14, 0))
        ttk.Label(right, text=tr("devices.detect_hint"), wraplength=560,
                  justify="left", style="Muted.TLabel").grid(
            row=2, column=0, sticky="ew", pady=(10, 0))

    # -------------------------------------------------------------- detect --
    def detect(self) -> None:
        """Fill the editor from the physically connected mouse."""
        found = hardware.detect_mice()
        if not found:
            self.detect_status.set(tr("devices.detect_none"))
            return

        mouse = found[0] if len(found) == 1 else self._choose(found)
        if mouse is None:
            return

        # Only the identity fields are touched: anything the user already typed
        # in model / switch / notes is left alone.
        self.vars["name"].set(mouse.display_name)
        if mouse.manufacturer:
            self.vars["manufacturer"].set(mouse.manufacturer)
        if mouse.serial:
            self.vars["serial_number"].set(mouse.serial)
        self.vars["hardware_id"].set(mouse.hardware_id)
        self.detect_status.set(tr("devices.detected", name=mouse.display_name))

    def _choose(self, found: list) -> object | None:
        """Small modal picker when several mice are connected."""
        dialog = tk.Toplevel(self)
        dialog.title(tr("devices.detect_title"))
        dialog.transient(self.winfo_toplevel())
        dialog.resizable(False, False)
        dialog.configure(background=self.app.palette.bg)

        body = ttk.Frame(dialog, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=tr("devices.detect_choose"), wraplength=420,
                  justify="left").pack(anchor="w", pady=(0, 10))

        choice = tk.StringVar(value=found[0].hardware_id)
        for mouse in found:
            ttk.Radiobutton(
                body, value=mouse.hardware_id, variable=choice,
                text=f"{mouse.display_name}   [{mouse.hardware_id}]",
            ).pack(anchor="w", pady=2)

        picked: dict[str, object] = {}

        def confirm() -> None:
            picked["mouse"] = next(
                (m for m in found if m.hardware_id == choice.get()), found[0])
            dialog.destroy()

        row = ttk.Frame(body)
        row.pack(anchor="e", pady=(14, 0))
        ttk.Button(row, text=tr("dlg.close"), command=dialog.destroy).pack(side="right")
        ttk.Button(row, text=tr("devices.detect"), style="Accent.TButton",
                   command=confirm).pack(side="right", padx=(0, 6))

        dialog.grab_set()
        self.wait_window(dialog)
        return picked.get("mouse")

    # ------------------------------------------------------------------ data --
    def reload(self, devices=None) -> None:
        devices = devices if devices is not None else self.app.db.list_devices()
        selected = self.tree.selection()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in devices:
            run_count = len(self.app.db.list_runs(device_id=row["id"]))
            self.tree.insert("", "end", iid=str(row["id"]),
                             values=(row["name"], row["manufacturer"],
                                     row["model"], run_count))
        for iid in selected:
            if self.tree.exists(iid):
                self.tree.selection_set(iid)

    def clear(self) -> None:
        for iid in self.tree.selection():
            self.tree.selection_remove(iid)
        for var in self.vars.values():
            var.set("")
        self.notes.delete("1.0", "end")

    def _load_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        row = self.app.db.get_device(int(selected[0]))
        if row is None:
            return
        for key, _label in FIELDS:
            self.vars[key].set(row[key] or "")
        self.notes.delete("1.0", "end")
        self.notes.insert("1.0", row["notes"] or "")

    def save(self) -> None:
        fields = {key: var.get().strip() for key, var in self.vars.items()}
        fields["notes"] = self.notes.get("1.0", "end").strip()
        if not fields["name"]:
            messagebox.showwarning(tr("devices.profile"), tr("devices.name_required"))
            return
        selected = self.tree.selection()
        try:
            if selected:
                self.app.db.update_device(int(selected[0]), **fields)
            else:
                self.app.db.create_device(**fields)
        except sqlite3.IntegrityError:
            messagebox.showerror(tr("devices.profile"), tr("devices.duplicate"))
            return
        self.app.refresh_devices()
        self.app.refresh_sessions()
        self.app.log(tr("devices.saved"))

    def delete(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        row = self.app.db.get_device(int(selected[0]))
        if row is None:
            return
        if not messagebox.askyesno(tr("devices.delete"),
                                   tr("devices.delete_confirm", name=row["name"])):
            return
        self.app.db.delete_device(int(selected[0]))
        self.clear()
        self.app.refresh_devices()
        self.app.refresh_sessions()
