"""Build an offline, source-traceable Step 22 mini/seed addendum. No database access."""
import csv,gzip,hashlib,io,json,re,shutil,sys,zipfile
from array import array
from collections import Counter,defaultdict
from contextlib import ExitStack
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'outputs/talentra_step22_mentor_v6'
OUT=ROOT/'outputs/talentra_step22_mini_seed_v7'
WORK=ROOT/'work/workflow_split_v7'
DATE='2026-11-01'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def readcsv(p):
 with gzip.open(p,'rt',encoding='utf-8',newline='') as f:yield from csv.DictReader(f)
def gz_writer(stack,p,headers):
 p.parent.mkdir(parents=True,exist_ok=True)
 raw=stack.enter_context(open(p,'wb'));gz=stack.enter_context(gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0,compresslevel=1));f=stack.enter_context(io.TextIOWrapper(gz,encoding='utf-8',newline=''))
 w=csv.DictWriter(f,fieldnames=headers,lineterminator='\n');w.writeheader();return w
def writecsv(p,headers,rows):
 with ExitStack() as stack:
  w=gz_writer(stack,p,headers)
  for r in rows:w.writerow(r)

GROUPS={1:'Identity and profile',2:'Identity and profile',3:'Organisation and access',4:'Demand and eligibility',5:'Demand and eligibility',6:'Hiring decisions',7:'Sourcing and messaging',8:'Sourcing and messaging',9:'Identity and profile',10:'Gig marketplace',11:'Gig marketplace',12:'Organisation and access',13:'Commerce and support',14:'Sourcing and messaging',15:'Sourcing and messaging',16:'Commerce and support',17:'Data and governance',18:'Identity and profile',19:'Demand and eligibility',20:'Hiring decisions',21:'Hiring decisions',22:'Hiring decisions',23:'Hiring decisions',24:'Gig marketplace',25:'Data and governance',26:'Sourcing and messaging',27:'Data and governance'}
NEW_ACTORS=[
 ('ACT-19','Eligibility Worker','Service context','Integration Worker','Evaluate job-scoped pre-application eligibility','WF-19'),
 ('ACT-20','Assessment Provider','External provider','Integration Worker','Supply assessment completion with application context','WF-20'),
 ('ACT-21','Interviewer','Business subrole','Employer','Record assigned interview evidence','WF-21'),
 ('ACT-22','Hiring Manager','Business subrole','Employer','Approve selection and offer terms for own organisation','WF-22'),
 ('ACT-23','Identity Verification Provider','External provider','Integration Worker','Return a tokenized identity outcome','WF-01;WF-03'),
 ('ACT-24','Company Verification Provider','External provider','Integration Worker','Return company verification outcome','WF-03;WF-04'),
 ('ACT-25','Gig Fulfilment Provider','External provider','Integration Worker','Own external fulfilment, completion and earnings status','WF-24'),
 ('ACT-26','Notification Worker','Service context','Integration Worker','Recheck consent and deliver bounded notifications','WF-26'),
 ('ACT-27','Reconciliation Analyst','Business subrole','Analyst','Review quarantined input and reconcile aggregates','WF-25;WF-27')]

