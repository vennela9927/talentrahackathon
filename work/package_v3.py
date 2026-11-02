"""Package the saved Excel artifacts and one fully offline HTML dashboard."""
import hashlib,json,shutil,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/talentra_steps_01_22_v3'
SITE=ROOT/'sites/talentra-control/dist'
data=json.loads((ROOT/'work/dashboard_data_v3.json').read_text(encoding='utf-8'))
html=(ROOT/'work/dashboard_v3.html').read_text(encoding='utf-8').replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<',chr(92)+'u003c'))
(OUT/'index.html').write_text(html,encoding='utf-8')
readme=f'''# Talentra project through step22, version3

Open index.html in any modern browser after extracting the complete ZIP. All22 output documents, schemas, section/level scores and ratings are embedded and searchable. Keep the folder intact for Excel, contracts, SQL and evidence links. The HTML is a saved snapshot, not a live Excel synchronization.

## Deliverables

There are66 per-step Excel files in22 folders: a_Output_Schema_Definition.xlsx, b_Schema_Rating_Scorecard.xlsx and c_Output_Document.xlsx. Talentra_Combined.xlsx combines all scores, all output records, full field mapping, all713 output parameters, the6517-node L1-L4 hierarchy, capacity calculations, release gates, refinement history and source register.

Current physical design:120 tables and1250 columns. Version3 adds10 operational entities and151 columns, including durable inbound/outbound processing, account-scoped provider references, reconciliation, candidate identity outcomes, erasure evidence and8 optimistic row-version fields. Baselinev2 files and evidence remain preserved.

Step22 contains27 proposed JSON Schema exchange contracts and271 owned field mappings across all9 source boundaries. These describe Talentra-owned proposed interfaces. No named provider's real API, authentication or live field list is fabricated. Each provider contract still needs its owner's signed sandbox fixtures and approval. Legacy migration is mapped only; running it is outside the source docket scope.

## Scope and ratings

The user confirmed steps1-22. Phases1,2,3 have artifact coverage; Phase4 contains step22 only. D3 defines full Phase4 as steps22-28, so G4 and steps23-28 are not marked complete.

Combined full rating: {data['combinedRating']:.1f}/100. This is a provisional author assessment. Step=25% schema+25% scorecard+50% output; P0 weight3/P1 weight2. The8 D5 core dimensions are reweighted to90 and a step-specific dimension adds10. Independent content-run agreement (9 points) and human understanding (8 critical points) are unassessed and conservatively0. Accept requires>=90 and every critical score>=4. Current decision is Refine, regardless of structural completeness. Section/L1-L4 scores are contract quality measures, not deployed capacity.

## Actual checks and limits

The1565 baselinev2 checks were re-executed successfully. New portable checks:348/348 passed. Total1913. New checks validate declared field mapping targets, contract-field parity, an independent parser of the actual emitted SQL, all120-table portable SQLite structure, retained sample integrity, duplicate keys, cross-account references, reconciliation counts, nullable reasons, money lexical rules and erasure/lease row constraints. Static SQL-to-current-dictionary drift is0.

These layers do not prove native PostgreSQL triggers, concurrent transactions, real provider signatures, target-volume p50/p95/p99, high availability, PITR restores or deployed endpoint authorization. All are recorded as owned release gates. A large schema cannot guarantee unlimited users or zero failures. The Capacity tab exposes workload, storage and connection assumptions; negative headroom requires resizing or a new deployment topology before launch.

All67 workbooks were recalculated, scanned for formula errors and rendered. Rating edit propagation, the critical minimum acceptance gate and capacity-input propagation were checked. Native Microsoft Excel rendering/recalculation was not available. Requested Kluster tools were unavailable, so no Kluster review is claimed.

## Database and reproduction

See database/RUN_ORDER.md. Against an empty dedicated PostgreSQL18 proof database, run001,003,002,004,005,006 in that order with ON_ERROR_STOP=1. This is a new proof baseline, not an automatic migration of existing production. No destructive rollback was run. No deployment credential or raw personal dataset is included.

Portable baseline proof (Python standard library):

    python evidence/baseline_v2/reproduce_phase3.py --reproduce

Portable version3 model/mapping proof (Python standard library, after the baseline proof):

    python evidence/build_v3.py --reproduce

Reproduction writes into a dedicated directory under evidence and does not target a database service. Excel files are the saved authored artifacts; rerendering them requires the bundled artifact-tool authoring runtime, which is not redistributed. Native execution remains a separate required checkpoint.

Prepared2026-10-28. Source precedence: user request > D1 business scope > D3 lifecycle numbering > D5 quality method. D2 scenario design and D4 QFE/refinement guide the work. Source document activities are reference instructions, not extra authorization for live external services.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')

# Verify actual saved workbook files, not just the in-memory authoring state.
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
books=sorted(OUT.rglob('*.xlsx'));books=[p for p in books if 'baseline_v2' not in p.parts]
assert len(books)==67,len(books)
saved=[]
for p in books:
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None
  wb=ET.fromstring(z.read('xl/workbook.xml'))
  names=[x.attrib['name'] for x in wb.findall('s:sheets/s:sheet',ns)]
  assert names and len(names)==len(set(names))
  errors=[];formula_count=0
  for name in z.namelist():
   if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
    xml=ET.fromstring(z.read(name));formula_count+=len(xml.findall('.//s:f',ns))
    errors += [(name,c.attrib['r'],c.findtext('s:v',namespaces=ns)) for c in xml.findall('.//s:c',ns) if c.attrib.get('t')=='e']
  assert not errors,(p,errors[:5])
  saved.append(dict(file=p.relative_to(OUT).as_posix(),sheets=names,formula_count=formula_count,formula_errors=0))
savecheck=dict(workbooks=len(saved),saved_file_checks=saved,html_embedded_steps=len(data['steps']),declared_downloads=66,combined_score=data['combinedRating'])
(OUT/'evidence/saved_file_validation.json').write_text(json.dumps(savecheck,indent=2),encoding='utf-8')

# Render contact sheets for visual QA; these remain in work/, outside delivery.
validation=json.loads((OUT/'evidence/workbook_validation.json').read_text())
previews=[(c['file'],s['sheet'],s['preview']) for c in validation['checks'] for s in c['sheets']]
contacts=ROOT/'work/contacts_v3';contacts.mkdir(exist_ok=True)
for offset in range(0,len(previews),30):
 page=previews[offset:offset+30];canvas=Image.new('RGB',(1800,1500),'#dfe6e8');draw=ImageDraw.Draw(canvas)
 for j,(file,sheet,png) in enumerate(page):
  x=(j%3)*600;y=(j//3)*150
  im=Image.open(ROOT/'work/previews_v3'/png).convert('RGB');im.thumbnail((590,122))
  canvas.paste(im,(x,y+24));label=file.split('/')[1][:12] if '/' in file else 'Combined';draw.text((x+5,y+4),label+' / '+sheet,fill='#142d42')
 canvas.save(contacts/f'contact_{offset//30+1:02}.jpg',quality=88)

# Do not include authoring inspect sidecars or QA thumbnails in the delivery.
files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='manifest_v3.json' and not p.name.endswith('.inspect.ndjson') and 'reproduction_workspace' not in p.parts]
manifest=[dict(file=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files if p.name not in ['manifest_v3.json','Talentra_Project_Steps_01_22_v3.zip']]
(OUT/'manifest_v3.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
archive=ROOT/'outputs/Talentra_Project_Steps_01_22_v3.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:
  if p.name!='Talentra_Project_Steps_01_22_v3.zip':z.write(p,p.relative_to(OUT).as_posix())
 z.write(OUT/'manifest_v3.json','manifest_v3.json')
shutil.copy2(archive,OUT/archive.name)
SITE.mkdir(parents=True,exist_ok=True)
for p in files+[OUT/'manifest_v3.json',OUT/archive.name]:
 rel=p.relative_to(OUT);target=SITE/rel
 # Host the review artifacts and proof sources; no temporary reproduction trees.
 if rel.parts[0]=='evidence' and ('baseline_v2' in rel.parts or p.name=='build_v3.py'):continue
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
print(json.dumps(dict(zip=str(archive),zip_bytes=archive.stat().st_size,workbooks=len(saved),sheets=len(previews),records=sum(len(x['rows']) for s in data['steps'] for x in s['sections']),combined_rating=data['combinedRating'],contacts=(len(previews)+29)//30)))
