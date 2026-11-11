# Review of prototype A1b

Scope: `mouse_latency_tester`, revision Prototype A1b / BPV10 of 11 November 2026. PCBWay, bare FR-4 two-layer PCBs, 1.6 mm, outer copper 1 oz, lead-free HASL finish. Hand soldering by Lorenzo. No procurement or assembly service examined.

## Independent review of 11 November: what changed

Schematic, pinouts, footprints, power supply and layout were re-read against the Vishay BPV10 (rev. 2.1), TI OPA380 (SBOS291G) and TLV3501 (SBOS321E) datasheets, the PJRC pinout and dimensions of the Teensy 2.0, and the geometry stored in the PCB.

| Item | Evidence | Outcome | Change |
|---|---|---|---|
| TIA gain, R3 | BPV10: 70 µA typical at 1 mW/cm² and 950 nm, relative sensitivity 0.45 at 550 nm, half angle ±20°. Estimate for the white of a 250 cd/m² display resting on the sensor: about 1 µA. With 10 kΩ that is about 10 mV, less than the comparator hysteresis (6 mV internal + 12.5 mV from R4) | **Functional error**: the comparator would not have switched or would not have re-armed | R3 from 10 kΩ to **1 MΩ**: about 1 V at 250 cd/m². C3 stays 15 pF: bandwidth 10.6 kHz, τ = 15 µs, stable (minimum Cf ≈ 0.15 pF) |
| D1 holes | Leads 0.63 × 0.5 mm, diagonal 0.80 mm nominal and up to 1.05 mm at tolerance; hole 0.9 mm | At risk of not fitting | **1.0 mm** hole, 1.8 mm pad unchanged, in library and on the PCB |
| Silkscreen | J1 without pin names, test points and J2 anonymous, no revision on the board | Risk of wiring the OLED backwards | Added `5V GND SCL SDA`, `PROBE`, `VBIAS TIA CMP GND`, `MLT A1b 2026-11`; on the back `K` and `LATO MONITOR` |
| U1, U2 pinout | SO-8: 1 NC, 2 −IN, 3 +IN, 4 V−, 5 NC, 6 OUT, 7 V+, 8 NC (OPA380) / SHDN (TLV3501, low = active) | Correct | None |
| D1 polarity and bias | Cathode on −IN, anode to GND, +IN at 2.5 V: reverse 2.5 V; common mode allowed up to V+ − 1.8 V = 3.2 V | Correct, at 5 V only | None |
| Teensy 2.0 | Rows at 15.24 mm, 2.54 mm pitch, 12 + 12 + 5 + 2 holes; PD0/PD1 = SCL/SDA, PD2/PD3 = INT2/INT3, PF0 = ADC0; USB towards the left edge, protrudes 0.3 mm from the board | Correct | None |
| Footprints of purchased components | SOIC-8 3.9 × 4.9 1.27 pitch; 3296W three in-line pins 2.54 pitch; 0805; buttons 6.5 × 4.5 mm; ECEA1CKS100 1.5 mm pitch, hole 0.6 | Consistent with the part codes | 100 nF: holes are at 2.5 mm pitch, the pitch of the real parts is not known (see assembly) |
| Power supply | USB only, from the Teensy; estimated consumption under 100 mA; TLV3501 absolute maximum 5.5 V | Acceptable | Added the voltage check at first power-up |
| Clearances | Distances between bodies calculated from the coordinates: minimum 0.6 mm (C4–U1, C5–U2, C1–R3) | Tight but buildable | None |

Left as they are, to keep in mind: the THRESH threshold derives from the unfiltered +5 V, so USB noise enters the threshold (with 1 MΩ the signal dominates it); TIA_OUT reaches PF0 without a series resistor, so the firmware must never set A0 as an output nor read the ADC in the measurement window; PROBE enters PD2 without ESD protection, as in the current setup; the optical trigger is on INT3 and not on a capture input (PC7/ICP3 is free).

## Reproducible results

Additional check of 11 November 2026 with **official KiCad 9.0.8 installed on Windows**, invoked directly without going through the 10.99 runtime. The first check found three wires not split at existing junctions, in the VBIAS net and in the U1 feedback: KiCad 9 rebuilt some nets differently. The wires were segmented at the junctions in both copies of the schematic, keeping the intended circuit, values, symbols and drawing geometry. No changes to the PCB or the Gerbers. The final check with KiCad 9.0.8 passes ERC, DRC and parity; the netlist exported from engine 9 also matches all 88 pin/net associations of the PCB. The SHA-256 comparison confirms that the PCBWay ZIP is identical to the A1b one preceding this schematic correction.

| Check | Outcome / evidence |
|---|---|
| Installed KiCad 9.0.8: ERC, DRC and parity | PASS, zero violations, missing connections or differences; `kicad9-native-erc.json`, `kicad9-native-drc.json` |
| Engine 9 netlist against PCB | PASS, 88 unique associations matching; `kicad9-native-summary.json` |
| Schematic ERC | PASS, zero errors and warnings; `final-erc.json` |
| DRC with filled zones | PASS, zero errors and zero warnings, zero missing connections, zero parity errors; `final-drc.json` |
| Schematic against PCB | PASS, 88 unique reference/pin/net associations; `independent-checks.json` |
| Critical pins against datasheet specification | PASS, 38 explicit associations for ICs, Teensy, diode, connectors and polarity; same report |
| Track geometry | PASS, no segment off multiples of 45°, minimum width 0.2 mm |
| C4 and C5 relative to pins 7 of U1/U2 | 2.825 mm between pad centres; each on the same side, GND return via a nearby THT pad |
| Mounting holes | PASS, four Ø2.2 mm NPTH at the intended centres; preserved as board-only objects |
| Exported Gerbers and Excellon | PASS, seven non-empty layers, 80 plated holes and four NPTH; all 84 holes match in position and diameter with the PCB's pads and vias; outline 56 × 48 mm; `fabrication-files.json`, `drill-report.txt` |
| KiCad 9 conversion | PASS, no losses/approximations reported; `kicad9-export.json` |
| KiCad 9 copy against original | PASS, 92 pad records, 122 track records and 90 schematic pin records equal; `portable-comparison.json` |
| DRC/parity and ERC of the KiCad 9 copy | PASS, zero violations, missing connections, parity issues or ERC issues; `portable-drc.json`, `portable-erc.json`. Run with the KiCad 10.99 engine on the format-9 files, not with an installed KiCad 9 |
| Appearance of schematic, assembly and Gerbers | Examined on renders; back orientation, polarity, access to USB/connectors and absence of obvious overlaps |

