"""Live test tab: current statistics, run configuration, controls, event log."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from typing import TYPE_CHECKING

from ..constants import CONNECTION_MODES, POLLING_RATES
from ..i18n import translator as tr
from ..protocol import CMD_LIGHT, CMD_STATS
from ..theme import FONT_FAMILY, MONO_FAMILY
from ..widgets import (SampleChart, attach_tooltip, form_row, info_row,
                       metric_card)

if TYPE_CHECKING:
    from ..app import LatencyTesterApp

METRICS = (
    ("mean", "live.mean"), ("median", "live.median"), ("p95", "live.p95"),
    ("p99", "live.p99"), ("stdev", "live.stdev"), ("min", "live.min"),
    ("max", "live.max"), ("iqr", "live.iqr"), ("mad", "live.mad"),
    ("jitter", "live.jitter"),
)


class LiveView(ttk.Frame):
    def __init__(self, parent: tk.Misc, app: "LatencyTesterApp"):
        super().__init__(parent, padding=10)
        self.app = app
        palette = app.palette

        self.columnconfigure(0, weight=3, minsize=520)
        self.columnconfigure(1, weight=2, minsize=380)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self)
        right = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right.grid(row=0, column=1, sticky="nsew")
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)
        right.columnconfigure(0, weight=1)

        self._build_metrics(left, palette)
        self._build_chart(left, palette)
        self._build_config(right, palette)
        self._build_controls(right, palette)
        self._build_run_actions(right, palette)
        self._build_log(right)

    # --------------------------------------------------------------- panels --
    def _build_metrics(self, parent: ttk.Frame, palette) -> None:
        box = ttk.LabelFrame(parent, text=f" {tr('live.stats')} ", padding=12)
        box.grid(row=0, column=0, sticky="ew")

        headline = ttk.Frame(box, style="Card.TFrame", padding=(14, 10))
        headline.pack(fill="x")
        ttk.Label(headline, text=tr("live.last"), style="CardMuted.TLabel").pack(anchor="w")
        row = ttk.Frame(headline, style="Card.TFrame")
        row.pack(anchor="w")
        ttk.Label(row, textvariable=self.app.metric_vars["last"],
                  style="MetricBig.TLabel").pack(side="left")
        ttk.Label(row, text="ms", style="Card.TLabel").pack(side="left", padx=(8, 0), pady=(18, 0))
        ttk.Label(headline, textvariable=self.app.metric_vars["n"],
                  style="Card.TLabel").pack(anchor="e")

        grid = ttk.Frame(box)
        grid.pack(fill="x", pady=(10, 0))
        for column in range(5):
            grid.columnconfigure(column, weight=1, uniform="metric")
        for index, (key, label) in enumerate(METRICS):
            card = metric_card(grid, tr(label), self.app.metric_vars[key],
                               palette=palette)
            card.grid(row=index // 5, column=index % 5, sticky="nsew", padx=3, pady=3)

        ttk.Label(box, textvariable=self.app.outlier_var,
                  style="Warn.TLabel").pack(anchor="w", pady=(8, 0))

    def _build_chart(self, parent: ttk.Frame, palette) -> None:
        box = ttk.LabelFrame(parent, text=f" {tr('live.chart')} ", padding=8)
        box.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.chart = SampleChart(box, palette, empty_text=tr("live.no_samples"))
        self.chart.pack(fill="both", expand=True)

    def _build_config(self, parent: ttk.Frame, palette) -> None:
        box = ttk.LabelFrame(parent, text=f" {tr('live.config')} ", padding=12)
        box.grid(row=0, column=0, sticky="ew")
        box.columnconfigure(1, weight=1)

        self.device_combo = ttk.Combobox(box, textvariable=self.app.device_var,
                                         state="readonly")
        form_row(box, 0, tr("live.device"), self.device_combo)
        form_row(box, 1, tr("live.run_name"),
                 ttk.Entry(box, textvariable=self.app.run_name_var))
        form_row(box, 2, tr("live.polling"),
                 ttk.Combobox(box, textvariable=self.app.polling_var,
                              values=POLLING_RATES),
                 tr("tip.polling"), palette)
        form_row(box, 3, tr("live.connection_mode"),
                 ttk.Combobox(box, textvariable=self.app.mode_var,
                              values=CONNECTION_MODES))
        form_row(box, 4, tr("live.dpi"), ttk.Entry(box, textvariable=self.app.dpi_var))
        form_row(box, 5, tr("live.mouse_firmware"),
                 ttk.Entry(box, textvariable=self.app.mouse_fw_var))
        form_row(box, 6, tr("live.debounce"),
                 ttk.Entry(box, textvariable=self.app.debounce_var))

        ttk.Label(box, text=tr("live.notes")).grid(row=7, column=0, sticky="nw", pady=4)
        self.notes = tk.Text(box, height=3, wrap="word", relief="flat",
                             background=palette.surface_alt, foreground=palette.fg,
                             insertbackground=palette.fg, font=(FONT_FAMILY, 9))
        self.notes.grid(row=7, column=1, sticky="ew", pady=4)

        options = ttk.Frame(box)
        options.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Label(options, text=tr("live.target")).pack(side="left")
        spin = ttk.Spinbox(options, from_=1, to=10000,
                           textvariable=self.app.target_var, width=7)
        spin.pack(side="left", padx=(6, 16))
        attach_tooltip(spin, tr("tip.target"), palette)
        check = ttk.Checkbutton(options, text=tr("live.auto_reset"),
                                variable=self.app.auto_reset_var)
        check.pack(side="left")
        attach_tooltip(check, tr("tip.auto_reset"), palette)

    def _build_controls(self, parent: ttk.Frame, palette) -> None:
        box = ttk.LabelFrame(parent, text=f" {tr('live.controls')} ", padding=12)
        box.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        info = ttk.Frame(box)
        info.pack(fill="x", pady=(0, 10))
        info.columnconfigure(1, weight=1)
        info_row(info, 0, tr("live.state"), self.app.state_var)
        info_row(info, 1, tr("live.calibration"), self.app.cal_var,
                 tr("tip.calibrate"), palette)
        info_row(info, 2, tr("live.light"), self.app.light_var, tr("tip.light"), palette)
        info_row(info, 3, tr("live.skipped"), self.app.skipped_var)
        # Protocol tokens, deliberately not translated.
        info_row(info, 4, "BTN1", self.app.button_vars[1], tr("tip.buttons"), palette)
        info_row(info, 5, "BTN2", self.app.button_vars[2], tr("tip.buttons"), palette)

        buttons = ttk.Frame(box)
        buttons.pack(fill="x")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        self.cal_btn = ttk.Button(buttons, text=tr("live.calibrate"),
                                  command=self.app.calibrate)
        self.cal_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=3)
        attach_tooltip(self.cal_btn, tr("tip.calibrate"), palette)

        self.reset_btn = ttk.Button(buttons, text=tr("live.reset"),
                                    command=self.app.reset_stats)
        self.reset_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=3)

        self.stats_btn = ttk.Button(buttons, text=tr("live.request_stats"),
                                    command=lambda: self.app.send(CMD_STATS))
        self.stats_btn.grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=3)

        self.light_btn = ttk.Button(buttons, text=tr("live.read_light"),
                                    command=lambda: self.app.send(CMD_LIGHT))
        self.light_btn.grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=3)

        self.test_btn = ttk.Button(box, text=tr("live.enter_test"),
                                   style="Accent.TButton",
                                   command=self.app.enter_test_mode)
        self.test_btn.pack(fill="x", pady=(12, 6), ipady=6)

        ttk.Label(box, text=tr("live.legend"), justify="center",
                  style="Muted.TLabel").pack(fill="x")

    def _build_run_actions(self, parent: ttk.Frame, palette) -> None:
        box = ttk.LabelFrame(parent, text=f" {tr('live.current_run')} ", padding=12)
        box.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        row = ttk.Frame(box)
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)
        ttk.Button(row, text=tr("live.save_run"), style="Accent.TButton",
                   command=self.app.save_current_run).grid(
            row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(row, text=tr("live.new_run"), command=self.app.new_run).grid(
            row=0, column=1, sticky="ew", padx=(4, 0))
        ttk.Button(box, text=tr("live.export_csv"),
                   command=self.app.export_current_csv).pack(fill="x", pady=(8, 0))

    def _build_log(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text=f" {tr('live.events')} ", padding=8)
        box.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        palette = self.app.palette
        holder = ttk.Frame(box)
        holder.pack(fill="both", expand=True)
        self.log_text = tk.Text(holder, height=8, wrap="word", state="disabled",
                                relief="flat", font=(MONO_FAMILY, 9),
                                background=palette.surface, foreground=palette.fg_muted)
        scroll = ttk.Scrollbar(holder, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ------------------------------------------------------------------ API --
    def set_device_choices(self, names: list[str]) -> None:
        self.device_combo["values"] = names

    def set_samples(self, values) -> None:
        self.chart.set_values(values)

    def set_connected(self, connected: bool) -> None:
        state = "normal" if connected else "disabled"
        for button in (self.cal_btn, self.reset_btn, self.stats_btn,
                       self.light_btn, self.test_btn):
            button.configure(state=state)

    def get_notes(self) -> str:
        return self.notes.get("1.0", "end").strip()

    def set_notes(self, text: str) -> None:
        self.notes.delete("1.0", "end")
        self.notes.insert("1.0", text)

    def log(self, line: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line + "\n")
        # Keep the widget bounded: an all-night session must not grow forever.
        if int(self.log_text.index("end-1c").split(".")[0]) > 500:
            self.log_text.delete("1.0", "100.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
