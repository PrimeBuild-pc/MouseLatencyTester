"""Read the exported files, independently of KiCad's editable board."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from gerbonara import ExcellonFile,GerberFile,LayerStack
import resvg_py
root=Path(__file__).resolve().parent
fab=root/'fab'
required={'F_Cu.gtl','B_Cu.gbl','F_Mask.gts','B_Mask.gbs','F_Silkscreen.gto','B_Silkscreen.gbo','Edge_Cuts.gm1'}
for suffix in required:
    p=fab/f'mouse_latency_tester-{suffix}'
    parsed=GerberFile.open(p)
    assert parsed.objects,(suffix,'empty plot')
pth=ExcellonFile.open(fab/'mouse_latency_tester-PTH.drl')
npth=ExcellonFile.open(fab/'mouse_latency_tester-NPTH.drl')
assert len(pth.objects)==80,len(pth.objects)
assert len(npth.objects)==4,len(npth.objects)
holes=sorted((round(o.x,3),round(o.y,3),round(o.tool.diameter,3)) for o in npth.objects)
assert holes==[(3,-45,2.2),(3,-3,2.2),(53,-45,2.2),(53,-3,2.2)],holes
# Drill files against the board they were exported from: same places, same diameters.
drilled=sorted([round(o.x,3),round(-o.y,3),round(o.tool.diameter,3)] for o in pth.objects+npth.objects)
wanted=json.loads((root/'checks/board-holes.json').read_text(encoding='utf-8'))
assert drilled==wanted,[h for h in drilled+wanted if h not in drilled or h not in wanted]
edge=GerberFile.open(fab/'mouse_latency_tester-Edge_Cuts.gm1')
(x0,y0),(x1,y1)=edge.bounding_box('mm')
assert abs(x1-x0-56)<.11 and abs(y1-y0-48)<.11,(x0,y0,x1,y1)
stack=LayerStack.open(fab)
for side in ('top','bottom'):
    (root/f'gerber-{side}.svg').write_text(str(stack.to_pretty_svg(side=side)),encoding='utf-8')
for side in ('top','bottom'):
    svg=ET.fromstring((root/f'gerber-{side}.svg').read_text(encoding='utf-8'))
    svg.set('width','1600')
    svg.set('height','1372')
    png=resvg_py.svg_to_bytes(svg_string=ET.tostring(svg,encoding='unicode'),width=1600,height=1372,dpi=96,background='#ffffff')
    (root/f'gerber-{side}.png').write_bytes(png)
report={'status':'PASS','gerber_layers':sorted(required),'plated_holes':len(pth.objects),'holes_match_board':len(drilled),'outline_mm':[round(x1-x0,2),round(y1-y0,2)],
        'unplated_holes':holes,'slots':0,'renders':'Gerbonara SVG + resvg, from exported Gerber/Excellon files',
        'physical_verification':'NOT PERFORMED'}
(root/'checks/fabrication-files.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
