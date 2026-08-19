"""What Windows can tell us about the physically connected mouse.

Two separate things live here:

* :func:`detect_mice` — *identification*. Reads the USB string descriptors
  Windows cached (``HidD_GetProductString`` and friends), because the registry
  only ever reports the generic INF name "HID-compliant mouse".
* :func:`measure_report_rate` — *measurement*. Counts Raw Input movement
  reports to work out the polling rate the mouse is actually achieving.

**DPI is deliberately absent.** No Windows API exposes it: it lives entirely
inside the mouse, and vendor software reads it over undocumented vendor-specific
HID reports that differ per manufacturer. Guessing it would put a wrong number
into benchmark metadata, which is worse than leaving the field blank.

Everything here is Windows-only and degrades to "no information" elsewhere,
never raising.
"""

from __future__ import annotations

import ctypes
import logging
import re
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable

log = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

# --------------------------------------------------------------- constants --
RIM_TYPEMOUSE = 0
RIDI_DEVICENAME = 0x20000007
RID_INPUT = 0x10000003
RIDEV_INPUTSINK = 0x00000100
WM_INPUT = 0x00FF
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

#: Gaps longer than this mean the hand stopped; they are excluded from the rate.
IDLE_GAP_S = 0.05
#: Below this many usable intervals the result is not trustworthy.
MIN_INTERVALS = 40

#: Nominal rates a result is snapped to when it is close enough.
COMMON_RATES = (125, 250, 500, 1000, 2000, 4000, 8000)
#: Fractional tolerance for that snap.
SNAP_TOLERANCE = 0.12


@dataclass(frozen=True)
class DetectedMouse:
    """A mouse as Windows describes it."""

    vendor_id: str          # "373B"
    product_id: str         # "11D9"
    product: str            # "Wireless mouse 8k dongle-L"
    manufacturer: str       # "Compx"
    serial: str
    path: str

    @property
    def hardware_id(self) -> str:
        """Stable key for matching a saved profile to this physical device."""
        return f"{self.vendor_id}:{self.product_id}"

    @property
    def display_name(self) -> str:
        """The name to pre-fill. Users are expected to rename it."""
        product = self.product.strip()
        maker = self.manufacturer.strip()
        if not product:
            return maker or f"Mouse {self.hardware_id}"
        # "Compx Wireless mouse 8k dongle-L", but not "Razer Razer Viper".
        if maker and maker.lower() not in product.lower():
            return f"{maker} {product}"
        return product


@dataclass(frozen=True)
class RateResult:
    """Outcome of a report-rate measurement."""

    hertz: float
    reports: int
    seconds: float

    @property
    def nominal(self) -> int:
        """``hertz`` snapped to the nearest standard rate when it is close."""
        for rate in COMMON_RATES:
            if abs(self.hertz - rate) <= rate * SNAP_TOLERANCE:
                return rate
        return int(round(self.hertz))


# ============================================================ identification =
def detect_mice() -> list[DetectedMouse]:
    """Every mouse Windows currently reports, deduplicated by VID:PID.

    Returns an empty list on non-Windows platforms or if anything fails.
    """
    if not IS_WINDOWS:
        return []
    try:
        return _detect_mice_windows()
    except Exception:
        log.debug("mouse detection failed", exc_info=True)
        return []


def _detect_mice_windows() -> list[DetectedMouse]:
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hid = ctypes.windll.hid

    class RAWINPUTDEVICELIST(ctypes.Structure):
        _fields_ = [("hDevice", wintypes.HANDLE), ("dwType", wintypes.DWORD)]

    class HIDD_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Size", wintypes.ULONG), ("VendorID", wintypes.USHORT),
                    ("ProductID", wintypes.USHORT), ("VersionNumber", wintypes.USHORT)]

    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                     ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                     wintypes.HANDLE]

    count = wintypes.UINT(0)
    entry_size = ctypes.sizeof(RAWINPUTDEVICELIST)
    if user32.GetRawInputDeviceList(None, ctypes.byref(count), entry_size) != 0:
        return []
    if not count.value:
        return []
    devices = (RAWINPUTDEVICELIST * count.value)()
    if user32.GetRawInputDeviceList(devices, ctypes.byref(count), entry_size) == -1:
        return []

    found: dict[str, DetectedMouse] = {}
    for entry in devices[:count.value]:
        if entry.dwType != RIM_TYPEMOUSE:
            continue

        length = wintypes.UINT(0)
        user32.GetRawInputDeviceInfoW(entry.hDevice, RIDI_DEVICENAME, None,
                                      ctypes.byref(length))
        if not length.value:
            continue
        buffer = ctypes.create_unicode_buffer(length.value + 1)
        user32.GetRawInputDeviceInfoW(entry.hDevice, RIDI_DEVICENAME, buffer,
                                      ctypes.byref(length))
        path = buffer.value
        if not path:
            continue

        # Remote-desktop and virtual mice have no VID/PID and are not useful.
        vid = re.search(r"VID_([0-9A-Fa-f]{4})", path)
        pid = re.search(r"PID_([0-9A-Fa-f]{4})", path)
        if not (vid and pid):
            continue

        strings = _hid_strings(path, kernel32, hid, HIDD_ATTRIBUTES)
        mouse = DetectedMouse(
            vendor_id=(strings.get("vid") or vid.group(1)).upper(),
            product_id=(strings.get("pid") or pid.group(1)).upper(),
            product=strings.get("product", ""),
            manufacturer=strings.get("manufacturer", ""),
            serial=strings.get("serial", ""),
            path=path,
        )
        # Several HID collections map to one physical device; keep the first
        # that actually carries a product string.
        existing = found.get(mouse.hardware_id)
        if existing is None or (not existing.product and mouse.product):
            found[mouse.hardware_id] = mouse

    return list(found.values())


