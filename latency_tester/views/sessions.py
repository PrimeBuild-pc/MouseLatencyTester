"""Archive browser: search, inspect, rename, edit, duplicate, export, delete."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import TYPE_CHECKING

from .. import export
from ..constants import CONNECTION_MODES, POLLING_RATES
from ..database import run_as_metadata
from ..i18n import translator as tr
from ..stats import compute_stats, fmt_ms
from ..widgets import form_row, tree_with_scrollbar

if TYPE_CHECKING:
    from ..app import LatencyTesterApp

COLUMNS = (
    ("date", "sessions.col_date", 140),
    ("device", "sessions.col_device", 150),
    ("run", "sessions.col_run", 180),
    ("poll", "sessions.col_poll", 60),
    ("mode", "sessions.col_mode", 90),
    ("dpi", "sessions.col_dpi", 60),
    ("n", "sessions.col_n", 50),
    ("median", "live.median", 80),
    ("mean", "live.mean", 80),
    ("p95", "live.p95", 80),
    ("p99", "live.p99", 80),
    ("stdev", "live.stdev", 80),
    ("jitter", "live.jitter", 80),
    ("cal", "sessions.col_cal", 70),
)


class SessionsView(ttk.Frame):
    def __init__(self, parent: tk.Misc, app: "LatencyTesterApp"):
        super().__init__(parent, padding=10)
        self.app = app
        self.search_var = tk.StringVar()
        self.show_demo_var = tk.BooleanVar(value=True)

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self._build_toolbar()
        self._build_table()
        self._build_details()

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, sticky="ew")

        ttk.Label(bar, text=tr("sessions.search")).pack(side="left")
        entry = ttk.Entry(bar, textvariable=self.search_var, width=26)
        entry.pack(side="left", padx=(6, 12))
        entry.bind("<KeyRelease>", lambda _e: self.reload())

        ttk.Checkbutton(bar, text=tr("sessions.show_demo"),
                        variable=self.show_demo_var,
                        command=self.reload).pack(side="left", padx=(0, 12))

        for label, command in (
            ("sessions.refresh", self.reload),
            ("sessions.rename", self.rename_selected),
            ("sessions.edit", self.edit_selected),
            ("sessions.duplicate", self.duplicate_selected),
            ("sessions.export", self.export_selected),
            ("sessions.compare", self.compare_selected),
        ):
            ttk.Button(bar, text=tr(label), command=command).pack(side="left", padx=3)
        ttk.Button(bar, text=tr("sessions.delete"),
                   command=self.delete_selected).pack(side="right")

    def _build_table(self) -> None:
        holder, self.tree = tree_with_scrollbar(
            self, columns=[c[0] for c in COLUMNS], show="headings",
            selectmode="extended")
        for key, label, width in COLUMNS:
            self.tree.heading(key, text=tr(label))
            self.tree.column(key, width=width, anchor="center",
                             stretch=key in ("device", "run"))
        holder.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._show_details())
        self.tree.bind("<Double-1>", lambda _e: self.edit_selected())
        self.tree.tag_configure("demo", foreground=self.app.palette.warn)

    def _build_details(self) -> None:
        box = ttk.LabelFrame(self, text=f" {tr('sessions.details')} ", padding=10)
        box.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        palette = self.app.palette
        self.details = tk.Text(box, height=6, wrap="word", state="disabled",
                               relief="flat", background=palette.surface,
                               foreground=palette.fg)
        self.details.pack(fill="x")

    # ------------------------------------------------------------------ data --
    def reload(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        runs = self.app.db.list_runs(search=self.search_var.get(),
                                     include_demo=self.show_demo_var.get())
        for run in runs:
            stats = compute_stats(self.app.db.get_latencies(run["id"]))
            self.tree.insert(
                "", "end", iid=str(run["id"]),
                tags=("demo",) if run["is_demo"] else (),
                values=(
                    run["started_at"].replace("T", " ")[:16],
                    run["device_name"],
                    ("[DEMO] " if run["is_demo"] else "") + run["name"],
                    run["polling_rate_hz"] or "",
                    run["connection_mode"] or "",
                    run["dpi"] or "",
                    stats["n"],
                    fmt_ms(stats["median"]), fmt_ms(stats["mean"]),
                    fmt_ms(stats["p95"]), fmt_ms(stats["p99"]),
                    fmt_ms(stats["stdev"]), fmt_ms(stats["jitter"]),
                    run["calibration_us"],
                ),
            )

    def _selected_ids(self) -> list[int]:
        return [int(iid) for iid in self.tree.selection()]

    def _single_id(self) -> int | None:
        selected = self._selected_ids()
        if len(selected) != 1:
            messagebox.showinfo(tr("tab.sessions"), tr("sessions.select_one"))
            return None
        return selected[0]

    def _show_details(self) -> None:
        selected = self._selected_ids()
        if len(selected) != 1:
            return
        run = self.app.db.get_run(selected[0])
        stats = compute_stats(self.app.db.get_latencies(selected[0]))
        lines = [
            f"{run['device_name']} — {run['name']}"
            + ("   [DEMO]" if run["is_demo"] else ""),
            f"{tr('live.polling')}: {run['polling_rate_hz'] or '—'}   "
            f"{tr('live.connection_mode')}: {run['connection_mode'] or '—'}   "
            f"{tr('live.dpi')}: {run['dpi'] or '—'}   "
            f"{tr('live.mouse_firmware')}: {run['mouse_firmware'] or '—'}   "
            f"{tr('live.debounce')}: {run['debounce_setting'] or '—'}",
            f"N={stats['n']}  {tr('live.mean')}={fmt_ms(stats['mean'])}  "
            f"{tr('live.median')}={fmt_ms(stats['median'])}  "
            f"{tr('live.p95')}={fmt_ms(stats['p95'])}  "
            f"{tr('live.p99')}={fmt_ms(stats['p99'])}  "
            f"{tr('live.stdev')}={fmt_ms(stats['stdev'])}  "
            f"{tr('live.iqr')}={fmt_ms(stats['iqr'])}  "
            f"{tr('live.mad')}={fmt_ms(stats['mad'])}  "
            f"{tr('live.jitter')}={fmt_ms(stats['jitter'])}",
            f"{tr('live.calibration')}={run['calibration_us']} µs   "
            f"Teensy={run['teensy_firmware'] or '—'}   "
            f"{tr('live.light')}: {run['light_start']} → {run['light_end']}   "
            f"{run['started_at']} → {run['ended_at']}",
            f"{tr('live.notes')}: {run['notes'] or '—'}",
        ]
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", "\n".join(lines))
        self.details.configure(state="disabled")

    # --------------------------------------------------------------- actions --
    def rename_selected(self) -> None:
        run_id = self._single_id()
        if run_id is None:
            return
        run = self.app.db.get_run(run_id)
        name = simpledialog.askstring(tr("sessions.rename"),
                                      tr("sessions.rename_prompt"),
                                      initialvalue=run["name"], parent=self)
        if not name or not name.strip():
            return
        self.app.db.rename_run(run_id, name)
        self.app.refresh_sessions()
        self.app.log(tr("sessions.renamed"))

    def edit_selected(self) -> None:
        run_id = self._single_id()
        if run_id is None:
            return
        RunEditor(self, self.app, run_id)

    def duplicate_selected(self) -> None:
        run_id = self._single_id()
        if run_id is None:
            return
        self.app.load_template(self.app.db.get_run(run_id))

    def export_selected(self) -> None:
        run_id = self._single_id()
        if run_id is None:
            return
        run = self.app.db.get_run(run_id)
        default = f"{run['device_name']}_{run['name']}.csv".replace(" ", "_").replace("/", "-")
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile=default,
            filetypes=[(tr("dlg.csv"), "*.csv"), (tr("dlg.all_files"), "*.*")])
        if not path:
            return
        samples = [{"latency_ms": s["latency_ms"], "timestamp": s["timestamp"]}
                   for s in self.app.db.get_samples(run_id)]
        export.write_csv(path, run_as_metadata(run), samples,
                         device_name=run["device_name"])
        self.app.log(tr("log.csv", path=path))

    def delete_selected(self) -> None:
        selected = self._selected_ids()
        if not selected:
            messagebox.showinfo(tr("tab.sessions"), tr("sessions.select_any"))
            return
        if not messagebox.askyesno(tr("sessions.delete"),
                                   tr("sessions.delete_confirm", count=len(selected))):
            return
        for run_id in selected:
            self.app.db.delete_run(run_id)
        self.app.refresh_sessions()

    def compare_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo(tr("tab.sessions"), tr("sessions.select_any"))
            return
        self.app.notebook.select(self.app.compare_view)
        self.app.compare_view.select_runs(selected)


class RunEditor(tk.Toplevel):
    """Edit the metadata of a stored run.  Samples are never modified."""

    def __init__(self, parent: tk.Misc, app: "LatencyTesterApp", run_id: int):
        super().__init__(parent)
        self.app = app
        self.run_id = run_id
        run = app.db.get_run(run_id)

        self.title(f"{tr('sessions.edit')} — {run['name']}")
        self.transient(parent.winfo_toplevel())
        self.resizable(True, False)
        self.configure(background=app.palette.bg)

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        devices = app.db.list_devices()
        self.device_names = {row["name"]: row["id"] for row in devices}
        current_device = app.db.get_device(run["device_id"])

        self.vars = {
            "device": tk.StringVar(value=current_device["name"] if current_device else ""),
            "name": tk.StringVar(value=run["name"]),
            "polling_rate_hz": tk.StringVar(value=str(run["polling_rate_hz"] or "")),
            "connection_mode": tk.StringVar(value=run["connection_mode"] or ""),
            "dpi": tk.StringVar(value=str(run["dpi"] or "")),
            "mouse_firmware": tk.StringVar(value=run["mouse_firmware"] or ""),
            "debounce_setting": tk.StringVar(value=run["debounce_setting"] or ""),
        }

        form_row(body, 0, tr("live.device"),
                 ttk.Combobox(body, textvariable=self.vars["device"],
                              values=list(self.device_names), state="readonly"))
        form_row(body, 1, tr("live.run_name"),
                 ttk.Entry(body, textvariable=self.vars["name"]))
        form_row(body, 2, tr("live.polling"),
                 ttk.Combobox(body, textvariable=self.vars["polling_rate_hz"],
                              values=POLLING_RATES))
        form_row(body, 3, tr("live.connection_mode"),
                 ttk.Combobox(body, textvariable=self.vars["connection_mode"],
                              values=CONNECTION_MODES))
        form_row(body, 4, tr("live.dpi"),
                 ttk.Entry(body, textvariable=self.vars["dpi"]))
        form_row(body, 5, tr("live.mouse_firmware"),
                 ttk.Entry(body, textvariable=self.vars["mouse_firmware"]))
        form_row(body, 6, tr("live.debounce"),
                 ttk.Entry(body, textvariable=self.vars["debounce_setting"]))

        ttk.Label(body, text=tr("live.notes")).grid(row=7, column=0, sticky="nw", pady=4)
        self.notes = tk.Text(body, height=5, wrap="word", relief="flat",
                             background=app.palette.surface_alt,
                             foreground=app.palette.fg,
                             insertbackground=app.palette.fg)
        self.notes.grid(row=7, column=1, sticky="ew", pady=4)
        self.notes.insert("1.0", run["notes"] or "")

        buttons = ttk.Frame(body)
        buttons.grid(row=8, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text=tr("devices.save"), style="Accent.TButton",
                   command=self.save).pack(side="right", padx=(6, 0))
        ttk.Button(buttons, text=tr("dlg.close"),
                   command=self.destroy).pack(side="right")

        self.grab_set()

    def save(self) -> None:
        run = self.app.db.get_run(self.run_id)
        metadata = run_as_metadata(run)
        metadata.update({
            "name": self.vars["name"].get().strip() or run["name"],
            "polling_rate_hz": _int_or_none(self.vars["polling_rate_hz"].get()),
            "connection_mode": self.vars["connection_mode"].get().strip(),
            "dpi": _int_or_none(self.vars["dpi"].get()),
            "mouse_firmware": self.vars["mouse_firmware"].get().strip(),
            "debounce_setting": self.vars["debounce_setting"].get().strip(),
            "notes": self.notes.get("1.0", "end").strip(),
            "device_id": self.device_names.get(self.vars["device"].get().strip(),
                                               run["device_id"]),
        })
        self.app.db.update_run(self.run_id, metadata)
        self.app.refresh_sessions()
        self.app.log(tr("sessions.saved"))
        self.destroy()


def _int_or_none(value: str):
    try:
        return int(value.strip())
    except (AttributeError, ValueError):
        return None
