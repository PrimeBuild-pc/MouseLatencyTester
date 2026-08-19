"""Small reusable Tk widgets: tooltips, metric cards, form rows, sample chart."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from typing import Sequence

from .stats import compute_stats, fmt_ms, outlier_indices
from .theme import FONT_FAMILY, Palette


log = logging.getLogger(__name__)


class Tooltip:
    """Hover help.  Created through :func:`attach_tooltip`."""

    DELAY_MS = 450

    def __init__(self, widget: tk.Misc, text: str, palette: Palette):
        self.widget = widget
        self.text = text
        self.palette = palette
        self._window: tk.Toplevel | None = None
        self._after_id: str | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.DELAY_MS, self._show)

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                log.debug("tooltip timer was already gone")
            self._after_id = None

    def _show(self) -> None:
        if self._window is not None or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        except tk.TclError:
            return
        window = tk.Toplevel(self.widget)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            window, text=self.text, justify="left", wraplength=320,
            background=self.palette.surface_alt, foreground=self.palette.fg,
            relief="solid", borderwidth=1, padx=8, pady=5,
            font=(FONT_FAMILY, 9),
        )
        label.pack()
        self._window = window

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self._window is not None:
            try:
                self._window.destroy()
            except tk.TclError:
                log.debug("tooltip window was already destroyed")
            self._window = None


def attach_tooltip(widget: tk.Misc, text: str, palette: Palette) -> None:
    if text:
        Tooltip(widget, text, palette)


def metric_card(parent: tk.Misc, title: str, variable: tk.StringVar,
                tooltip: str = "", palette: Palette | None = None,
                big: bool = False) -> ttk.Frame:
    """A titled value tile."""
    card = ttk.Frame(parent, style="Card.TFrame", padding=(8, 7))
    ttk.Label(card, text=title, style="CardMuted.TLabel").pack(anchor="w")
    ttk.Label(card, textvariable=variable,
              style="MetricBig.TLabel" if big else "Metric.TLabel").pack(anchor="w")
    if tooltip and palette is not None:
        attach_tooltip(card, tooltip, palette)
    return card


def form_row(parent: tk.Misc, row: int, label: str, widget: tk.Misc,
             tooltip: str = "", palette: Palette | None = None) -> None:
    """Label in column 0, widget stretching in column 1."""
    text = ttk.Label(parent, text=label)
    text.grid(row=row, column=0, sticky="w", pady=4, padx=(0, 10))
    widget.grid(row=row, column=1, sticky="ew", pady=4)
    if tooltip and palette is not None:
        attach_tooltip(text, tooltip, palette)
        attach_tooltip(widget, tooltip, palette)


def info_row(parent: tk.Misc, row: int, name: str, variable: tk.StringVar,
             tooltip: str = "", palette: Palette | None = None) -> ttk.Label:
    label = ttk.Label(parent, text=name, style="Muted.TLabel")
    label.grid(row=row, column=0, sticky="w", pady=2)
    value = ttk.Label(parent, textvariable=variable, font=(FONT_FAMILY, 10, "bold"))
    value.grid(row=row, column=1, sticky="e", pady=2)
    if tooltip and palette is not None:
        attach_tooltip(label, tooltip, palette)
    return value


def tree_with_scrollbar(parent: tk.Misc, **kwargs) -> tuple[ttk.Frame, ttk.Treeview]:
    """A Treeview that keeps its vertical scrollbar glued to it."""
    holder = ttk.Frame(parent)
    tree = ttk.Treeview(holder, **kwargs)
    scroll = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    return holder, tree


class SampleChart(tk.Canvas):
    """Live plot of the current run.

    Drawn on a plain canvas so the live view never waits on matplotlib.
    Outliers are ringed, never removed.
    """

    PAD = 34
    WINDOW = 150         # how many recent samples stay visible

    def __init__(self, parent: tk.Misc, palette: Palette, empty_text: str = ""):
        super().__init__(parent, height=280, highlightthickness=1,
                         background=palette.surface,
                         highlightbackground=palette.border)
        self.palette = palette
        self.empty_text = empty_text
        self._values: list[float] = []
        self.bind("<Configure>", lambda _e: self.redraw())

    def set_palette(self, palette: Palette) -> None:
        self.palette = palette
        self.configure(background=palette.surface, highlightbackground=palette.border)
        self.redraw()

    def set_values(self, values: Sequence[float]) -> None:
        self._values = list(values)
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        p = self.palette
        width = max(self.winfo_width(), 120)
        height = max(self.winfo_height(), 120)
        values = self._values[-self.WINDOW:]

        if not values:
            self.create_text(width / 2, height / 2, text=self.empty_text,
                             fill=p.fg_muted, font=(FONT_FAMILY, 11))
            return

        stats = compute_stats(values)
        low, high = min(values), max(values)
        if high - low < 0.001:
            high = low + 1.0

        pad = self.PAD
        plot_w = width - 2 * pad
        plot_h = height - 2 * pad

        def y_for(value: float) -> float:
            return pad + (1 - (value - low) / (high - low)) * plot_h

        self.create_line(pad, pad, pad, height - pad, fill=p.border)
        self.create_line(pad, height - pad, width - pad, height - pad, fill=p.border)

        for reference, colour, dash, text in (
            (stats["median"], p.ok, (6, 4), f"MED {fmt_ms(stats['median'], 2)}"),
            (stats["p95"], p.warn, (2, 4), f"P95 {fmt_ms(stats['p95'], 2)}"),
        ):
            y = y_for(reference)
            self.create_line(pad, y, width - pad, y, fill=colour, dash=dash)
            self.create_text(pad + 5, y - 3, text=text, anchor="sw",
                             fill=colour, font=(FONT_FAMILY, 8, "bold"))

        denominator = max(len(values) - 1, 1)
        points: list[float] = []
        for index, value in enumerate(values):
            points.extend((pad + (index / denominator) * plot_w, y_for(value)))
        if len(points) >= 4:
            self.create_line(*points, fill=p.accent, width=2, smooth=False)

        for index in outlier_indices(values):
            x = pad + (index / denominator) * plot_w
            y = y_for(values[index])
            self.create_oval(x - 4, y - 4, x + 4, y + 4,
                             outline=p.error, width=2)

        self.create_text(pad + 5, pad - 6, text=f"{high:.2f} ms", anchor="sw",
                         fill=p.fg_muted, font=(FONT_FAMILY, 8))
        self.create_text(pad + 5, height - pad + 12, text=f"{low:.2f} ms",
                         anchor="nw", fill=p.fg_muted, font=(FONT_FAMILY, 8))
        self.create_text(width - pad, height - pad + 12, text=f"n={len(self._values)}",
                         anchor="ne", fill=p.fg_muted, font=(FONT_FAMILY, 8))
