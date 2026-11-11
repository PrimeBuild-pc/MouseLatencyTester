"""Assign vetted local footprints and retain the saved schematic as source."""
from pathlib import Path
from cad import kicad_sch
from cad.engine.formats.kicad import sexpr as sx
root=Path(__file__).resolve().parent
def get(n,k):return next((s for s in n if isinstance(s,list) and s[0]==k),None)
file=root/'mouse_latency_tester.kicad_sch'
before={(p.ref,p.number):(p.name,p.type,p.net) for p in kicad_sch.read(file).pins}
tree=sx.parse(file.read_text(encoding='utf-8'))
mapping={
 'U1':'SOIC-8_3.9x4.9mm_P1.27mm','U2':'SOIC-8_3.9x4.9mm_P1.27mm','U3':'Teensy2.0',
 'D1':'LED_D5.0mm', 'RV1':'Potentiometer_Bourns_3296W_Vertical',
 'J1':'PinHeader_1x04_P2.54mm_Vertical','J2':'PinHeader_1x02_P2.54mm_Vertical',
 'SW1':'SW_PUSH_6mm_H4.3mm','SW2':'SW_PUSH_6mm_H4.3mm',
 'C2':'CP_Radial_D4.0mm_P1.50mm','C6':'CP_Radial_D4.0mm_P1.50mm',
 'C3':'C_0805_2012Metric_Pad1.18x1.45mm_HandSolder',
}
for ref in ('C1','C4','C5'):mapping[ref]='C_Disc_D5.0mm_W2.5mm_P2.50mm'
for ref in ('R1',):mapping[ref]='R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal'
for ref in ('R2','R3','R4','R5'):mapping[ref]='R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical'
for ref in ('TP1','TP2','TP3','TP4'):mapping[ref]='TestPoint_Pad_D1.5mm'
for item in tree:
    if not isinstance(item,list) or item[0]!='symbol':continue
    props={n[1]:n for n in item if isinstance(n,list) and n[0]=='property'}
    ref=props['Reference'][2]
    if ref not in mapping:continue
    assert (root/'mlt.pretty'/f'{mapping[ref]}.kicad_mod').is_file(),ref
    props['Footprint'][2]='mlt:'+mapping[ref]
    if ref.startswith('SW'):
        at=get(item,'at')
        for name,dy in (('Reference',-4),('Value',4)):
            field=get(props[name],'at');field[1:3]=[at[1]+5,at[2]+dy]
file.write_text(sx.dumps(tree)+'\n',encoding='utf-8')
after={(p.ref,p.number):(p.name,p.type,p.net) for p in kicad_sch.read(file).pins}
assert before==after
(root/'fp-lib-table').write_text('''(fp_lib_table
  (version 7)
  (lib (name "mlt")(type "KiCad")(uri "${KIPRJMOD}/mlt.pretty")(options "")(descr "Verified local prototype footprints"))
)
''',encoding='utf-8')
# A missing courtyard in the source module is added to the local library copy.
fp_file=root/'mlt.pretty/Teensy2.0.kicad_mod'
fp=sx.parse(fp_file.read_text(encoding='utf-8'))
if not any(isinstance(x,list) and x[0]=='fp_line' and get(x,'layer')==[sx.Sym('layer'),'F.CrtYd'] for x in fp):
    for a,b in (((-16.76,-9.14),(15.49,-9.14)),((15.49,-9.14),(15.49,9.14)),((15.49,9.14),(-16.76,9.14)),((-16.76,9.14),(-16.76,-9.14))):
        fp.append([sx.Sym('fp_line'),[sx.Sym('start'),*a],[sx.Sym('end'),*b],[sx.Sym('layer'),'F.CrtYd'],[sx.Sym('width'),0.05]])
    fp_file.write_text(sx.dumps(fp)+'\n',encoding='utf-8')
print(f'{len(mapping)} schematic footprints assigned; all pin nets preserved.')
