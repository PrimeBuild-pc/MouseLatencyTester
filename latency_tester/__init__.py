"""Latency Tester — desktop benchmark manager for the Teensy 2.0 probe tester."""

__version__ = "3.0.0"

# Firmware versions this release speaks.  v1.3 is the measurement baseline;
# v1.4 adds the BTN1/BTN2 test events and changes nothing else.
SUPPORTED_FIRMWARE = ("v1.3", "v1.4")
RECOMMENDED_FIRMWARE = "v1.4"

__all__ = ["__version__", "SUPPORTED_FIRMWARE", "RECOMMENDED_FIRMWARE"]
