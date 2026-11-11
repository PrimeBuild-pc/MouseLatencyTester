"""Review A1b: TIA gain, BPV10 hole, hand-assembly legends. Safe to run twice.

Text edits of the native files; no geometry is regenerated. Refill + DRC after.
"""
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
import re

root = Path(__file__).resolve().parent
pcb = root / 'mouse_latency_tester.kicad_pcb'
sch = root / 'mouse_latency_tester.kicad_sch'
led = root / 'mlt.pretty/LED_D5.0mm.kicad_mod'
REV, DATE = 'Prototype A1b / BPV10', '2026-11-11'


def block(text, ref):
    """Span of the footprint/symbol record holding (property "Reference" "<ref>")."""
    at = text.index(f'(property "Reference" "{ref}"')
    start = max(text.rfind('\n\t(footprint ', 0, at), text.rfind('\n\t(symbol', 0, at))
    end = min(i for i in (text.find('\n\t(footprint ', at), text.find('\n\t(symbol', at), len(text)) if i > 0)
    return start, end


def in_block(text, ref, old, new, count):
    start, end = block(text, ref)
    body = text[start:end]
    assert body.count(old) == count or (body.count(old) == 0 and new in body), (ref, old, body.count(old))
    return text[:start] + body.replace(old, new) + text[end:]


# R3: 10k gives ~10 mV on a display (below the comparator hysteresis); 1M gives ~1 V/uA.
b = pcb.read_text(encoding='utf-8')
b = in_block(b, 'R3', '(property "Value" "10k 1%"', '(property "Value" "1M 1%"', 1)
# BPV10 leads are 0.63 x 0.5 mm (diagonal 0.80, up to 1.05 at tolerance): 0.9 mm is too tight.
b = in_block(b, 'D1', '(drill 0.9)', '(drill 1)', 2)


def legend(text, x, y, layer='F.SilkS', size=.8, justify=''):
    uid = uuid5(NAMESPACE_URL, f'primebuild:mlt-a1b-legend:{layer}:{x}:{y}')
    mirror = ' mirror' if layer.startswith('B.') else ''
    just = f'\n\t\t\t(justify{" " + justify if justify else ""}{mirror})' if justify or mirror else ''
    return (f'\t(gr_text "{text}"\n\t\t(at {x} {y} 0)\n\t\t(layer "{layer}")\n\t\t(uuid "{uid}")\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {size} {size})\n\t\t\t\t(thickness 0.15)\n\t\t\t){just}\n\t\t)\n\t)\n')


legends = ''.join((
    legend('5V', 34, 2), legend('GND', 36.54, 2), legend('SCL', 39.08, 2), legend('SDA', 41.62, 2),
    legend('PROBE', 49.7, 42.5, justify='left'),
    legend('VBIAS', 9, 43.8), legend('TIA', 25, 44.4),
    legend('CMP', 30.4, 46, justify='right'), legend('GND', 22.1, 46, justify='left'),
    legend('MLT A1b 2026-11', 43.5, 9.5, size=1),
    legend('K', 15.9, 39.6, 'B.SilkS', 1), legend('LATO MONITOR', 20.5, 16.5, 'B.SilkS', 1.2),
))
if 'mlt-a1b' not in b and 'LATO MONITOR' not in b:
    tail = '\t(embedded_fonts no)\n)'
    assert b.rstrip().endswith(tail)
    b = b.rstrip()[:-len(tail)] + legends + tail + '\n'
pcb.write_text(b, encoding='utf-8')

s = sch.read_text(encoding='utf-8')
s = in_block(s, 'R3', '(property "Value" "10k 1%"', '(property "Value" "1M 1%"', 1)
s = re.sub(r'\(date "[^"]*"\)', f'(date "{DATE}")', s, count=1)
s = re.sub(r'\(rev "[^"]*"\)', f'(rev "{REV}")', s, count=1)
s = s.replace('PROTOTYPE A1: routed PCB supplied.', 'PROTOTYPE A1b: routed PCB supplied.')
s = s.replace('R/C values start from docs/optical_front_end.md. Gain and stability require measurement.',
              'R3 1M / C3 15pF: about 1 V per uA, 10.6 kHz. Display white on BPV10 is about 0.5-2 uA: 10k gave only mV. Verify on bench.')
sch.write_text(s, encoding='utf-8')

f = led.read_text(encoding='utf-8')
assert f.count('(drill 0.9)') == 2 or f.count('(drill 1)') == 2
led.write_text(f.replace('(drill 0.9)', '(drill 1)'), encoding='utf-8')
print('A1b edits applied')
