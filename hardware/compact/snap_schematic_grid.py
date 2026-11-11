"""Snap the newly placed connection geometry to KiCad's 50 mil grid."""
from pathlib import Path
from cad import kicad_sch
from cad.engine.formats.kicad import sexpr as sx
file=Path(__file__).resolve().parent/'mouse_latency_tester.kicad_sch'
original=file.read_text(encoding='utf-8')
before={(p.ref,p.number):(p.name,p.type,p.net) for p in kicad_sch.read(file).pins}
tree=sx.parse(original)
def find(item,tag):return next((s for s in item if isinstance(s,list) and s[0]==tag),None)
def snap(v):return round(round(v/1.27)*1.27,6)
for item in tree:
    if not isinstance(item,list):continue
    if item[0] in ('symbol','label','junction','no_connect'):
        at=find(item,'at')
        if not at:continue
        dx,dy=snap(at[1])-at[1],snap(at[2])-at[2]
        at[1:3]=[snap(at[1]),snap(at[2])]
        if item[0]=='symbol':
            for field in item:
                if isinstance(field,list) and field[0]=='property':
                    pos=find(field,'at')
                    if pos:pos[1:3]=[round(pos[1]+dx,6),round(pos[2]+dy,6)]
    elif item[0]=='wire':
        pts=find(item,'pts')
        for point in pts[1:]:point[1:3]=[snap(point[1]),snap(point[2])]
file.write_text(sx.dumps(tree)+'\n',encoding='utf-8')
after={(p.ref,p.number):(p.name,p.type,p.net) for p in kicad_sch.read(file).pins}
if before!=after:
    file.write_text(original,encoding='utf-8')
    raise AssertionError('Snapping changed a pin: source restored')
print('50 mil grid applied; all pin names, types and nets preserved.')
