"""Latency Tester — desktop benchmark manager for the Teensy 2.0 probe tester."""

__version__ = "1.2.0"

# Firmware versions this release speaks.  v1.3 is the measurement baseline;
# v1.4 adds the BTN1/BTN2 test events; v1.5 adds Probe-to-Photon and leaves the
# Probe-to-PC measurement path byte-identical to both.
SUPPORTED_FIRMWARE = ("v1.3", "v1.4", "v1.5")
RECOMMENDED_FIRMWARE = "v1.5"
#: Probe-to-Photon needs firmware that has the optical path.
PHOTON_FIRMWARE = "v1.5"

__all__ = ["__version__", "SUPPORTED_FIRMWARE", "RECOMMENDED_FIRMWARE",
           "PHOTON_FIRMWARE"]
