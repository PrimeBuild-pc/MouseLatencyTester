"""Shared UI choice lists and the measurement-mode identifiers."""

POLLING_RATES = ("125", "250", "500", "1000", "2000", "4000", "8000")
CONNECTION_MODES = ("Wireless", "Wired", "Bluetooth", "Altro")

#: Stored verbatim in ``runs.mode``.  Never translated, never renamed: archived
#: runs are matched against these strings.
MODE_PROBE_PC = "probe_to_pc"
MODE_PHOTON = "probe_to_photon"
#: Reserved now so the archive vocabulary is fixed before the mode exists: a run
#: written by a later build must be readable by this one.  Not selectable yet --
#: it needs the photodiode front-end, see docs/optical_front_end.md.
MODE_INGAME = "probe_to_photon_ingame"
MEASUREMENT_MODES = (MODE_PROBE_PC, MODE_PHOTON)
KNOWN_MODES = (MODE_PROBE_PC, MODE_PHOTON, MODE_INGAME)

#: Label key per mode, for the interface.
MODE_LABELS = {
    MODE_PROBE_PC: "mode.probe_to_pc",
    MODE_PHOTON: "mode.probe_to_photon",
    MODE_INGAME: "mode.probe_to_photon_ingame",
}

#: Frame caps offered for the optical target, in frames per second.  Fixed steps
#: rather than a free field: the point is to compare a handful of well-known
#: cadences, and a spinbox would invite 137 fps.
FRAME_CAPS = (30, 60, 120, 240, 360, 500, 1000)
#: Sentinel for "whatever the monitor is running at".
FRAME_CAP_AUTO = 0
#: Used when auto is selected and Windows will not say what the refresh rate is.
FRAME_CAP_FALLBACK = 1000
