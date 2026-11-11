from pathlib import Path
from cad import kicad_pcb
from kicode.geometry import Vector2
root=Path(__file__).resolve().parent
with kicad_pcb.edit(root/'mouse_latency_tester.kicad_pcb') as board:
    have={fp.reference_field.text.value for fp in board.get_footprints()}
    for ref,x,y in (('H1',3,3),('H2',53,3),('H3',3,45),('H4',53,45)):
        if ref in have:continue
        fp=board.place_footprint_from_library('mlt:MountingHole_2.2mm_M2',Vector2.from_xy_mm(x,y))
        fp.reference_field.text.value=ref;fp.value_field.visible=False
        board.update_items([fp])
print('Four M2 mounting holes present.')
