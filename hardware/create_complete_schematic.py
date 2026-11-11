"""Initial complete schematic, derived from the reviewed optical sheet.

Never overwrites an existing native design. Source optical sheet stays untouched.
"""
from copy import deepcopy
from pathlib import Path
from uuid import NAMESPACE_URL,uuid5
from cad.engine.formats.kicad import sexpr as sx
from cad import kicad_sch

root=Path(__file__).resolve().parent
folder=root/'compact';folder.mkdir(exist_ok=True)
file=folder/'mouse_latency_tester.kicad_sch'
assert not file.exists(),'Native complete schematic already exists: edit it in place.'
def n(tag,*args):return [sx.Sym(tag),*args]
def get(node,tag):return next((s for s in node if isinstance(s,list) and s[0]==tag),None)
def uid(key):return str(uuid5(NAMESPACE_URL,'primebuild:mlt-complete-a:'+key))
def effects(size=1.016,justify=('left','bottom'),hide=False):
    result=n('effects',n('font',n('size',size,size)))
    if justify:result.append(n('justify',*(sx.Sym(s) for s in justify)))
    if hide:result.append(sx.Sym('hide'))
    return result
base=root/'optical-front-end'
tree=sx.parse((base/'optical_front_end.kicad_sch').read_text(encoding='utf-8'))
old_id=get(tree,'uuid')[1];sheet_id=uid('sheet');get(tree,'uuid')[1]=sheet_id
get(tree,'paper')[1]='A3'
title=get(tree,'title_block');get(title,'title')[1]='MouseLatencyTester - complete prototype circuit'
get(title,'rev')[1]='DRAFT B - complete electrical schematic'
get(title,'comment')[2]='Teensy 2.0 / BPV10 / SH1106 - no fabrication approval'
embedded=get(tree,'lib_symbols')
lib=sx.parse((base/'mlt.kicad_sym').read_text(encoding='utf-8'))
for path in ('carrier-extra.kicad_sym','cap-polarized.kicad_sym'):
    extras=sx.parse((root/'sources'/path).read_text(encoding='utf-8'))
    for s in extras:
        if isinstance(s,list) and s[0]=='symbol':lib.append(s)
teensy_lib=sx.parse((root/'sources/teensy.kicad_sym').read_text(encoding='utf-8'))
teensy=deepcopy(next(s for s in teensy_lib if isinstance(s,list) and s[0]=='symbol' and s[1]=='Teensy2.0_(C)'))
teensy[1]='Teensy2.0_C'
for unit in teensy:
    if not isinstance(unit,list) or unit[0]!='symbol':continue
    unit[1]=unit[1].replace('Teensy2.0_(C)','Teensy2.0_C',1)
    for pin in unit:
        if isinstance(pin,list) and pin[0]=='pin':
            # Keep the verified physical pad numbers and electrical types.
            get(pin,'name')[1]=get(pin,'name')[1].split('_')[0]
lib.append(teensy)
symbols={s[1]:s for s in lib if isinstance(s,list) and s[0]=='symbol'}
for name in ('SW_Push','Conn_01x02','C_Polarized','Teensy2.0_C'):
    item=deepcopy(symbols[name]);item[1]='mlt:'+name;embedded.append(item)

# Remove the standalone optical module's external header and its annotation.
clean=[]
for item in tree:
    if not isinstance(item,list):clean.append(item);continue
    if item[0]=='symbol':
        props={p[1]:p for p in item if isinstance(p,list) and p[0]=='property'}
        ref=props['Reference'][2]
        if ref=='J1':continue
        if ref in ('C2','C6'):
            get(item,'lib_id')[1]='mlt:C_Polarized';props['Value'][2]='10uF 16V'
            props['Footprint'][2]='mlt:CP_Radial_D4.0mm_P1.50mm'
            item.append(n('property','MPN','ECEA1CKS100',n('at',0,0,0),effects(hide=True)))
        if ref.startswith('#FLG'):
            # These flags identify the USB-powered rail from the existing module.
            at=get(item,'at');at[1:3]=[268,34 if ref.endswith('01') else 44]
        instances=get(item,'instances')
        if instances:
            for project in instances[1:]:
                project[1]='mouse_latency_tester'
                for path in project[2:]:
                    if isinstance(path,list) and path[0]=='path':path[1]=path[1].replace(old_id,sheet_id)
    elif item[0]=='wire':
        pts=get(item,'pts');a,b=pts[1][1:],pts[2][1:]
        if abs(a[0]-254)<1e-6 and abs(b[0]-243.84)<1e-6 and 38<=a[1]<=46:continue
    elif item[0]=='label':
        at=get(item,'at')
        if abs(at[1]-243.84)<1e-6 and 38<=at[2]<=46:continue
    elif item[0]=='junction':
        at=get(item,'at')
        if abs(at[1]-246.38)<1e-6 and 38<=at[2]<=41:continue
    elif item[0]=='text':
        text=item[1]
        if text.startswith(('4. 5 V INPUT','J1.','Not compatible','Old probe')):continue
    clean.append(item)
tree=clean
def label(net,x,y,angle=0):
    tree.append(n('label',net,n('at',x,y,angle),effects(justify=('right' if angle==180 else 'left','bottom')),n('uuid',uid(f'label:{net}:{x}:{y}'))))
