from pathlib import Path
from cad.engine.formats.kicad import sexpr as sx
root=Path(__file__).resolve().parent
tree=sx.parse((root/'sources/teensy.kicad_sym').read_text(encoding='utf-8'))
symbol=next(n for n in tree if isinstance(n,list) and n[0]=='symbol' and n[1]=='Teensy2.0_(C)')
for unit in symbol:
    if not isinstance(unit,list) or unit[0]!='symbol':continue
    for pin in unit:
        if not isinstance(pin,list) or pin[0]!='pin':continue
        fields={n[0]:n[1:] for n in pin if isinstance(n,list)}
        print(fields['number'][0],fields['name'][0],fields['at'],pin[1])