# The 52 additions describe specific actions, rather than padding existing steps.
# Each tuple is action, data context, primary actor, applicable rules.
ADDITIONS=[
 ('Search and job eligibility','Search matches and job-scoped screening',[
 ('Create target-job journey','candidate_job_journey.journey_id;job_requirement.id','Candidate','R01;R02'),
 ('Bind candidate and account scope','candidate_profile.id;job_requirement.organisation_id','Eligibility Worker','R05;R06'),
 ('Resolve job family and engagement','job_family_code;engagement_type','Eligibility Worker','R01;R02;R03'),
 ('Evaluate the versioned eligibility rules','eligibility_outcome;rule_version','Eligibility Worker','R07;R25'),
 ('Record screening source event','journey_stage_event.source_event_id;occurred_at','Eligibility Worker','R13'),
 ('Permit eligible candidate submission','job_application.applied_at','Candidate','R04;R07')]),
 ('Assessment with application context','Assessment completion and its source event',[
 ('Confirm application and assessment context','job_application.id;assessment_attempt.id','Assessment Provider','R05;R25'),
 ('Issue a scoped assessment invitation','assessment_id;invitation_reference','Recruiter','R06;R20'),
 ('Record a tokenized provider attempt','assessment_attempt.candidate_profile_id;provider_attempt_ref','Assessment Provider','R05'),
 ('Validate completion and result units','assessment_attempt.completed_at;score;score_scale','Assessment Provider','R13;R25'),
 ('Link the attempt to this application','assessment_application_bridge.application_id','Integration Worker','R05'),
 ('Publish the assessed milestone','journey_stage_event.stage_code;occurred_at','Integration Worker','R13')]),
 ('Interview and employer decision','Assigned interview and employer decision',[
 ('Authorize the assigned interviewer','interview.id;organisation_id','Interviewer','R05;R06'),
 ('Schedule the candidate interview','interview.scheduled_at;candidate_profile.id','Recruiter','R25'),
 ('Record interview completion','interview.completed_at;outcome_code','Interviewer','R25'),
 ('Apply the job-specific evaluation rubric','rubric_version;interview_score','Interviewer','R25'),
 ('Record selected or employer-rejected decision','application_status_event.occurred_at;decision_owner','Hiring Manager','R08'),
 ('Publish outcome to the hiring cohort','journey_stage_event.stage_code;source_version','Integration Worker','R13')]),
 ('Offer issue and candidate response','Offer, acceptance and candidate decline',[
 ('Verify selection before offer creation','job_application.id;selected_at','Hiring Manager','R09'),
 ('Approve terms, currency and expiry','job_offer.id;currency_code;expires_at','Hiring Manager','R19;R25'),
 ('Deliver the offer under valid consent','notification.id;consent_record.id','Notification Worker','R20'),
 ('Authenticate the responding candidate','candidate_profile.id;job_offer.id','Candidate','R04;R05'),
 ('Record acceptance or candidate decline','job_offer.status_reference_value_id;responded_at','Candidate','R10'),
 ('Publish the first offer and response times','journey_stage_event.occurred_at;stage_code','Integration Worker','R13')]),
 ('Onboarding confirmation','Acceptance, joining and vacancy reconciliation',[
 ('Verify accepted offer and identity','job_offer.id;candidate_profile.id','Employer','R11;R05'),
 ('Keep pending onboarding visible','pending_since;expected_joining_date','Recruiter','R11'),
 ('Confirm the actual joining date','joining_record.joined_on','Employer','R11'),
 ('Validate job vacancy capacity','job_requirement.positions;positions_filled','Employer','R22'),
 ('Publish the onboarded milestone','journey_stage_event.stage_code;occurred_at','Integration Worker','R13'),
 ('Reconcile onboarding KPI and pending ageing','cohort_code;first_accepted_at;first_onboarded_at','Analyst','R25')]),
 ('External gig fulfilment','External handoff, callback, earnings and rating',[
 ('Verify accepted assignment and time window','gig_assignment.id;start_at;end_at','Requester','R15;R16'),
 ('Send a uniquely keyed external handoff','gig_assignment.external_handoff_key','Integration Worker','R12'),
 ('Return signed provider state and source version','provider_status;source_version;source_event_id','Gig Fulfilment Provider','R05;R13'),
 ('Keep failed handoff pending for retry','retry_at;attempt_count;handoff_key','Integration Worker','R12;R13'),
 ('Reconcile externally completed earnings','gig_earnings_snapshot.total_amount;currency_code','Gig Fulfilment Provider','R17;R19'),
 ('Allow the owner to rate completed work','gig_rating.rating;requester_organisation_id','Requester','R18')]),
 ('Source ingest and reconciliation','Owned source contracts and quarantined records',[
 ('Fingerprint the received file and contract','file_sha256;contract_id;schema_version','Data Engineer','R25'),
 ('Validate account binding and required types','organisation_id;required_fields','Integration Worker','R05;R25'),
 ('Translate source identifiers within account','source_id;canonical_id;organisation_id','Integration Worker','R05'),
 ('Detect duplicate keys and conflicting payloads','event_key;payload_hash','Integration Worker','R12'),
 ('Quarantine invalid or stale state updates','rejection_code;source_version','Reconciliation Analyst','R13'),
 ('Reconcile applied, refused and pending counts','reconciliation_run.id;source_rows;outcome_counts','Reconciliation Analyst','R25')]),
 ('Consent-aware notification delivery','Queued notification and delivery result',[
 ('Resolve the owning account and recipient','notification.recipient_app_user_id','Notification Worker','R05'),
 ('Recheck consent, blocking and expiry','consent_record.revoked_at;blocking_entry.id;expires_at','Notification Worker','R06;R20'),
 ('Reserve an idempotent delivery key','notification_event.id;event_key','Notification Worker','R12'),
 ('Send or retain a bounded pending retry','provider_ref;retry_at;attempt_count','Notification Worker','R20'),
 ('Audit delivery or cancellation outcome','audit_event.action_code;occurred_at','Notification Worker','R25')]),
 ('Workflow dataset analytics','Versioned smaller sets and reproducible analytics',[
 ('Select mini or seed and its workflow set','version;workflow_id;set_id','Data Engineer','R25'),
 ('Resolve the set grain, filters and source hashes','grain;selector;source_sha256','Data Engineer','R25'),
 ('Generate scoped workflow example envelopes','case_id;step_id;example_payload','Data Engineer','R05;R25'),
 ('Calculate counts, outcomes and business ratios','numerator;denominator;metric_unit','Analyst','R25'),
 ('Review anomalies and publish the evidence','validation_id;owner;review_status','Reconciliation Analyst','R25')])]

