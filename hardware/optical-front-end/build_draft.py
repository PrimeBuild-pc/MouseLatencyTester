"""Create the first circuit draft; KiCad upgrades/validates its legacy source.

Run only before editing the native schematic. This script deliberately refuses
to overwrite an existing native design. No fabrication files are generated.
"""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parent
NAME = "optical_front_end"
assert not (ROOT / f"{NAME}.kicad_sch").exists(), "Native design exists; edit it instead."

library = (ROOT / "mlt.lib").read_text(encoding="utf-8")
for name, shutdown in (("OPA380", False), ("TLV3501", True)):
    extra = "X SHDN 8 100 -400 200 U 40 40 1 1 I" if shutdown else "X NC 8 300 400 200 D 40 40 1 1 N N"
    symbol = f'''#
DEF {name} U 0 30 Y Y 1 F N
F0 "U" 200 250 50 H V L CNN
F1 "{name}" 200 150 50 H V L CNN
F2 "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm_HandSolder" 0 0 40 H I C CNN
F3 "https://www.ti.com/lit/ds/symlink/{name.lower()}.pdf" 0 0 40 H I C CNN
DRAW
P 4 0 1 10 -150 200 -150 -200 200 0 -150 200 f
X NC 1 100 400 200 D 40 40 1 1 N N
X -IN 2 -350 -100 200 R 40 40 1 1 I
X +IN 3 -350 100 200 R 40 40 1 1 I
X V- 4 0 -400 250 U 40 40 1 1 W
X NC 5 200 400 200 D 40 40 1 1 N N
X OUT 6 400 0 200 L 40 40 1 1 O
X V+ 7 0 400 250 D 40 40 1 1 W
{extra}
ENDDRAW
ENDDEF
'''
    library = library.replace("#End Library", symbol + "#End Library")
(ROOT / "mlt.lib").write_text(library, encoding="utf-8")
(ROOT / "sym-lib-table").write_text('''(sym_lib_table
  (version 7)
  (lib (name "mlt")(type "KiCad")(uri "${KIPRJMOD}/mlt.kicad_sym")(options "")(descr "Project-local circuit symbols"))
)
''', encoding="utf-8")
(ROOT / f"{NAME}.kicad_pro").write_text("{}\n", encoding="utf-8")

lines = ['EESchema Schematic File Version 4', 'LIBS:mlt', 'EELAYER 29 0', 'EELAYER END',
         '$Descr A4 11693 8268', 'encoding utf-8', 'Sheet 1 1',
         'Title "MouseLatencyTester - optical front-end"', 'Date "2026-11-08"',
         'Rev "DRAFT A - electrical review"', 'Comp "PrimeBuild"',
         'Comment1 "BPV10 + OPA380 + TLV3501 / Teensy 2.0, 5 V only"',
         'Comment2 "Prototype: not physically tested; footprints/BOM pending"',
         '$EndDescr']
refs = set()
def component(ref, kind, value, x, y, rotate=False, footprint=""):
    assert ref not in refs, ref
    refs.add(ref)
    stamp = hashlib.sha256(ref.encode()).hexdigest()[:8].upper()
    matrix = '0 -1 -1 0' if rotate else '1 0 0 -1'
    visibility = '0001' if ref.startswith('#') else '0000'
    lines.extend(['$Comp', f'L mlt:{kind} {ref}', f'U 1 1 {stamp}', f'P {x} {y}',
                  f'F 0 "{ref}" H {x+180} {y+70} 45 {visibility} L CNN',
                  f'F 1 "{value}" H {x+180} {y-30} 45 {visibility} L CNN',
                  f'F 2 "{footprint}" H {x} {y} 40 0001 C CNN',
                  f'\t1    {x} {y}', f'\t{matrix}', '$EndComp'])
def wire(a, b):
    assert a != b
    lines.extend(['Wire Wire Line', f'\t{a[0]} {a[1]} {b[0]} {b[1]}'])
def label(net, at, orientation=0):
    lines.extend([f'Text Label {at[0]} {at[1]} {orientation} 40 ~ 0', net])
def stub(net, pin, dx=0, dy=-200):
    end=(pin[0]+dx,pin[1]+dy)
    wire(pin,end)
    label(net,end,1 if dy else (2 if dx < 0 else 0))
def note(text,x,y,size=55):
    lines.extend([f'Text Notes {x} {y} 0 {size} ~ 0',text])
def passive(ref,kind,value,x,y,top,bottom):
    component(ref,kind,value,x,y)
    stub(top,(x,y-150))
    stub(bottom,(x,y+150),dy=200)

note('1. BIAS (nominal 2.5 V)',1300,900)
component('R1','R','10k 1%',1600,1500)
component('R2','R','10k 1%',1600,2300)
stub('+5V',(1600,1350))
wire((1600,1650),(1600,2150))
wire((1600,1900),(1900,1900)); label('VBIAS',(1900,1900))
lines.append('Connection ~ 1600 1900')
stub('GND',(1600,2450),dy=200)
passive('C1','C','100nF',2500,2000,'VBIAS','GND')
passive('C2','C','10uF [package TBD]',3500,2000,'VBIAS','GND')

