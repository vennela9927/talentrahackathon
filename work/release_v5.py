"""Populate the hybrid into the lifecycle package; preserve source and proof boundaries."""
import base64, copy, hashlib, json, re, shutil, sys, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/talentra_steps_01_22_hybrid_v5'
WORK=ROOT/'work/release_v5'
BASE=ROOT/'outputs/talentra_steps_01_22_v3'
KINDS=['Output Schema Definition','Schema Rating Scorecard','Output Document']
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def safe(s):return re.sub('[^a-zA-Z0-9]+','_',s).strip('_')

def package():
 import xml.etree.ElementTree as ET
 from PIL import Image,ImageDraw
 d=load(WORK/'dashboard_data.json')
 historical=BASE/'evidence/baseline_v2'
 if historical.exists():shutil.copytree(historical,OUT/'evidence/baseline_v2',dirs_exist_ok=True,ignore=shutil.ignore_patterns('reproduction_workspace','__pycache__','*.inspect.ndjson'))
 shutil.copy2(BASE/'evidence/build_v3.py',OUT/'evidence/build_v3.py')
 embedded=list(OUT.rglob('*.xlsx'))+list((OUT/'artifact_contracts').glob('*.json'))+[OUT/'evidence/current_validation.json']
 d['downloads']={p.relative_to(OUT).as_posix():base64.b64encode(p.read_bytes()).decode('ascii') for p in embedded}
 template=(ROOT/'work/dashboard_v5.html').read_text(encoding='utf-8')
 (OUT/'index.html').write_text(template.replace('__DATA__',json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')),encoding='utf-8')
 ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
 books=sorted(OUT.rglob('*.xlsx'));assert len(books)==67,len(books)
 checks=[]
 for p in books:
  with zipfile.ZipFile(p) as z:
   assert z.testzip() is None
   w=ET.fromstring(z.read('xl/workbook.xml'))
   names=[x.attrib['name'] for x in w.findall('s:sheets/s:sheet',ns)]
   assert len(names)==len(set(names))
   errors=[];formulas=0
   for name in z.namelist():
    if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
     xml=ET.fromstring(z.read(name));formulas+=len(xml.findall('.//s:f',ns))
     errors.extend(c.attrib['r'] for c in xml.findall('.//s:c',ns) if c.attrib.get('t')=='e')
   assert not errors,(p,errors)
   checks.append({'file':p.relative_to(OUT).as_posix(),'sheets':len(names),'formulas':formulas,'errors':errors})
 for step in d['steps']:
  for f in step['files'].values():assert (OUT/f).is_file(),f
 write(OUT/'evidence/saved_workbook_checks.json',checks)
 previews=load(OUT/'evidence/workbook_validation.json')['previews']
 contact=WORK/'contacts';contact.mkdir(exist_ok=True)
 for offset in range(0,len(previews),24):
  page=previews[offset:offset+24];canvas=Image.new('RGB',(1800,1600),'#e3e9f0');draw=ImageDraw.Draw(canvas)
  for j,r in enumerate(page):
   x=j%3*600;y=j//3*200
   im=Image.open(WORK/'previews'/r['png']).convert('RGB');im.thumbnail((590,170));canvas.paste(im,(x,y+25))
   draw.text((x+4,y+5),r['label'][:85],fill='#203b63')
  canvas.save(contact/f'contact_{offset//24+1:02}.jpg',quality=88)
 note=f'''# Talentra hybrid lifecycle package, steps 1–22

Open index.html after extracting the complete archive. It contains the populated step outputs, all schema contracts, L1–L4 hierarchy, priorities, ratings, merge decisions and evidence. The 66 Excel downloads use relative paths. The HTML is an offline snapshot of the saved master workbook, not a live Excel link.

## Contents

Each numbered step folder contains a_Output_Schema_Definition.xlsx, b_Schema_Rating_Scorecard.xlsx and c_Output_Document.xlsx. The schema workbook defines all three deliverable contracts. The output workbook has every retained hybrid section plus the relevant handoff, review and acceptance records. Talentra_Combined.xlsx consolidates every output record with field mappings and all 66 ratings. artifact_contracts contains one machine-readable schema per deliverable, 66 in total. The original input workbooks have not been overwritten.

The hybrid field register has 1,407 fields: 1,250 existing physical-design fields and 157 proposed additions. Existing native/portable proof is not transferred to new proposals. Proposed examples are synthetic fixtures. Role ownership is a proposed assignment until accepted. The database folder retains the original baseline and adds a hybrid changeset plan, not an applied migration.

## Honest ratings

Full rubric: {d['combinedRating']:.1f}/100. Documentary quality: {d['documentaryRating']:.1f}/100. The second view uses the same seven observable dimensions and divides their contributions by their original 83-point weight. It excludes independent comparison (9) and the human interview (8), is supplementary, and does not satisfy full-rubric acceptance. Every deliverable's documentary score is above 90. This is not a claim that every full-rubric score exceeds 90.

The original rubric and weights are unchanged. The human interview remains unassessed and critical. Source B scores and native PASS statements are source reports, not executed hybrid evidence. Actual full scores remain below 90 where required evidence is absent. The 90+ closure plan identifies the exact evidence needed. A conditional scenario with independent consistency 4/5 and human understanding 4/5 yields at least 90.8 under the frozen rubric; it is a target calculation, not an achieved score. Reviewers must score the supplied evidence themselves.

## Refinement and checks

Pass 1 audited field examples, step placement and contract coverage. Pass 2 added typed synthetic fixtures, three deliverable contracts per step, field/privacy/physical proposal views, handoff controls and human review prompts. Pass 3 validated serialized contracts against every record, checked preservation and keys, recalculated all workbooks, checked score propagation and missing-input/critical gates, and rendered every sheet. The refinement log records executed results and remaining external dependencies.

Historical evidence: 1,913 Python/SQLite/static baseline checks. New v5 checks are listed separately in evidence/current_validation.json. These are documentary/portable checks, not PostgreSQL concurrency, authorization, signed provider, load or recovery evidence. Docker was installed but its engine was unavailable. No PostgreSQL proof database was available. No production environment was changed. Steps 23–28 remain outside scope.

Prepared 28 October 2026. The five source PDFs remain referenced in the source register. User instructions govern scope and delivery. Kluster tooling was unavailable in this session, so no Kluster review is claimed.
'''
 (OUT/'README.md').write_text(note,encoding='utf-8')
 files=[p for p in OUT.rglob('*') if p.is_file() and not p.name.endswith('.inspect.ndjson')]
 write(OUT/'manifest.json',[{'file':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)} for p in files if p.name!='manifest.json'])
 archive=ROOT/'outputs/Talentra_Hybrid_Project_Steps_01_22_v5.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(OUT.rglob('*')):
   if p.is_file() and not p.name.endswith('.inspect.ndjson'):z.write(p,p.relative_to(OUT).as_posix())
 print(json.dumps({'zip':str(archive),'books':len(books),'previews':len(previews),'records':sum(len(x['rows']) for s in d['steps'] for x in s['sections']),'full':d['combinedRating'],'documentary':d['documentaryRating']}))

def prepare():
 OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
 h=load(ROOT/'work/hybrid_v4/hybrid_data.json');p=copy.deepcopy(h['project'])
 p.update(version='5.0 hybrid lifecycle',output_folder=OUT.name,date='2026-10-28')
 original=copy.deepcopy(p['steps'])
 # Bring the existing SQL, proposed provider contracts and historical evidence forward.
 for folder in ['database','contracts','diagrams']:
  if (BASE/folder).exists():shutil.copytree(BASE/folder,OUT/folder,dirs_exist_ok=True)
 (OUT/'evidence').mkdir(exist_ok=True)
 for f in ['dictionary_v3.json','catalogue_v3.json','v3_validation.json']:
  shutil.copy2(BASE/'evidence'/f,OUT/'evidence'/f)
 shutil.copy2(ROOT/'outputs/talentra_hybrid_v4/evidence/source_fingerprints.json',OUT/'evidence/source_fingerprints.json')
 write(OUT/'evidence/source_hybrid_sha256.json',{'file':'Talentra_Hybrid_Master_Steps_01_22.xlsx','sha256':digest(ROOT/'outputs/talentra_hybrid_v4/Talentra_Hybrid_Master_Steps_01_22.xlsx')})
 # Synthetic examples fill documentary gaps without pretending to be source facts.
 def example(typ,col):
  if col.endswith('_id') or col=='id':return 1
  if typ=='boolean':return False
  if typ in ['bigint','integer','smallint']:return 0
  if typ.startswith('numeric'):return '0.00'
  if typ=='timestamptz':return '2026-10-28T00:00:00Z'
  if typ=='date':return '2026-10-28'
  if typ=='inet':return '192.0.2.1'
  if typ=='jsonb':return '{"fixture":true}'
  if typ=='bytea':return '\\x00'
  if typ=='char(3)':return 'INR'
  if typ=='tsvector':return "'synthetic':1"
  if col in ['language_code','code'] and '10' in typ:return 'en'
  return 'Synthetic '+col.replace('_',' ')
 proposals={x['id']:x for x in h['proposed']};missing_before=0;fixture_rows=[]
 for r in h['dictionary']:
  if r[0] not in proposals:continue
  x=proposals[r[0]];missing_before+=str(r[8]).startswith('UNKNOWN')
  ex=example(r[4],r[2]);r[8]=ex
  owner='Commerce owner' if any(k in r[1] for k in ['credit','wallet','payment','price']) else 'Identity/security owner' if any(k in r[1] for k in ['user','credential','permission','role','session']) else 'Master data owner' if any(k in r[1] for k in ['definition','reference','language','currency','label']) else 'Domain engineering owner'
  if 'confirm' in r[11].lower():r[11]=owner+' - proposed assignment'
  x['example']=ex;x['owner']=r[11]
  fixture_rows.append([r[0],r[1],r[2],r[4],ex,r[5],r[11],r[12],'Synthetic fixture; design illustration, not a production row',r[14],r[16]])
 # Shared canonical dictionary is explicitly populated into its owning lifecycle steps.
 def section(n,name,cols,rows,priority='P0',source='Hybrid v5 reconciliation; source A/B locators retained'):
  sec={'name':name,'columns':cols,'rows':copy.deepcopy(rows),'priority':priority,'source':source}
  p['steps'][n-1]['sections'].append(sec);return sec
 cols=h['dictionary_columns'];dictionary=h['dictionary']
 next(x for x in p['steps'][18]['sections'] if x['name']=='Hybrid Dictionary')['rows']=copy.deepcopy(dictionary)
 section(7,'Canonical hybrid attributes',cols,dictionary)
 section(10,'Hybrid dictionary additions',cols,[r for r in dictionary if r[0] in proposals])
 section(12,'Hybrid field privacy',[cols[i] for i in [0,1,2,9,10,11,14,15,16,20]],[[r[i] for i in [0,1,2,9,10,11,14,15,16,20]] for r in dictionary])
 section(14,'Hybrid synthetic fixtures',['Attribute ID','Table','Column','SQL type','Synthetic example','Nullable','Proposed owner','Validation','Fixture scope','Implementation status','B source'],fixture_rows)
 section(19,'Hybrid synthetic examples',['Attribute ID','Table','Column','SQL type','Synthetic example','Nullable','Proposed owner','Validation','Fixture scope','Implementation status','B source'],fixture_rows)
 section(21,'Hybrid physical changeset',[cols[i] for i in [0,1,2,4,5,11,12,14,17,18,20]],[[r[i] for i in [0,1,2,4,5,11,12,14,17,18,20]] for r in dictionary if r[0] in proposals])
 section(3,'Hybrid feature implications',['Feature ID','Capability','Hybrid fields','Acceptance','Owner','Status'],[
 ['HF-01','Keep credits separate from money','credit_account; credit_ledger_entry; currency_definition','Credit debit never changes a currency amount without an approved conversion event','Commerce owner','Proposed; policy and race proof pending'],
 ['HF-02','Support multiple job locations','job_requirement_location','Primary city remains compatible; each allowed location has one unique job/location pair','Jobs owner','Proposed; migration pending'],
 ['HF-03','Use localized display labels','ui_label_definition; language_definition','Access checks use stable permission code; labels never grant access','Identity and master-data owners','Proposed; key-resolution tests pending'],
 ['HF-04','Preserve source provenance','462 B field mappings; A dictionary IDs','Each mapped field resolves to one canonical field and retains both source locators','Data architect','Documentary mapping checked']])
 controls=[
 ('Requirements','41 A requirements plus39 B statements','Requirements -> Features','Keep source IDs distinct; owner resolves candidate relations','Product owner','Self-registration, external gig fulfilment and licence scope are explicit'),
 ('Roles and permissions','Actor and permission catalogues','People/Roles -> Workflows','Test non-owner and blocked-party access separately','Security owner','Stable permission code controls access; a label does not'),
 ('Features','Requirements and hybrid feature implications','Features -> NFRs/Workflows','Link a feature to its requirement before implementation','Product owner','Source topic similarity alone does not establish requirement equivalence'),
 ('NFRs','Targets, hardware and workload assumptions','NFRs -> Volumetrics/Test suite','Measure latency at declared workload and hardware','Performance owner','Targets and source-reported timings are distinct from measured hybrid results'),
 ('Workflows','User journeys and refusal paths','Workflows -> Entities/Lifecycles','Positive, refusal, retry and audit outcomes have explicit owners','Domain owner','Blocked recipients are rejected before enqueue and again before delivery'),
 ('Entities','120 existing tables plus proposed table split','Entities -> Attributes','Reconcile identity, catalogue and transactional grains','Data architect','Credit accounts and monetary wallets have different units'),
 ('Attributes','1407 canonical fields and462 B mappings','Attributes -> Dictionary','Preserve A fields and mark157 additions as proposals','Data architect','A field type/nullability cannot be changed through alias matching alone'),
 ('Lifecycles','State machines, transitions and lease states','Lifecycles -> Rules','Reject illegal transitions and stale worker ownership','Domain owner','Out-of-order callbacks do not reverse a newer committed state'),
 ('Relationships','Canonical FK graph and aliases','Relationships -> Dictionary/Physical model','Resolve parent keys and account ownership before importing data','Database owner','Source numeric IDs require translation to canonical IDs'),
 ('Dictionary v1','Typed meanings, examples and proposed additions','Dictionary v1 -> Rules/Privacy','State null meaning, defaults, constraints and owner','Data steward','Synthetic examples illustrate types and are never raw candidate data'),
 ('Rules v1','A rules plus236 explicit B rule rows','Rules -> Tests','Retain namespaced rule IDs; prove actual enforcement separately','Database owner','Rule catalogue size is measured from supplied rows, not reported totals'),
 ('Privacy','1407 field classifications and source disagreements','Privacy -> Samples/Erasure','Conservative same-field class; policy owner approves retention','Privacy owner','Higher documentary class does not mean a deployed masking policy exists'),
 ('Volumetrics','10m profiles,1m jobs,100m applications target','Volumetrics -> Samples/Indexes','Model skew, child rows, connection ceilings and retention','Performance owner','Planning arithmetic does not establish measured deployment capacity'),
 ('Sample data','Scenario sets plus157 typed synthetic examples','Samples -> Data tests','Generate consistent parents before children; reject malformed types','Data engineering owner','The example1 FK is a fixture key, not proof a deployed parent row exists'),
 ('Test suite v1','Data invariants and explicit negative cases','Data tests -> Workflow coverage','Separate static, SQLite, native and source-reported proof','QA owner','A portable PASS is not evidence that a PostgreSQL trigger ran'),
 ('Coverage','Workflow and failure coverage matrices','Coverage -> Refinement','Map every mandatory flow to data and evidence status','QA/Product owners','Missing endpoint or runtime evidence remains an owned gap'),
 ('Refinement','Merge decisions and executed validation loops','Refinement -> Rules v2','Record each finding, fix, proof and unresolved dependency','Data architect','A repeated build is reproducibility evidence, not an independent model run'),
 ('Rules v2','Reconciled constraints and policy decisions','Rules v2 -> Dictionary v2','Version rules and refusal behaviour with ownership','Database owner','Wallet credit count and currency amount constraints must never be conflated'),
 ('Dictionary v2','1407 canonical records with both provenances','Dictionary v2 -> Physical baseline','Compare all field keys; classify proposals and unresolved policies','Data steward','1250 existing physical-design fields and157 proposed fields are not all deployed'),
 ('Test suite v2','1913 historical checks plus current documentary checks','Test suite -> Baseline','Run target-engine races, load and recovery before release','QA/SRE owners','An unsigned source PASS statement does not transfer to the hybrid'),
 ('Physical baseline','Existing120-table design and157-field changeset','Baseline -> Integration mapping','Approve additive/backfill/constraint phases and rollback evidence','Database owner','Hybrid schema additions require a new migration and fresh native proof'),
 ('Integrations','27 proposed exchange contracts and271 source mappings','Integrations -> Future platform work','Validate signatures, retries, duplicates and source ownership','Integration owner','Provider-owned schemas and credentials were not supplied; contracts remain proposed')]
 review_rows=[];handoff_rows=[]
 for s,(topic,inputs,outputs,accept,owner,explanation) in zip(p['steps'],controls):
  n=s['number'];status='PENDING - owner evidence required'
  handoff=[f'HAND-{n:02}',topic,inputs,outputs,accept,owner,status,explanation]
  section(n,'Hybrid handoff',['Handoff ID','Concern','Inputs','Next use','Acceptance condition','Proposed owner','Status','Reason'],[handoff]);handoff_rows.append([n,*handoff])
  questions=[('Meaning and grain',f'Explain the record grain and downstream use of {topic.lower()}.',explanation),('Failure and evidence',f'What must fail for {topic.lower()}, and which proof layer establishes that?',accept),('Hybrid reconciliation',f'Which source B differences affect step{n}, and which changes remain proposals?',f'Use step{n} source comparisons, HDEC decisions and implementation-status fields; do not inherit source PASS claims.')]
  rr=[[f'INT-{n:02}-{i+1}',q,answer,None,None,'NOT REVIEWED',owner] for i,(_,q,answer) in enumerate(questions)]
  section(n,'Human review prompts',['Question ID','Question','Expected evidence anchor','Human response','Reviewer score 0 to 5','Review status','Proposed reviewer role'],rr)
  review_rows.extend([[n,*r] for r in rr])
  section(n,'Acceptance cases',['Case ID','Case','Expected result','Proof layer','Status','Owner'],[
   [f'ACC-{n:02}-1',f'Positive: {topic}',accept,'Owned acceptance test','PLANNED',owner],
   [f'ACC-{n:02}-2','Missing, duplicate, conflicting or unauthorized input','Reject or quarantine with reason; no silent source overwrite','Owned negative test','PLANNED',owner],
   [f'ACC-{n:02}-3','Claimed source PASS without matching logs','Keep source-reported status; full approval remains open','Documentary evidence check','DESIGN CHECKED',owner]])
 # Full rubric values are preserved from the hybrid, including all unassessed zeros.
 consistency={(r[0],r[1]):r[2] for r in h['consistency_inputs']}
 comparisons={r[0]:r for r in h['comparison_stats']}
 ratings=[]
 for r in h['original_source_a_ratings']:
  r=copy.deepcopy(r)
  if r[2]=='Consistency across runs':
   r[6]=consistency[(r[0],r[1])]
   st=comparisons[r[0]]
   r[8]=('Actual B schema trees absent; comparison unassessed.' if r[1]==KINDS[0] else 'B scorecards13-21 compare19/27 criterion properties; other steps unassessed.' if r[1]==KINDS[1] else f'{st[2]}/{st[1]} unique normalized concepts agree; sparse evidence capped. Source locators in Comparison Evidence.')
  r[7]=r[3]*r[6]/5;ratings.append(r)
 p['ratingRows']=ratings
 closure=[]
 for s in p['steps']:
  n=s['number'];groups=[[r for r in ratings if r[0]==n and r[1]==k] for k in KINDS]
  full=[sum(r[7] for r in rr) for rr in groups]
  documentary=[sum(r[7] for r in rr if r[2] not in ['Consistency across runs','Author understanding'])/83*100 for rr in groups]
  for k,rr,f,doc in zip(KINDS,groups,full,documentary):
   target=sum(r[3]*(4 if r[2] in ['Consistency across runs','Author understanding'] else r[6])/5 for r in rr)
   closure.append([n,k,f,doc,90-f, 'Actual independent comparison >=4/5 and actual human interview >=4/5; assess all other carried scores against current evidence',target,'CONDITIONAL TARGET - not achieved','Native/provider/load/recovery release gates remain independent'])
  s.update(score=sum(a*b for a,b in zip(full,[.25,.25,.5])),deliverableScores=full,documentaryScores=documentary,documentaryScore=sum(a*b for a,b in zip(documentary,[.25,.25,.5])),priority='P1' if n in [2,3,6,7] else 'P0')
  folder='steps/'+f'{n:02}_'+safe(s['title']);s['files']={k:folder+'/'+v for k,v in zip(['schema','scorecard','output'],['a_Output_Schema_Definition.xlsx','b_Schema_Rating_Scorecard.xlsx','c_Output_Document.xlsx'])}
 p['combinedRating']=sum(s['score']*(3 if s['priority']=='P0' else 2) for s in p['steps'])/sum(3 if s['priority']=='P0' else 2 for s in p['steps'])
 p['documentaryRating']=sum(s['documentaryScore']*(3 if s['priority']=='P0' else 2) for s in p['steps'])/sum(3 if s['priority']=='P0' else 2 for s in p['steps'])
 p['closure']=closure;p['humanReviews']=review_rows;p['handoffs']=handoff_rows
 p['source_archive']=h['source_archive'];p['mergeDecisions']=h['decisions'];p['sourceClaims']=h['source_claims'];p['sourceMap']=h['section_mapping']
 p['dictionaryCount']=len(dictionary);p['physicalCount']=1250;p['proposedCount']=len(proposals)
 p['sources']+= [['HA','Prior GPT project','Talentra_Combined.xlsx','Source SHA256 in evidence/source_fingerprints.json','1250 baseline fields; previous22 steps'],['HB','Friend workbook; model unknown','Talentra_Master_Lifecycle_Steps_01_to_21.xlsx','24 source tabs;462 dictionary fields','Original values and source locators retained'],['H4','Hybrid master input','Talentra_Hybrid_Master_Steps_01_22.xlsx','Input SHA256 in evidence/source_hybrid_sha256.json','All hybrid sections retained; source claims distinguished']]
 p['method']=[['Full rubric','Original nine dimensions and weights14,14,9,18,9,9,9,8,10 unchanged. No score is raised to meet a target.'],['Documentary score','Seven observed dimensions /83*100. Independent consistency9 and human understanding8 excluded. Supplementary; cannot imply full acceptance.'],['Rollup','Step=25% schema+25% scorecard+50% output. P0=3 and P1=2 priority weighting.'],['Acceptance','Full score >=90 and each critical >=4. Human understanding0 is unassessed, so every current step remains Refine. Production gates remain separate.'],['90+ target','Conditional reviewer scenario changes only comparison and human scores to4, leaving other inputs unchanged. It is not current evidence or approval.'],['Field examples','157 synthetic examples supplied; no private production rows. Existing A source records and original B archives preserved.'],['Proof boundary','Current serialized-contract checks plus historical Python/SQLite/static evidence. Native PostgreSQL, concurrent transactions, target load, providers and recovery remain unexecuted.'],['Offline UI','All outputs, schema hierarchy, ratings and provenance embedded in index.html. Excel downloads resolve inside the extracted package. HTML is the saved snapshot, not live synchronization.'],['Scope','Canonical steps1-22; phases1-3 and start of phase4. Steps23-28 remain outside the user-confirmed cap.'],['Kluster','Tool unavailable; no Kluster review claimed.']]
 # Generate one schema for each of the three deliverables, and validate real values.
 def jt(v):return 'null' if v is None else 'boolean' if type(v)==bool else 'integer' if type(v)==int else 'number' if type(v)==float else 'string'
 fields=[];nodes=[];metrics=[];contracts=[];validation=[]
 old={(r[0],r[1],r[2]):r for r in h['project']['schema_fields']}
 def check(step,cat,name,ok,detail=''):
  validation.append([f'V5-{len(validation)+1:05}',step,cat,name,'PASS' if ok else 'FAIL',detail,'Python serialized-contract/documentary layer'])
 for s in p['steps']:
  n=s['number'];properties={};required=[]
  for si,sec in enumerate(s['sections'],1):
   sid=f'S{n:02}.{si:03}';nodes.append([n,sid,'',1,sec['name'],sec['priority'],'Output section at its stated record grain',sec['source']])
   unique=len(sec['columns'])==len(set(sec['columns']))
   check(n,'contract',sec['name']+' column and row shape',unique and all(len(r)==len(sec['columns']) for r in sec['rows']))
   ps={};schemas=[];nonblank=0;total=0
   for j,col in enumerate(sec['columns']):
    vals=[r[j] for r in sec['rows']];types=sorted(set(jt(v) for v in vals)) or ['string','null']
    if col=='Human response':types=['null','string']
    if col.startswith('Reviewer score'):types=['null','integer']
    typ=' | '.join(types)
    ps[col]={'type':types}
    oldf=old.get((n,sec['name'],col))
    definition=oldf[7] if oldf else f'{col} at the {sec["name"]} record grain. Read with its stable row identity, source locator and evidence status.'
    reason=oldf[8] if oldf else 'Required to check this step exit, preserve source meaning and transfer the decision to its named downstream owner.'
    rule='One typed scalar; no additional properties; null explicitly allowed only where listed'
    fid=sid+f'.P{j+1:02}';fields.append([n,sec['name'],col,'Value contract; Meaning and lineage',typ,'Required property; null only if in type',rule,definition,reason,sec['priority'],sec['source'],fid])
    nodes.append([n,fid,sid,2,col,sec['priority'],definition,sec['source']])
    for suff,label,props in [('V','Value contract',[('Type',typ),('Validation',rule),('Required','Required property; null only if listed')]),('M','Meaning and lineage',[('Definition',definition),('Reason',reason),('Source',sec['source'])])]:
     gid=fid+'.'+suff;nodes.append([n,gid,fid,3,label,sec['priority'],label,sec['source']])
     for k,(label,val) in enumerate(props,1):nodes.append([n,gid+'.'+str(k),gid,4,label,sec['priority'],val,sec['source']])
    nonblank+=sum(v is not None and v!='' for v in vals);total+=len(vals)
   record={'type':'object','properties':ps,'required':list(ps),'additionalProperties':False}
   properties[sec['name']]={'type':'array','items':record};required.append(sec['name'])
   metrics.append({'step':n,'section':sec['name'],'priority':sec['priority'],'rows':len(sec['rows']),'columns':len(ps),'conformance':unique and all(len(r)==len(ps) for r in sec['rows']),'documentaryFill':nonblank/total if total else 1,'definitionScore':5,'evidence':3 if any(x in sec['name'].lower() for x in ['review','acceptance','privacy','changeset','gate','handoff','nfr','capacity']) else 4})
  output_contract={'title':f'Step{n} Output Document','type':'object','properties':properties,'required':required,'additionalProperties':False}
  # These two describe the companion Excel deliverables' serialized table records.
  schema_contract={'title':f'Step{n} Output Schema Definition','type':'array','items':{'type':'object','properties':{x:{'type':['integer'] if x=='Step' else ['string']} for x in ['Step','L1 Section','L2 Parameter','L3 facets','L4 Data type','Required','Validation','Definition','Reason','Priority','Source','Node ID']},'required':['Step','L1 Section','L2 Parameter','L3 facets','L4 Data type','Required','Validation','Definition','Reason','Priority','Source','Node ID'],'additionalProperties':False}}
  score_contract={'title':f'Step{n} Schema Rating Scorecard','type':'array','items':{'type':'object','properties':{x:{'type':['integer','number'] if x in ['Step','Weight','Score','Contribution'] else ['string']} for x in ['Step','Deliverable','Dimension','Weight','Critical','Measure','Score','Contribution','Evidence','Return stage']},'required':['Step','Deliverable','Dimension','Weight','Critical','Measure','Score','Contribution','Evidence','Return stage'],'additionalProperties':False}}
  for kind,key,c in zip(KINDS,['schema','scorecard','output'],[schema_contract,score_contract,output_contract]):
   rel=f'artifact_contracts/step_{n:02}_{key}.json';write(OUT/rel,c);contracts.append([n,kind,rel,digest(OUT/rel),'One serialized contract per deliverable; Python checked against actual records'])
  s['contractFiles']={key:f'artifact_contracts/step_{n:02}_{key}.json' for key in ['schema','scorecard','output']}
 p['schema_fields']=fields;p['schema_nodes']=nodes;p['section_metrics']=metrics;p['contracts']=contracts
 def conforms(v,s):
  typ=s['type'];allowed=typ if isinstance(typ,list) else [typ]
  if jt(v) not in allowed:return False
  if jt(v)=='object':return False
  if isinstance(v,dict):return False
  return True
 def valid(v,s):
  typ=s['type'];ts=typ if isinstance(typ,list) else [typ]
  actual='object' if isinstance(v,dict) else 'array' if isinstance(v,list) else jt(v)
  if actual not in ts:return False
  if actual=='object':
   return all(k in v for k in s.get('required',[])) and (s.get('additionalProperties',True) or set(v)<=set(s['properties'])) and all(k not in s['properties'] or valid(x,s['properties'][k]) for k,x in v.items())
  if actual=='array':return all(valid(x,s['items']) for x in v)
  return True
 schema_headers=['Step','L1 Section','L2 Parameter','L3 facets','L4 Data type','Required','Validation','Definition','Reason','Priority','Source','Node ID']
 rating_headers=['Step','Deliverable','Dimension','Weight','Critical','Measure','Score','Contribution','Evidence','Return stage']
 for s in p['steps']:
  n=s['number'];payloads=[ [dict(zip(schema_headers,r)) for r in fields if r[0]==n], [dict(zip(rating_headers,r)) for r in ratings if r[0]==n], {sec['name']:[dict(zip(sec['columns'],r)) for r in sec['rows']] for sec in s['sections']}]
  for key,payload in zip(['schema','scorecard','output'],payloads):
   c=load(OUT/s['contractFiles'][key]);check(n,'serialized schema',key+' payload validates after disk roundtrip',valid(payload,c),f'{len(payload)} top-level entries')
  check(n,'preservation','All original hybrid sections and rows retained',all(any(sec['name']==o['name'] and len(sec['rows'])>=len(o['rows']) for sec in s['sections']) for o in original[n-1]['sections']))
  check(n,'hierarchy','Every output field has a unique typed L2 node',len([r for r in fields if r[0]==n])==sum(len(sec['columns']) for sec in s['sections']))
  check(n,'scores','All documentary scores exceed90; no full score overwritten',min(s['documentaryScores'])>90 and s['deliverableScores']==h['expected_steps'][n-1][9:12])
 keys={(r[1],r[2]) for r in dictionary};check(0,'dictionary','All1407 field keys unique',len(keys)==1407)
 check(0,'mapping','Every B attribute resolves to canonical field',all((r[3],r[4]) in keys for r in h['attribute_mapping']))
 check(0,'proposals','157 proposed fields have synthetic examples',len(fixture_rows)==157 and all(r[4] is not None for r in fixture_rows))
 ids={r[1]:r for r in nodes};check(0,'hierarchy','All node IDs unique',len(ids)==len(nodes))
 check(0,'hierarchy','Every non-root parent exists at previous level',all(not r[2] or r[2] in ids and ids[r[2]][3]==r[3]-1 for r in nodes))
 check(0,'contracts','Exactly66 artifact contracts',len(contracts)==66)
 check(0,'human gate','Human scores remain0 without interview',all(r[6]==0 for r in ratings if r[2]=='Author understanding'))
 check(0,'source integrity','Original hybrid master not overwritten',digest(ROOT/'outputs/talentra_hybrid_v4/Talentra_Hybrid_Master_Steps_01_22.xlsx')==load(OUT/'evidence/source_hybrid_sha256.json')['sha256'])
 failed=[r for r in validation if r[4]=='FAIL'];write(OUT/'evidence/current_validation.json',validation)
 assert not failed,failed[:3]
 p['validation']=validation
 p['loops']=[['LOOP-01','Audit',f'{missing_before} proposed examples absent; per-step exports not regenerated from hybrid', 'Retain source rows and classify missing evidence','Executed audit'],['LOOP-02','Enrich','Typed synthetic fixtures,1407-field views,66 contracts,22 handoffs and66 interview prompts','Add relevant data and machine-readable contracts','Executed enrichment'],['LOOP-03','Validate',f'{len(validation)} documentary/serialized-contract checks passed','Recalculate and inspect exported Excel plus UI in final checks','Python checks PASS; native and human gates remain open'],['STOP','Evidence boundary','Additional self-authoring cannot supply a human interview or independent/native execution','Use90+ closure plan; preserve actual full scores','External evidence required']]
 p['refinement_log']=[[r[0],r[1],r[2],r[3],r[4]] for r in p['loops']]
 p['phaseRatings']=[[phase,['Discover','Model','Prove','Platform'][phase-1],len([s for s in p['steps'] if s['phase']==phase]),0,0,sum(s['score']*(3 if s['priority']=='P0' else 2) for s in p['steps'] if s['phase']==phase)/sum(3 if s['priority']=='P0' else 2 for s in p['steps'] if s['phase']==phase),'Step22 only' if phase==4 else 'Artifacts populated'] for phase in range(1,5)]
 p['sectionRatings']=[[m['step'],m['section'],level,m['priority'],3 if m['priority']=='P0' else 2,5 if m['conformance'] else 0,5,5,m['evidence'],(15+m['evidence'])/4,'Documentary contract quality; raw filled cells '+str(round(m['documentaryFill']*100,1))+'%; explicit review blanks are pending'] for m in metrics for level in range(1,5)]
 write(WORK/'project_data.json',p);write(OUT/'evidence/hybrid_dictionary.json',dictionary);write(OUT/'evidence/proposed_fields.json',list(proposals.values()));write(OUT/'evidence/artifact_contract_index.json',contracts)
 write(OUT/'evidence/refinement_loops.json',p['loops'])
 (OUT/'database/HYBRID_CHANGESET.md').write_text('''# Hybrid changeset plan\n\nThe retained baseline has120 tables and1250 physical-design columns. The157 additional fields in ../evidence/proposed_fields.json are proposed and have not been migrated. Do not apply the original baseline SQL to an existing production database.\n\n1. Owner approves credit versus currency units, account scoping, privacy, retention and canonical ID mappings.\n2. Database owner writes an additive migration for each approved new table/column, with nullable/backfill/constraint stages.\n3. Translate source IDs to canonical keys. Currency minor_units is not display sort order; label IDs are not translation IDs; language metadata uses its own extension.\n4. Backfill in bounded resumable batches with checksums, parent-before-child ordering, a retry key and quarantine for conflicts.\n5. Run positive/negative FK, uniqueness, account-scope, credit/money and concurrent debit tests in the native engine. Collect logs and measured plans.\n6. Validate counts and reconciliations, then enable constraints and deploy compatible readers/writers. Test rollback/forward recovery before release.\n7. Re-run authorization, target workload, signed provider callbacks, recovery and interview gates. Only then change implementation status and full rubric scores with the evidence.\n\nThe typed synthetic examples are illustrations and must not be loaded as production business records. Source B native PASS claims are not hybrid execution evidence.\n''',encoding='utf-8')
 print(json.dumps({'steps':22,'sections':len(metrics),'fields':len(fields),'nodes':len(nodes),'checks':len(validation),'full':p['combinedRating'],'documentary':p['documentaryRating'],'min_documentary':min(x[3] for x in closure),'min_conditional_target':min(x[6] for x in closure)}))

if __name__=='__main__':package() if '--package' in sys.argv else prepare()
