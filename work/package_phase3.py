"""Package the updated through-step21 workbooks, proof source and one offline HTML."""
import hashlib,json,re,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'outputs'/'talentra_steps_01_16';OUT=ROOT/'outputs'/'talentra_steps_01_21'
data=json.loads((ROOT/'work'/'dashboard_data_phase3.json').read_text(encoding='utf-8'))
template=(ROOT/'work'/'dashboard.html').read_text(encoding='utf-8')
replacements={
 'through step 16':'through step 21','steps 01–16':'steps 01–21',
 'across 16 steps and 48 deliverables':'across 21 steps and 63 deliverables',
 '<strong>48</strong>':'<strong>63</strong>',
 'Sixteen steps. One review.':'Twenty-one steps. One review.',
 'All 16 steps':'All 21 steps','Prove · 4':'Prove · 9',
 '>16 steps</div>':'>21 steps</div>',
 'all sixteen steps':'all twenty-one steps',
 'Prove (through step 16)':'Prove (steps 13–21)',
 'evidence/test_results.json':'evidence/suite_v2_results.json',
 '48 deliverable scores':'63 deliverable scores',
 'Talentra · version 1.0':'Talentra · version 2.0',
 "(phase===3?' · partial phase':'')":"(phase===3?' · artifacts through step 21; G3 open':'')",
 "P.summary.contract_passed+P.summary.database_passed":"P.summary.v2_passed",
 "P.summary.contract_tests+P.summary.database_tests":"P.summary.v2_executed",
 "'187 contract checks and 15 SQLite database checks.'":"'V1 regression, v2 business contracts, all state-edge combinations, full portable schema and dictionary checks.'",
 'Python contract tests and a portable SQLite constraint subset were executed. PostgreSQL DDL, concurrent transaction races, target-volume latency and endpoint authorization have not been executed. Logical workflow coverage is a design measure.':'V1 regression and the full portable SQLite structural baseline were executed. Static PostgreSQL DDL/dictionary drift is zero. Native PostgreSQL, concurrent transaction races, target-volume latency and endpoint authorization remain pending. The G3 proof gate stays open.',
 "const first":"const first",
}
for old,new in replacements.items():template=template.replace(old,new)
template=re.sub(r'<div class="note"><strong>Scope and scoring:</strong>.*?</div>', '<div class="note"><strong>Phase 3 through step 21:</strong> design refinement, rules v2, dictionary v2, test suite v2 and the baseline ER/physical model are included. G3 remains open for native PostgreSQL execution, required NFR evidence and independent human review. Unassessed review dimensions conservatively score zero.</div>',template,count=1,flags=re.S)
template=template.replace("<button data-panel=\"sources\">Sources</button>","<button data-panel=\"model\">ER & physical baseline</button><button data-panel=\"sources\">Sources</button>")
core=(OUT/'diagrams'/'er_core.svg').read_text(encoding='utf-8')
overview=(OUT/'diagrams'/'er_overview.svg').read_text(encoding='utf-8')
model_panel='''<section class="panel" id="model"><div class="section-head"><div><h2>Baseline ER and physical model</h2><p class="muted">Version2.0. Logical cardinalities and physical objects are traceable to the refined catalogue. Native-engine execution is a separate checkpoint.</p></div><div class="links"><a class="button" href="database/001_baseline.sql" download>Schema SQL</a><a class="button" href="database/002_controls.sql" download>Controls SQL</a><a class="button" href="database/RUN_ORDER.md" download>Run order</a><a class="button" href="diagrams/er_model.mmd" download>Detailed ER source</a></div></div><div class="note">G3 is OPEN. The delivered native SQL has not been executed against PostgreSQL18 in this session. The portable schema, synthetic sample and static dictionary comparison have passed their stated checks.</div><div class="card" style="padding:0;overflow:auto">'''+core+'''</div><h3 style="margin:28px 0 12px">Module catalogue</h3><div class="card" style="padding:0;overflow:auto">'''+overview+'''</div></section>'''
template=template.replace('<section class="panel" id="sources">',model_panel+'<section class="panel" id="sources">')
template=template.replace('</style>','svg{display:block;max-width:100%;height:auto}\n</style>',1)
template=template.replace("'NULL — permitted by contract'","'NULL — permitted by contract'")
template=template.replace('The user\'s step cutoff and requested formats control this delivery.','The requested scope now covers phases1–3 through step21.')
template=template.replace('__PROJECT_DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c'))
(OUT/'index.html').write_bytes(template.encode('utf-8'))

# Keep the v1 evidence referenced by the preserved earlier sample/test records.
for name in ['catalogue.json','sample_data.json','test_results.json','invalid_fixtures.json','generate_and_test.py']:
 shutil.copyfile(OLD/'evidence'/name,OUT/'evidence'/name)
inputs=OUT/'evidence'/'v1_inputs';(inputs/'evidence').mkdir(parents=True,exist_ok=True)
shutil.copyfile(ROOT/'work'/'project_data.json',inputs/'project_data.json')
for name in ['catalogue.json','sample_data.json','test_results.json','generate_and_test.py']:
 shutil.copyfile(OLD/'evidence'/name,inputs/'evidence'/name)
