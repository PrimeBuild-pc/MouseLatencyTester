"""One-time conversion of our draft records to a native KiCad schematic.

Uses text-to-cad's existing S-expression parser; refuses to replace native edits.
KiCad ERC and a pin-by-pin specification check are required afterwards.
"""
from copy import deepcopy
from pathlib import Path
from shlex import split
from uuid import NAMESPACE_URL, uuid5
from cad.engine.formats.kicad import sexpr as sx

root = Path(__file__).resolve().parent
target = root / 'optical_front_end.kicad_sch'
assert not target.exists(), 'Edit the native schematic; do not regenerate it.'
def uid(key): return str(uuid5(NAMESPACE_URL, 'primebuild:optical-front-end:draft-a:'+key))
def node(tag,*values): return [sx.Sym(tag),*values]
def mm(value): return round(float(value)*0.0254,6)
sheet_id=uid('sheet')
library=sx.parse((root/'mlt.kicad_sym').read_text(encoding='utf-8'))
symbols={s[1]:s for s in library if isinstance(s,list) and s[0]=='symbol'}
embedded=[]
for name,symbol in symbols.items():
    symbol=deepcopy(symbol); symbol[1]='mlt:'+name; embedded.append(symbol)
out=node('kicad_sch',node('version',20250114),node('generator',sx.Sym('eeschema')),
         node('uuid',sheet_id),node('paper','A4'),
         node('title_block',node('title','MouseLatencyTester - optical front-end'),
              node('date','2026-11-08'),node('rev','DRAFT A'),
              node('comment',1,'Electrical draft / footprints pending / not bench tested')),
         node('lib_symbols',*embedded))
def effects(size=1.016,justify=None,hidden=False):
    n=node('effects',node('font',node('size',size,size)))
    if justify:n.append(node('justify',*(sx.Sym(x) for x in justify)))
    if hidden:n.append(sx.Sym('hide'))
    return n
source=(root/'optical_front_end.sch').read_text(encoding='utf-8').splitlines()
i=0; sequence=0
while i<len(source):
    line=source[i]; sequence+=1
    if line=='$Comp':
        end=source.index('$EndComp',i); block=source[i+1:end]
        library_id,ref=split(block[0])[1:3]
        pos=next(split(s) for s in block if s.startswith('P ')); x,y=map(mm,pos[1:3])
        angle=90 if block[-1].strip()=='0 -1 -1 0' else 0
        part=node('symbol',node('lib_id',library_id),node('at',x,y,angle),node('unit',1),
                  node('exclude_from_sim',sx.Sym('no')),node('in_bom',sx.Sym('yes')),
                  node('on_board',sx.Sym('yes')),node('dnp',sx.Sym('no')),node('uuid',uid(ref)))
        for item in block:
            if item.startswith('F '):
                field=split(item); number=int(field[1]); name=('Reference','Value','Footprint','Datasheet')[number]
                part.append(node('property',name,field[2],node('at',mm(field[4]),mm(field[5]),0),
                                 effects(mm(field[6]),['left'],field[7]=='0001')))
        part.append(node('instances',node('project','optical_front_end',
                    node('path','/'+sheet_id,node('reference',ref),node('unit',1)))))
        out.append(part); i=end
    elif line=='Wire Wire Line':
        a,b,c,d=map(mm,source[i+1].split())
        out.append(node('wire',node('pts',node('xy',a,b),node('xy',c,d)),
                   node('stroke',node('width',0),node('type',sx.Sym('default'))),node('uuid',uid(f'wire{sequence}')))); i+=1
    elif line.startswith('Text Label '):
        f=split(line); angle=int(f[4])*90
        out.append(node('label',source[i+1],node('at',mm(f[2]),mm(f[3]),angle),
                   effects(mm(f[5]),['right' if angle==180 else 'left','bottom']),node('uuid',uid(f'label{sequence}')))); i+=1
    elif line.startswith('Text Notes '):
        f=split(line)
        out.append(node('text',source[i+1],node('at',mm(f[2]),mm(f[3]),0),
                   effects(mm(f[5]),['left','bottom']),node('uuid',uid(f'text{sequence}')))); i+=1
    elif line.startswith('NoConn ~ '):
        f=split(line)
        out.append(node('no_connect',node('at',mm(f[2]),mm(f[3])),node('uuid',uid(f'nc{sequence}'))))
    elif line.startswith('Connection ~ '):
        f=split(line)
        out.append(node('junction',node('at',mm(f[2]),mm(f[3])),node('diameter',0),
                   node('color',0,0,0,0),node('uuid',uid(f'junction{sequence}'))))
    i+=1
out.extend([node('sheet_instances',node('path','/',node('page','1'))),node('embedded_fonts',sx.Sym('no'))])
text=sx.dumps(out)+'\n'
assert sx.parse(text)==out
target.write_text(text,encoding='utf-8')
print(target)
