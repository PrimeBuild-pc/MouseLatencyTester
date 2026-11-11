"""Explicit hand-planned copper for the saved prototype; no autorouter.

Only items recorded in route-item-ids.json are replaced on a subsequent run.
Other board records and the footprints remain the editable source.
"""
from pathlib import Path
from uuid import NAMESPACE_URL,uuid5
import json,math
from cad import kicad_pcb
from cad.engine.formats.kicad import sexpr as sx
root=Path(__file__).resolve().parent
file=root/'mouse_latency_tester.kicad_pcb'
board=kicad_pcb.read(file)
def n(tag,*values):return [sx.Sym(tag),*values]
def get(item,tag):return next((p for p in item if isinstance(p,list) and p[0]==tag),None)
def uid(key):return str(uuid5(NAMESPACE_URL,'primebuild:mlt-route-a:'+key))
def pt(x,y):return (round(x,6),round(y,6))
def pad(ref,number):return pt(*board.part(ref).pad(str(number)).at)
def net_name(name):return '/'+name.removeprefix('/')
tree=sx.parse(file.read_text(encoding='utf-8'))
manifest=root/'checks/route-item-ids.json'
prior=set(json.loads(manifest.read_text(encoding='utf-8'))) if manifest.exists() else set()
tree=[item for item in tree if not(isinstance(item,list) and get(item,'uuid') and get(item,'uuid')[1] in prior)]
items=[];ids=[]
def add(item,key):
    identifier=uid(key);item.append(n('uuid',identifier));items.append(item);ids.append(identifier)
def route(key,net,layer,*points,width=.25):
    for i,(a,b) in enumerate(zip(points,points[1:])):
        a,b=pt(*a),pt(*b)
        if a==b:continue
        add(n('segment',n('start',*a),n('end',*b),n('width',width),n('layer',layer),n('net',net_name(net))),key+':'+str(i))
def via(key,net,at):
    add(n('via',n('at',*at),n('size',.7),n('drill',.3),n('layers','F.Cu','B.Cu'),n('net',net_name(net))),key)

# Board: 56 x 48 mm, 2 mm chamfers, 1.6 mm FR-4, two copper layers.
outline=[(0,2),(2,0),(54,0),(56,2),(56,46),(54,48),(2,48),(0,46),(0,2)]
for i,(a,b) in enumerate(zip(outline,outline[1:])):
    add(n('gr_line',n('start',*a),n('end',*b),n('stroke',n('width',.05),n('type',sx.Sym('default'))),n('layer','Edge.Cuts')),f'edge:{i}')

# Library placement through IPC is unavailable for board-only holes here.
# Embed the unchanged stock hole land pattern and give each its actual position.
existing_refs={p.ref for p in board.parts}
for ref,x,y in (('H1',3,3),('H2',53,3),('H3',3,45),('H4',53,45)):
    if ref in existing_refs and uid(ref) not in prior:continue
    fp=sx.parse((root/'mlt.pretty/MountingHole_2.2mm_M2.kicad_mod').read_text(encoding='utf-8'))
    fp[0]=sx.Sym('footprint');fp[1]='mlt:MountingHole_2.2mm_M2'
    attribute=get(fp,'attr')
    if attribute:attribute[1:]=[sx.Sym('board_only'),sx.Sym('exclude_from_pos_files'),sx.Sym('exclude_from_bom')]
    else:fp.append(n('attr',sx.Sym('board_only'),sx.Sym('exclude_from_pos_files'),sx.Sym('exclude_from_bom')))
    fp.append(n('transform',n('translate',x,y),n('rotate',0),n('scale',1,1)))
    for field in fp:
        if isinstance(field,list) and field[0]=='fp_text':
            if field[1]=='reference':field[2]=ref
            if field[1] in ('reference','value'):field.append(sx.Sym('hide'))
    add(fp,ref)

