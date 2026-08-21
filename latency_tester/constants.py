"""Shared UI choice lists and the measurement-mode identifiers."""

POLLING_RATES = ("125", "250", "500", "1000", "2000", "4000", "8000")
CONNECTION_MODES = ("Wireless", "Wired", "Bluetooth", "Altro")

#: Stored verbatim in ``runs.mode``.  Never translated, never renamed: archived
#: runs are matched against these strings.
MODE_PROBE_PC = "probe_to_pc"
MODE_PHOTON = "probe_to_photon"
MEASUREMENT_MODES = (MODE_PROBE_PC, MODE_PHOTON)

#: Label key per mode, for the interface.
MODE_LABELS = {
    MODE_PROBE_PC: "mode.probe_to_pc",
    MODE_PHOTON: "mode.probe_to_photon",
}