def catalogue(d):
 actors=[]
 for r in d['steps'][1]['sections'][0]['rows']:
  actors.append({'actor_id':r[0],'actor':r[1],'kind':'Existing project persona','parent_context':None,'purpose':r[2],'scope':r[3],'source':f'Step 2 Personas / {r[0]}','status':'Retained project design'})
 for a,n,k,parent,purpose,wfs in NEW_ACTORS:actors.append({'actor_id':a,'actor':n,'kind':k,'parent_context':parent,'purpose':purpose,'scope':'Scoped to assigned organisation, subject or owned provider contract','source':wfs+' / Step 22 mentor-derived detail','status':'Proposed actor context; not a new deployed RBAC role'})
 byname={a['actor']:a['actor_id'] for a in actors}
 maps=next(x for x in d['steps'][4]['sections'] if x['name']=='Workflow maps')['rows'];ops=next(x for x in d['steps'][4]['sections'] if x['name']=='Workflow operations')['rows']
 workflows=[{'workflow_id':r[0],'workflow':r[1],'group':GROUPS[int(r[0][-2:])],'primary_actor':r[2],'trigger':r[3],'business_sequence':r[4],'exceptions':r[5],'source':r[8],'status':'Retained source design','data_scope':'Synthetic workflow envelopes plus linked hiring/gig records where applicable'} for r in maps]
 steps=[]
 for r in ops:
  steps.append({'step_id':r[0],'workflow_id':r[1],'sequence':int(r[0].split('.')[1]),'actor_id':byname[r[2]],'actor':r[2],'action':r[3],'data_elements':r[4]+': '+r[5],'target_entity':r[4],'rules':'R05;R25','failure':'Reject account mismatch or missing input; preserve audit reason','source':f'Step 5 Workflow operations / {r[0]}','status':'Retained source design','native_proof':'Not executed against native database'})
 for ix,(name,trigger,items) in enumerate(ADDITIONS,19):
  wid=f'WF-{ix:02}';workflows.append({'workflow_id':wid,'workflow':name,'group':GROUPS[ix],'primary_actor':items[0][2],'trigger':trigger,'business_sequence':' > '.join(a[0] for a in items),'exceptions':'Cross-account, missing required input, blocked subject, duplicate or invalid business transition','source':'Mentor image / v6 business scenarios and gap register','status':'Proposed detailed workflow','data_scope':'Synthetic workflow envelopes; proposed fields remain staging examples'})
  for seq,(action,fields,actor,rules) in enumerate(items,1):steps.append({'step_id':f'{wid}.{seq:02}','workflow_id':wid,'sequence':seq,'actor_id':byname[actor],'actor':actor,'action':action,'data_elements':fields,'target_entity':fields.split('.')[0],'rules':rules,'failure':'Reject or quarantine with an explicit scoped outcome; no fabricated provider success','source':f'Proposed v7 / {wid} / v6 scenario or model gap','status':'Proposed detailed step','native_proof':'Portable example only; service/native implementation pending'})
 # Extra supporting participants are explicit, without rewriting retained source owners.
 extra={'WF-01':['Identity Verification Provider'],'WF-03':['Company Verification Provider'],'WF-04':['Company Verification Provider'],'WF-12':['Account Admin'],'WF-16':['Support Agent'],'WF-17':['Super Admin','Admin','Auditor','Analyst','Placement Officer'],'WF-25':['Reconciliation Analyst'],'WF-27':['Data Engineer','Analyst']}
 extra['WF-19']=['Guest']
 for w in workflows:
  ss=[s for s in steps if s['workflow_id']==w['workflow_id']];w['step_count']=len(ss)
  w['actor_ids']=sorted({s['actor_id'] for s in ss}|{byname[a] for a in extra.get(w['workflow_id'],[])})
 assert len(actors)==27 and len(steps)==168 and sum(w['step_count'] for w in workflows)==168
 return actors,workflows,steps

RULE_DEFS=[
 ('R01','Valid job family','Taxonomy','family_code in versioned six-family catalogue'),('R02','Collar and branch consistency','Taxonomy','family code resolves its declared collar, branch and function'),('R03','Engagement is a separate axis','Taxonomy','permanent, contract, gig or apprentice'),('R04','Candidate owns registration and offer response','Identity','principal equals subject and a recruiter does not impersonate'),('R05','Organisation scope','Access','credential organisation equals target organisation'),('R06','Blocked visibility','Access','blocked subject access is refused'),('R07','Screen before applying','Hiring','application follows job-scoped eligible screening'),('R08','Interview before selection','Hiring','selection follows completed interview'),('R09','Selection before offer','Hiring','offer follows employer selection'),('R10','Offer before candidate acceptance','Hiring','acceptance follows a valid issued offer'),('R11','Acceptance before joining','Hiring','onboarding follows acceptance'),('R12','Idempotent business effect','Integration','same key/hash returns prior result and changed hash conflicts'),('R13','Version and event ordering','Integration','stale state update cannot regress current state'),('R14','Worker-to-requester gig application','Gig','application direction is worker to requester'),('R15','Positive gig time window','Gig','end time is later than start time'),('R16','Assignment after acceptance','Gig','assignment exists only for an accepted application'),('R17','External completed earnings','Gig','external completion with nonnegative exact decimal amount'),('R18','Completed own-assignment rating','Gig','requester owns completed assignment and rating is 1 through 5'),('R19','Currency representation','Money','three-letter uppercase currency code with decimal amount'),('R20','Consent before notification','Messaging','consent active and delivery not expired'),('R21','Approved consultant sourcing','Sourcing','job open to consultants and request accepted'),('R22','Vacancy capacity','Hiring','zero <= filled positions <= positions'),('R23','Versioned set identity','Data','version, workflow and unique case key required'),('R24','Coherent analytics denominator','Analytics','zero denominator is not applicable and cohort/grain match'),('R25','Required source input','Contract','required field present with a permitted non-null value')]

