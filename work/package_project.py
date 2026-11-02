"""Assemble the self-contained HTML and reproducible proof package."""
import json, shutil, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'/'talentra_steps_01_16'
data=json.loads((ROOT/'work'/'dashboard_data.json').read_text(encoding='utf-8'))
template=(ROOT/'work'/'dashboard.html').read_text(encoding='utf-8')
html=template.replace('__PROJECT_DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c'))
(OUT/'index.html').write_text(html,encoding='utf-8')
reproduce=(ROOT/'work'/'project.py').read_text(encoding='utf-8')
reproduce=reproduce.replace("ROOT = Path(__file__).resolve().parents[1]", "ROOT = Path(__file__).resolve().parent / 'reproduced'\n(ROOT / 'work').mkdir(parents=True, exist_ok=True)")
reproduce=reproduce.replace("OUT = ROOT / 'outputs' / 'talentra_steps_01_16'",'OUT = ROOT')
(OUT/'evidence'/'generate_and_test.py').write_text(reproduce,encoding='utf-8')
(OUT/'README.md').write_text('''# Talentra project package

Open `index.html` in a browser. The HTML contains all project records and works offline. Keep the folder intact so its Excel and evidence links work.

## Deliverables

- `Talentra_Combined.xlsx`: combined score, all ratings, output schemas, section/level ratings and concatenated populated outputs. `Field Mapping` names the generic fields in `All Outputs`.
- `steps/`: sixteen step folders, each with `a_Output_Schema_Definition.xlsx`, `b_Schema_Rating_Scorecard.xlsx` and `c_Output_Document.xlsx` (48 files).
- `evidence/`: full synthetic sample, invalid fixtures, catalogue, test results and a reproducible generator/test runner.

## Scope

Uses the detailed lifecycle playbook's step numbering. Discover 1-5 and Model 6-12 are prepared; Prove 13-16 is prepared through the requested cutoff. Phase 3 continues to step 21, so G3 is not reached. The hackathon docket's separate milestones/backlogs are not substituted for lifecycle steps.

## Rating

The full project rating is a provisional author assessment. Independent-run consistency and human author understanding are unassessed and conservatively score zero. Human understanding is critical, so acceptance remains open. No peer/mentor approval is claimed. Per-step workbooks and the consolidated workbook have local formulas. HTML is a saved snapshot; it does not read later Excel edits.

Each step uses 25% schema, 25% scorecard and 50% output. P0 steps have project weight 3, P1 steps 2. Core scorecard weights are reweighted to 90 and step-specific coverage is 10. Source rubric, formulas and evidence are recorded in the scorecards and the combined workbook.

## Reproduce sample checks

Requires Python 3 standard library only:

    python evidence/generate_and_test.py

Writes regenerated JSON/sample/test evidence under `evidence/reproduced/`. Seed is 20261027. All names and records are synthetic. Compare the sample SHA256 in the manifest. Contract checks and a SQLite database subset execute; these do not certify PostgreSQL DDL, RLS, concurrency, endpoint enforcement or target-volume performance.

## Source use

All five user-provided PDFs are cited by source ID and page in the workbooks. Competitor evidence uses official Naukri, Monster/foundit and LinkedIn pages. Unknown coverage is explicitly marked; no unsupported claim of competitor absence is made. Proposed latency, recovery, growth and retention values are assumptions requiring owner confirmation. The supplied docket references KPI/NFR sections that are not present in its pages.

Kluster review tools were not available in the authoring session. No kluster review is claimed.
''',encoding='utf-8')
(OUT/'evidence'/'manifest.json').write_text(json.dumps({'as_of':data['date'],'combined_rating':data['combinedRating'],'summary':data['summary'],'xlsx_files':49,'step_deliverables':48,'html_records':sum(len(s['rows']) for step in data['steps'] for s in step['sections']),'limitations':['Independent content review and human understanding unassessed','PostgreSQL execution and concurrency not performed','Target-volume NFR benchmarks not performed','G3 is outside step16 cap','Kluster unavailable']},indent=2),encoding='utf-8')
# Package excludes authoring diagnostics and previews.
archive=ROOT/'outputs'/'Talentra_Project.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for f in OUT.rglob('*'):
  if f.is_file() and not f.name.endswith('.inspect.ndjson'):
   z.write(f,f.relative_to(OUT))
print(json.dumps({'html':str(OUT/'index.html'),'archive':str(archive),'archive_bytes':archive.stat().st_size,'combined_rating':data['combinedRating']},indent=2))
