# MouseLatencyTester — prototype A1b, BPV10

Compact board for the components Lorenzo purchased: Teensy 2.0, BPV10, OPA380AIDR, TLV3501AID, 3296W trimmer and I²C SH1106 OLED. Project dated 2026-11-08, revised on the 11th (A1b: TIA gain, BPV10 hole, silkscreen; details in `Documentation/VERIFICATION.md`). Intended for a first build and bring-up. **The earlier A1 Gerbers must no longer be used.**

**The PCB is routed and passes the documented checks. The circuit has not been built or measured. The firmware for the new comparator input still has to be implemented and verified.** Accuracy equivalence with NVIDIA LDAT is not demonstrated.

## Files to use

- `KiCad/mouse_latency_tester.kicad_pro`: open this project with KiCad 9 or later. Schematic, PCB and local libraries are included. The conversion from the 10.99 working copy reported no losses; checks were repeated on the 9 copy.
- `PCBWay/`: seven Gerbers, two separate Excellon files (PTH/NPTH) and the Gerber job file. The separate PCBWay ZIP contains only these files.
- `Documentation/mouse_latency_tester-bom.csv`: bill of materials exported from the schematic. TP1–TP4 are pads already on the PCB, not parts to buy.
- `Documentation/ASSEMBLY.md`: population, pinout and first power-up.
- `Documentation/VERIFICATION.md` and `Checks/`: results, limits and comparison with PCBWay.
- `Mechanical/mouse_latency_tester-outline.dxf`: outline and holes, in millimetres. It is not the complete assembly model.
- `Previews/`: renders from the Gerbers, schematic and assembly drawing. The green in the render is illustrative; the colour is chosen when ordering.

## PCBWay order

Upload **MouseLatencyTester-A1-PCBWay.zip**, checking the CAM preview with the two drill files. Do not upload the full project ZIP as the Gerber package.

| Option | Choice for A1 |
|---|---|
| Service | Bare PCBs, hand soldering |
| Number of designs | 1 |
| Nominal size | 56 × 48 mm |
| Layers | 2 |
| Material / thickness | FR-4 / 1.6 mm |
| Outer copper | 1 oz |
| Finish | Lead-free HASL; ENIG possible |
| Solder mask / legend | Green / white; other colours as preferred |
| Mounting holes | 4 × Ø2.2 mm non-plated |
| Controlled impedance / blind vias / castellation | None |
| Stencil / assembly | Not needed |

The files have not been uploaded to or ordered from PCBWay. The manufacturer's CAM check remains separate from the project checks. Order a prototype batch first, before producing variants.

## Parts still to obtain

Get **2 × 10 µF 16 V**, radial electrolytic, Ø4 mm, height 5 mm, pitch 1.5 mm: reference Panasonic **ECEA1CKS100**. An equivalent must also match footprint, pitch and polarity. The capacitors already photographed are 15 pF 0805 and 100 nF radial: they do not replace the 10 µF.

Check the values of the resistors you already own with a multimeter: **2 × 10 kΩ, 2 × 1 MΩ, 1 × 100 Ω**, 1%, axial bodies up to about 6.3 × 2.5 mm. The photos do not allow reading them. You also need connectors/cables for the OLED and probe; any sockets for the Teensy; two 6 × 6 mm THT push buttons compatible with the footprint. These accessories were not completely identified in the orders.

## Case and variants

This is the compact A1 variant: photodiode facing the monitor on the back, Teensy/controls on the front, OLED connected with four wires. The PCB has four holes for M2 screws, spaced 50 × 42 mm. The LDAT case still has to be designed around the heights of the real assembly: no ready-to-print STL is included.

The OLED module as stated by the seller measures 35.5 × 33.5 × 4.3 mm; connector protrusion and the spacing of its holes have not been established. No dimensions were invented for a rigid mounting. The Teensy 2.0 connector is **USB Mini-B**. The BPV10 window must exclude ambient light and OLED light.

A separate optical head or a BPW34 version can be evaluated after A1 bring-up. BPW34 must not be swapped for the BPV10 with just cables: diode geometry and capacitance change, so compensation and stability must be re-verified. No other Gerbers to be produced at the same time are included.

## Repo and alternatives

I recommend keeping MouseLatencyTester: the dashboard and the existing work are reusable. S4N-T0S/Open-Source-LDAT uses different hardware and did not provide a PCB/case in the tree examined. MiSTer Laggy measures the display with a MiSTer system; it does not replace this mouse/PC path. adolfintel/OpenLDAT includes hardware and a case, but uses different electronics/protocol. The detailed comparison is attached in `Research/`.

text-to-cad was concretely useful for creating, checking and exporting the native KiCad files; bring-up of the electronics is still required. No changes were published to the GitHub repo.

## Component sources

- [Teensy 2.0 / PJRC](https://www.pjrc.com/store/teensy.html), [pinout](https://www.pjrc.com/teensy/card2a_rev5_web.pdf), [dimensions](https://www.pjrc.com/teensy/dimensions_teensy20.png).
- [OPA380 / TI](https://www.ti.com/lit/ds/symlink/opa380.pdf), [TLV3501 / TI](https://www.ti.com/lit/ds/symlink/tlv3501.pdf), [BPV10 / Vishay](https://www.vishay.com/docs/81502/bpv10.pdf).
- [Panasonic ECEA1CKS100](https://industrial.panasonic.com/ww/products/pt/aluminum-cap-lead/models/ECEA1CKS100).
- [PCBWay capabilities](https://www.pcbway.com/capabilities.html), consulted on 2026-11-08.
