# Compact PCB A1b / BPV10

This section collects the research and documentation for the compact PCB. Firmware, dashboard and hardware now live in the same project folder.

## Main files

| Content | Path |
|---|---|
| PCBWay package, Gerbers and drill files | [MouseLatencyTester-A1-PCBWay.zip](../../outputs/MouseLatencyTester-A1/MouseLatencyTester-A1-PCBWay.zip) |
| Complete package | [MouseLatencyTester-A1-Project.zip](../../outputs/MouseLatencyTester-A1/MouseLatencyTester-A1-Project.zip) |
| Delivery instructions | [README](../../outputs/MouseLatencyTester-A1/Delivery-A1/README.md) |
| Portable KiCad 9 project | [mouse_latency_tester.kicad_pro](../../outputs/MouseLatencyTester-A1/Delivery-A1/KiCad/mouse_latency_tester.kicad_pro) |
| Assembly and connections | [ASSEMBLY](../../outputs/MouseLatencyTester-A1/Delivery-A1/Documentation/ASSEMBLY.md) |
| Verification and limits | [VERIFICATION](../../outputs/MouseLatencyTester-A1/Delivery-A1/Documentation/VERIFICATION.md) |
| 3D renders (design, not photos) | [iso top](../images/hardware/pcb-a1b-iso-top.png), [iso bottom](../images/hardware/pcb-a1b-iso-bottom.png), [top](../images/hardware/pcb-a1b-top.png), [bottom](../images/hardware/pcb-a1b-bottom.png); regenerable with [render_3d.py](../../hardware/compact/render_3d.py) |
| STEP model for the case | [mouse_latency_tester.step](../../hardware/compact/mechanical/mouse_latency_tester.step) (Teensy 2.0 without a 3D model) |
| KiCad 10.99 working sources and scripts | [hardware/compact](../../hardware/compact/) |
| First draft of the front-end only | [hardware/optical-front-end](../../hardware/optical-front-end/) |
| Original libraries and licences | [hardware/sources](../../hardware/sources/) |

The working copy and the KiCad 9 export have different formats and distinct roles. The portable copy that is maintained is the one in `Delivery-A1/KiCad`; no other `KiCad9` or `KiCad9-Final` folders are needed.

## Research and components

- [Design decisions and alternatives](recommendation.md).
- [Purchased components and additions](purchased-components.md).
- [Optical datasheet audit](optical-datasheet-audit.md).
- [OpenLDAT comparison](open-ldat-comparison.md).
- [Teensy 2.0 dimensions](teensy20-dimensions.png) and [pinout](teensy20-pinout.png).

**Status:** 56 × 48 mm PCB, two layers, revision A1b of 11 November 2026 (R3 = 1 MΩ, D1 hole 1.0 mm, silkscreen; reasons in [VERIFICATION](../../outputs/MouseLatencyTester-A1/Delivery-A1/Documentation/VERIFICATION.md)). ERC/DRC and schematic-PCB comparison passed. The circuit has not been built or tested. Still to do: comparator firmware, timing verification and case. The historical scripts that create the first draft must not be used to regenerate the existing project.

For the manufacturer use only the PCBWay ZIP. The complete package includes documentation, sources and reports, so it is not the ZIP to upload as Gerbers.
