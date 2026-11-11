"""Independent pin mapping, geometry and routing checks of the saved revision."""
from pathlib import Path
import json,math,sys
from cad import kicad_sch,kicad_pcb
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent
sch=kicad_sch.read(root/'mouse_latency_tester.kicad_sch')
board=kicad_pcb.read(root/'mouse_latency_tester.kicad_pcb')
want={(p.ref,p.number):p.net for p in sch.pins if not p.ref.startswith('#')}
have={}
for p in board.pads:
    if p.part.startswith('H'):continue
    key=(p.part,p.number)
    if key in have:assert have[key]==p.net,(key,'duplicate pad on different net')
    have[key]=p.net
assert want==have,[(key,want.get(key),have.get(key)) for key in set(want)|set(have) if want.get(key)!=have.get(key)]
contract={
 'U1':{'2':'SUM','3':'VBIAS','4':'GND','6':'TIA_OUT','7':'+5V'},
 'U2':{'2':'TIA_OUT','3':'THRESH','4':'GND','6':'CMP_RAW','7':'+5V','8':'GND'},
 'U3':{'1':'GND','2':'BTN1','3':'BTN2','7':'I2C_SCL','8':'I2C_SDA','9':'PROBE','10':'OPT_TRIGGER','14':'+5V','15':'GND','28':'TIA_OUT','29':'+5V'},
 'D1':{'1':'SUM','2':'GND'},'J1':{'1':'+5V','2':'GND','3':'I2C_SCL','4':'I2C_SDA'},
 'J2':{'1':'PROBE','2':'GND'},'C2':{'1':'VBIAS','2':'GND'},'C6':{'1':'+5V','2':'GND'},
 'SW1':{'1':'BTN1','2':'GND'},'SW2':{'1':'BTN2','2':'GND'},
}
for ref,pins in contract.items():
    for number,net in pins.items():assert have[(ref,number)].removeprefix('/')==net,(ref,number,net)
off_angle=[]
for t in board.tracks:
    assert not t.net.startswith('unconnected-'),t.net
    for a,b in zip(t.points,t.points[1:]):
        angle=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))%45
        if min(angle,45-angle)>.001:off_angle.append((t.net,a,b))
assert not off_angle,off_angle
def at(ref,p):return board.part(ref).pad(str(p)).at
distances={ref:round(math.dist(at(ref,7),at(cap,1)),6) for ref,cap in (('U1','C4'),('U2','C5'))}
assert all(d<=3 for d in distances.values()),distances
assert round(math.dist(at('U3',1),at('U3',12)),6)==27.94
assert round(math.dist(at('U3',1),at('U3',29)),6)==15.24
minimum_track=min(t.width for t in board.tracks)
assert minimum_track>=.2-1e-6
from cad.engine.formats.kicad import sexpr as sx
tree=sx.parse((root/'mouse_latency_tester.kicad_pcb').read_text(encoding='utf-8'))
def item_field(item,tag):return next((f for f in item if isinstance(f,list) and f[0]==tag),None)
mechanical={}
for fp in tree:
    if not isinstance(fp,list) or fp[0]!='footprint':continue
    reference=next((f[2] for f in fp if isinstance(f,list) and f[0]=='property' and f[1]=='Reference'),None)
    if reference not in ('H1','H2','H3','H4'):continue
    attr=item_field(fp,'attr')
    assert attr and sx.Sym('board_only') in attr,reference
    holes=[p for p in fp if isinstance(p,list) and p[0]=='pad' and p[2]==sx.Sym('np_thru_hole')]
    assert len(holes)==1 and item_field(holes[0],'drill')[1]==2.2,reference
    transform=item_field(fp,'transform')
    position=item_field(transform,'translate')[1:] if transform else item_field(fp,'at')[1:3]
    mechanical[reference]=position
assert mechanical=={'H1':[3,3],'H2':[53,3],'H3':[3,45],'H4':[53,45]},mechanical
report={'status':'PASS','schematic_to_board_unique_pins':len(want),'explicit_datasheet_pin_checks':sum(map(len,contract.values())),
        'off_45_degree_segments':0,'decoupler_distance_mm':distances,'minimum_track_mm':minimum_track,
        'board_nominal_mm':[56,48,1.6],'layers':2,'mounting_holes_np_through':mechanical,'physical_test':'NOT PERFORMED','timing_accuracy':'NOT CHARACTERIZED'}
(root/'checks').mkdir(exist_ok=True)
# Every drilled hole of the board, for audit_fabrication.py to hold the Excellon files against.
holes=sorted([round(q.at[0],3),round(q.at[1],3),q.drill] for q in board.pads if q.drill)+sorted([round(v.at[0],3),round(v.at[1],3),v.drill] for v in board.vias)
holes+=[[x,y,2.2] for x,y in mechanical.values() if [x,y,2.2] not in holes]
(root/'checks/board-holes.json').write_text(json.dumps(sorted(holes))+'\n',encoding='utf-8')
assert board.part('R3').value=='1M 1%' and board.part('D1').pad('1').drill==1,'A1b review edits missing'
(root/'checks/independent-checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
