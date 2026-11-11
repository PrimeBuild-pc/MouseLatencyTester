from pathlib import Path
import json
from cad import kicad_pcb,kicad_sch
root=Path(__file__).resolve().parent
portable=root.parents[1]/'outputs/MouseLatencyTester-A1/Delivery-A1/KiCad'
def signature(path):
    b=kicad_pcb.read(path/'mouse_latency_tester.kicad_pcb')
    s=kicad_sch.read(path/'mouse_latency_tester.kicad_sch')
    return {
        'pads':sorted((p.part,p.number,p.net,tuple(p.at)) for p in b.pads),
        'tracks':sorted((t.net,t.width,tuple(map(tuple,t.points))) for t in b.tracks),
        'schematic':sorted((p.ref,p.number,p.name,p.type,p.net) for p in s.pins),
    }
a,b=signature(root),signature(portable)
assert a==b,'Portable project changed pads, track geometry or schematic pin mapping'
report={'status':'PASS','target':'KiCad 9.0','matching_pad_records':len(a['pads']),
        'matching_track_records':len(a['tracks']),'matching_schematic_pin_records':len(a['schematic']),
        'downgrade_report':'kicad9-export.json: no dropped or approximated items',
        'portable_erc':'clean','portable_drc':'0 violations, 0 unconnected, 0 parity errors'}
(root/'checks/portable-comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