# TIA: small input island, reverse-side C0G directly under U1.
via('sum-via','SUM',(16.2,35.365))
route('sum-pin','SUM','F.Cu',pad('U1',2),(16.2,35.365),width=.2)
route('sum-cf','SUM','B.Cu',(16.2,35.365),(16.835,36),pad('C3',1),width=.2)
route('sum-rf','SUM','B.Cu',pad('R3',1),(13.5,32.665),(16.2,35.365),width=.2)
route('sum-diode','SUM','B.Cu',pad('D1',1),(14.93,36.635),(16.2,35.365),width=.2)
via('tia-via','TIA_OUT',(23.5,36.635))
route('tia-pin','TIA_OUT','F.Cu',pad('U1',6),(23.5,36.635),width=.2)
route('tia-cf','TIA_OUT','B.Cu',pad('C3',2),(22.3,36),(22.935,36.635),(23.5,36.635),width=.2)
route('tia-rf','TIA_OUT','B.Cu',pad('R3',2),(17,31.6),(21.0375,35.6375),pad('C3',2),width=.2)
route('tia-comp','TIA_OUT','F.Cu',pad('U1',6),(25.9,36.635),(27.17,35.365),pad('U2',2),width=.2)
via('tia-adc-via','TIA_OUT',(16.3,26))
route('tia-adc-f','TIA_OUT','F.Cu',pad('R3',2),(16.3,31.34),(16.3,26),width=.2)
route('tia-adc','TIA_OUT','B.Cu',(16.3,26),(12.96,26),(12.96,17.8),(5.86,10.7),(4.07,10.7),pad('U3',28),width=.2)
via('tia-test-via','TIA_OUT',(25,41.3))
route('tia-test-b','TIA_OUT','B.Cu',(23.5,36.635),(23.5,39.8),(25,41.3),width=.2)
route('tia-test-f','TIA_OUT','F.Cu',(25,41.3),pad('TP2',1),width=.2)

# Bias divider, local bypass and the ordinary 10uF radial bulk capacitor.
route('bias-r1-r2','VBIAS','F.Cu',pad('R1',2),(8,31.62),(4.38,31.62),pad('R2',1))
route('bias-c1','VBIAS','F.Cu',pad('R1',2),(11.12,28.5),pad('C1',1))
route('bias-input','VBIAS','F.Cu',pad('R1',2),(10.5,30.88),(10.5,32),(12.5,34),(15,34),(15,36),(15.635,36.635),pad('U1',3))
route('bias-bulk','VBIAS','F.Cu',pad('R2',1),(2,38.3),pad('C2',1))
route('bias-test','VBIAS','F.Cu',pad('C2',1),(5.7,42),pad('TP1',1))

# Comparator threshold and output damping.
route('threshold-pin','THRESH','F.Cu',pad('U2',3),(30,36.635),(30,40),(28.5,41.5))
route('threshold-pot','THRESH','B.Cu',pad('R4',1),(28.5,45.5),(37.96,45.5),pad('RV1',2))
route('comparator-series','CMP_RAW','F.Cu',pad('U2',6),(40.8,36.635),(41.365,37.2),pad('R5',1))
route('comparator-hysteresis','CMP_RAW','B.Cu',pad('R5',1),(38.5,41.5),pad('R4',2))
via('comparator-test-via','CMP_RAW',(31.5,44.6))
route('comparator-test-b','CMP_RAW','B.Cu',pad('R4',2),(32.5,42.96),(32.5,44.6),(31.5,44.6))
route('comparator-test-f','CMP_RAW','F.Cu',(31.5,44.6),pad('TP3',1))
route('optical-irq','OPT_TRIGGER','F.Cu',pad('R5',2),(43,34.86),(43,27),(41.5,25.5),(25.76,25.5),pad('U3',10))

# Slow interfaces. Their crossings use opposite layers, outside the optical island.
route('i2c-scl','I2C_SCL','B.Cu',pad('U3',7),(16.77,12.7),(39.08,12.7),pad('J1',3))
route('i2c-sda','I2C_SDA','B.Cu',pad('U3',8),(19.31,15.24),(41.62,15.24),pad('J1',4))
route('btn1','BTN1','F.Cu',pad('U3',2),(4.07,17.78),(42,17.78),(44.75,15.03),(44.75,14.75),(51.25,14.75))
route('btn2','BTN2','F.Cu',pad('U3',3),(6.61,20.32),(42,20.32),(43,21.32),(43,24.5),(46,27.5),(46,28.75),(51.25,28.75))
route('btn2-left-pad','BTN2','F.Cu',(46,28.75),(44.75,28.75))
route('probe','PROBE','B.Cu',pad('U3',9),(21.85,25.5),(52.5,25.5),(54,27),(54,36.5),pad('J2',1))

