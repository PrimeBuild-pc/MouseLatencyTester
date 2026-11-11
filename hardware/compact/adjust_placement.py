from pathlib import Path
from cad import kicad_pcb
from kicode.geometry import Vector2
root=Path(__file__).resolve().parent
with kicad_pcb.edit(root/'mouse_latency_tester.kicad_pcb') as board:
    fps={f.reference_field.text.value:f for f in board.get_footprints()}
    for ref,(x,y) in {'R1':(2,30),'R2':(2,34),'C1':(12.5,28.5),'C4':(25.3,35.365),'C5':(39.3,35.365)}.items():
        fp=fps[ref];fp.position=Vector2.from_xy_mm(x,y);board.update_items([fp])
print('Adjusted clearances; reroute affected copper before checking.')
