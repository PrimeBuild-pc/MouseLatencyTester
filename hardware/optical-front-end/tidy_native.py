"""Adjust only draft labels/fields after visual review; preserve electrical nets."""
from pathlib import Path
from cad import kicad_sch
from cad.engine.formats.kicad import sexpr as sx

root=Path(__file__).resolve().parent
file=root/'optical_front_end.kicad_sch'
before={(p.ref,p.number):(p.name,p.type,p.net) for p in kicad_sch.read(file).pins}
tree=sx.parse(file.read_text(encoding='utf-8'))
def get(n,k):return next((s for s in n if isinstance(s,list) and s[0]==k),None)
def mm(v):return round(v*0.0254,6)
positions={
 'U1':((4800,4350),(4800,4500)), 'U2':((8400,4100),(8400,4250)),
 'D1':((2400,4250),(2400,4380)), 'RV1':((7000,2070),(7000,2200)),
 'R3':((4400,2740),(4400,2860)), 'C3':((4400,3140),(4400,3440)),
 'R4':((8000,1500),(8000,1630)), 'R5':((8800,3000),(8800,3120)),
}
rotated={'R3','C3','R4','R5'}
values={'C2':'10uF','C3':'15pF NP0','C4':'100nF','C5':'100nF','C6':'10uF'}
for item in tree:
    if not isinstance(item,list):continue
    if item[0]=='symbol':
        props={s[1]:s for s in item if isinstance(s,list) and s[0]=='property'}
        ref=props['Reference'][2]
        if ref.startswith('#'):continue
        at=get(item,'at')
        pair=positions.get(ref,((at[1]/.0254+180,at[2]/.0254-70),(at[1]/.0254+180,at[2]/.0254+70)))
        for name,position in zip(('Reference','Value'),pair):
            field=props[name]; field_at=get(field,'at'); field_at[1:]=[mm(position[0]),mm(position[1]),90 if ref in rotated else 0]
            effects=get(field,'effects'); justify=get(effects,'justify')
            if justify:effects.remove(justify)
            if ref not in rotated:effects.append([sx.Sym('justify'),sx.Sym('left')])
        if ref in values:props['Value'][2]=values[ref]
    elif item[0]=='wire':
        pts=get(item,'pts')
        if pts[1][1:]==[mm(4400),mm(3600)] and pts[2][1:]==[mm(4400),mm(3450)]:
            pts[2][1:]=[mm(4100),mm(3600)]
    elif item[0]=='label' and item[1]=='+5V':
        at=get(item,'at')
        if at[1:3]==[mm(4400),mm(3450)]:at[1:]=[mm(4100),mm(3600),180]
file.write_text(sx.dumps(tree)+'\n',encoding='utf-8')
after={(p.ref,p.number):(p.name,p.type,p.net) for p in kicad_sch.read(file).pins}
assert before==after,'Electrical change during visual cleanup'
print('Field layout adjusted; every pin name/type/net preserved.')
