"""Render the A1b board in 3D for the README and export its STEP for the enclosure.

Run from anywhere:  python hardware/compact/render_3d.py
Needs text-to-cad's `cad` (its kicad-cli reads the board's nightly file format; KiCad 9 cannot)
and KiCad 9's 3D library, which the board names through ${KISYS3DMOD}.
Reads a copy of the board, so the source files (and fab/) are never touched.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BOARD = "mouse_latency_tester"
OUT_IMG = REPO / "docs" / "images" / "hardware"
OUT_STEP = HERE / "mechanical" / f"{BOARD}.step"
CAD = shutil.which("cad") or str(Path.home() / ".local" / "bin" / ("cad.exe" if os.name == "nt" else "cad"))
MODELS = os.environ.get(
    "KISYS3DMOD",
    str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/KiCad/9.0/share/kicad/3dmodels"),
)

VIEWS = {
    "pcb-a1b-iso-top": ["--perspective", "--rotate", "-50,0,35", "--zoom", "0.85"],
    "pcb-a1b-top": ["--side", "top", "--zoom", "0.95"],
    "pcb-a1b-bottom": ["--side", "bottom", "--zoom", "0.95"],
    "pcb-a1b-iso-bottom": ["--perspective", "--rotate", "130,0,-35", "--zoom", "0.85"],
}


def kicad_cli(*args):
    subprocess.run([CAD, "run", "kicad-cli", *args], check=True, stdout=subprocess.DEVNULL)


def render(pcb, out, view, quality):
    kicad_cli("pcb", "render", "-D", f"KISYS3DMOD={MODELS}", "-w", "1600", "-h", "1200",
              "--background", "transparent", "--quality", quality, *view, "-o", str(out), str(pcb))


def main():
    if not Path(MODELS).is_dir():
        sys.exit(f"KiCad 3D library not found: {MODELS} (set KISYS3DMOD)")
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for ext in (".kicad_pcb", ".kicad_pro"):
            shutil.copy2(HERE / f"{BOARD}{ext}", tmp)
        pcb = tmp / f"{BOARD}.kicad_pcb"
        for name, view in VIEWS.items():
            hi, lo = tmp / f"{name}-hi.png", tmp / f"{name}-lo.png"
            render(pcb, hi, view, "high")
            render(pcb, lo, view, "basic")
            # "high" draws shadows and reflections as half-transparent ghosts on a transparent
            # background; the "basic" render of the same camera gives a clean silhouette.
            img = Image.open(hi).convert("RGBA")
            img.putalpha(Image.open(lo).getchannel("A"))
            box = img.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
            assert box, f"{name}: empty render"
            pad = 24
            img = img.crop((max(box[0] - pad, 0), max(box[1] - pad, 0),
                            min(box[2] + pad, img.width), min(box[3] + pad, img.height)))
            img.save(OUT_IMG / f"{name}.png", optimize=True)
            print(OUT_IMG / f"{name}.png", img.size)
        OUT_STEP.parent.mkdir(exist_ok=True)
        kicad_cli("pcb", "export", "step", "-D", f"KISYS3DMOD={MODELS}", "--subst-models",
                  "--force", "-o", str(OUT_STEP), str(pcb))
        print(OUT_STEP)


if __name__ == "__main__":
    main()