The differences between the counts concern virtual power pins, duplicate button pads and four mechanical holes. They do not indicate missing connections.

The DRC includes errors and warnings. The report lists five checks ignored in the runtime's starting configuration: missing courtyard, track centring on vias, tuning profiles, footprint filters and footprint type match. No checks were disabled to hide violations. Courtyard/clearances and pinout were examined separately; the report is not equivalent to a verification of every possible KiCad property.

## Rules and fabrication

Comparison with [PCBWay capabilities](https://www.pcbway.com/capabilities.html), consulted on 2026-11-08, for two layers and 1 oz copper. The limits are published conditions, not a quote or CAM acceptance.

| Item | Design | Published limit / outcome |
|---|---|---|
| Track / copper spacing | Configured minimums 0.20 / 0.20 mm, DRC clean | 0.10 / 0.10 mm: PASS |
| Copper to milled edge | Configured minimum 0.50 mm, DRC clean | 0.25 mm: PASS |
| Smallest drill | Vias Ø0.30 mm; components 0.6 / 0.8 / 1.0 / 1.1 mm | A surcharge is indicated below Ø0.20 mm: PASS |
| Annular ring | Vias Ø0.70 / hole Ø0.30: 0.20 mm; minimum rule 0.15 mm | Minimum 0.15 mm: PASS |
| Visible silkscreen | Height 0.8–1.2 mm, stroke 0.15 mm | Minimums 0.8 / 0.15 mm: PASS, at the limit for the 0.8 mm lettering |
| Special holes / slots | No blind or buried holes, slots or plated edges | No special process expected |

The Gerbers were re-read with a parser different from KiCad and rendered on both faces together with the Excellon files. The parser reports the position of the G90 command after the Excellon header closes; it correctly recognises units, coordinates, tools and all 84 holes. No parsing errors. No solder paste exported: manual assembly, stencil not required.

## Electrical coverage and tests still needed

- U1/U2: supplies, NC pins, SHDN to GND, feedback, BPV10 polarity and output to the Teensy verified on the schematic and on the PCB. Local bypasses present. The inverting node has short paths and clearing of the surrounding plane; the comparator is separated from the photodiode.
- C2 and C6 are polarised electrolytics chosen instead of the ceramic 10 µF mentioned in the initial proposal; ceramic C1/C4/C5 remain for bypass. Value, voltage, pitch and polarity are explicit in the bill of materials.
- The actual consumption of the assembly and the current available from the USB port are not measured. No validated thermal rating of the tracks is declared. There are no power loads planned, but a complete budget also requires the real OLED and Teensy.
- The value of R3 comes from an estimate based on datasheet data, not from a measurement: the real photocurrent depends on the display, brightness and alignment.
- Not verified by simulation or on the bench: TIA stability, comparator ringing, ambient light immunity, tolerances, noise, saturation, false edges and re-arming. The layout and values are a first implementation of the repo's topology.
- No EMC/ESD tests, cable robustness or protection of the external ports have been done. The intended probe is a passive contact.
- No timestamp of the optical firmware has been implemented or tested in this package. Timer resolution and nominal component times do not demonstrate system accuracy.
- No physical assembly tried. Packages are derived from part codes and datasheets; authenticity and dimensions of the parts received are not established by the listings. The resistors must be measured; OLED, buttons, sockets and cables must be compared with the real components.
- A complete STEP of the assembly is not provided: verified 3D models for all components are missing. The DXF shows outline and holes; vertical clearances and case are still to be defined.

The review supports fabrication of a **prototype** with the attached files; it is not a functional bring-up nor a promise of equivalence with LDAT. No uploads, payments, orders or GitHub publications were made.

## Main commands

Run in the working copy with text-to-cad / KiCad headless 10.99:

```text
cad kicad_sch erc mouse_latency_tester.kicad_sch --json
python apply_review_a1b.py
cad run kicad-cli pcb drc --refill-zones --save-board --schematic-parity --severity-all --format json -o checks/final-drc.json mouse_latency_tester.kicad_pcb
cad run verify_final.py
cad run kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts -o fab mouse_latency_tester.kicad_pcb
cad run kicad-cli pcb export drill --format excellon --excellon-units mm --excellon-separate-th --generate-report --report-path checks/drill-report.txt -o fab mouse_latency_tester.kicad_pcb
uv run --no-project --with gerbonara --with resvg-py audit_fabrication.py
cad run kicad-cli project downgrade --target 9.0 --output <new-folder> --report-json checks/kicad9-export.json mouse_latency_tester.kicad_pro
```

The verification scripts are included in `Checks/script/`. The source to edit for the user is the native project in `KiCad/`; the scripts are not a complete generator of the project. The SHA-256 manifest identifies the exact files delivered.
