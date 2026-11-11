"""Place the prototype from its schematic netlist, without routing or export."""
from pathlib import Path
import json
from cad import kicad_pcb,kicad_sch
from kicode.geometry import Vector2,Angle
from kicode.proto.board.board_types_pb2 import BoardLayer
root=Path(__file__).resolve().parent
schematic=root/'mouse_latency_tester.kicad_sch'
board_file=root/'mouse_latency_tester.kicad_pcb'
export=kicad_sch.export(schematic,'netlist',root/'checks')
netlist=next(p for p in export.written if str(p).endswith('.net'))
positions={
 'U3':(15.5,16.51,0),'U1':(20,36,0),'U2':(34,36,0),
 'D1':(13.54,36.635,180),'C3':(20,36,0),
 'R1':(2,30,0),'R2':(2,34,0),'R3':(13.5,31.6,0),
 'R4':(28.5,41.5,0),'R5':(42.8,37.2,0),
 'C1':(12.5,28.5,0),'C2':(3.5,39.8,0),'C6':(29,29.5,0),
 'C4':(25.3,35.365,-90),'C5':(39.3,35.365,-90),
 'RV1':(42,44,0),'J1':(34,4.5,90),'J2':(48,42.5,0),
 'SW1':(44.75,14.75,0),'SW2':(44.75,28.75,0),
 'TP1':(9,42,0),'TP2':(25,42.5,0),'TP3':(31.5,46,0),'TP4':(21,46,0),
}
with kicad_pcb.edit(board_file) as board:
    result=board.import_netlist(str(netlist))
    print('Netlist import completed.')
    fps={fp.reference_field.text.value:fp for fp in board.get_footprints()}
    assert set(positions)<=set(fps),set(positions)-set(fps)
    for ref in ('D1','C3'):
        fp=fps[ref]
        if fp.layer!=BoardLayer.BL_B_Cu:board.flip_items([fp])
    fps={fp.reference_field.text.value:fp for fp in board.get_footprints()}
    for ref,(x,y,angle) in positions.items():
        fp=fps[ref];fp.position=Vector2.from_xy_mm(x,y);fp.orientation=Angle.from_degrees(angle)
        fp.value_field.visible=False
        board.update_items([fp])
board=kicad_pcb.read(board_file)
data={ref:[{'number':pad.number,'at':pad.at,'net':pad.net} for pad in board.part(ref).pads] for ref in positions}
(root/'checks/pad-positions.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print('Saved initial positions; no fabrication output. Pad coordinates in checks/pad-positions.json.')
