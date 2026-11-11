# Open-Source-LDAT: what to reuse for MouseLatencyTester

Checked: 8 November 2026. Open-Source-LDAT repository examined at commit `8e0173e42369316ef7b38d9b7735b61706cdbbb2`, through the recursive tree and the actual sources.

**Conclusion:** useful as a reference for automation and interface, but it does not offer a ready PCB or enclosure to adapt. To keep the Teensy 2.0, SH1106 and the future BPV10–OPA380–TLV3501 chain, transplanting the firmware would require substantial changes.

## Material actually published

The complete tree contains `src/main.cpp`, `include/config.h`, PlatformIO configuration, USB patch, wiring images and Windows tools. There are no electronic CAD schematics, PCB layouts, Gerbers, production bill of materials, STL, STEP or case CAD. The wiring photograph does not replace those files. The release list is also empty. So the project does not avoid the board or mechanical design work. [Full tree](https://api.github.com/repos/S4N-T0S/Open-Source-LDAT/git/trees/8e0173e42369316ef7b38d9b7735b61706cdbbb2?recursive=1), [releases](https://api.github.com/repos/S4N-T0S/Open-Source-LDAT/releases).

## Measurement and modes

The project documents a Teensy 4.1, TEMT6000 analogue sensor, SSD1306 128×64 OLED, a button and, to drive a real mouse, a BC547A with a 220 Ω resistor. The **Automatic/Auto UE4** modes electrically drive the microswitch of a wired mouse: they include its electronics downstream of the command, not the mechanical travel of the button. **Direct Auto/Direct UE4** instead generate an HID event from the Teensy: they measure system and display through that device, excluding the mouse to be compared. UE4 uses Aperture Grille's Black to White software; Automatic can use markers or luminance changes in the game. [README](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/README.md).

The source configures two ADCs at **8 bit, very high speed** and repeatedly reads `adc->analogRead()`: it does not capture a comparator edge. `elapsedMicros` starts before the click command. In Automatic the final value is read after the click is released, also including that software path. In Auto UE4 the physical click is held for the configured time before the sensor is polled. These are concrete differences from two interrupt timestamps of the probe and the comparator. [ADC and initialisation](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/src/main.cpp#L223-L235), [Automatic](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/src/main.cpp#L903-L949), [UE4](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/src/main.cpp#L689-L713).

## Practical compatibility

| Item | Open-Source-LDAT | Implication for Lorenzo's device |
|---|---|---|
| MCU | Teensy 4.1, Cortex-M7, 600 MHz | Teensy 2.0 is an AVR ATmega32U4, 16 MHz: builds and specific code are not interchangeable |
| Signals | I/O and ADC 0–3.3 V; not 5 V tolerant | The 5 V chain of the Teensy 2.0 design does not connect directly to a 4.1 |
| OLED | SSD1306; SDA 18/SCL 19 | SH1106 requires an appropriate driver and mapping |
| Firmware pins | Button 4, click 5, mouse presence 21, light 23 | To be remapped: they are not AVR pad names |
| USB Direct | `teensy4` core patch, 125 µs HID interval | Not a portable patch for the AVR/USB Full Speed core of the Teensy 2.0 |

Sources: [hardware configuration](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/include/config.h), [build](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/platformio.ini), [USB patch](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/scripts/8kHz_polling.py), [PJRC specifications](https://www.pjrc.com/teensy/techspecs.html), [Teensy 4.1 levels](https://www.pjrc.com/store/teensy41.html), [ATmega32U4 USB](https://www.pjrc.com/teensy/atmega32u4.pdf).

## Accuracy: evidence and limits

The README claims high precision and proposes a polling check with HamsterWheel; this verifies HID behaviour, it does not calibrate the optical chain. In the tree examined there are no measurements against an oscilloscope/LDAT, characterised sensor times or uncertainty budget. The thresholds are configurable values, tuned by the author on an OLED. Absolute accuracy equivalent to LDAT is therefore not demonstrated. [README and tuning notes](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/README.md).

Inference from the code: the four decimal digits displayed in milliseconds do not demonstrate 0.1 µs resolution, since the result passes through an integer microsecond count. Sensor, ADC conversion, threshold and software calls remain part of the measurement. [Statistical conversion](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/src/main.cpp#L1134-L1148), [display format](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/src/main.cpp#L1559-L1574).

## Recommended reuse

Take the ideas of automatic sessions, warm-up, timeouts, random interval between trials, statistics and CSV saving. For the PCB and case, start instead from the real dimensions of the modules, after validating the MouseLatencyTester front-end. The documentation of its photodiode front-end already proposes a different route: probe as `t0`, comparator on D3/digital 8 as `t1`, A0 for telemetry; that page declares itself still unverified. The existing `photon_v1_5` firmware still uses the KY-018 with ADC reading, not this comparator. [MouseLatencyTester front-end](https://github.com/PrimeBuild-pc/MouseLatencyTester/blob/5dbc38db602ff642d39eb9fda592c3cf0161cec4/docs/optical_front_end.md).

To copy code also consider the licences: Open-Source-LDAT indicates GPL v3 or later in its headers; MouseLatencyTester publishes MIT. Record the provenance and licence of the material actually incorporated before distributing it. [Open-Source-LDAT headers](https://github.com/S4N-T0S/Open-Source-LDAT/blob/8e0173e42369316ef7b38d9b7735b61706cdbbb2/src/main.cpp#L1-L17), [MouseLatencyTester MIT](https://github.com/PrimeBuild-pc/MouseLatencyTester/blob/5dbc38db602ff642d39eb9fda592c3cf0161cec4/LICENSE).