def evaluate(rule,r):
 if rule=='R01':return r['family'] in FAMILIES
 if rule=='R02':return r['family'] in FAMILIES and r['collar']==FAMILIES[r['family']]['collar'] and r['branch']==FAMILIES[r['family']]['branch'] and r.get('function')==FAMILIES[r['family']]['function']
 if rule=='R03':return r['engagement'] in ['permanent','contract','gig','apprentice']
 if rule=='R04':return r['principal']==r['subject'] and r['role']!='Recruiter'
 if rule=='R05':return r['org']==r['target_org']
 if rule=='R06':return not r['blocked']
 if rule in ['R07','R08','R09','R10','R11']:return r['previous']=={'R07':'screened','R08':'interviewed','R09':'selected','R10':'offered','R11':'accepted'}[rule]
 if rule=='R12':return not r['duplicate'] or r['hash']==r['prior_hash']
 if rule=='R13':return r['version']>=r['current_version']
 if rule=='R14':return r['direction']=='worker_to_requester'
 if rule=='R15':return r['end']>r['start']
 if rule=='R16':return r['accepted'] or not r['assignment']
 if rule=='R17':return r['provider_status']=='completed' and Decimal(str(r['amount']))>=0
 if rule=='R18':return r['provider_status']=='completed' and r['org']==r['target_org'] and 1<=r['rating']<=5
 if rule=='R19':return bool(re.fullmatch('[A-Z]{3}',r['currency']))
 if rule=='R20':return r['consent'] and not r['expired']
 if rule=='R21':return r['consultant_open'] and r['sourcing_accepted']
 if rule=='R22':return 0<=r['filled']<=r['positions']
 if rule=='R23':return r['set_version'] in ['mini','seed'] and bool(r['case_id']) and r['workflow_id'] in [f'WF-{i:02}' for i in range(1,28)]
 if rule=='R24':return r['same_cohort'] and r['same_grain'] and (r['denominator']!=0 or r['value'] is None)
 if rule=='R25':return r.get('required_value') is not None
 raise ValueError(rule)

def rule_tests():
 base={'family':'IT_DEV','collar':'White collar','branch':'IT','engagement':'gig','principal':1,'subject':1,'role':'Candidate','org':1,'target_org':1,'blocked':False,'previous':'screened','duplicate':True,'hash':'a','prior_hash':'a','version':2,'current_version':1,'direction':'worker_to_requester','end':2,'start':1,'accepted':True,'assignment':1,'provider_status':'completed','amount':'100.00','rating':4,'currency':'INR','consent':True,'expired':False,'consultant_open':True,'sourcing_accepted':True,'filled':1,'positions':2,'set_version':'mini','workflow_id':'WF-01','case_id':'x','same_cohort':True,'same_grain':True,'denominator':0,'value':None,'required_value':'input'}
 bad={'R01':{'family':'unknown'},'R02':{'collar':'Blue collar'},'R03':{'engagement':'IT'},'R04':{'role':'Recruiter'},'R05':{'org':2},'R06':{'blocked':True},'R07':{'previous':'searched'},'R08':{'previous':'assessed'},'R09':{'previous':'interviewed'},'R10':{'previous':'selected'},'R11':{'previous':'rejected'},'R12':{'hash':'changed'},'R13':{'version':0},'R14':{'direction':'requester_to_worker'},'R15':{'end':0},'R16':{'accepted':False},'R17':{'amount':'-0.01'},'R18':{'provider_status':'in_progress'},'R19':{'currency':'inr'},'R20':{'consent':False},'R21':{'sourcing_accepted':False},'R22':{'filled':3},'R23':{'case_id':''},'R24':{'value':0},'R25':{'required_value':None}}
 base['function']='Development'
 assert not evaluate('R02',{**base,'function':'Sales'})
 results=[]
 for rule,_,_,_ in RULE_DEFS:
  b=dict(base)
  if rule in ['R08','R09','R10','R11']:b['previous']={'R08':'interviewed','R09':'selected','R10':'offered','R11':'accepted'}[rule]
  for label,rec,expected in [('valid',b,True),('refusal',{**b,**bad[rule]},False)]:
   actual=evaluate(rule,rec);assert actual==expected
   results.append({'test_id':rule+'-'+label,'rule_id':rule,'case':label,'expected':expected,'actual':actual,'result':'PASS','layer':'Portable rule function; no deployed endpoint or native SQL proof'})
 return results

