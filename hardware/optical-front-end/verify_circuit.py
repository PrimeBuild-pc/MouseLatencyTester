"""Check the saved design against the independently reviewed pin/net contract."""
from pathlib import Path
from cad import kicad_sch

root=Path(__file__).resolve().parent
schematic=kicad_sch.read(root/'optical_front_end.kicad_sch')
expected={
    'U1': {'2':'SUM','3':'VBIAS','4':'GND','6':'TIA_OUT','7':'+5V'},
    'U2': {'2':'TIA_OUT','3':'THRESH','4':'GND','6':'CMP_RAW','7':'+5V','8':'GND'},
    'D1': {'1':'SUM','2':'GND'},
    'RV1': {'1':'+5V','2':'THRESH','3':'GND'},
    'R1': {'1':'+5V','2':'VBIAS'},'R2': {'1':'VBIAS','2':'GND'},
    'R3': {'1':'SUM','2':'TIA_OUT'},'R4': {'1':'THRESH','2':'CMP_RAW'},
    'R5': {'1':'CMP_RAW','2':'OPT_TRIGGER'},
    'C1': {'1':'VBIAS','2':'GND'},'C2': {'1':'VBIAS','2':'GND'},
    'C3': {'1':'SUM','2':'TIA_OUT'},
    'C4': {'1':'+5V','2':'GND'},'C5': {'1':'+5V','2':'GND'},'C6': {'1':'+5V','2':'GND'},
    'J1': {'1':'+5V','2':'GND','3':'TIA_OUT','4':'OPT_TRIGGER'},
    'TP1': {'1':'VBIAS'},'TP2': {'1':'TIA_OUT'},'TP3': {'1':'CMP_RAW'},'TP4': {'1':'GND'},
}
pins={(p.ref,p.number):p for p in schematic.pins}
for ref,values in expected.items():
    for number,net in values.items():
        pin=pins[(ref,number)]
        assert pin.net.removeprefix('/')==net,(ref,number,pin.net,net)
nc={('U1','1'),('U1','5'),('U1','8'),('U2','1'),('U2','5')}
for key in nc:
    assert pins[key].type=='no_connect',(key,pins[key].type)
    assert pins[key].net.startswith('unconnected-'),(key,pins[key].net)
for ref in ('U1','U2'):
    assert {p.number for p in schematic.pins if p.ref==ref}==set(map(str,range(1,9)))
assert len(schematic.no_connects)==5,len(schematic.no_connects)
print(f'PASS: {sum(map(len,expected.values()))} connected pins, five NC pins, both 8-pin IC definitions.')
