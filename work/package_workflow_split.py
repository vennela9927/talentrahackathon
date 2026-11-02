"""Package the completed offline project with a fresh file manifest."""
import base64,hashlib,json,re,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/talentra_step22_mini_seed_v7';WORK=ROOT/'work/workflow_split_v7'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 html=(OUT/'index.html').read_text(encoding='utf-8');match=re.search(r'<script type="application/json" id="dataset">(.*?)</script>',html,re.S);d=json.loads(match.group(1));checked=0
 for rel,value in d['downloads'].items():
  fp=OUT/rel;assert fp.is_file(),rel;assert hashlib.sha256(base64.b64decode(value)).hexdigest()==sha(fp),rel;checked+=1
 facts=json.loads((OUT/'catalogue/mini_seed_project.json').read_text(encoding='utf-8'));assert len(facts['actors'])==27 and len(facts['steps'])==168 and len(facts['sets'])==54 and len(facts['family_sets'])==12
 ui={'date':'2026-11-01','scope':'Mini and seed dashboard; portable datasets and offline artifacts','actors':27,'workflow_steps':168,'groups':8,'versions':['mini','seed'],'workflow_sets':54,'family_sets':12,'default_step_rows':168,'guest_participation_filter':True,'seed_gig_workflow_rows':6,'seed_gig_case_count':60,'new_step22_output_sections':10,'step22_filtered_records':168,'hierarchy_levels':[1,2,3,4],'download_clicked':'Updated output Excel','download_mechanism':'Browser download verified before final membership metadata update. All final embedded payloads compared byte-for-byte with saved files.','embedded_downloads_verified':checked,'saved_workbook_checks':'mini_seed_saved_artifacts.json','native_database_or_load_proof':False,'result':'PASS'}
 (OUT/'evidence/mini_seed_ui_validation.json').write_text(json.dumps(ui,indent=2),encoding='utf-8')
 readme=OUT/'README.md';text=readme.read_text(encoding='utf-8')
 text+='''\n## Open and explain\n1. Open index.html in Chrome or Edge. Choose Mini and seed.\n2. Select Mini or Seed, then a workflow group, workflow or actor.\n3. Use the Actor catalogue, Workflow steps, Business rules and Business analytics shortcuts.\n4. In Step outputs, select Step 22 and a Mini Seed section to inspect the same records. In Schemas, select Step 22 and L1–L4.\n\nThe Step 22 Output workbook adds tabs 27–36. The schema workbook adds Mini Seed Definition and Mini Seed Hierarchy. The scorecard adds Mini Seed Evidence. Historical inventory paths scenario_data/*.csv.gz correspond to seed/core/*.csv.gz in this release. The release keeps the complete folder structure for data links.\n\nKluster tools were unavailable in this session. The recorded checks cover source preservation, contracts, data relationships, portable rules, reproducibility, saved workbooks and browser behavior. No Kluster review, native database execution or production load pass is claimed.\n'''
 readme.write_text(text,encoding='utf-8')
 files=[p for p in OUT.rglob('*') if p.is_file() and not p.name.endswith('.inspect.ndjson') and '__pycache__' not in p.parts and p.name!='manifest.json']
 manifest={'version':'7.0 mini and seed','date':'2026-11-01','scope':'Offline Step 22 addendum with retained lifecycle artifacts','actors':27,'workflow_steps':168,'seed_journeys':1500000,'mini_journeys':120,'workflow_sets':54,'family_sets':12,'files':[{'path':str(p.relative_to(OUT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');files.append(OUT/'manifest.json')
 archive=ROOT/'outputs/Talentra_Step22_Mini_Seed_v7.zip'
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=4) as z:
  for p in files:z.write(p,str(Path(OUT.name)/p.relative_to(OUT)))
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None;names=z.namelist();assert sum(n.endswith('.xlsx') for n in names)==68;assert sum('/core/' in n and n.endswith('.csv.gz') for n in names)==10
 print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'files':len(files),'embedded_downloads':checked,'xlsx_files':68,'result':'PASS'},indent=2))
if __name__=='__main__':main()