shutil.copyfile(ROOT/'work'/'phase3.py',OUT/'evidence'/'reproduce_phase3.py')
shutil.copyfile(ROOT/'work'/'physical_controls.py',OUT/'evidence'/'physical_controls.py')

files=[]
for f in sorted((OUT/'database').iterdir()):
 if f.is_file():files.append(dict(file=f.relative_to(OUT).as_posix(),sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
manifest=dict(version='2.0',as_of=data['date'],project_rating=data['combinedRating'],phase3_rating=data['phase3Rating'],steps=21,step_deliverables=63,workbooks=64,phase3_steps=list(range(13,22)),new_steps=list(range(17,22)),summary=data['summary'],database_files=files,gate_g3=data['phase3_gate'])
(OUT/'evidence'/'manifest_v2.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
readme=f'''# Talentra through step21

Open `index.html` after extracting the complete ZIP. The single HTML contains the concatenated outputs, scoring data, L1-L4 schemas and embedded ER diagrams. Keep the folder intact for Excel, SQL and evidence links.

## Deliverables

- `steps/`:21 folders with three Excel files each (63 deliverables). The new steps17-21 add15 deliverables.
- `Talentra_Combined.xlsx`: all step/deliverable scores, Phase3 score, all schemas, section/level ratings, field mapping and concatenated output records.
- `database/`: PostgreSQL18 schema, controls, seed, native verification, metadata comparison and an explicitly manual rollback file.
- `diagrams/`: module overview, core ER SVG and detailed field-level Mermaid ER source.
- `evidence/`: v1 regression inputs, sample v2, dictionary/catalogue v2, suite v2 results, drift evidence and reproducible builders.

## Scope and source precedence

Uses the detailed lifecycle playbook's numbering: Discover1-5, Model6-12 and Prove13-21. All five PDFs inform this version. The hackathon docket's separate milestone/backlog numbering is not substituted. The previous through-step16 package remains unchanged in its original folder.

Step17 records concrete model refinements and deferrals. Step18 gives every rule an owner, enforcement point and positive/negative cases. Step19 includes dictionary v2, classification/retention and independent drift evidence. Step20 distinguishes executed sample tests from pending NFR/integration tests. Step21 publishes the baseline ER and physical source with a G3 checklist.

## Ratings

Project: {data['combinedRating']:.1f}/100. Phase3: {data['phase3Rating']:.1f}/100. Provisional author assessments, not mentor approvals.

Eight core scorecard dimensions total90 after reweighting; step-specific coverage is10. Unassessed independent-run consistency and human understanding contribute zero. Human understanding is critical, so no accepted gate is inferred from an average. Each step uses25% schema,25% scorecard and50% output. Project/phase totals use P0 weight3 and P1 weight2. Method and evidence are in the workbooks and HTML.

## Executed evidence and limits

{data['summary']['v2_passed']}/{data['summary']['v2_executed']} v2 checks passed at the labelled Python/SQLite/static-source layers. These include a re-executed v1 regression, all known-state transition combinations, full portable-schema sample load and column metadata checks. {data['summary']['sample_rows']} synthetic rows loaded with zero orphaned references. Static PostgreSQL DDL-to-dictionary differences:0.

Native PostgreSQL was unavailable: Docker is installed, but both local engine endpoints were unavailable and startup did not expose an engine. Native DDL/controls execution and concurrent-transaction proof remain pending. Thirteen NFR/integration measurements remain pending their stated environment/targets. G3 stays OPEN. No PostgreSQL or full-scale pass is fabricated.

Schema source uses bigint surrogate ids. Transition actor_role_code is an explicitly documented natural-key FK exception to a unique role code. Partitioning is a measured future cutover decision so baseline id-only FK contracts remain intact. Runtime identity is set by trusted middleware; end users receive no DB credentials. Full purpose-gated APIs are later lifecycle work.

## Reproduce the model and portable proof

Requires Python3 standard library only:

    python evidence/reproduce_phase3.py --reproduce

Writes rebuilt evidence, SQL and diagrams under `evidence/reproduced/`. Original inputs are not changed. Compare `sample_data_v2.json` SHA256 to `manifest_v2.json`. This command re-runs portable proof and never starts a database or executes the destructive rollback file.

## Native checkpoint

See `database/RUN_ORDER.md`. Required order is001 baseline,003 seed,002 controls,004 verification, all with `psql -v ON_ERROR_STOP=1` against an empty dedicated PostgreSQL18 proof database. Capture native metadata CSV and run `database/check_dictionary.py` against `evidence/dictionary_v2.json`. The schema/controls are not an automatic migration of an existing production database.

Kluster tools were unavailable. No kluster review is claimed. Proposed growth, latency, recovery and retention values still require their named owners' confirmation.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
archive=ROOT/'outputs'/'Talentra_Phases_1_3_Through_Step_21.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for f in OUT.rglob('*'):
  if f.is_file() and not f.name.endswith('.inspect.ndjson') and '__pycache__' not in f.parts and 'reproduced' not in f.parts:
   z.write(f,f.relative_to(OUT))
print(json.dumps(dict(archive=str(archive),bytes=archive.stat().st_size,project_rating=data['combinedRating'],phase3_rating=data['phase3Rating'],records=sum(len(sec['rows']) for s in data['steps'] for sec in s['sections'])),indent=2))