# Five-volt distribution; the high-frequency capacitors stay beside each IC.
route('power-left','+5V','B.Cu',pad('U3',29),(2.8,10.16),(2.8,27),(28,27),(29,28),pad('C6',1),width=.3)
route('power-divider','+5V','B.Cu',(2.8,27),(2.8,29.2),pad('R1',1),width=.3)
route('power-oled','+5V','F.Cu',pad('U3',29),(1.53,7),(34,7),pad('J1',1),width=.5)
route('power-module-end','+5V','B.Cu',pad('U3',14),(43.1,19.05),(43.1,2.5),(34,2.5),pad('J1',1),width=.5)
route('power-u1-b','+5V','B.Cu',pad('C6',1),(26.5,32),(25.3,33.2),pad('C4',1),width=.5)
route('power-u2-b','+5V','B.Cu',pad('C6',1),(29,28),(30.5,26.5),(36.3,26.5),(39.3,29.5),pad('C5',1),width=.5)
route('power-u1-pin','+5V','F.Cu',pad('C4',1),pad('U1',7),width=.3)
route('power-u2-pin','+5V','F.Cu',pad('C5',1),pad('U2',7),width=.3)
via('power-pot-via','+5V',(34,40))
route('power-pot-b','+5V','B.Cu',pad('C6',1),(29,28),(30.5,26.5),(34,26.5),(34,40),width=.5)
route('power-pot-f','+5V','F.Cu',(34,40),(35.5,41.5),(39.5,41.5),pad('RV1',1),width=.5)

for key,ref,pin,at in (('u1-ground','U1',4,(17.525,39)),('u2-ground','U2',4,(31.525,39)),('shutdown','U2',8,(36.475,32.8)),('ground-test','TP4',1,(21,44.8))):
    via(key+'-via','GND',at);route(key,'GND','F.Cu',pad(ref,pin),at,width=.3)

# Copper fill keeps away from the summing node, as required for TIA input capacitance.
for layer in ('F.Cu','B.Cu'):
    add(n('zone',n('net','/GND'),n('layer',layer),n('hatch',sx.Sym('edge'),.5),
          n('connect_pads',n('clearance',.2)),n('min_thickness',.2),
          n('fill',sx.Sym('yes'),n('thermal_gap',.3),n('thermal_bridge_width',.3)),
          n('polygon',n('pts',*(n('xy',*p) for p in ((.5,.5),(55.5,.5),(55.5,47.5),(.5,47.5)))))),layer+'-ground')
    add(n('zone',n('net',''),n('layer',layer),n('hatch',sx.Sym('edge'),.5),
          n('keepout',n('tracks',sx.Sym('allowed')),n('vias',sx.Sym('allowed')),n('pads',sx.Sym('allowed')),n('copperpour',sx.Sym('not_allowed')),n('footprints',sx.Sym('allowed'))),
          n('polygon',n('pts',*(n('xy',*p) for p in ((12,30.3),(19.9,30.3),(19.9,37.2),(12,37.2)))))),layer+'-input-void')

tree.extend(items)
file.write_text(sx.dumps(tree)+'\n',encoding='utf-8')
manifest.write_text(json.dumps(ids,indent=2)+'\n',encoding='utf-8')
project=root/'mouse_latency_tester.kicad_pro'
p=json.loads(project.read_text(encoding='utf-8'))
rules=p['board']['design_settings']['rules']
rules.update(min_clearance=.2,min_track_width=.2,min_via_annular_width=.15,min_copper_edge_clearance=.5,min_through_hole_diameter=.3)
classes=p.setdefault('net_settings',{}).setdefault('classes',[])
if not classes:classes.append({'name':'Default'})
for group in classes:
    if group['name']=='Default':group.update(clearance=.2,track_width=.25,via_diameter=.7,via_drill=.3)
project.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
print(f'Wrote {len(items)} explicit routing/outline/zone items. Refill and DRC required.')