note('2. PHOTODIODE / TRANSIMPEDANCE',1300,3100)
component('D1','D_Photo','BPV10',2400,4000)
stub('SUM',(2200,4000),dx=-300,dy=0)
stub('GND',(2500,4000),dx=300,dy=0)
note('K -> SUM; A -> GND',1700,4500,45)
component('U1','OPA380','OPA380AIDR',4400,4000,footprint='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm_HandSolder')
stub('VBIAS',(4050,3900),dx=-150,dy=0)
wire((4050,4100),(3750,4100)); label('SUM',(3750,4100),2)
stub('+5V',(4400,3600),dy=-150)
stub('GND',(4400,4400),dy=150)
for x in (4500,4600,4700): lines.append(f'NoConn ~ {x} 3600')
component('R3','R','10k 1%',4400,3000,rotate=True)
component('C3','C','15pF NP0 0805',4400,3300,rotate=True,footprint='Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder')
wire((3750,4100),(3750,3000)); wire((3750,3000),(4250,3000))
wire((3750,3300),(4250,3300)); lines.append('Connection ~ 3750 3300')
wire((4550,3000),(5250,3000)); wire((4550,3300),(5250,3300))
wire((5250,3000),(5250,4000)); lines.append('Connection ~ 5250 3300')
wire((4800,4000),(5250,4000)); wire((5250,4000),(5500,4000)); label('TIA_OUT',(5500,4000))
lines.append('Connection ~ 5250 4000')

note('3. THRESHOLD / HYSTERESIS / DIGITAL OUTPUT',6100,900)
component('RV1','R_Potentiometer','3296W 10k',6700,1800)
stub('+5V',(6700,1650))
stub('GND',(6700,1950),dy=200)
stub('THRESH',(6850,1800),dx=300,dy=0)
component('R4','R','1M 1%',8000,1800,rotate=True)
stub('THRESH',(7850,1800),dx=-150,dy=0)
stub('CMP_RAW',(8150,1800),dx=150,dy=0)
component('U2','TLV3501','TLV3501AID',8000,3300,footprint='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm_HandSolder')
stub('THRESH',(7650,3200),dx=-150,dy=0)
stub('TIA_OUT',(7650,3400),dx=-150,dy=0)
stub('+5V',(8000,2900),dy=-150)
wire((8000,3700),(8000,3900)); wire((8100,3700),(8100,3900))
wire((8000,3900),(8100,3900)); stub('GND',(8000,3900),dy=150)
lines.append('Connection ~ 8000 3900')
for x in (8100,8200): lines.append(f'NoConn ~ {x} 2900')
wire((8400,3300),(8650,3300)); label('CMP_RAW',(8500,3300))
component('R5','R','100R 1%',8800,3300,rotate=True)
stub('OPT_TRIGGER',(8950,3300),dx=250,dy=0)

note('4. 5 V INPUT / OUTPUT TO TEENSY 2.0',9300,900)
component('J1','Conn_01x04','TO_TEENSY_2.0',10200,1600)
for y,net in ((1500,'+5V'),(1600,'GND'),(1700,'TIA_OUT'),(1800,'OPT_TRIGGER')):
    stub(net,(10000,y),dx=-400,dy=0)
component('#FLG01','PWR_FLAG','PWR_FLAG',9700,1500)
component('#FLG02','PWR_FLAG','PWR_FLAG',9700,1600)
lines.extend(['Connection ~ 9700 1500','Connection ~ 9700 1600'])
note('J1.1 -> VCC (~5 V USB)',9400,2300,45)
note('J1.2 -> GND',9400,2450,45)
note('J1.3 -> F0 / A0 (telemetry)',9400,2600,45)
note('J1.4 -> D3 / digital 8 (FALLING ISR)',9400,2750,45)
note('Not compatible with 3.3 V Teensy 4.x I/O',9400,3000,45)

note('5. LOCAL BYPASS / BULK SUPPLY',6100,4650)
passive('C4','C','100nF at U1',6500,5300,'+5V','GND')
passive('C5','C','100nF at U2',7900,5300,'+5V','GND')
passive('C6','C','10uF [package TBD]',9300,5300,'+5V','GND')
note('Place bypass at IC pins; keep D1 / U1 / R3 / C3 loop short.',6100,6000,45)

for i,(net,x) in enumerate((('VBIAS',1600),('TIA_OUT',2900),('CMP_RAW',4200),('GND',5500)),1):
    component(f'TP{i}','TestPoint',net,x,5350)
    stub(net,(x,5350),dy=300)
note('DRAFT: electrical schematic only. No routing, case clearance or bench validation.',1300,6400,55)
note('R/C values start from docs/optical_front_end.md. Gain and stability require measurement.',1300,6650,45)
note('Old probe D2/pin7, OLED and buttons remain on the Teensy carrier; not drawn on this sheet.',1300,6850,45)
lines.append('$EndSCHEMATC')
(ROOT / f"{NAME}.sch").write_text('\n'.join(lines)+'\n',encoding='utf-8')
assert {'U1','U2','D1','R1','R2','R3','R4','R5','C1','C2','C3','C4','C5','C6','RV1','J1'} <= refs
print(f'Created {NAME}.sch with {len(refs)} symbol instances. Convert library, then schematic with KiCad.')