def core_sets(summary):
 mini_ids=set();mini_jobs=set();buckets=Counter();families=array('B',[0])*(summary['population']+1);family_codes=list(FAMILIES)
 for r in readcsv(BASE/'scenario_data/journey.csv.gz'):
  jid=int(r['journey_id']);fi=family_codes.index(r['job_family_code']);families[jid]=fi
  key=(r['job_family_code'],r['current_stage'])
  if buckets[key]<2:mini_ids.add(jid);mini_jobs.add(int(r['job_requirement_id']));buckets[key]+=1
 assert len(mini_ids)==120 and len(buckets)==60
 keys=['journey','event','application','job','gig'];inventory=[]
 for key in keys:
  source=BASE/'scenario_data'/summary['files'][key]['file'];destination=OUT/'seed/core'/source.name
  destination.parent.mkdir(parents=True,exist_ok=True)
  if not destination.exists() or sha(destination)!=summary['files'][key]['sha256']:shutil.copyfile(source,destination)
  assert sha(destination)==summary['files'][key]['sha256']
  first=next(readcsv(source));headers=list(first);counts=Counter()
  with ExitStack() as stack:
   mw=gz_writer(stack,OUT/'mini/core'/source.name,headers)
   partitions={}
   if key in ['journey','gig']:
    partitions={f:gz_writer(stack,OUT/'seed/sets'/f/(key+'.csv.gz'),headers) for f in FAMILIES}
   for r in readcsv(destination):
    counts['seed']+=1
    keep=int(r['journey_id']) in mini_ids if key in ['journey','event'] else int(r['candidate_profile_id']) in mini_ids if key=='application' else int(r['job_requirement_id']) in mini_jobs if key=='job' else int(r['gig_request_id'])<=20
    if keep:mw.writerow(r);counts['mini']+=1
    if partitions:partitions[r['job_family_code']].writerow(r)
  for version in ['mini','seed']:
   fp=OUT/version/'core'/source.name
   inventory.append({'version':version,'dataset':key,'file':str(fp.relative_to(OUT)).replace('\\','/'),'rows':counts[version],'sha256':sha(fp),'bytes':fp.stat().st_size,'grain':{'journey':'Candidate-job journey snapshot','event':'One journey stage event','application':'One submitted hiring application','job':'One job requirement','gig':'One gig application with optional assignment context'}[key]})
 return inventory,mini_ids

def analytics_core(version):
 p=OUT/version/'core';families={};journey_by_id={};stage=Counter();timing=defaultdict(dict);times=defaultdict(lambda:[0,0]);app_count=0;gig=Counter();byfamily=defaultdict(Counter)
 # Only retain family byte codes for the full seed, and complete mini dictionaries for linkage validation.
 family_ids=array('B',[0])*1500001
 for r in readcsv(p/'journey.csv.gz'):
  fi=list(FAMILIES).index(r['job_family_code']);family_ids[int(r['journey_id'])]=fi
  byfamily[r['job_family_code']]['journeys']+=1
  if version=='mini':journey_by_id[int(r['journey_id'])]=r
 active=None;et={};last_stage=None;last_time=None;jobmap={int(r['job_requirement_id']):r for r in readcsv(p/'job.csv.gz')};mini_apps=set()
 parents={'screened':'searched','applied':'screened','shortlisted':'applied','assessed':'shortlisted','interviewed':'assessed','selected':'interviewed','rejected':'interviewed','offered':'selected','accepted':'offered','offer_declined':'offered','onboarded':'accepted'}
 def accumulate():
  for label,end,start in [('time_to_offer','offered','applied'),('time_to_hire','accepted','applied'),('time_to_onboard','onboarded','accepted')]:
   if end in et:
    days=(datetime.fromisoformat(et[end].replace('Z','+00:00'))-datetime.fromisoformat(et[start].replace('Z','+00:00'))).total_seconds()/86400
    assert days>=0;times[label][0]+=days;times[label][1]+=1
 for r in readcsv(p/'event.csv.gz'):
  jid=int(r['journey_id']);st=r['stage_code'];j=int(r['job_requirement_id'])
  if active!=jid:
   if active is not None:accumulate()
   active=jid;et={};last_stage=None;last_time=None
  assert (st=='searched' and last_stage is None) or parents.get(st)==last_stage
  assert last_time is None or r['occurred_at']>=last_time
  assert j in jobmap and r['organisation_id']==jobmap[j]['organisation_id']
  assert (r['application_id']=='\\N') if st in ['searched','screened'] else (r['application_id']==r['candidate_profile_id'])
  if version=='mini':assert jid in journey_by_id
  et[st]=r['occurred_at'];last_stage=st;last_time=r['occurred_at'];stage[st]+=1;byfamily[list(FAMILIES)[family_ids[jid]]][st]+=1
 if active is not None:accumulate()
 for r in readcsv(p/'application.csv.gz'):
  app_count+=1
  assert int(r['job_requirement_id']) in jobmap
  if version=='mini':assert int(r['candidate_profile_id']) in journey_by_id;mini_apps.add(r['application_id'])
 assert app_count==stage['applied']
 if version=='mini':
  for r in journey_by_id.values():assert r['application_id']=='\\N' or r['application_id'] in mini_apps
 for r in jobmap.values():assert 0<=int(r['positions_filled'])<=int(r['positions'])
 for r in readcsv(p/'gig.csv.gz'):
  gig['applications']+=1;gig[r['status_code']]+=1
  assert r['end_at']>r['start_at']
  assert (r['assignment_id']!='\\N')== (r['status_code']=='accepted')
  if r['provider_status']=='completed':gig['completed']+=1
  if r['requester_rating']!='\\N':assert r['provider_status']=='completed' and 1<=int(r['requester_rating'])<=5;gig['rated']+=1
  if r['total_amount']!='\\N':assert Decimal(r['total_amount'])>=0 and r['provider_status']=='completed'
 kpis=[]
 for st,parent in parents.items():kpis.append({'metric':st+' conversion','numerator':stage[st],'denominator':stage[parent],'value':stage[st]/stage[parent] if stage[parent] else None,'unit':'ratio','grain':'Journey reaching milestone in same cohort'})
 for label,(total,count) in times.items():kpis.append({'metric':label,'numerator':round(total,6),'denominator':count,'value':total/count if count else None,'unit':'calendar days','grain':'Journey reaching both first milestones'})
 for label,num,den in [('Gig acceptance',gig['accepted'],gig['applications']),('Gig completion',gig['completed'],gig['accepted']),('Gig rating coverage',gig['rated'],gig['completed'])]:kpis.append({'metric':label,'numerator':num,'denominator':den,'value':num/den if den else None,'unit':'ratio','grain':'Gig application or assignment as named'})
 return {'version':version,'selection_basis':'Coverage sample, deliberately balanced across family and current outcome. Rates are descriptive of this sample, not estimates of the seed.' if version=='mini' else 'Full saved v6 synthetic population. Scenario rates remain proposed workload assumptions.','stages':dict(stage),'families':{f:dict(v) for f,v in byfamily.items()},'gig':dict(gig),'kpis':kpis,'validation':'Saved-file readback and scoped referential/business invariants passed. No database or load test.'}

