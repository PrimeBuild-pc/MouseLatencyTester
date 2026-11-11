"""Place readable references and remove module decoration from fabrication silk."""
from pathlib import Path
import math
from cad.engine.formats.kicad import sexpr as sx
root=Path(__file__).resolve().parent
def get(item,tag):return next((p for p in item if isinstance(p,list) and p[0]==tag),None)
def n(tag,*v):return [sx.Sym(tag),*v]
def clean_teensy(fp):
    for item in fp:
        if not isinstance(item,list):continue
        if item[0] in ('fp_line','fp_poly','fp_circle','fp_arc','fp_rect','fp_text'):
            if item[0]=='fp_text' and item[1] in ('reference','value'):continue
            layer=get(item,'layer')
            if layer and str(layer[1])=='F.SilkS':layer[1]='F.Fab'
        elif item[0]=='pad' and str(item[1])=='1':
            connect=get(item,'zone_connect')
            if connect:connect[1]=2
            else:item.append(n('zone_connect',2))
library=root/'mlt.pretty/Teensy2.0.kicad_mod'
fp=sx.parse(library.read_text(encoding='utf-8'));clean_teensy(fp)
library.write_text(sx.dumps(fp)+'\n',encoding='utf-8')
file=root/'mouse_latency_tester.kicad_pcb'
tree=sx.parse(file.read_text(encoding='utf-8'))
positions={'U3':(15.5,5.7),'R2':(6.8,34.0),'R3':(18.5,30.0),'C1':(13.75,26.0),
           'C2':(8.2,38.2),'C5':(41.8,35.0),'R5':(46,39.8),'D1':(12.27,40.5)}
for fp in tree:
    if not isinstance(fp,list) or fp[0]!='footprint':continue
    reference=next((p for p in fp if isinstance(p,list) and p[0]=='property' and p[1]=='Reference'),None)
    if reference is None:continue
    ref=reference[2]
    if ref=='U3':clean_teensy(fp)
    if ref.startswith('H'):
        if not get(reference,'hide'):reference.append(n('hide',sx.Sym('yes')))
    if ref in positions:
        transform=get(fp,'transform');pos=get(transform,'translate');theta=get(transform,'rotate')[1]
        x,y=positions[ref];dx,dy=x-pos[1],y-pos[2];a=math.radians(theta)
        local=(round(math.cos(a)*dx-math.sin(a)*dy,6),round(math.sin(a)*dx+math.cos(a)*dy,6))
        get(reference,'at')[1:]=[*local,-theta]
file.write_text(sx.dumps(tree)+'\n',encoding='utf-8')
print('Adjusted silk; solid ground connection on module pad 1 resolves the starved thermal.')
