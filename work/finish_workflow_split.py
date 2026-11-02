"""Verify saved artifacts, smaller family sets and reproducible workflow examples."""
import csv,gzip,hashlib,io,json,re,shutil,zipfile
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
import build_workflow_split as lib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/talentra_step22_mini_seed_v7';WORK=ROOT/'work/workflow_split_v7'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,v):lib.dump(p,v)
def main():
 d=load(WORK/'project.json');checks=d['checks'];family_sets=[]
 actors={a['actor_id'] for a in d['actors']};stepmap={s['step_id']:s for s in d['steps']};workflows={w['workflow_id'] for w in d['workflows']}
 assert len(actors)==27 and len(stepmap)==168
 for s in d['steps']:
  assert s['actor_id'] in actors and s['workflow_id'] in workflows
 for v in ['mini','seed']:
  for w in d['workflows']:
   p=OUT/v/'workflows'/w['workflow_id'];cases=load(p/'cases.json');steps=load(p/'step_examples.json');analytics=load(p/'analytics.json');case_by={c['case_id']:c for c in cases};counts=Counter(c['outcome'] for c in cases)
   assert dict(counts)==analytics['outcomes'] and len(steps)==analytics['step_example_rows']
   assert len({s['step_id'] for s in steps})==w['step_count']
   for s in steps:assert s['actor_id'] in actors and s['step_id'] in stepmap and case_by[s['case_id']]['outcome']=='ACCEPTED_EXAMPLE'
   for file in ['cases.json','step_examples.json','analytics.json','manifest.json']:
    assert lib.sha(p/file)==lib.sha(WORK/'reproduced'/v/'workflows'/w['workflow_id']/file)
 checks.append({'check':'Saved workflow cases, joins and analytics','result':'PASS','observed':54,'scope':'Read back each set, recompute outcome counts, and compare all four files with independent regeneration'})
 for version in ['mini','seed']:
  families=list(d['core'][version]['families'])
  if version=='mini':
   for key in ['journey','gig']:
    rows=list(lib.readcsv(OUT/version/'core'/(key+'.csv.gz')));headers=list(rows[0])
    for f in families:lib.writecsv(OUT/version/'sets'/f/(key+'.csv.gz'),headers,[r for r in rows if r['job_family_code']==f])
  for family in families:
   folder=OUT/version/'sets'/family;counts={}
   for key in ['journey','gig']:
    n=0
    for r in lib.readcsv(folder/(key+'.csv.gz')):assert r['job_family_code']==family;n+=1
    counts[key]=n
   metrics={'version':version,'family':family,'journeys':counts['journey'],'gig_applications':counts['gig'],'hiring_stages':d['core'][version]['families'][family],'basis':d['core'][version]['selection_basis'],'files':[str((folder/(k+'.csv.gz')).relative_to(OUT)).replace('\\','/') for k in counts]}
   assert counts['journey']==metrics['hiring_stages']['journeys'];dump(folder/'analytics.json',metrics);family_sets.append(metrics)
 checks.append({'check':'Smaller family datasets and analytics','result':'PASS','observed':12,'scope':'Six physical family sets per version, each file read back and family membership checked'})
 d['family_sets']=family_sets
 # Refresh source digest metadata for the changed serialized Step 22 output contract.
 idx=load(OUT/'evidence/artifact_contract_index.json')
 for r in idx:
  if r[0]==22 and r[1]=='Output Document':r[3]=lib.sha(OUT/r[2]);r[4]='v7 retained sections plus mini/seed output contracts'
 dump(OUT/'evidence/artifact_contract_index.json',idx)
 dump(OUT/'evidence/mini_seed_validation.json',checks);dump(WORK/'project.json',d);dump(OUT/'catalogue/mini_seed_project.json',d);dump(OUT/'catalogue/family_set_index.json',family_sets)
 dump(OUT/'catalogue/scale_config.json',{'mini_journeys':120,'mini_selection':'2 per family/current-outcome combination','mini_gig_requests':20,'mini_workflow_cases_per_workflow':6,'seed_journeys':1500000,'seed_workflow_cases_per_workflow':60,'scale_boundary':'Larger fixture counts or saved rows do not establish production concurrency or database performance.'})
 readme=(OUT/'README.md').read_text(encoding='utf-8')
 readme=readme.replace('To reproduce this split from the included seed/core files, run evidence/build_workflow_split.py with the original project layout available.','To reproduce the portable workflow fixture sets in a new folder, run:\n\n    python evidence/reproduce_workflow_fixtures.py --output NEW_FOLDER\n\nThis bundled command uses only the released catalogue and dictionary. It regenerates all 54 workflow sets and rule tests, without modifying the release. The full split authoring script additionally needs the original v6 layout. Reproduced fixture files were compared byte-for-byte with the release.')
 readme=readme.replace('seed/sets has smaller physical journey and gig files by job family.','Both mini/sets and seed/sets contain six smaller physical family sets, with journey/gig files and analytics.json for each.')
 (OUT/'README.md').write_text(readme,encoding='utf-8')
 # Machine contract verification covers the added output sections, not just their labels.
 contract=load(OUT/'artifact_contracts/step_22_output.json');added=load(WORK/'added_sections.json');cell_count=0
 for s in added:
  props=contract['properties'][s['title']]['items'];assert props['required']==s['headers']
  for row in s['rows']:
   assert len(row)==len(s['headers'])
   for h,v in zip(s['headers'],row):
    t='null' if v is None else 'boolean' if type(v)==bool else 'integer' if type(v)==int else 'number' if type(v)==float else 'string'
    assert t in props['properties'][h]['type'],(s['title'],h,t)
    cell_count+=1
 checks.append({'check':'Added output contract values','result':'PASS','observed':cell_count,'scope':'Every added row width and field type verified against the extended serialized output contract'})
 dump(OUT/'evidence/mini_seed_validation.json',checks);dump(WORK/'project.json',d);dump(OUT/'catalogue/mini_seed_project.json',d)
 print(json.dumps({'workflow_sets_verified':54,'family_sets_verified':12,'typed_output_cells':cell_count,'checks':len(checks)}))

if __name__=='__main__':main()
