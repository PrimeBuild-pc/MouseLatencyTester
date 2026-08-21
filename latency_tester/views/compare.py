"""Compare tab: several runs side by side, with deltas against a baseline."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

from ..constants import MODE_PHOTON
from ..database import run_mode
from ..i18n import translator as tr
from ..stats import compute_stats, delta, fmt_delta, fmt_ms
from ..theme import series_style, style_axes, style_figure
from ..widgets import attach_tooltip, tree_with_scrollbar

if TYPE_CHECKING:
    from ..app import LatencyTesterApp

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB = True
except Exception:      # pragma: no cover - depends on the environment
    MATPLOTLIB = False

CHART_KEYS = ("samples", "box", "ecdf", "hist")
CHART_LABELS = {
    "samples": "compare.chart_samples",
    "box": "compare.chart_box",
    "ecdf": "compare.chart_ecdf",
    "hist": "compare.chart_hist",
}

STAT_COLUMNS = (
    ("session", "compare.col_session", 220),
    ("n", "live.n", 50),
    ("mean", "live.mean", 80),
    ("median", "live.median", 80),
    ("p95", "live.p95", 80),
    ("p99", "live.p99", 80),
    ("stdev", "live.stdev", 80),
    ("mad", "live.mad", 80),
    ("min", "live.min", 80),
    ("max", "live.max", 80),
    ("jitter", "live.jitter", 85),
)

DELTA_COLUMNS = (
    ("session", "compare.col_session", 220),
    ("dmedian", "live.median", 130),
    ("dmean", "live.mean", 130),
    ("dp95", "live.p95", 130),
    ("dp99", "live.p99", 130),
)


class CompareView(ttk.Frame):
    def __init__(self, parent: tk.Misc, app: "LatencyTesterApp"):
        super().__init__(parent, padding=10)
        self.app = app
        self.chart_var = tk.StringVar(value=tr(CHART_LABELS["samples"]))
        self.baseline_var = tk.StringVar(value=tr("compare.baseline_none"))
        self.status_var = tk.StringVar(value=tr("compare.hint_select"))
        self._series: list[tuple] = []

        self.columnconfigure(0, weight=1, minsize=330)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(0, weight=1)

        self._build_selector()
        self._build_charts()

    def _build_selector(self) -> None:
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text=tr("compare.select"),
                  style="Muted.TLabel").grid(row=0, column=0, sticky="w")

        holder, self.tree = tree_with_scrollbar(
            left, columns=("date", "device", "run", "poll", "n", "median"),
            show="headings", selectmode="extended", height=18)
        for key, label, width in (
            ("date", "sessions.col_date", 110), ("device", "sessions.col_device", 120),
            ("run", "sessions.col_run", 140), ("poll", "sessions.col_poll", 55),
            ("n", "sessions.col_n", 45), ("median", "live.median", 70),
        ):
            self.tree.heading(key, text=tr(label))
            self.tree.column(key, width=width, anchor="center",
                             stretch=key in ("device", "run"))
        holder.grid(row=1, column=0, sticky="nsew", pady=(6, 8))
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._selection_changed())

        controls = ttk.Frame(left)
        controls.grid(row=2, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text=tr("compare.chart")).grid(row=0, column=0, sticky="w")
        ttk.Combobox(controls, textvariable=self.chart_var, state="readonly",
                     values=[tr(CHART_LABELS[k]) for k in CHART_KEYS]).grid(
            row=0, column=1, sticky="ew", padx=6, pady=3)

        baseline_label = ttk.Label(controls, text=tr("compare.baseline"))
        baseline_label.grid(row=1, column=0, sticky="w")
        self.baseline_combo = ttk.Combobox(controls, textvariable=self.baseline_var,
                                           state="readonly",
                                           values=[tr("compare.baseline_none")])
        self.baseline_combo.grid(row=1, column=1, sticky="ew", padx=6, pady=3)
        attach_tooltip(baseline_label, tr("tip.baseline"), self.app.palette)

        buttons = ttk.Frame(left)
        buttons.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(buttons, text=tr("compare.plot"), style="Accent.TButton",
                   command=self.plot).pack(side="left")
        ttk.Button(buttons, text=tr("compare.export_chart"),
                   command=self.export_chart).pack(side="left", padx=6)

        ttk.Label(left, textvariable=self.status_var, wraplength=320,
                  style="Muted.TLabel", justify="left").grid(
            row=4, column=0, sticky="ew", pady=(10, 0))

    def _build_charts(self) -> None:
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=3)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        figure_box = ttk.LabelFrame(right, text=f" {tr('compare.figure')} ", padding=6)
        figure_box.grid(row=0, column=0, sticky="nsew")

        if MATPLOTLIB:
            self.figure = Figure(figsize=(7.5, 4.4), dpi=100)
            self.axes = self.figure.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.figure, master=figure_box)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            style_figure(self.figure, self.app.palette)
            self.canvas.draw()
        else:
            self.figure = self.axes = self.canvas = None
            ttk.Label(figure_box, text=tr("compare.no_matplotlib"),
                      justify="center").pack(expand=True)

        stats_box = ttk.LabelFrame(right, text=f" {tr('compare.table')} ", padding=6)
        stats_box.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        holder, self.stats_tree = tree_with_scrollbar(
            stats_box, columns=[c[0] for c in STAT_COLUMNS], show="headings", height=5)
        for key, label, width in STAT_COLUMNS:
            self.stats_tree.heading(key, text=tr(label))
            self.stats_tree.column(key, width=width, anchor="center",
                                   stretch=key == "session")
        holder.pack(fill="both", expand=True)

        delta_box = ttk.LabelFrame(right, text=f" {tr('compare.deltas')} ", padding=6)
        delta_box.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        holder, self.delta_tree = tree_with_scrollbar(
            delta_box, columns=[c[0] for c in DELTA_COLUMNS], show="headings", height=5)
        for key, label, width in DELTA_COLUMNS:
            heading = tr(label) if key == "session" else f"Δ {tr(label)}"
            self.delta_tree.heading(key, text=heading)
            self.delta_tree.column(key, width=width, anchor="center",
                                   stretch=key == "session")
        holder.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ data --
    def reload(self) -> None:
        selected = set(self.tree.selection())
        for item in self.tree.get_children():
            self.tree.delete(item)
        for run in self.app.db.list_runs():
            stats = compute_stats(self.app.db.get_latencies(run["id"]))
            self.tree.insert(
                "", "end", iid=str(run["id"]),
                values=(run["started_at"].replace("T", " ")[:16],
                        run["device_name"],
                        ("[DEMO] " if run["is_demo"] else "") + run["name"],
                        run["polling_rate_hz"] or "", stats["n"],
                        fmt_ms(stats["median"])))
        still_there = [iid for iid in selected if self.tree.exists(iid)]
        if still_there:
            self.tree.selection_set(still_there)

    def select_runs(self, iids) -> None:
        existing = [iid for iid in iids if self.tree.exists(iid)]
        if not existing:
            return
        self.tree.selection_set(existing)
        self.tree.see(existing[0])
        self.plot()

    def _selection_changed(self) -> None:
        labels = [tr("compare.baseline_none")]
        labels.extend(self._label_for(int(iid)) for iid in self.tree.selection())
        self.baseline_combo["values"] = labels
        if self.baseline_var.get() not in labels:
            self.baseline_var.set(labels[0])

    def _label_for(self, run_id: int) -> str:
        run = self.app.db.get_run(run_id)
        bits = [run["device_name"], run["name"]]
        if run["polling_rate_hz"]:
            bits.append(f"{run['polling_rate_hz']} Hz")
        # The mode is part of the identity of a run, not a detail: two runs from
        # different modes measure different things and must never look alike.
        if run_mode(run) == MODE_PHOTON:
            bits.append(tr("mode.short_photon"))
        return " — ".join(bits)

    def _mixed_modes(self, series: list[tuple]) -> bool:
        return len({run_mode(entry[0]) for entry in series}) > 1

    def _collect(self) -> list[tuple]:
        series = []
        for iid in self.tree.selection():
            run_id = int(iid)
            values = self.app.db.get_latencies(run_id)
            if values:
                series.append((self.app.db.get_run(run_id), self._label_for(run_id),
                               values, compute_stats(values)))
        return series

    # ---------------------------------------------------------------- plotting --
    def plot(self) -> None:
        if not self.tree.selection():
            self.status_var.set(tr("compare.hint_select"))
            return
        series = self._collect()
        if not series:
            self.status_var.set(tr("compare.hint_empty"))
            return
        self._series = series

        self._fill_stats(series)
        baseline = self._baseline(series)
        self._fill_deltas(series, baseline)

        if not MATPLOTLIB:
            self.status_var.set(tr("compare.no_matplotlib"))
            return
        self._draw(series)

        if self._mixed_modes(series):
            # Allowed -- sometimes it is exactly what you want to look at -- but
            # never without saying so: the two modes do not measure the same
            # interval, so a delta between them is not a like-for-like figure.
            self.status_var.set(tr("compare.mixed_modes"))
        elif len(series) >= 2:
            self.status_var.set(f"{tr('compare.baseline')}: {baseline[1]}")
        else:
            self.status_var.set(tr("compare.hint_one"))

    def _baseline(self, series: list[tuple]) -> tuple:
        chosen = self.baseline_var.get()
        for entry in series:
            if entry[1] == chosen:
                return entry
        return series[0]

    def _fill_stats(self, series: list[tuple]) -> None:
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)
        for _run, label, _values, stats in series:
            self.stats_tree.insert("", "end", values=(
                label, stats["n"], fmt_ms(stats["mean"]), fmt_ms(stats["median"]),
                fmt_ms(stats["p95"]), fmt_ms(stats["p99"]), fmt_ms(stats["stdev"]),
                fmt_ms(stats["mad"]), fmt_ms(stats["min"]), fmt_ms(stats["max"]),
                fmt_ms(stats["jitter"])))

    def _fill_deltas(self, series: list[tuple], baseline: tuple) -> None:
        for item in self.delta_tree.get_children():
            self.delta_tree.delete(item)
        base_stats = baseline[3]
        for _run, label, _values, stats in series:
            if label == baseline[1]:
                continue
            cells = [label]
            for key in ("median", "mean", "p95", "p99"):
                absolute, percent = delta(stats[key], base_stats[key])
                # A zero baseline makes the percentage undefined; show the
                # absolute difference alone rather than "nan%".
                cells.append(f"{fmt_delta(absolute)} ms"
                             if math.isnan(percent)
                             else f"{fmt_delta(absolute)} ms ({percent:+.1f}%)")
            self.delta_tree.insert("", "end", values=cells)

    def _chart_key(self) -> str:
        for key in CHART_KEYS:
            if self.chart_var.get() == tr(CHART_LABELS[key]):
                return key
        return "samples"

    def _draw(self, series: list[tuple]) -> None:
        palette = self.app.palette
        axes = self.axes
        axes.clear()
        chart = self._chart_key()

        if chart == "samples":
            for index, (_run, label, values, _stats) in enumerate(series):
                style = series_style(index, palette)
                axes.plot(range(1, len(values) + 1), values, label=label,
                          linewidth=1.3, markersize=3.2, alpha=0.9, **style)
            axes.set_xlabel(tr("compare.axis_sample"))
            axes.set_ylabel(tr("compare.axis_latency"))

        elif chart == "box":
            plot = axes.boxplot(
                [values for _r, _l, values, _s in series],
                tick_labels=[label for _r, label, _v, _s in series],
                showmeans=True, patch_artist=True)
            for index, patch in enumerate(plot["boxes"]):
                patch.set_facecolor(palette.series[index % len(palette.series)])
                patch.set_alpha(0.45)
                patch.set_edgecolor(palette.fg_muted)
            for key in ("whiskers", "caps", "medians"):
                for artist in plot[key]:
                    artist.set_color(palette.fg_muted)
            for flier in plot["fliers"]:
                flier.set(markeredgecolor=palette.error, alpha=0.8)
            axes.set_ylabel(tr("compare.axis_latency"))
            axes.tick_params(axis="x", labelrotation=15)

        elif chart == "ecdf":
            for index, (_run, label, values, _stats) in enumerate(series):
                ordered = sorted(values)
                shares = [(i + 1) / len(ordered) for i in range(len(ordered))]
                style = series_style(index, palette)
                axes.step(ordered, shares, where="post", label=label,
                          color=style["color"], linestyle=style["linestyle"],
                          linewidth=1.6)
            axes.set_xlabel(tr("compare.axis_latency"))
            axes.set_ylabel(tr("compare.axis_share"))

        else:  # histogram
            for index, (_run, label, values, _stats) in enumerate(series):
                style = series_style(index, palette)
                axes.hist(values, bins="auto", histtype="step", linewidth=1.6,
                          label=label, color=style["color"],
                          linestyle=style["linestyle"])
            axes.set_xlabel(tr("compare.axis_latency"))
            axes.set_ylabel(tr("compare.axis_count"))

        axes.set_title(tr(CHART_LABELS[chart]))
        style_axes(axes, palette)
        if chart != "box":
            legend = axes.legend(fontsize=8, facecolor=palette.surface,
                                 edgecolor=palette.border)
            for text in legend.get_texts():
                text.set_color(palette.fg)
        style_figure(self.figure, palette)
        self.figure.tight_layout()
        self.canvas.draw()

    def export_chart(self) -> None:
        if not MATPLOTLIB or not self._series:
            messagebox.showinfo(tr("tab.compare"), tr("compare.hint_select"))
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png", initialfile="latency_compare.png",
            filetypes=[("PNG", "*.png"), ("SVG", "*.svg"),
                       ("PDF", "*.pdf"), (tr("dlg.all_files"), "*.*")])
        if not path:
            return
        self.figure.savefig(path, dpi=160, facecolor=self.figure.get_facecolor())
        self.app.log(tr("compare.exported", path=path))
