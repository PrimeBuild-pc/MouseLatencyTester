"""Full-screen test mode overlay.

Colour is the whole message: GREEN = armed, RED = wait/release, BLUE = target
reached.  The overlay only reads state the app already computed; it never
issues serial commands and never blocks, so it cannot influence timing.

In Probe-to-Photon it also carries the optical target: a black rectangle that
turns white the moment Windows reports the click.  The KY-018 is aimed at that
rectangle, and the Teensy times from the probe contact to the light change.
The rectangle is a bare Label with no bindings, so it can never be clicked.

The repaint is driven by a poll rather than by the input callback: touching a
Tk widget from the ``pynput`` thread is not safe.  That poll -- and the paint
itself -- happen on the machine under test and are therefore *inside* the
measured interval.  That is not a defect of the method: click-to-photon
measures everything up to the photons, the application included.
"""

from __future__ import annotations

import logging
import time
import tkinter as tk
from typing import TYPE_CHECKING

from ..i18n import translator as tr
from ..stats import compute_stats, fmt_ms
from ..theme import FONT_FAMILY

if TYPE_CHECKING:
    from ..app import LatencyTesterApp


log = logging.getLogger(__name__)

#: How often the optical target looks for a new OS click when no frame cap is in
#: force.  1 ms is the finest Tk offers; whatever is left is part of what
#: click-to-photon measures.
TARGET_POLL_MS = 1
#: The optical target, in pixels, and where it sits on the screen.  Deliberately
#: large: the sensor is held on the glass with elastic bands, not aligned on an
#: optical bench, and a target you have to hit precisely is a target you miss.
#: The calibration window and the test overlay use the *same* numbers, because a
#: baseline is only worth anything if it comes from the patch of screen the
#: measurement will use.
TARGET_W_PX = 620
TARGET_H_PX = 440
TARGET_RELY = 0.5
#: Where the text sits in the test overlay when the target owns the middle.
PHOTON_TEXT_RELY = 0.17


def place_target(parent: tk.Misc) -> tk.Label:
    """The black/white target, centred, identical in both windows."""
    holder = tk.Frame(parent, width=TARGET_W_PX, height=TARGET_H_PX,
                      background="#000000")
    holder.place(relx=0.5, rely=TARGET_RELY, anchor="center")
    holder.pack_propagate(False)
    target = tk.Label(holder, background="#000000", foreground="#3a3a3a",
                      text=tr("photon.target"), font=(FONT_FAMILY, 12, "bold"))
    target.pack(fill="both", expand=True)
    return target