def workflow_sets(actors,workflows,steps,dictionary):
 fields={(r[1],r[2]):r for r in dictionary};examples={};metrics=[];sets=[];all_cases=[]
 variants=['valid','cross_account','missing_required','blocked','duplicate','stale_version']
 for version,count in [('mini',6),('seed',60)]:
  for w in workflows:
   wid=w['workflow_id'];ws=[s for s in steps if s['workflow_id']==wid];cases=[];executions=[]
   for i in range(count):
    kind=variants[i%6];org=i%10+1;case_id=f'{version}-{wid}-{i+1:04}'
    request={'version':version,'case_id':case_id,'workflow_id':wid,'organisation_id':org,'target_organisation_id':org if kind!='cross_account' else org+1,'required_value':None if kind=='missing_required' else 'synthetic-input','blocked':kind=='blocked','duplicate':kind=='duplicate','source_version':0 if kind=='stale_version' else 1,'current_version':1}
    # Actual generic envelope guard. Specific domain rules have separate positive/negative tests.
    if request['organisation_id']!=request['target_organisation_id']:outcome='CROSS_ACCOUNT'
    elif request['required_value'] is None:outcome='MISSING_REQUIRED'
    elif request['blocked']:outcome='BLOCKED_SUBJECT'
    elif request['duplicate']:outcome='DUPLICATE_NO_SECOND_EFFECT'
    elif request['source_version']<request['current_version']:outcome='STALE_VERSION'
    else:outcome='ACCEPTED_EXAMPLE'
    cases.append({**request,'variant':kind,'outcome':outcome,'executed_example_steps':len(ws) if outcome=='ACCEPTED_EXAMPLE' else 0,'proof_layer':'Portable envelope guard. Does not execute the native workflow.'})
    if outcome=='ACCEPTED_EXAMPLE':
     for st in ws:
      entity=st['target_entity'];ef={r[2]:r[8] for r in dictionary if r[1]==entity}
      if not ef:ef={'business_context':st['data_elements'],'organisation_id':org,'source_version':1,'is_synthetic':True}
      examples.setdefault(st['step_id'],{'step_id':st['step_id'],'entity':entity,'data_elements':st['data_elements'],'example_payload':ef,'status':'Dictionary-derived scalar examples; not a joined native row' if any(r[1]==entity for r in dictionary) else 'Proposed staging example; no physical target claimed'})
      executions.append({'case_id':case_id,'workflow_id':wid,'step_id':st['step_id'],'sequence':st['sequence'],'actor_id':st['actor_id'],'organisation_id':org,'outcome':'EXAMPLE_EMITTED','example_ref':st['step_id'],'native_execution':False})
   folder=OUT/version/'workflows'/wid;dump(folder/'cases.json',cases);dump(folder/'step_examples.json',executions)
   ct=Counter(c['outcome'] for c in cases)
   row={'version':version,'set_id':version+'-'+wid,'workflow_id':wid,'workflow':w['workflow'],'group':w['group'],'case_count':len(cases),'accepted_examples':ct['ACCEPTED_EXAMPLE'],'refused_or_duplicate':len(cases)-ct['ACCEPTED_EXAMPLE'],'step_example_rows':len(executions),'defined_steps':len(ws),'covered_steps':len({e['step_id'] for e in executions}),'outcomes':dict(ct),'scope':'Workflow envelope fixtures and examples. No endpoint, database transaction, or external provider was invoked.'}
   metrics.append(row);dump(folder/'analytics.json',row)
   linked=['gig'] if wid in ['WF-10','WF-11','WF-24'] else ['journey','event','application','job'] if wid in ['WF-04','WF-05','WF-06','WF-07','WF-19','WF-20','WF-21','WF-22','WF-23'] else []
   manifest={'version':version,'workflow_id':wid,'record_grain':'One guarded workflow example case; emitted step rows refer to shared dictionary examples','case_file':str((folder/'cases.json').relative_to(OUT)).replace('\\','/'),'example_file':str((folder/'step_examples.json').relative_to(OUT)).replace('\\','/'),'analytics_file':str((folder/'analytics.json').relative_to(OUT)).replace('\\','/'),'linked_business_datasets':[version+'/core/'+k+'.csv.gz' for k in linked],'business_selector':'See workflow action and declared data elements. Shared business files are references, not duplicated per workflow.','native_model_status':'Existing or proposed context as recorded per step','proof_layer':row['scope']}
   dump(folder/'manifest.json',manifest);sets.append(manifest)
   all_cases+=cases
 dump(OUT/'catalogue/field_examples.json',list(examples.values()))
 assert len(examples)==168
 return metrics,sets,all_cases