def wire(x,y,xx,yy):
    tree.append(n('wire',n('pts',n('xy',x,y),n('xy',xx,yy)),n('stroke',n('width',0),n('type',sx.Sym('default'))),n('uuid',uid(f'wire:{x}:{y}:{xx}:{yy}'))))
def text(message,x,y,size=1.27):
    tree.append(n('text',message,n('at',x,y,0),effects(size),n('uuid',uid(message))))
def part(ref,kind,value,x,y,footprint=''):
    symbol=n('symbol',n('lib_id','mlt:'+kind),n('at',x,y,0),n('unit',1),
             n('exclude_from_sim',sx.Sym('no')),n('in_bom',sx.Sym('yes')),n('on_board',sx.Sym('yes')),n('dnp',sx.Sym('no')),n('uuid',uid(ref)))
    for key,val,yy in (('Reference',ref,y-3),('Value',value,y),('Footprint',footprint,y+3)):
        symbol.append(n('property',key,val,n('at',x+5,yy,0),effects(hide=key=='Footprint')))
    symbol.append(n('instances',n('project','mouse_latency_tester',n('path','/'+sheet_id,n('reference',ref),n('unit',1)))))
    tree.append(symbol)
    return symbol
def hook(ref,kind,cx,cy,pin_nets):
    pins=[]
    for unit in symbols[kind]:
        if isinstance(unit,list) and unit[0]=='symbol':
            pins.extend(p for p in unit if isinstance(p,list) and p[0]=='pin')
    for pin in pins:
        number=get(pin,'number')[1];at=get(pin,'at');x=round(cx+at[1],6);y=round(cy-at[2],6)
        if number not in pin_nets:
            tree.append(n('no_connect',n('at',x,y),n('uuid',uid(ref+':nc:'+number))));continue
        end_x=round(x+(-5.08 if at[1]<0 else 5.08),6)
        wire(x,y,end_x,y);label(pin_nets[number],end_x,y,180 if at[1]<0 else 0)

label('+5V',268,34);label('GND',268,44)
text('4. USB-powered rails from Teensy 2.0',236,24)
text('Mini-B USB; all sensor electronics share GND.',236,54,1.016)
text('6. TEENSY 2.0 / EXISTING MODULE',300,22)
part('U3','Teensy2.0_C','Teensy 2.0',340,75,'mlt:Teensy2.0')
teensy_nets={'1':'GND','2':'BTN1','3':'BTN2','7':'I2C_SCL','8':'I2C_SDA',
             '9':'PROBE','10':'OPT_TRIGGER','14':'+5V','15':'GND','28':'TIA_OUT','29':'+5V'}
hook('U3','Teensy2.0_C',340,75,teensy_nets)
text('D2 = Arduino 7: probe / D3 = Arduino 8: optical IRQ',300,104,1.016)
text('F0 = A0: analog telemetry only; I2C pauses during measurement.',300,109,1.016)

text('7. OLED / EXTERNAL PROBE / BUTTONS',300,120)
part('J1','Conn_01x04','OLED SH1106',320,138)
hook('J1','Conn_01x04',320,138,{'1':'+5V','2':'GND','3':'I2C_SCL','4':'I2C_SDA'})
part('J2','Conn_01x02','PROBE + RETURN',380,138)
hook('J2','Conn_01x02',380,138,{'1':'PROBE','2':'GND'})
part('SW1','SW_Push','BTN1',320,160)
hook('SW1','SW_Push',320,160,{'1':'BTN1','2':'GND'})
part('SW2','SW_Push','BTN2',380,160)
hook('SW2','SW_Push',380,160,{'1':'BTN2','2':'GND'})
text('OLED pins: 1 VDD, 2 GND, 3 SCK/SCL, 4 SDA (seller photos).',300,178,1.016)
text('OLED envelope 35.5 x 33.5 x 4.3 mm; header excluded/unverified.',300,183,1.016)
text('BTN1/BTN2 and probe use INPUT_PULLUP; no external pull-down.',300,188,1.016)
text('C2/C6: polarized 10uF/16V radial, + at VBIAS/+5V; - at GND.',300,198,1.016)
text('Reference: Panasonic ECEA1CKS100, body D4 x H5 mm, pitch 1.5 mm.',300,203,1.016)
text('Borrowed substitutes must match voltage, polarity and actual footprint/height.',300,208,1.016)

(folder/'mlt.kicad_sym').write_text(sx.dumps(lib)+'\n',encoding='utf-8')
(folder/'sym-lib-table').write_text((base/'sym-lib-table').read_text(encoding='utf-8'),encoding='utf-8')
(folder/'mouse_latency_tester.kicad_pro').write_text('{}\n',encoding='utf-8')
file.write_text(sx.dumps(tree)+'\n',encoding='utf-8')
schematic=kicad_sch.read(file)
have={(p.ref,p.number):p.net.removeprefix('/') for p in schematic.pins}
for number,net in teensy_nets.items():assert have[('U3',number)]==net,(number,have[('U3',number)],net)
assert have[('J1','1')]=='+5V' and have[('J1','2')]=='GND'
for cap in ('C2','C6'):
    assert have[(cap,'1')]==('VBIAS' if cap=='C2' else '+5V') and have[(cap,'2')]=='GND'
print('Complete schematic created; Teensy, OLED and polarized capacitor mappings checked.')
