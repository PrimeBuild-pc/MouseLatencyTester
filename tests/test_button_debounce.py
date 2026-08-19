"""Behaviour check for the firmware v1.4 button debounce.

`ButtonDebouncer` below is a line-for-line transcription of `serviceButtons()`
and `flushButtonEvents()` in
`firmware/latency_tester_oled_ldr_v1_4/latency_tester_oled_ldr_v1_4.ino`.
It exists so the acceptance rules ("10 presses -> 10 events", "a held button
never repeats", "nothing is transmitted between t0 and t1") are verified in CI
instead of only on the bench.

**If the .ino changes, change this too** — it is a mirror, not an import.
"""

import pytest

HIGH, LOW = 1, 0
BUTTON_COUNT = 2
BUTTON_DEBOUNCE_MS = 30


class ButtonDebouncer:
    """Mirror of the firmware logic, driven by a simulated millis() clock."""

    def __init__(self):
        self.now = 0
        self.pin = [HIGH] * BUTTON_COUNT           # physical level
        self.reading = [HIGH] * BUTTON_COUNT       # buttonReading[]
        self.stable = [HIGH] * BUTTON_COUNT        # buttonStable[]
        self.changed_at = [0] * BUTTON_COUNT       # buttonChangedAt[]
        self.pending = 0                           # pendingButtonPress
        self.measurement_active = False
        self.probe_flag = False
        self.emitted = [0] * BUTTON_COUNT          # Serial.println() calls

    def service_buttons(self) -> None:
        now = self.now
        for i in range(BUTTON_COUNT):
            reading = self.pin[i]
            if reading != self.reading[i]:
                self.reading[i] = reading
                self.changed_at[i] = now
                continue
            if (reading != self.stable[i]
                    and (now - self.changed_at[i]) >= BUTTON_DEBOUNCE_MS):
                self.stable[i] = reading
                if reading == LOW:
                    self.pending |= 1 << i

    def flush_button_events(self) -> None:
        if self.pending == 0:
            return
        if self.measurement_active or self.probe_flag:
            return
        for i in range(BUTTON_COUNT):
            if self.pending & (1 << i):
                self.emitted[i] += 1
        self.pending = 0

    # -- test helpers -----------------------------------------------------
    def tick(self, milliseconds: int) -> None:
        """Run loop() for n milliseconds (the sketch ends with delay(1))."""
        for _ in range(milliseconds):
            self.now += 1
            self.service_buttons()
            self.flush_button_events()

    def press(self, button: int, hold_ms: int = 120, gap_ms: int = 120) -> None:
        self.pin[button] = LOW
        self.tick(hold_ms)
        self.pin[button] = HIGH
        self.tick(gap_ms)


@pytest.fixture
def buttons():
    return ButtonDebouncer()


def test_idle_produces_no_phantom_events(buttons):
    buttons.tick(2000)
    assert buttons.emitted == [0, 0]


@pytest.mark.parametrize("button", [0, 1])
def test_ten_presses_give_exactly_ten_events(buttons, button):
    """The bench acceptance criterion, in CI."""
    for _ in range(10):
        buttons.press(button)
    assert buttons.emitted[button] == 10
    assert buttons.emitted[1 - button] == 0


def test_a_held_button_never_repeats(buttons):
    buttons.pin[0] = LOW
    buttons.tick(3000)          # held for three seconds
    assert buttons.emitted[0] == 1
    buttons.pin[0] = HIGH
    buttons.tick(200)
    assert buttons.emitted[0] == 1


def test_contact_bounce_produces_one_event(buttons):
    for index in range(6):      # 12 ms of chatter, under the debounce window
        buttons.pin[0] = HIGH if index % 2 else LOW
        buttons.tick(2)
    buttons.pin[0] = LOW
    buttons.tick(150)
    buttons.pin[0] = HIGH
    buttons.tick(150)
    assert buttons.emitted[0] == 1


def test_release_bounce_does_not_add_an_event(buttons):
    buttons.pin[0] = LOW
    buttons.tick(150)
    for index in range(6):
        buttons.pin[0] = LOW if index % 2 else HIGH
        buttons.tick(2)
    buttons.pin[0] = HIGH
    buttons.tick(150)
    assert buttons.emitted[0] == 1


def test_a_press_shorter_than_the_debounce_window_is_ignored(buttons):
    buttons.pin[0] = LOW
    buttons.tick(10)            # 10 ms < 30 ms
    buttons.pin[0] = HIGH
    buttons.tick(200)
    assert buttons.emitted[0] == 0


def test_nothing_is_transmitted_during_a_measurement(buttons):
    """The core timing guarantee: no serial output between t0 and t1."""
    buttons.measurement_active = True
    buttons.pin[0] = LOW
    buttons.tick(500)
    assert buttons.emitted[0] == 0          # queued, not sent
    assert buttons.pending == 0b01          # ...but not lost either

    buttons.measurement_active = False
    buttons.tick(5)
    assert buttons.emitted[0] == 1          # flushed once it is safe


def test_nothing_is_transmitted_while_a_probe_event_is_pending(buttons):
    buttons.probe_flag = True
    buttons.press(1)
    assert buttons.emitted[1] == 0
    buttons.probe_flag = False
    buttons.tick(5)
    assert buttons.emitted[1] == 1


def test_both_buttons_are_independent(buttons):
    for _ in range(3):
        buttons.press(0)
    for _ in range(7):
        buttons.press(1)
    assert buttons.emitted == [3, 7]


def test_simultaneous_presses_both_report(buttons):
    buttons.pin[0] = LOW
    buttons.pin[1] = LOW
    buttons.tick(150)
    assert buttons.emitted == [1, 1]


def test_a_button_held_at_power_on_produces_no_press(buttons):
    """setup() seeds the debounce state from the real pin level."""
    buttons.pin[0] = LOW
    buttons.reading[0] = LOW    # as seeded in setup()
    buttons.stable[0] = LOW
    buttons.tick(500)
    assert buttons.emitted[0] == 0
    # Releasing and pressing again works normally.
    buttons.pin[0] = HIGH
    buttons.tick(150)
    buttons.press(0)
    assert buttons.emitted[0] == 1
