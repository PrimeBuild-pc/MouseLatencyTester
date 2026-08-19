"""Light / dark / system theming for ttk, the raw Tk widgets and matplotlib.

Only the standard library is used: ttk's ``clam`` theme is fully restylable, so
there is no reason to pull in a theming dependency.
"""

from __future__ import annotations

import sys
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

THEMES = ("system", "light", "dark")

FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"
MONO_FAMILY = "Consolas" if sys.platform == "win32" else "DejaVu Sans Mono"


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str            # window background
    surface: str       # cards / frames sitting on the background
    surface_alt: str   # table stripes, inputs
    border: str
    fg: str            # primary text
    fg_muted: str      # secondary text
    accent: str
    accent_fg: str
    ok: str
    warn: str
    error: str
    grid: str          # chart gridlines
    # Test-mode overlay: these three carry the whole meaning of the screen,
    # so they stay strongly saturated in both themes.
    test_armed: str
    test_wait: str
    test_done: str
    # Distinguishable series colours for the compare charts.
    series: tuple[str, ...]


LIGHT = Palette(
    name="light",
    bg="#f4f5f7",
    surface="#ffffff",
    surface_alt="#eceef1",
    border="#c8ccd4",
    fg="#16181d",
    fg_muted="#5c6270",
    accent="#2563eb",
    accent_fg="#ffffff",
    ok="#137a3b",
    warn="#b45309",
    error="#b91c1c",
    grid="#d6d9df",
    test_armed="#15803d",
    test_wait="#b91c1c",
    test_done="#1d4ed8",
    series=("#2563eb", "#d97706", "#059669", "#db2777",
            "#7c3aed", "#0891b2", "#b45309", "#4d7c0f"),
)

DARK = Palette(
    name="dark",
    bg="#14161a",
    surface="#1c1f25",
    surface_alt="#252932",
    border="#39404d",
    fg="#eef1f6",
    fg_muted="#a2abbb",
    accent="#5b9cff",
    accent_fg="#0b0d10",
    ok="#4ade80",
    warn="#fbbf24",
    error="#f87171",
    grid="#39404d",
    test_armed="#14532d",
    test_wait="#7f1d1d",
    test_done="#1e3a8a",
    series=("#5b9cff", "#fbbf24", "#34d399", "#f472b6",
            "#a78bfa", "#22d3ee", "#fb923c", "#a3e635"),
)

#: Line styles and markers, so series stay distinguishable without colour.
SERIES_LINESTYLES = ("-", "--", "-.", ":")
SERIES_MARKERS = ("o", "s", "^", "D", "v", "P", "X", "*")


def detect_system_theme() -> str:
    """``"dark"`` or ``"light"`` according to the OS, defaulting to light."""
    if sys.platform == "win32":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            with key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if value else "dark"
        except OSError:
            return "light"
    if sys.platform == "darwin":
        try:
            import subprocess

            out = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True, timeout=2,
            )
            return "dark" if "dark" in out.stdout.lower() else "light"
        except Exception:
            return "light"
    return "light"


def resolve(mode: str) -> Palette:
    """Map a settings value (``system``/``light``/``dark``) to a palette."""
    if mode == "system":
        mode = detect_system_theme()
    return DARK if mode == "dark" else LIGHT