def _hid_strings(path: str, kernel32, hid, attributes_type) -> dict[str, str]:
    """Read the cached USB descriptor strings for one HID path.

    Opened with access 0 on purpose: Windows keeps an exclusive lock on system
    mice, so requesting read access fails, while a query-only handle succeeds.
    """
    from ctypes import wintypes

    result: dict[str, str] = {}
    handle = kernel32.CreateFileW(
        path, 0, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
    if not handle or handle == INVALID_HANDLE_VALUE:
        return result
    try:
        buffer = ctypes.create_unicode_buffer(256)
        for key, function in (("product", hid.HidD_GetProductString),
                              ("manufacturer", hid.HidD_GetManufacturerString),
                              ("serial", hid.HidD_GetSerialNumberString)):
            ctypes.memset(buffer, 0, ctypes.sizeof(buffer))
            try:
                if function(handle, buffer, ctypes.sizeof(buffer)):
                    value = buffer.value.strip()
                    if value:
                        result[key] = value
            except OSError:
                continue
        attributes = attributes_type()
        attributes.Size = ctypes.sizeof(attributes)
        if hid.HidD_GetAttributes(handle, ctypes.byref(attributes)):
            result["vid"] = f"{attributes.VendorID:04X}"
            result["pid"] = f"{attributes.ProductID:04X}"
    finally:
        kernel32.CloseHandle(handle)
    return result


# ============================================================== report rate =
def compute_rate(timestamps_ns: list[int]) -> RateResult | None:
    """Reports per second of *active* movement.

    Counting reports over wall-clock time under-reports whenever the hand
    pauses. Taking the median interval over-reports whenever the OS delivers a
    batch of reports at once — both were measured. Dividing the number of
    intervals by the time those intervals actually span is immune to both.
    """
    if len(timestamps_ns) < MIN_INTERVALS:
        return None
    gaps = [(b - a) / 1e9 for a, b in zip(timestamps_ns, timestamps_ns[1:])]
    active = [g for g in gaps if 0 < g <= IDLE_GAP_S]
    if len(active) < MIN_INTERVALS:
        return None
    span = sum(active)
    if span <= 0:
        return None
    return RateResult(hertz=len(active) / span,
                      reports=len(timestamps_ns),
                      seconds=span)


def measure_report_rate(seconds: float = 2.0,
                        on_progress: Callable[[int], None] | None = None,
                        ) -> RateResult | None:
    """Count Raw Input movement reports for ``seconds`` and derive the rate.

    Runs its own message-only window on the calling thread, so it must **not**
    be called from the Tk thread. Returns ``None`` if the mouse was not moved
    enough to be sure.
    """
    if not IS_WINDOWS:
        return None
    try:
        stamps = _collect_reports(seconds, on_progress)
    except Exception:
        log.debug("report rate measurement failed", exc_info=True)
        return None
    return compute_rate(stamps)


def _collect_reports(seconds: float,
                     on_progress: Callable[[int], None] | None) -> list[int]:
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, wintypes.UINT,
                                 wintypes.WPARAM, wintypes.LPARAM)

    # Every signature is declared explicitly. Without this, ctypes defaults to
    # a 32-bit int return and silently truncates 64-bit handles -- a truncated
    # HINSTANCE from GetModuleHandleW makes RegisterClassW fault.
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterClassW.restype = wintypes.ATOM
    user32.RegisterClassW.argtypes = [ctypes.c_void_p]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.DefWindowProcW.restype = ctypes.c_longlong
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT,
                                      wintypes.WPARAM, wintypes.LPARAM]
    user32.GetRawInputData.restype = wintypes.UINT
    user32.GetRawInputData.argtypes = [wintypes.HANDLE, wintypes.UINT,
                                       wintypes.LPVOID,
                                       ctypes.POINTER(wintypes.UINT), wintypes.UINT]
    user32.RegisterRawInputDevices.restype = wintypes.BOOL
    user32.RegisterRawInputDevices.argtypes = [ctypes.c_void_p, wintypes.UINT,
                                               wintypes.UINT]
    user32.PeekMessageW.restype = wintypes.BOOL
    user32.PeekMessageW.argtypes = [ctypes.c_void_p, wintypes.HWND,
                                    wintypes.UINT, wintypes.UINT, wintypes.UINT]
    user32.TranslateMessage.argtypes = [ctypes.c_void_p]
    user32.DispatchMessageW.restype = ctypes.c_longlong
    user32.DispatchMessageW.argtypes = [ctypes.c_void_p]
    user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]

    class WNDCLASS(ctypes.Structure):
        _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
                    ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                    ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                    ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                    ("lpszMenuName", wintypes.LPCWSTR),
                    ("lpszClassName", wintypes.LPCWSTR)]

    class RAWINPUTDEVICE(ctypes.Structure):
        _fields_ = [("usUsagePage", wintypes.USHORT), ("usUsage", wintypes.USHORT),
                    ("dwFlags", wintypes.DWORD), ("hwndTarget", wintypes.HWND)]

    class RAWINPUTHEADER(ctypes.Structure):
        _fields_ = [("dwType", wintypes.DWORD), ("dwSize", wintypes.DWORD),
                    ("hDevice", wintypes.HANDLE), ("wParam", wintypes.WPARAM)]

    class RAWMOUSE(ctypes.Structure):
        _fields_ = [("usFlags", wintypes.USHORT), ("ulButtons", wintypes.ULONG),
                    ("ulRawButtons", wintypes.ULONG), ("lLastX", wintypes.LONG),
                    ("lLastY", wintypes.LONG), ("ulExtraInformation", wintypes.ULONG)]

    class RAWINPUT(ctypes.Structure):
        _fields_ = [("header", RAWINPUTHEADER), ("mouse", RAWMOUSE)]

    stamps: list[int] = []
    perf_counter_ns = time.perf_counter_ns
    header_size = ctypes.sizeof(RAWINPUTHEADER)
    payload_size = ctypes.sizeof(RAWINPUT)

    def window_proc(hwnd, message, wparam, lparam):
        if message == WM_INPUT:
            size = wintypes.UINT(payload_size)
            data = RAWINPUT()
            got = user32.GetRawInputData(wintypes.HANDLE(lparam), RID_INPUT,
                                         ctypes.byref(data), ctypes.byref(size),
                                         header_size)
            if got > 0 and data.header.dwType == RIM_TYPEMOUSE:
                # Movement only: button and wheel packets would skew the rate.
                if data.mouse.lLastX or data.mouse.lLastY:
                    stamps.append(perf_counter_ns())
            return 0
        return user32.DefWindowProcW(hwnd, message, wparam, lparam)

    callback = WNDPROC(window_proc)          # must outlive the window
    window_class = WNDCLASS()
    window_class.lpfnWndProc = callback
    window_class.hInstance = kernel32.GetModuleHandleW(None)
    window_class.lpszClassName = (
        f"LatencyTesterRate{threading.get_ident():x}{time.perf_counter_ns():x}")

    if not user32.RegisterClassW(ctypes.byref(window_class)):
        return []
    hwnd = user32.CreateWindowExW(0, window_class.lpszClassName, None, 0, 0, 0, 0, 0,
                                  wintypes.HWND(-3),   # HWND_MESSAGE
                                  None, window_class.hInstance, None)
    if not hwnd:
        user32.UnregisterClassW(window_class.lpszClassName, window_class.hInstance)
        return []

    # Usage page 1, usage 2 = generic desktop / mouse. INPUTSINK delivers even
    # while the app is not focused, which it will not be while you move the
    # mouse around.
    device = RAWINPUTDEVICE(0x01, 0x02, RIDEV_INPUTSINK, hwnd)
    registered = user32.RegisterRawInputDevices(ctypes.byref(device), 1,
                                                ctypes.sizeof(device))
    try:
        if not registered:
            return []
        message = wintypes.MSG()
        deadline = time.perf_counter() + seconds
        last_report = 0
        while time.perf_counter() < deadline:
            while user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
            if on_progress is not None and len(stamps) != last_report:
                last_report = len(stamps)
                on_progress(last_report)
            time.sleep(0.0005)
    finally:
        device.dwFlags = 0x00000001          # RIDEV_REMOVE
        device.hwndTarget = None
        user32.RegisterRawInputDevices(ctypes.byref(device), 1, ctypes.sizeof(device))
        user32.DestroyWindow(hwnd)
        user32.UnregisterClassW(window_class.lpszClassName, window_class.hInstance)

    return stamps
