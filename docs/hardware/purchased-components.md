# Components shown in the order screenshots

8 November 2026. Lorenzo confirms keeping the Teensy 2.0 and having purchased the components of the future optical version. The order images document the following items; they do not demonstrate the manufacturer's identity, the dimensions of the parts actually received, or performance.

| Component | Readable data | Implication for the PCB |
|---|---|---|
| BPV10 | Variant selected BPV10, listing of 10 pieces | Sensor of the current design; cylindrical optical package, to be confirmed physically |
| BPW34 | Variant selected BPW34, listing of 5 pieces | Flat alternative already purchased; do not confuse with an SMD variant inferred from the generic title |
| Trimmer | 3296W 10K | Provide screw access in the case; check the size of the real part |
| Feedback capacitor | 0805, 15 pF, NP0, 50 V | Confirms the SMD format of the capacitor; pads for hand soldering |
| Bypass capacitors | 100 nF, marking 104, radial ceramic | Footprint and lead length need attention near fast ICs |
| Resistors | Three images of axial resistors; values not readable | Do not infer 10k/1M/100R from the screenshot; values needed from the repo's bill of materials, to be confirmed |
| Adapters | SOP/SMD to DIP kit | Useful for experiments; avoidable if the ICs are soldered directly on the final PCB |
| Perfboard | 5 × 7 cm | Prototyping material, not needed for the board to be produced |

The later images confirm **OPA380AIDR SOIC-8** and **TLV3501AID/AIDR SOIC-8**. The resistors remain without readable values. The photographed OLED is an **EstarDyn 1.30 IIC V2.0, SH1106 128×64**, pinout **1 VDD, 2 GND, 3 SCK/SCL, 4 SDA**; stated size 35.5 × 33.5 × 4.3 mm, real header and holes to be verified. A1 connection via a cable. Teensy confirmed **2.0**, USB **Mini-B**.

The **10 µF capacitors do not appear in the photos**, as clarified by Lorenzo, who can obtain them from a friend. Selected: **2 × Panasonic ECEA1CKS100**, radial electrolytics **10 µF 16 V, Ø4 mm, height 5 mm, pitch 1.5 mm**, for C2 and C6. They are polarised, pad 1 positive, pad 2 GND; an equivalent must also respect the footprint and size. The local 100 nF ceramics are kept. The generic NP0 photo does not show a 10 µF capacitor.

The A1b bill of materials requires **2 × 10 kΩ, 2 × 1 MΩ, 1 × 100 Ω, 1%** (R3 changed from 10 kΩ to 1 MΩ in the revision of 11 November). Check the parts already available with the multimeter. R1 horizontal; R2–R5 vertical to reduce the footprint. Buttons chosen on the PCB: THT 6 × 6 mm, 4 terminals, reference height 4.3 mm; compare them with the parts available. Headers/cables and any Teensy sockets were not completely documented in the photos.

## BPV10 or BPW34

Primary sources: [Vishay BPV10](https://www.vishay.com/docs/81502/bpv10.pdf), [Vishay BPW34](https://www.vishay.com/docs/81521/bpw34.pdf).

The BPV10 is a 5 mm cylindrical sensor with a half-sensitivity angle of ±20°. The BPW34 is flat, 5.4 × 4.3 × 3.2 mm, angle ±65°. The latter offers an interesting mechanical option for a monitor-facing sensor in a flat case, but this is a design judgement, not demonstrated accuracy superiority.

Typical zero-bias capacitance differs: 11 pF for the BPV10, 70 pF for the BPW34. Choosing the photodiode therefore requires a new check of the TIA compensation, bandwidth and stability; changing the footprint is not enough while leaving Rf/Cf unverified. Do not connect both sensors in parallel to make them selectable. If two populations or two small optical heads are planned, the one not fitted must remain electrically excluded and the inverting node must keep very short paths.

Proposal: keep the BPV10 as the initial reference, consistent with the repo's bill of materials, evaluating the BPW34 for the compact format after comparing the signal on the display and the TIA stability. Do not order two different electronics just to use all the parts purchased.
