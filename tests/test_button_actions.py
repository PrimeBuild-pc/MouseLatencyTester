"""BTN1/BTN2 semantics: the firmware reports, the dashboard decides.

``_button_action`` is called directly on a stub instead of a real window: the
guards *are* the function, and they must hold without a Tk root.
"""

import pytest

pytest.importorskip("tkinter")

from latency_tester import app as app_module  # noqa: E402
from latency_tester.app import LatencyTesterApp  # noqa: E402


class _Serial:
    def __init__(self, connected=True, calibrating=False):
        self.connected = connected
        self.calibrating = calibrating


class _Flag:
    """Stand-in for a ``tk.BooleanVar``."""

    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class _App:
    """Just enough dashboard for the button rules."""

    press = LatencyTesterApp._button_action

    def __init__(self, connected=True, calibrating=False, test_mode=False,
                 confirm_btn2=False, samples=0):
        self.serial = _Serial(connected, calibrating)
        self.test_mode = test_mode
        self.confirm_btn2_var = _Flag(confirm_btn2)
        self.current_samples = [{"latency_ms": 5.0}] * samples
        self.calls: list[str] = []
        self.logs: list[str] = []

    def enter_test_mode(self):
        self.calls.append("enter")

    def exit_test_mode(self):
        self.calls.append("exit")

    def reset_stats(self):
        self.calls.append("reset")

    def log(self, message):
        self.logs.append(message)


def test_btn1_enters_test_mode_when_idle():
    app = _App()
    app.press(1)
    assert app.calls == ["enter"]


def test_btn1_leaves_test_mode_when_it_is_running():
    app = _App(test_mode=True)
    app.press(1)
    assert app.calls == ["exit"]


def test_btn2_clears_the_live_run_outside_test_mode():
    app = _App()
    app.press(2)
    assert app.calls == ["reset"]


def test_btn2_is_refused_inside_test_mode():
    """The whole point: a stray press must never wipe a running test."""
    app = _App(test_mode=True)
    app.press(2)
    assert app.calls == []
    assert len(app.logs) == 1


@pytest.mark.parametrize("index", [1, 2])
def test_nothing_acts_while_calibrating(index):
    app = _App(calibrating=True)
    app.press(index)
    assert app.calls == []
    assert len(app.logs) == 1


@pytest.mark.parametrize("index", [1, 2])
def test_nothing_acts_while_disconnected(index):
    app = _App(connected=False)
    app.press(index)
    assert app.calls == []


def test_an_unknown_button_does_nothing():
    app = _App()
    app.press(3)
    assert app.calls == []


@pytest.fixture
def answer(monkeypatch):
    """Replace the confirmation dialog with a scripted answer."""
    box = {"asked": 0, "reply": True}

    def fake_askyesno(*_args, **_kwargs):
        box["asked"] += 1
        return box["reply"]

    monkeypatch.setattr(app_module.messagebox, "askyesno", fake_askyesno)
    return box


def test_btn2_asks_first_when_the_confirmation_is_on(answer):
    """Default-on, because BTN2 sits on the same desk as the mouse being
    tested and a knock must not cost a run."""
    answer["reply"] = True
    app = _App(confirm_btn2=True, samples=4)
    app.press(2)
    assert answer["asked"] == 1
    assert app.calls == ["reset"]


def test_a_refused_confirmation_keeps_the_run(answer):
    answer["reply"] = False
    app = _App(confirm_btn2=True, samples=4)
    app.press(2)
    assert answer["asked"] == 1
    assert app.calls == []
    assert len(app.logs) == 1


def test_btn2_with_the_confirmation_on_but_nothing_to_lose(answer):
    """No samples yet means nothing to lose: reset without asking."""
    app = _App(confirm_btn2=True, samples=0)
    app.press(2)
    assert answer["asked"] == 0
    assert app.calls == ["reset"]


def test_the_confirmation_can_be_switched_off(answer):
    app = _App(confirm_btn2=False, samples=4)
    app.press(2)
    assert answer["asked"] == 0
    assert app.calls == ["reset"]
