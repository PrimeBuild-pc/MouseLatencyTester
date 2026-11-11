from pathlib import Path
from cad import kicad_sch,kicad_pcb
root=Path(__file__).resolve().parent
before={(p.part,p.number):p.net for p in kicad_pcb.read(root/'mouse_latency_tester.kicad_pcb').pads}
refs_before={p.ref for p in kicad_pcb.read(root/'mouse_latency_tester.kicad_pcb').parts}
export=kicad_sch.export(root/'mouse_latency_tester.kicad_sch','netlist',root/'checks')
netlist=next(p for p in export.written if str(p).endswith('.net'))
with kicad_pcb.edit(root/'mouse_latency_tester.kicad_pcb') as b:
    b.import_netlist(str(netlist))
after={(p.part,p.number):p.net for p in kicad_pcb.read(root/'mouse_latency_tester.kicad_pcb').pads}
assert before==after
assert refs_before=={p.ref for p in kicad_pcb.read(root/'mouse_latency_tester.kicad_pcb').parts}
print('Sourcing metadata synchronized; copper/pad net mapping preserved.')
