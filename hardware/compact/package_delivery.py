"""Package only the checked final revision; never collect intermediate exports."""
from pathlib import Path
import hashlib,json,shutil,zipfile
root=Path(__file__).resolve().parent
project_root=root.parents[1]
research=project_root/'docs/hardware'
output=project_root/'outputs/MouseLatencyTester-A1'
delivery=output/'Delivery-A1'
portable=delivery/'KiCad'
def copy(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    if source.resolve()==target.resolve():
        return
    shutil.copy2(source,target)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name in ('mouse_latency_tester.kicad_pro','mouse_latency_tester.kicad_pcb','mouse_latency_tester.kicad_sch','mlt.kicad_sym','fp-lib-table','sym-lib-table'):
    copy(portable/name,delivery/'KiCad'/name)
for p in (portable/'mlt.pretty').glob('*.kicad_mod'):
    copy(p,delivery/'KiCad/mlt.pretty'/p.name)
for p in (root/'fab').iterdir():
    assert p.suffix in ('.gtl','.gbl','.gts','.gbs','.gto','.gbo','.gm1','.gbrjob','.drl'),p
    copy(p,delivery/'PCBWay'/p.name)
assert len(list((delivery/'PCBWay').iterdir()))==10
for p in (root/'documentation').iterdir():
    if p.name=='README.md':copy(p,delivery/p.name)
    else:copy(p,delivery/'Documentation'/p.name)
for name in ('LICENSE-teensy-symbols','LICENSE-teensy-footprint'):
    copy(root.parent/'sources'/name,delivery/'Documentation'/name)
for name in ('final-erc.json','final-drc.json','independent-checks.json','fabrication-files.json','drill-report.txt','kicad9-export.json','portable-comparison.json','kicad9-native-erc.json','kicad9-native-drc.json','kicad9-native-summary.json'):
    copy(root/'checks'/name,delivery/'Checks'/name)
# Reports for the portable project are stored beside the other delivery checks.
for name in ('portable-drc.json','portable-erc.json'):
    assert (delivery/'Checks'/name).is_file(),name
for name in ('verify_final.py','audit_fabrication.py','compare_portable.py','normalize_junction_wires.py'):
    copy(root/name,delivery/'Checks/script'/name)
for name in ('gerber-top.png','gerber-bottom.png','assembly-top.png','board-top.png','preview-complete.png'):
    copy(root/name,delivery/'Previews'/name)
for p in (root/'mechanical').glob('*.dxf'):copy(p,delivery/'Mechanical'/p.name)
for name in ('recommendation.md','purchased-components.md','optical-datasheet-audit.md','open-ldat-comparison.md'):
    copy(research/name,delivery/'Research'/name)
manifest=''.join(f'{digest(p)}  {p.relative_to(delivery).as_posix()}\n' for p in sorted(delivery.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.txt')
(delivery/'SHA256SUMS.txt').write_text(manifest,encoding='utf-8',newline='\n')
def zip_folder(source,destination,prefix=''):
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(source.rglob('*')):
            if p.is_file():z.write(p,prefix+p.relative_to(source).as_posix())
    with zipfile.ZipFile(destination) as z:assert z.testzip() is None
bare=output/'MouseLatencyTester-A1-PCBWay.zip'
project=output/'MouseLatencyTester-A1-Project.zip'
zip_folder(delivery/'PCBWay',bare)
zip_folder(delivery,project,'MouseLatencyTester-A1/')
(output/'SHA256SUMS.txt').write_text(''.join(f'{digest(p)}  {p.name}\n' for p in (bare,project)),encoding='utf-8',newline='\n')
print(json.dumps({'delivery':str(delivery),'project_zip':str(project),'pcbway_zip':str(bare),'project_bytes':project.stat().st_size,'fab_bytes':bare.stat().st_size,'packaged_files':len(manifest.splitlines()),'zip_integrity':'PASS'},indent=2))