class OpticalCalibrationWindow:
    """Full-screen black window with a centred target, for calibrating alone.

    Same geometry as the test-mode target, on purpose: the whole point is that
    the baselines come from the patch of screen the measurement will use. Tape
    the KY-018 to the middle of the screen once and it stays valid for both.

    Exposes the same three methods the test overlay does — ``show_calibrating``,
    ``finish_calibration`` and ``close`` — so the app drives either with one
    piece of code.
    """

    def __init__(self, root: tk.Misc, app: LatencyTesterApp):
        self.app = app
        self._target_bright = False

        window = tk.Toplevel(root)
        self.window = window
        window.title(f"{tr('app.title')} — {tr('photon.calibrate')}")
        window.attributes("-fullscreen", True)
        window.attributes("-topmost", True)
        window.configure(background="#0b0b0b", cursor="none")
        window.bind("<Escape>", lambda _e: self.app.cancel_optical_calibration())
        window.bind("<Return>", lambda _e: self.app.retry_optical_calibration())
        window.bind("<space>", lambda _e: self.app.retry_optical_calibration())
        window.protocol("WM_DELETE_WINDOW", self.app.cancel_optical_calibration)

        top = tk.Frame(window, background="#0b0b0b")
        top.place(relx=0.5, rely=0.12, anchor="center")

        self.state = tk.Label(top, text=tr("photon.calibrating_state"),
                              font=(FONT_FAMILY, 22, "bold"),
                              background="#0b0b0b", foreground="#8a8a8a")
        self.state.pack()
        self.hint = tk.Label(top, text=tr("photon.calibrating"),
                             font=(FONT_FAMILY, 13), background="#0b0b0b",
                             foreground="#8a8a8a", wraplength=900,
                             justify="center")
        self.hint.pack(pady=(10, 0))

        self.target_area = place_target(window)

        # Live reading, so aiming is not guesswork: if this number barely moves
        # between the black and the white phase, the sensor is not on the target.
        bottom = tk.Frame(window, background="#0b0b0b")
        bottom.place(relx=0.5, rely=0.9, anchor="center")
        tk.Label(bottom, text=tr("live.light"), font=(FONT_FAMILY, 12),
                 background="#0b0b0b", foreground="#6a6a6a").pack(side="left")
        tk.Label(bottom, textvariable=app.light_var,
                 font=(FONT_FAMILY, 20, "bold"), background="#0b0b0b",
                 foreground="#c8c8c8").pack(side="left", padx=(12, 0))

        window.focus_force()

    def show_calibrating(self, bright: bool) -> None:
        self._paint(bright)
        try:
            self.state.configure(text=tr("photon.calibrating_state"))
            self.hint.configure(text=tr("photon.calibrating"))
        except tk.TclError:
            log.debug("calibration window is gone")

    def finish_calibration(self, ok: bool, reason: str) -> None:
        self._paint(False)
        try:
            self.state.configure(
                text=tr("photon.calibrating_done") if ok
                else tr("photon.calibrating_failed"),
                foreground="#4ade80" if ok else "#f87171")
            self.hint.configure(
                text=reason if ok
                else reason + "\n\n" + tr("photon.retry_hint"))
        except tk.TclError:
            log.debug("calibration window is gone")
        if ok:
            # A success is a step, not a place to sit: show it, then get out.
            self.window.after(1800, self.app.cancel_optical_calibration)
        # A failure stays put on purpose.  The live reading below is the only
        # tool for aiming the sensor, and it is useless once the window closes.

    def _paint(self, bright: bool) -> None:
        self._target_bright = bright
        try:
            self.target_area.configure(
                background="#ffffff" if bright else "#000000",
                foreground="#b0b0b0" if bright else "#4d4d4d")
            self.target_area.update_idletasks()
        except tk.TclError:
            log.debug("calibration target is gone")

    def close(self) -> None:
        try:
            self.window.destroy()
        except tk.TclError:
            log.debug("calibration window was already destroyed")


