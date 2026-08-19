# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — one-folder build.

One-folder (not one-file) on purpose: a one-file build unpacks to a temp
directory on every launch, which adds startup cost and confuses antivirus
heuristics.  A plain folder is also what the installer ships.
"""

from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "run_dashboard.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "latency_tester" / "locales"), "latency_tester/locales"),
    ],
    hiddenimports=["pynput.keyboard._win32", "pynput.mouse._win32"],
    hookspath=[],
    runtime_hooks=[],
    # Trim the parts of matplotlib and friends the app never touches.
    excludes=[
        "PyQt5", "PyQt6", "PySide2", "PySide6", "wx",
        "IPython", "jupyter", "notebook", "pytest",
        "matplotlib.backends.backend_qt5agg",
        "matplotlib.backends.backend_qtagg",
        "matplotlib.backends.backend_webagg",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LatencyTester",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # GUI app: no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "packaging" / "app.ico") if (ROOT / "packaging" / "app.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="LatencyTester",
)
