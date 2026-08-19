"""Full-screen test mode overlay.

Colour is the whole message: GREEN = armed, RED = wait/release, BLUE = target
reached.  The overlay only reads state the app already computed; it never
issues serial commands and never blocks, so it cannot influence timing.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import TYPE_CHECKING

from ..i18n import translator as tr
from ..stats import compute_stats, fmt_ms
from ..theme import FONT_FAMILY

if TYPE_CHECKING:
    from ..app import LatencyTesterApp


log = logging.getLogger(__name__)


class TestModeOverlay:
    def __init__(self, root: tk.Misc, app: "LatencyTesterApp", target: int):
        self.app = app
        self.target = target
        self.mode = "wait"

        window = tk.Toplevel(root)
        self.window = window
        window.title(f"{tr('app.title')} — {tr('test.title')}")
        window.attributes("-fullscreen", True)
        window.attributes("-topmost", True)
        window.configure(cursor="none")
        window.bind("<Escape>", lambda _e: self.app.exit_test_mode())
        window.protocol("WM_DELETE_WINDOW", self.app.exit_test_mode)

        frame = tk.Frame(window)
        self.frame = frame
        frame.pack(fill="both", expand=True)

        # Everything lives in a block centred on the screen: at 1440p a
        # top-aligned layout leaves most of the display empty, and the point of
        # this screen is to be readable at a glance from a normal seating
        # distance.
        inner = tk.Frame(frame)
        self.inner = inner
        inner.place(relx=0.5, rely=0.5, anchor="center")

        device = self.app.device_var.get().strip() or "—"
        run_name = self.app.run_name_var.get().strip()
        polling = self.app.polling_var.get().strip()
        parts = [device, run_name]
        # Do not repeat the rate when the run name already carries it.
        if polling and f"{polling} Hz" not in run_name:
            parts.append(f"{polling} Hz")
        header = " — ".join(x for x in parts if x)

        self.labels: list[tk.Label] = []
        self._label(inner, header, 22, "bold", pady=(0, 6))
        if self.app.is_demo:
            self._label(inner, tr("app.demo_banner"), 13, "bold", pady=(0, 6))
        self._label(inner, tr("test.title"), 30, "bold", pady=(0, 14))

        self.hint = self._label(inner, tr("test.wait_hint"), 18, "bold", pady=(0, 0))
        self.state = self._label(inner, tr("test.preparing"), 24, "bold", pady=(28, 6))

        self.value = self._label(inner, "—", 96, "bold")
        self._label(inner, "ms", 20, "normal")

        row = tk.Frame(inner)
        self.frame_children_rows = [row]
        row.pack(pady=30)
        self.median = self._label(row, f"{tr('test.median')} —", 18, "bold", side="left")
        self.p95 = self._label(row, f"{tr('test.p95')} —", 18, "bold", side="left")
        self.count = self._label(row, f"N 0 / {target}", 18, "bold", side="left")

        self._label(inner, tr("test.exit"), 12, "normal", pady=(10, 0))

        self.set_mode("wait")
        window.focus_force()

    def _label(self, parent: tk.Misc, text: str, size: int, weight: str,
               pady=0, side: str | None = None) -> tk.Label:
        label = tk.Label(parent, text=text, font=(FONT_FAMILY, size, weight))
        if side:
            label.pack(side=side, padx=24)
        else:
            label.pack(pady=pady)
        self.labels.append(label)
        return label

    def set_mode(self, mode: str) -> None:
        palette = self.app.palette
        if mode == "armed":
            background = palette.test_armed
            state, hint = tr("test.armed_state"), tr("test.armed_hint")
        elif mode == "complete":
            background = palette.test_done
            state, hint = tr("test.complete_state"), tr("test.complete_hint")
        else:
            mode = "wait"
            background = palette.test_wait
            state, hint = tr("test.wait_state"), tr("test.wait_hint")

        if mode == self.mode and self.state.cget("text") == state:
            return
        self.mode = mode

        try:
            self.frame.configure(background=background)
            self.inner.configure(background=background)
            for row in self.frame_children_rows:
                row.configure(background=background)
            for label in self.labels:
                label.configure(background=background, foreground="#ffffff")
            self.state.configure(text=state)
            self.hint.configure(text=hint)
        except tk.TclError:
            log.debug("overlay recolour skipped: the window is already gone")

    def refresh(self) -> None:
        """Repaint the numbers.  Called from the app's event pump."""
        values = [s["latency_ms"] for s in self.app.current_samples]
        stats = compute_stats(values)
        try:
            self.value.configure(text=fmt_ms(values[-1]) if values else "—")
            self.median.configure(text=f"{tr('test.median')} {fmt_ms(stats['median'])} ms")
            self.p95.configure(text=f"{tr('test.p95')} {fmt_ms(stats['p95'])} ms")
            self.count.configure(
                text=f"N {self.app.test_sample_count()} / {self.target}")
        except tk.TclError:
            log.debug("overlay refresh skipped: the window is already gone")

    def close(self) -> None:
        try:
            self.window.destroy()
        except tk.TclError:
            log.debug("overlay was already destroyed")