class TestModeOverlay:
    def __init__(self, root: tk.Misc, app: LatencyTesterApp, target: int):
        self.app = app
        self.target = target
        self.mode = "wait"
        self.photon = app.photon_mode
        # In Probe-to-Photon the overlay opens in a calibration phase: the two
        # baselines have to be sampled from the *same* screen area the test
        # will use, or the threshold describes a different patch of screen.
        self.calibrating = app.photon_mode
        self.target_area: tk.Label | None = None
        self._target_bright = False
        self._last_click_ns = app.serial.clicks.last_click_ns
        self._poll_id: str | None = None
        self._alive = True

        # Frame cadence.  A game samples input at the start of a frame and
        # presents at the end, so one timer at the frame interval models both:
        # a click lands at a uniform point inside a frame and waits for the next
        # boundary, which is exactly the quantisation being measured.
        self.frame_cap = app.effective_frame_cap() if self.photon else 0
        self._frame_s = 1.0 / self.frame_cap if self.frame_cap else 0.001
        self._next_frame = time.perf_counter() + self._frame_s

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

        if self.photon:
            # The target owns the middle of the screen, so the numbers move up.
            inner.place_configure(rely=PHOTON_TEXT_RELY)
            self._build_target()
            # On screen because a screenshot of a run has to carry its own
            # conditions: the same mouse at 30 and at 360 fps is two results.
            self._label(inner, tr("photon.frame_cap_active", fps=self.frame_cap),
                        13, "bold", pady=(6, 0))

        self.set_mode("wait")
        window.focus_force()
        if self.photon:
            self._poll_click()

    # ------------------------------------------------------------- optical --

    def _build_target(self) -> None:
        """The optical target.  No bindings, ever: aiming must not click.

        Placed on the window rather than inside the text block, at exactly the
        position and size the calibration window uses.
        """
        self.target_area = place_target(self.frame)

    def show_calibrating(self, bright: bool) -> None:
        """Paint the target for one calibration baseline."""
        self.calibrating = True
        self._set_target_bright(bright)
        try:
            self.hint.configure(text=tr("photon.calibrating"))
            self.state.configure(text=tr("photon.calibrating_state"))
        except tk.TclError:
            log.debug("overlay is gone during calibration")

    def finish_calibration(self, ok: bool, reason: str) -> None:
        """Hand control back to the normal arm/wait cycle, or refuse to start."""
        self._set_target_bright(False)
        if ok:
            self.calibrating = False
            self.mode = ""          # force the next set_mode() to repaint
            self.set_mode("wait")
            return
        # Still blocked: the firmware would answer OPT_ERR:NO_CAL anyway, but
        # the person in front of a full-screen window deserves to be told why.
        try:
            self.state.configure(text=tr("photon.calibrating_failed"))
            self.hint.configure(text=reason)
        except tk.TclError:
            log.debug("overlay is gone after a failed calibration")

    def _set_target_bright(self, bright: bool) -> None:
        if self.target_area is None or bright == self._target_bright:
            return
        self._target_bright = bright
        try:
            self.target_area.configure(
                background="#ffffff" if bright else "#000000",
                foreground="#b0b0b0" if bright else "#4d4d4d")
            # Paint now: everything after this point is the display's own
            # latency, which is exactly what this mode is trying to measure.
            self.target_area.update_idletasks()
        except tk.TclError:
            log.debug("optical target is gone")

    def _poll_click(self) -> None:
        """Turn the target white on the first frame boundary after the click."""
        if not self._alive:
            return
        latest = self.app.serial.clicks.last_click_ns
        if latest != self._last_click_ns:
            self._last_click_ns = latest
            # A click during calibration must not disturb the baseline being
            # sampled; the calibration owns the target until it is done.
            if not self.calibrating:
                self._set_target_bright(True)
        self._schedule_next_frame()

    def _schedule_next_frame(self) -> None:
        """Keep the long-run cadence honest.

        ``after()`` takes whole milliseconds, and 360 fps is 2.78 ms.  Rounding
        every tick would drift 8%; aiming at an absolute deadline instead keeps
        the average right even though individual ticks land on 3 ms or 2 ms.
        """
        now = time.perf_counter()
        self._next_frame += self._frame_s
        if self._next_frame < now:
            # Fell behind -- Tk was busy, or the cap is finer than the event
            # loop can serve.  Resynchronise rather than trying to catch up.
            self._next_frame = now + self._frame_s
        delay = max(TARGET_POLL_MS, round((self._next_frame - now) * 1000))
        try:
            self._poll_id = self.window.after(delay, self._poll_click)
        except tk.TclError:
            self._poll_id = None

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

        # A fresh arm/re-arm means the next press is still to come, so the
        # target goes back to black and the sensor sees a real transition.
        # Done before the short-circuit below: a target left white would make
        # the firmware answer OPT_ERR:NOT_DARK on the very next press.
        if mode in ("armed", "wait") and not self.calibrating:
            self._set_target_bright(False)

        # While calibrating, the arm/re-arm text would overwrite the progress
        # message; the calibration hands control back when it is finished.
        if self.calibrating:
            return

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
            if self.target_area is not None:
                # Deliberately excluded from the recolour above: black and
                # white are the measurement, not decoration.
                self._set_target_bright(self._target_bright)
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
        self._alive = False
        if self._poll_id is not None:
            try:
                self.window.after_cancel(self._poll_id)
            except tk.TclError:
                log.debug("target poll was already cancelled")
            self._poll_id = None
        try:
            self.window.destroy()
        except tk.TclError:
            log.debug("overlay was already destroyed")
