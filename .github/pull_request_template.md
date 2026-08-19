## What this changes

<!-- One or two sentences. -->

## Why

<!-- The problem being solved. -->

## Checklist

- [ ] `python -m pytest tests -q` passes
- [ ] New logic has a test
- [ ] No new runtime dependency (or it is justified below)
- [ ] The app still starts — demo mode is enough

## Does this touch the measurement pipeline?

<!--
The pipeline is: TRIG↔click association, t0/t1, calibration, the 2-100 ms
filter, debounce/re-arm, test mode, the OLED freeze, existing protocol tokens.
-->

- [ ] No, this does not touch it
- [ ] Yes — and I have included below **what** changed, **why**, and the
      before/after measurements

<!-- If yes, paste the numbers. Two saved runs compared with one as baseline. -->

## Firmware

- [ ] Not applicable
- [ ] I added a new versioned sketch directory and left older ones untouched
- [ ] I updated `docs/serial_protocol.md` including the compatibility table
- [ ] I updated the mirror test in `tests/test_button_debounce.py` if the
      corresponding firmware logic changed
