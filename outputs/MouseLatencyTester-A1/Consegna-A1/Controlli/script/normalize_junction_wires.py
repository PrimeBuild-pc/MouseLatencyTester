"""Split wires at explicit junctions for consistent KiCad 9/10 connectivity.

Does not join unmarked crossings or change the circuit. Existing segment UUIDs
are retained; extra segments receive deterministic UUIDs. Safe to run again.
"""
from pathlib import Path
from copy import deepcopy
from uuid import UUID,uuid5
import json,sys
from cad import kicad_sch
from cad.engine.formats.kicad import sexpr as sx

def get(n,k):return next((f for f in n if isinstance(f,list) and f[0]==k),None)
def pins(file):return {(p.ref,p.number):(p.name,p.type,p.net) for p in kicad_sch.read(file).pins}
def normalize(file):
    original=file.read_text(encoding='utf-8');before=pins(file)
    tree=sx.parse(original)
    junctions=[tuple(get(n,'at')[1:3]) for n in tree if isinstance(n,list) and n[0]=='junction']
    result=[];changes=[]
    for n in tree:
        if not isinstance(n,list) or n[0]!='wire':result.append(n);continue
        a,b=[tuple(p[1:3]) for p in get(n,'pts')[1:]]
        dx,dy=b[0]-a[0],b[1]-a[1];length=dx*dx+dy*dy
        if not length:result.append(n);continue
        cuts=[]
        for x,y in junctions:
            t=((x-a[0])*dx+(y-a[1])*dy)/length
            if 1e-8<t<1-1e-8 and abs((x-a[0])*dy-(y-a[1])*dx)<1e-8:cuts.append((t,(x,y)))
        if not cuts:result.append(n);continue
        ordered=[a]+[p for t,p in sorted(set(cuts))]+[b]
        original_id=get(n,'uuid')[1]
        for i,(start,end) in enumerate(zip(ordered,ordered[1:])):
            segment=deepcopy(n);p=get(segment,'pts');p[1][1:]=start;p[2][1:]=end
            if i:get(segment,'uuid')[1]=str(uuid5(UUID(original_id),f'split:{i}:{start}:{end}'))
            result.append(segment)
        changes.append(original_id)
    if changes:
        file.write_text(sx.dumps(result)+'\n',encoding='utf-8')
        if before!=pins(file):
            file.write_text(original,encoding='utf-8')
            raise AssertionError('Circuit mapping changed; original restored')
    return {'path':str(file),'split_wires':changes,'intended_pin_mapping':'unchanged'}

if __name__=='__main__':
    files=[Path(p).resolve() for p in sys.argv[1:]] or [Path(__file__).resolve().parent/'mouse_latency_tester.kicad_sch']
    for file in files:print(json.dumps(normalize(file)))