def schemas():
 for fp in (BASE/'contracts').glob('mentor.*.schema.json'):shutil.copyfile(fp,OUT/'contracts'/fp.name)
 spec={'actor':{'actor_id':'string','actor':'string','kind':'string','parent_context':['string','null'],'purpose':'string','scope':'string','source':'string','status':'string'},'workflow_step':{'step_id':'string','workflow_id':'string','sequence':'integer','actor_id':'string','actor':'string','action':'string','data_elements':'string','target_entity':'string','rules':'string','failure':'string','source':'string','status':'string','native_proof':'string'}}
 for name,fields in spec.items():dump(OUT/'contracts'/f'{name}.schema.json',{'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','properties':{k:{'type':t} for k,t in fields.items()},'required':list(fields),'additionalProperties':False})

def main():
 d=load(ROOT/'work/release_v6/dashboard_data.json');summary=load(BASE/'scenario_data/generation_summary.json')
 global FAMILIES
 FAMILIES={f['code']:f for f in summary['families']}
 WORK.mkdir(parents=True,exist_ok=True)
 if not OUT.exists():
  shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('*.inspect.ndjson','scenario_data'))
  (OUT/'scenario_data').mkdir();shutil.copyfile(BASE/'scenario_data/generation_summary.json',OUT/'scenario_data/generation_summary.json');shutil.copyfile(BASE/'scenario_data/journey_sample.csv',OUT/'scenario_data/journey_sample.csv')
 actors,workflows,steps=catalogue(d)
 rules=[{'rule_id':a,'rule':b,'domain':c,'predicate':e,'enforcement':'Proposed service/native rule; portable function checks only','source':'Existing project semantics or mentor-derived detailed rule'} for a,b,c,e in RULE_DEFS]
 for name,obj in [('actors',actors),('workflows',workflows),('workflow_steps',steps),('rules',rules)]:dump(OUT/'catalogue'/f'{name}.json',obj)
 inventory,_=core_sets(summary);print('Core datasets split',flush=True)
 core={v:analytics_core(v) for v in ['mini','seed']};print('Saved core analytics verified',flush=True)
 metrics,sets,cases=workflow_sets(actors,workflows,steps,load(BASE/'evidence/hybrid_dictionary.json'));tests=rule_tests();schemas()
 checks=[{'check':'Actor catalogue','result':'PASS','observed':len(actors),'scope':'18 retained + 9 proposed contexts'},{'check':'Workflow steps','result':'PASS','observed':len(steps),'scope':'116 retained + 52 proposed steps; not lifecycle step numbers'},{'check':'Per-workflow smaller sets','result':'PASS','observed':len(sets),'scope':'27 workflows for each of two versions'},{'check':'Rule examples','result':'PASS','observed':len(tests),'scope':'25 positive + 25 refusal portable checks'},{'check':'Step example coverage','result':'PASS','observed':168,'scope':'Every declared step has a dictionary or explicit staging example'},{'check':'Seed source fingerprints','result':'PASS','observed':5,'scope':'All five seed core files match v6 byte-for-byte'},{'check':'Mini linkage and family/outcome coverage','result':'PASS','observed':120,'scope':'Six families, ten current outcomes, two examples per combination'},{'check':'Full-file business invariants','result':'PASS','observed':2,'scope':'Mini and seed saved-file event order, organisation, application and gig guards'}]
 data={'date':DATE,'scope':'Step 22 mini/seed workflow addendum. Original lifecycle remains steps 1–22.','actors':actors,'workflows':workflows,'steps':steps,'rules':rules,'tests':tests,'inventory':inventory,'analytics':metrics,'sets':sets,'core':core,'checks':checks,'source_counts':{'retained_actors':18,'proposed_actors':9,'retained_steps':116,'proposed_steps':52},'full_score':82.9,'documentary_score':97.71084337349399,'score_note':'Carried-forward v6 Step 22 ratings only. New addendum has not received an independent full-rubric or human review. No score increase claimed.'}
 dump(OUT/'catalogue/mini_seed_project.json',data);dump(WORK/'project.json',data);dump(OUT/'evidence/mini_seed_validation.json',checks);dump(OUT/'evidence/mini_seed_rule_tests.json',tests)
 for version in ['mini','seed']:dump(OUT/version/'analytics.json',core[version])
 dump(OUT/'catalogue/workflow_set_index.json',sets)
 for version in ['mini','seed']:
  for w in workflows:
   m=next(m for m in metrics if m['version']==version and m['workflow_id']==w['workflow_id'])
   assert m['covered_steps']==m['defined_steps']
   folder=OUT/version/'workflows'/w['workflow_id']
   for c in load(folder/'cases.json'):assert c['workflow_id']==w['workflow_id']
 # Actual source preservation checks remain visible.
 preserved=0
 for fp in (BASE/'steps').glob('*/*xlsx'):
  if not fp.parent.name.startswith('22_'):assert sha(fp)==sha(OUT/fp.relative_to(BASE));preserved+=1
 checks.append({'check':'Steps 1–21 retained unchanged','result':'PASS','observed':preserved,'scope':'SHA256 matches for all 63 existing workbooks'})
 dump(OUT/'evidence/mini_seed_validation.json',checks);dump(WORK/'project.json',data)
 readme=f'''# Talentra Step 22: mini and seed workflow sets
Prepared {DATE}. Open index.html and choose Mini and seed.

The mentor images specify a split into mini and seed versions, 27 actors, 168 workflow steps, smaller workflow-defined sets, job-family/gig rules and analytics for each set. The user authorized a proposed catalogue derived from the existing project.

## Scope and provenance
The 168 entries are workflow operations, not 168 D3 lifecycle steps. Preserve the requested lifecycle cap at step 22. The catalogue retains all 18 Step 2 personas and all 116 Step 5 operations, then adds 9 proposed actor contexts and 52 proposed detailed steps. These include external providers and business subroles, not 27 newly deployed RBAC roles. The original source owners are retained. The additions remain proposals awaiting owner review.

## Two versions
mini/core contains 120 linked hiring journeys selected for coverage across six families and ten current outcomes, plus 100 gig applications from 20 requests. Application, event and job subsets retain their source identifiers and references. It is deliberately balanced for explanation and testing. Its rates must not estimate the full seed cohort. Mini job positions_filled retains the source job snapshot, which includes joins outside the mini sample.

seed/core contains the existing five v6 synthetic files, with matching SHA256 values, including 1,500,000 candidate-job journeys. This is 15 lakh, not 15 million and not 1.5 million submitted applications. The applied subset is 669,375. No database import or production capacity proof is claimed.

Each version has 27 workflow folders. A folder contains a manifest, guarded example cases, emitted step-example references and analytics. Mini has six cases per workflow. Seed has sixty cases per workflow. The cases exercise a generic envelope guard: valid input, cross-account, missing required input, blocked subject, duplicate and stale version. They do not execute the native workflow business transactions. Domain-specific rules have separate positive and refusal functions and recorded outcomes. Dictionary scalar examples do not form complete joined database rows.

seed/sets has smaller physical journey and gig files by job family. Other shared core files are referenced by the workflow manifests rather than duplicated. catalogue/field_examples.json supplies associated data elements and typed source examples for all 168 steps. Proposed fields are explicit staging examples.

## Rules and analytics
catalogue/rules.json covers job family, collar/branch, engagement, identity ownership, account scope, blocking, hiring order, duplicate/version handling, gig direction/window/assignment, external earnings, completed-own rating, currency, consent, sourcing approval, vacancies and denominator semantics. Fifty portable positive/refusal cases are in evidence/mini_seed_rule_tests.json. Analytics for all 54 sets distinguish example counts from business-stage KPIs. Version analytics use saved-file readback. Full native SQL, authorization, provider and load gates remain open.

## Files
The original dashboard views and steps 1–21 workbooks remain available. The three updated Step 22 workbooks retain original tabs and add the mini/seed catalogue, rules and results. Prior v6 scores remain visible as carried-forward ratings; this addendum has not received a new independent/human assessment.

To reproduce this split from the included seed/core files, run evidence/build_workflow_split.py with the original project layout available. The generation uses no database or network. Do not run the legacy v6 generator without its --generate-only option: its default mode targets the authoring layout. Source fingerprints and verification results are in evidence.
'''
 (OUT/'README.md').write_text(readme,encoding='utf-8')
 print(json.dumps({'actors':len(actors),'steps':len(steps),'sets':len(sets),'mini':core['mini']['stages'],'seed':core['seed']['stages'],'rule_tests':len(tests)},ensure_ascii=True),flush=True)

if __name__=='__main__':main()
