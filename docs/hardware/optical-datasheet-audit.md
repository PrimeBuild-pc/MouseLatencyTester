# Verification of the BPV10 / OPA380 / TLV3501 optical front-end

Documentary check: 8 November 2026. No assembly, simulation or bring-up performed. Document examined through the GitHub connector: [optical_front_end.md](https://github.com/PrimeBuild-pc/MouseLatencyTester/blob/main/docs/optical_front_end.md), blob `f87307ba82cdc1d8058b42bd20731c27583896eb`. The page explicitly states that the circuit is not built/verified and is not yet supported by the firmware.

## Outcome

No errors emerge in the pinout, in the SHDN connection or in the photodiode polarity of the current schematic. These three aspects are consistent. The performance of the whole detector remains to be demonstrated; the times of individual components do not equal the accuracy of a complete LDAT.

## Verified pinout, top view

| SOIC-8 pin | OPA380AID | TLV3501AID |
|---|---|---|
| 1 | NC | NC |
| 2 | −IN | −IN |
| 3 | +IN | +IN |
| 4 | V− / GND | V− / GND |
| 5 | NC | NC |
| 6 | OUT | OUT |
| 7 | V+ | V+ |
| 8 | NC | SHDN |

Sources: [OPA380, page 2](https://www.ti.com/lit/ds/symlink/opa380.pdf#page=2) and [TLV3501, page 3](https://www.ti.com/lit/ds/symlink/tlv3501.pdf#page=3). For the TLV3501, SHDN low enables the device; high turns it off and puts OUT in high impedance. The intended connection to GND is correct; do not leave it floating. [TI, §7.4.1](https://www.ti.com/lit/ds/symlink/tlv3501.pdf#page=11).

## TIA polarity and margins

The OPA380 allows a 2.7–5.5 V supply and common mode up to V+−1.8 V. At 5 V the 2.5 V bias is within the 3.2 V limit. The same mid-supply division is **not valid at 3.3 V**: 1.65 V exceeds 1.5 V. A positive photodiode bias is a topology explicitly provided for by TI. [OPA380, pages 3, 9 and 11](https://www.ti.com/lit/ds/symlink/opa380.pdf).

Circuit deduction: with the BPV10 anode to GND and cathode to the inverting node, the diode is reverse biased by about 2.5 V. The photocurrent leaves the node through the diode; the output must supply that current through Rf. Therefore `VOUT ≈ VBIAS + Iphoto × 10 kΩ`: more light makes VOUT rise. With VOUT connected to the comparator's −IN, the transition to white correctly generates a FALLING edge.

The guaranteed OPA380 output limit is about V+−0.6 V with the specified load. Conservative estimate at 5 V: margin 4.4−2.5=1.9 V, equal to about 190 µA with Rf=10 kΩ. This is not a photocurrent limit measured on the assembly. [OPA380, page 10](https://www.ti.com/lit/ds/symlink/opa380.pdf#page=10).

## Gain: correction of 11 November 2026

The check above verified the margin towards saturation, not the signal amplitude. From the BPV10 datasheet: 70 µA typical (38 minimum) at 1 mW/cm² and 950 nm, relative sensitivity about 0.45 at 550 nm, half angle ±20°. A white display at 250 cd/m² resting on the sensor gives a radiance of about 0.9 W/(m²·sr); over the useful angle of the BPV10 (about 0.5 sr) that equals 0.05 mW/cm², i.e. about **1 µA**. With Rf = 10 kΩ that is about 10 mV, below the comparator hysteresis calculated further on (18.5 mV). The A1b PCB therefore fits **Rf = 1 MΩ**: about 1 V at 250 cd/m², saturation above about 1.9 µA. With Cf = 15 pF the pole drops to 10.6 kHz (τ = 15 µs): at the threshold the delay is a few microseconds. This is an estimate, to be confirmed on TP2. The bandwidth calculations in the following paragraph still refer to the original 10 kΩ value.

## Bandwidth, threshold and photodiode

- Calculation on the feedback alone: 10 kΩ × 15 pF = 150 ns, pole about 1.06 MHz. It does not guarantee the real delay: diode capacitance, parasitics and stability must be verified. The choice is plausible; TI also shows a 10 kΩ / 16 pF example to limit the bandwidth near 1 MHz. [OPA380, page 12](https://www.ti.com/lit/ds/symlink/opa380.pdf#page=12).
- The TLV3501 already has about 6 mV of internal hysteresis. The 1 MΩ resistor adds positive hysteresis: with the 10 kΩ trimmer at mid-travel, the equivalent resistance is 2.5 kΩ and the ideal contribution is about `5 V × 2.5 kΩ/(1 MΩ+2.5 kΩ) = 12.5 mV`; approximate total 18.5 mV. This is a deduction, dependent on the trimmer position and the real output swing. Small optical signals might not allow reliable switching and re-arming. [TLV3501, §8.1.1](https://www.ti.com/lit/ds/symlink/tlv3501.pdf#page=12).
- The BPV10 sees visible and near infrared: band 380–1100 nm, peak 920 nm. Vishay specifies typical times of 80 ns rise and 60 ns fall at **10 V reverse, 50 Ω and 830 nm**; they are not a guarantee under the circuit's conditions. Typical capacitance 11 pF at 0 V, 3.8 pF at 5 V. Ambient light must be shielded and the white/black contrast measured on the real display. [BPV10, pages 1–3](https://www.vishay.com/docs/81502/bpv10.pdf).

## Hand assembly

The purchased codes with suffix **D** are SOIC-8; **DR** changes the packaging, not the package. Avoid confusing them with OPA380AIDGK or TLV3501AIDBVR. [OPA380AID page](https://www.ti.com/product/OPA380/part-details/OPA380AID), [TLV3501AID page](https://www.ti.com/product/TLV3501/part-details/TLV3501AID).

The D package has 1.27 mm pitch and accessible leads: practical judgement, it can be hand soldered with flux and magnification on an appropriate PCB/adapter. A SOIC→DIP adapter helps on 2.54 mm perfboard, but does not automatically make the fast layout valid. [Official drawing D0008A](https://www.ti.com/lit/pdf/MSOI002K).

TI requires bypass close to the pins, short paths and a good ground return for the comparator. For a dedicated PCB put the SOICs directly on the board, without adapters; keep the photodiode and Rf/Cf close to the OPA380 and separate the digital output path from the inverting node. These are implementation guidelines, not bring-up.  [TLV3501, §10](https://www.ti.com/lit/ds/symlink/tlv3501.pdf#page=15).

## Documentation corrections and tests needed

The statement that the diode must never load capacitance is a simplification: junction capacitance and parasitics remain. The claim that the capacitor on +IN must directly sustain the photocurrent steps is also imprecise: the main current flows in the inverting node and in the feedback. They do not compromise the topology, but do not by themselves justify the performance.

Before relying on the measurements: check the real supply and logic levels, bias in the dark, white/black increment, absence of saturation, transients/oscillations and multiple edges with an oscilloscope; then verify ISR, timer and software latency. The PCB must allow measuring VBIAS, TIA OUT and comparator OUT. The Teensy/firmware part was not verified here.