def apply(root: tk.Misc, palette: Palette) -> None:
    """Restyle ttk and the Tk defaults for ``palette``."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    p = palette
    base_font = (FONT_FAMILY, 10)

    root.option_add("*Font", base_font)
    # Raw tk widgets (Text, Canvas, Toplevel) do not follow ttk styles.
    for option, value in (
        ("*background", p.bg),
        ("*foreground", p.fg),
        ("*Text.background", p.surface),
        ("*Text.foreground", p.fg),
        ("*Text.insertBackground", p.fg),
        ("*Text.selectBackground", p.accent),
        ("*Text.selectForeground", p.accent_fg),
        ("*Canvas.background", p.surface),
        ("*Canvas.highlightBackground", p.border),
    ):
        root.option_add(option, value)

    try:
        root.configure(background=p.bg)
    except tk.TclError:
        pass

    style.configure(".", background=p.bg, foreground=p.fg,
                    fieldbackground=p.surface_alt, bordercolor=p.border,
                    font=base_font)
    style.configure("TFrame", background=p.bg)
    style.configure("Card.TFrame", background=p.surface, relief="flat")
    style.configure("TLabel", background=p.bg, foreground=p.fg)
    style.configure("Muted.TLabel", background=p.bg, foreground=p.fg_muted)
    style.configure("Card.TLabel", background=p.surface, foreground=p.fg)
    style.configure("CardMuted.TLabel", background=p.surface, foreground=p.fg_muted,
                    font=(FONT_FAMILY, 8, "bold"))
    style.configure("Heading.TLabel", background=p.bg, foreground=p.fg,
                    font=(FONT_FAMILY, 12, "bold"))
    style.configure("Metric.TLabel", background=p.surface, foreground=p.fg,
                    font=(FONT_FAMILY, 15, "bold"))
    style.configure("MetricBig.TLabel", background=p.surface, foreground=p.accent,
                    font=(FONT_FAMILY, 36, "bold"))
    style.configure("Ok.TLabel", background=p.bg, foreground=p.ok,
                    font=(FONT_FAMILY, 10, "bold"))
    style.configure("Error.TLabel", background=p.bg, foreground=p.error,
                    font=(FONT_FAMILY, 10, "bold"))
    style.configure("Warn.TLabel", background=p.bg, foreground=p.warn,
                    font=(FONT_FAMILY, 10, "bold"))
    style.configure("Demo.TLabel", background=p.warn, foreground="#1a1205",
                    font=(FONT_FAMILY, 10, "bold"), padding=6, anchor="center")

    style.configure("TLabelframe", background=p.bg, bordercolor=p.border,
                    relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=p.bg, foreground=p.fg_muted,
                    font=(FONT_FAMILY, 9, "bold"))

    style.configure("TButton", background=p.surface_alt, foreground=p.fg,
                    bordercolor=p.border, focuscolor=p.accent,
                    padding=(10, 6), relief="flat")
    style.map("TButton",
              background=[("pressed", p.border), ("active", p.border),
                          ("disabled", p.surface)],
              foreground=[("disabled", p.fg_muted)])
    style.configure("Accent.TButton", background=p.accent, foreground=p.accent_fg,
                    padding=(10, 8), relief="flat", font=(FONT_FAMILY, 10, "bold"))
    style.map("Accent.TButton",
              background=[("pressed", p.border), ("active", p.accent),
                          ("disabled", p.surface_alt)],
              foreground=[("disabled", p.fg_muted)])

    style.configure("TEntry", fieldbackground=p.surface_alt, foreground=p.fg,
                    bordercolor=p.border, insertcolor=p.fg, padding=4)
    style.configure("TSpinbox", fieldbackground=p.surface_alt, foreground=p.fg,
                    bordercolor=p.border, arrowcolor=p.fg, padding=4)
    style.configure("TCombobox", fieldbackground=p.surface_alt, foreground=p.fg,
                    background=p.surface_alt, bordercolor=p.border,
                    arrowcolor=p.fg, padding=4)
    style.map("TCombobox",
              fieldbackground=[("readonly", p.surface_alt)],
              foreground=[("disabled", p.fg_muted)])
    # The dropdown list is a raw Tk listbox owned by Tk, not by ttk.
    root.option_add("*TCombobox*Listbox.background", p.surface_alt)
    root.option_add("*TCombobox*Listbox.foreground", p.fg)
    root.option_add("*TCombobox*Listbox.selectBackground", p.accent)
    root.option_add("*TCombobox*Listbox.selectForeground", p.accent_fg)

    style.configure("TCheckbutton", background=p.bg, foreground=p.fg,
                    focuscolor=p.accent)
    style.map("TCheckbutton",
              background=[("active", p.bg)],
              indicatorcolor=[("selected", p.accent), ("!selected", p.surface_alt)])
    style.configure("TRadiobutton", background=p.bg, foreground=p.fg)
    style.map("TRadiobutton", background=[("active", p.bg)])

    style.configure("TNotebook", background=p.bg, bordercolor=p.border, tabmargins=(2, 6, 2, 0))
    style.configure("TNotebook.Tab", background=p.surface_alt, foreground=p.fg_muted,
                    padding=(16, 9), font=(FONT_FAMILY, 10, "bold"))
    style.map("TNotebook.Tab",
              background=[("selected", p.bg)],
              foreground=[("selected", p.accent)])

    style.configure("Treeview", background=p.surface, fieldbackground=p.surface,
                    foreground=p.fg, bordercolor=p.border, rowheight=26)
    style.map("Treeview",
              background=[("selected", p.accent)],
              foreground=[("selected", p.accent_fg)])
    style.configure("Treeview.Heading", background=p.surface_alt, foreground=p.fg,
                    font=(FONT_FAMILY, 9, "bold"), relief="flat", padding=5)
    style.map("Treeview.Heading", background=[("active", p.border)])

    style.configure("TSeparator", background=p.border)
    style.configure("Vertical.TScrollbar", background=p.surface_alt,
                    troughcolor=p.bg, bordercolor=p.border, arrowcolor=p.fg)
    style.configure("Horizontal.TScrollbar", background=p.surface_alt,
                    troughcolor=p.bg, bordercolor=p.border, arrowcolor=p.fg)


def style_figure(figure, palette: Palette) -> None:
    """Recolour a matplotlib figure and all of its axes."""
    figure.patch.set_facecolor(palette.surface)
    for ax in figure.get_axes():
        style_axes(ax, palette)


def style_axes(ax, palette: Palette) -> None:
    p = palette
    ax.set_facecolor(p.surface)
    ax.tick_params(colors=p.fg_muted, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(p.border)
    ax.xaxis.label.set_color(p.fg_muted)
    ax.yaxis.label.set_color(p.fg_muted)
    ax.title.set_color(p.fg)
    ax.grid(True, color=p.grid, alpha=0.55, linewidth=0.7)
    ax.set_axisbelow(True)


def series_style(index: int, palette: Palette) -> dict:
    """Colour + linestyle + marker for series ``index``.

    Colour alone is never the only difference between two series.
    """
    return {
        "color": palette.series[index % len(palette.series)],
        "linestyle": SERIES_LINESTYLES[index % len(SERIES_LINESTYLES)],
        "marker": SERIES_MARKERS[index % len(SERIES_MARKERS)],
    }
