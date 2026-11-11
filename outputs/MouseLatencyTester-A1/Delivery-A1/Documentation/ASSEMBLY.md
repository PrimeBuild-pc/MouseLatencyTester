# A1b assembly

Use the schematic and previews included. Views of the back side are mirrored relative to the front. Coordinates here are seen from above, origin at the top-left corner of the PCB, X to the right and Y downwards.

## Population

| References | Component | Side / notes |
|---|---|---|
| U1 | OPA380AIDR, SOIC-8 1.27 mm pitch | Front; pin 1 as per footprint, do not orient from the marking in the listing |
| U2 | TLV3501AID/AIDR, SOIC-8 1.27 mm pitch | Front; do not swap U1/U2 |
| U3 | Teensy 2.0 | Front; USB Mini-B towards the left edge |
| D1 | BPV10 | **Back** (silkscreen `LATO MONITOR`), body facing the monitor; square pad 1 marked `K` = cathode, pad 2 = anode. Ø1.0 mm holes for the 0.63 × 0.5 mm leads |
| C3 | 15 pF NP0/C0G 0805 | **Back**, under U1; no polarity |
| R1 | 10 kΩ 1% | Front, horizontal, 7.62 mm pitch |
| R2 | 10 kΩ 1% | Front, **vertical**, 2.54 mm pitch |
| R3 | **1 MΩ 1%** (TIA gain) | Front, vertical. **Body on the pad with the silkscreen circle** (SUM node, towards R1); the bent lead goes on the pad towards U1 |
| R4 | 1 MΩ 1% | Front, vertical |
| R5 | 100 Ω 1% | Front, vertical |
| C1, C4, C5 | 100 nF radial ceramic, holes at 2.5 mm pitch | Front; short leads, especially C4/C5 near the ICs. If yours have 5 mm pitch, bend the leads inwards and keep the body close to the board |
| C2, C6 | 10 µF 16 V radial, Ø4 mm, 1.5 mm pitch | Front, polarised: square pad 1 = positive, pad 2 = negative/GND |
| RV1 | 3296W 10 kΩ | Front; screw accessible from the case |
| SW1, SW2 | 6 × 6 mm THT push buttons, 4 legs, reference height 4.3 mm | Front; check orientation and spacing before soldering |
| J1 | 1 × 4 header, 2.54 mm pitch | Front; towards the OLED with a cable. Silkscreen `5V GND SCL SDA` |
| J2 | 1 × 2 header, 2.54 mm pitch | Front; towards the external probe. Silkscreen `PROBE` on pin 1 |

The light stripe on electrolytic capacitors normally indicates the **negative**: do not align it with the + symbol. In the Vishay drawing the BPV10 cathode is the shorter lead (1.5 mm difference). Confirm it with the multimeter in diode mode before soldering: when it shows about 0.5–0.7 V the black probe is on the cathode, which goes in the square pad `K`. A BPV10 mounted backwards does not break but drives TP2 to saturate towards ground.

The two SOICs are soldered directly: the SOP→DIP adapters purchased are not needed on this board. Start with C3 and the SOICs, then resistors/ceramics, photodiode, electrolytics, trimmer and connectors. Keep the back accessible until soldering is finished. Clean the flux thoroughly around U1, R3 and C3.

The Teensy can be removable using two rows of 12 contacts at 2.54 mm pitch, 15.24 mm between the rows; directly soldered pins reduce the height. The additional inner/end pins must not create misaligned supports: the two outer rows include power, ground and all signals used by A1. The numbering of the module pads in the CAD does not match the Arduino numbering.

## Connections

**OLED J1 — specific order for the photographed EstarDyn 1.30 IIC V2.0 module:**

| J1 pin | Net | OLED pin |
|---|---|---|
| 1, square | +5 V | VDD |
| 2 | GND | GND |
| 3 | I2C_SCL | SCK/SCL |
| 4 | I2C_SDA | SDA |

Check the silkscreen of the actual part before powering: many OLEDs from other brands have VCC/GND swapped. Use a short cable, do not force the module onto the carrier holes.

**Probe J2:** square pin 1 = PROBE, pin 2 = GND. Intended for a passive normally-open contact that closes to ground. The pull-up must be enabled by the firmware. No external voltage must be applied to the probe.

| Function | ATmega32U4 / Teensy 2.0 port | Intended use |
|---|---|---|
| BTN1, BTN2 | PB0, PB1 / Arduino 0, 1 | INPUT_PULLUP, press = low |
| OLED SCL, SDA | PD0, PD1 / Arduino 5, 6 | I²C SH1106 |
| PROBE | PD2 / Arduino 7 | Measurement start, falling edge |
| OPT_TRIGGER | PD3 / Arduino 8 | Optical end, FALLING edge |
| TIA_OUT | PF0 / A0 | Analogue diagnostics; not the timing end of the measurement |

The current firmware of the KY-018 version is not automatically turned into comparator firmware by these files. Local timestamps of the two events, timeout/re-arm handling and compatibility with the dashboard/OLED must be implemented and verified. Avoid OLED/I²C updates during the measurement window.

## First power-up and bring-up

1. With power off, check solder joints, polarity and absence of a short between +5 V and GND; measure the resistor values before fitting them. Check continuity of the probe contacts and buttons.
2. Power from the Teensy's USB Mini-B. The board is designed for about 5 V, not for the Teensy 3.3 V modification. For the first test a USB supply with monitored current is preferable. Do not join a second external supply to the USB rail.
3. With TP4 GND as reference, check +5 V on the bypass capacitors: it must be between 4.5 and 5.25 V. Above 5.5 V the TLV3501 is outside the absolute maximum: change port or supply. Wait at least one second and measure TP1 VBIAS: about half the supply, nominally 2.5 V.
4. Read TP2 TIA_OUT with the diode darkened and then lit by the display's white. The voltage must increase with light. With R3 = 1 MΩ the gain is 1 V per µA: datasheet estimate 0.3–1.5 V swing between black and white at 100–300 cd/m², not measured. Above about 4.4 V the output saturates: for the trigger alone this is not a problem; if you want linear A0 telemetry on very bright screens, go down to 330–470 kΩ. If the swing is below 100 mV, check the alignment and polarity of D1 before touching the values. C3 = 15 pF with 1 MΩ gives a bandwidth of about 10 kHz, time constant 15 µs.
5. With an oscilloscope check that TP2 does not oscillate and that the black/white transition is distinguishable. Adjust RV1 so that the threshold falls between the two levels, 0.1–0.2 V above the dark value (the THRESH threshold is measured on the middle pin of RV1); check TP3 CMP_RAW: the transition to white must drive the output low. The hysteresis must not prevent re-arming at black.
6. Verify at the Teensy that the edges arrive exactly once, then test the optical firmware and the complete path. Only afterwards quantify repeatability and error, by comparing against an independent time reference.

Do not load the SUM node with long probes or with the capacitance of an ordinary probe: take routine measurements at the test points provided. The alignment between the mechanical probe and the mouse click remains part of the measurement uncertainty.

## Dimensions for the future case

PCB 56 × 48 × 1.6 mm, 2 mm planar chamfers. Ø2.2 mm holes at the centres (3;3), (53;3), (3;45), (53;45). These are project dimensions, not additional tolerances required of the manufacturer. Use the included DXF for the outline and leave clearance for manufacturing tolerances.

On the monitor side provide a cavity for D1 and the soldered leads, a shielded optical window and room for C3. The front needs space for the Teensy, vertical resistors, connectors and the RV1 screw. The overall height depends on the actual sockets and headers; measure it before closing the case. Secure the USB cable and the probe cable and relieve their strain mechanically.
