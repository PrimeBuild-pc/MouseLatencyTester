# Sources and libraries

Circuit and PCB design A1 prepared for Lorenzo / PrimeBuild-pc, starting from the requirements and topology described in [MouseLatencyTester/docs/optical_front_end.md](https://github.com/PrimeBuild-pc/MouseLatencyTester/blob/main/docs/optical_front_end.md). The repo's firmware and dashboard are neither copied nor modified in the package.

The local library `mlt.kicad_sym` and `mlt.pretty` collects only the symbols and footprints needed, included in the project to make it portable.

- Teensy symbol from [XenGi/teensy_library](https://github.com/XenGi/teensy_library), MIT licence. Displayed name field shortened while keeping pin numbers and types.
- Teensy footprint from [XenGi/teensy.pretty](https://github.com/XenGi/teensy.pretty), MIT licence. Courtyard added and silkscreen/Fab changes made; direct connection to the plane for the GND pad 1.
- Other symbols from [KiCad/kicad-symbols](https://github.com/KiCad/kicad-symbols) and footprints from [KiCad/kicad-footprints](https://github.com/KiCad/kicad-footprints), copyright KiCad contributors, CC-BY-SA 4.0 with an exception for electronic designs. The local copies are renamed in the mlt library; references and positions may be adapted in the project. The polarised capacitor symbol is a local representation with pin 1 positive / 2 negative.

The upstream licences are included in this folder. These attributions describe the reused materials and do not change the licences of the other projects mentioned in the research.
