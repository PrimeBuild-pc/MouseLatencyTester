# Optical front-end — first electrical draft

This project contains the schematic of the BPV10 / OPA380AIDR / TLV3501AID front-end only. It is not yet the complete board with Teensy, buttons and OLED; no file here is a Gerber to be ordered.

The topology and initial values come from [MouseLatencyTester](https://github.com/PrimeBuild-pc/MouseLatencyTester/blob/main/docs/optical_front_end.md), checked on paper against the [OPA380](https://www.ti.com/lit/ds/symlink/opa380.pdf), [TLV3501](https://www.ti.com/lit/ds/symlink/tlv3501.pdf) and [BPV10](https://www.vishay.com/docs/81502/bpv10.pdf) datasheets. They are a starting point to be tested, not guaranteed performance.

The passive, power and connector symbols derive from the archived official [KiCad](https://github.com/KiCad/kicad-symbols) libraries, with their [licence](https://github.com/KiCad/kicad-symbols/blob/master/LICENSE.md). The two local IC symbols are derived from the TI pinouts; all eight pins are represented, including NC and SHDN.

The native file `optical_front_end.kicad_sch` is the source to edit. `build_draft.py` and `make_native.py` are initial builders and refuse to overwrite it. KiCad CLI did not directly convert the legacy schematic, so `make_native.py` composed the first native file using the text-to-cad S-expression parser and the symbols converted by the official KiCad command. `mlt.lib` and `.sch` are historical intermediates; `mlt.kicad_sym` and `sym-lib-table` make the project self-contained. The intermediates must not be regenerated after changes to the native file. `tidy_native.py` documents the tidying of the fields after the first visual check and verifies that no pin's name, type or net changes.

Check of the present revision: `cad kicad_sch erc optical_front_end.kicad_sch --json` passes with zero errors and zero warnings; three footprint library checks not performed remain, declared in `erc.json`. `cad run verify_circuit.py` passes: 46 pin/net connections compared with the independent specification, five NC and complete numbering of both ICs. `preview.png` was generated from the final schematic and inspected after tidying the text. No electrical simulation or physical test was run. The runtime used is cad-server 0.11.1 with KiCad headless 10.99: the library format is that of the development version and opening in a stable KiCad version has not been verified.

Nominal supply 5 V from the Teensy 2.0, never beyond the components' limits. The mid-supply VBIAS divider is not valid at 3.3 V for the OPA380 common mode. J1.4 is intended for pad D3, Arduino digital 8; J1.3 is intended for F0/A0. The KY-018 must not drive the same analogue input at the same time.

Still to complete: format of the two 10 µF and of the other passives; placement of the bypass with short connections; footprint of the real trimmer; pinout/geometry of Teensy and OLED; case dimensions and access to the adjustments. Missing footprints are not to be invented during export: they must be fixed before layout.

The existing firmware v1.5 uses the KY-018 and ADC: the comparator-edge timestamp must be implemented. Neither the firmware nor the circuit has been tested on this new hardware. The complete PCB and the case remain open work.
