from pathlib import Path
from cad import kicad_sch
from cad.engine.formats.kicad import sexpr as sx
root=Path(__file__).resolve().parent
file=root/'mouse_latency_tester.kicad_sch'
before={(p.ref,p.number):(p.name,p.type,p.net) for p in kicad_sch.read(file).pins}
tree=sx.parse(file.read_text(encoding='utf-8'))
def get(n,k):return next((s for s in n if isinstance(s,list) and s[0]==k),None)
title=get(tree,'title_block');get(title,'rev')[1]='Prototype A1 / BPV10'
get(title,'comment')[2]='PCBWay bare board 56 x 48 mm / first build requires bench validation'
for part in tree:
    if not isinstance(part,list) or part[0]!='symbol':continue
    fields={s[1]:s for s in part if isinstance(s,list) and s[0]=='property'}
    ref=fields['Reference'][2]
    if ref=='J1':fields['Value'][2]='OLED connector 1x04'
    if ref=='J2':fields['Value'][2]='PROBE connector 1x02'
    mpn={'U1':'OPA380AIDR','U2':'TLV3501AID','D1':'BPV10','U3':'Teensy 2.0'}.get(ref)
    if mpn:
        if 'MPN' in fields:fields['MPN'][2]=mpn
        else:part.append([sx.Sym('property'),'MPN',mpn,[sx.Sym('at'),0,0,0],[sx.Sym('effects'),[sx.Sym('font'),[sx.Sym('size'),1.016,1.016]],sx.Sym('hide')]])
file.write_text(sx.dumps(tree)+'\n',encoding='utf-8')
assert before=={(p.ref,p.number):(p.name,p.type,p.net) for p in kicad_sch.read(file).pins}
print('Prototype revision and sourcing fields set; electrical mapping unchanged.')
