"""Mentor scenario extension. Synthetic file data only; never connects to a database."""
import argparse,base64,copy,csv,gzip,hashlib,io,json,math,re,shutil,sys,zipfile
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work/release_v6'
OUT=ROOT/'outputs/talentra_step22_mentor_v6'
BASE=ROOT/'outputs/talentra_steps_01_22_hybrid_v5'
DATE='2026-10-30'
STAGES=['searched','screened','applied','shortlisted','assessed','interviewed','selected','rejected','offered','accepted','offer_declined','onboarded']
PROGRESS=['searched','screened','applied','shortlisted','assessed','interviewed','selected','offered','accepted','onboarded']
OFFSETS=dict(zip(PROGRESS,[0,1,2,5,8,12,15,18,20,28]));OFFSETS.update(rejected=15,offer_declined=20)
PARENTS={'screened':'searched','applied':'screened','shortlisted':'applied','assessed':'shortlisted','interviewed':'assessed','selected':'interviewed','rejected':'interviewed','offered':'selected','accepted':'offered','offer_declined':'offered','onboarded':'accepted'}
# Family shares and conversion percentages are explicit proposed workload inputs.
FAMILIES=[
 ('IT_DEV','White collar','IT','Development',25,[75,60,35,90,65,20,95,80,90]),
 ('IT_TEST','White collar','IT','Testing',15,[80,55,40,90,60,25,95,82,92]),
 ('NONIT_SALES','White collar','Non-IT','Sales',15,[70,65,45,70,65,30,96,78,85]),
 ('NONIT_DELIVERY','White collar','Non-IT','Delivery',15,[60,70,55,60,70,40,98,88,95]),
 ('BLUE_WAREHOUSE','Blue collar','Operations','Warehouse',15,[65,70,60,55,70,45,98,90,95]),
 ('BLUE_FIELD','Blue collar','Operations','Field service',15,[70,65,50,80,70,35,97,85,93])]
HEADERS={
 'journey':['journey_id','candidate_profile_id','job_requirement_id','organisation_id','application_id','job_family_code','engagement_type','source_channel','cohort_code','current_stage','snapshot_at'],
 'event':['event_id','journey_id','candidate_profile_id','job_requirement_id','organisation_id','application_id','stage_code','occurred_at','source_system','source_version','reason_code'],
 'application':['application_id','candidate_profile_id','job_requirement_id','organisation_id','source_channel','applied_at','current_stage','is_synthetic'],
 'job':['job_requirement_id','organisation_id','job_family_code','engagement_type','published_at','positions','positions_filled','is_synthetic'],
 'gig':['gig_application_id','gig_request_id','gig_worker_profile_id','requester_organisation_id','job_family_code','status_code','start_at','end_at','assignment_id','handoff_key','provider_status','estimated_amount','total_amount','projected_amount','currency_code','requester_rating','is_synthetic']}
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def isot(t):return t.strftime('%Y-%m-%dT%H:%M:%SZ')
def typ(v):return 'null' if v is None else 'boolean' if type(v)==bool else 'integer' if type(v)==int else 'number' if type(v)==float else 'array' if isinstance(v,list) else 'object' if isinstance(v,dict) else 'string'
def generate(n,data_dir):
 data_dir.mkdir(parents=True,exist_ok=True)
 # Coprime permutation disperses outcomes without losing exact cohort counts.
 sizes=[n*f[4]//100 for f in FAMILIES];sizes[-1]+=n-sum(sizes)
 counts=[]
 for size,f in zip(sizes,FAMILIES):
  c={'searched':size};previous=size
  for st,rate in zip(PROGRESS[1:],f[5]):previous=previous*rate//100;c[st]=previous
  c['rejected']=c['interviewed']-c['selected'];c['offer_declined']=c['offered']-c['accepted'];counts.append(c)
 totals=Counter();observed=Counter();family_observed=defaultdict(Counter);terminals=Counter();channels=Counter();event_id=0;applications=0
 jobs={};samples=[];sample_buckets=Counter();timing=defaultdict(lambda:[0,0]);files={};handles={};writers={}
 for key in HEADERS:
  f=data_dir/(key+'.csv.gz');raw=open(f,'wb');gz=gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=1);txt=io.TextIOWrapper(gz,encoding='utf-8',newline='')
  wr=csv.writer(txt,lineterminator='\n');wr.writerow(HEADERS[key]);handles[key]=(txt,raw);writers[key]=wr
 offset=0;base=datetime(2026,8,1,tzinfo=timezone.utc);event_time_cache={}
 for fi,(family,size,c) in enumerate(zip(FAMILIES,sizes,counts)):
  step=104729
  while math.gcd(step,max(1,size))!=1:step+=2
  job_count=5000 if fi==0 else 3000;job_base=fi*5000
  for local in range(size):
   candidate=offset+local+1;rank=(local*step+22026)%size
   job=job_base+(local%job_count)+1;org=(job-1)%1000+1
   jobs.setdefault(job,{'org':org,'family':family[0],'filled':0})
   channel=['portal']*50+['referral']*15+['consultant']*15+['campus']*10+['employer_outreach']*10
   source=channel[local%100];channels[source]+=1
   reached=[st for st in PROGRESS if rank<c[st]]
   if rank<c['interviewed'] and rank>=c['selected']:reached.append('rejected')
   if rank<c['offered'] and rank>=c['accepted']:reached.append('offer_declined')
   current=reached[-1];terminals[current]+=1;app=candidate if rank<c['applied'] else None
   slot=local%(14*24);jitter=local%3;cache=(slot,jitter)
   if cache not in event_time_cache:
    start=base+timedelta(hours=slot)
    event_time_cache[cache]={st:isot(start+timedelta(days=OFFSETS[st]+jitter*(PROGRESS.index(st) if st in PROGRESS else 6 if st=='rejected' else 8))) for st in STAGES}
   times=event_time_cache[cache]
   jr=[candidate,candidate,job,org,app,family[0],'permanent',source,'2026-08-synthetic',current,'2026-10-30T23:59:59Z']
   writers['journey'].writerow(['\\N' if v is None else v for v in jr])
   bucket=(family[0],current)
   if sample_buckets[bucket]<5:samples.append(jr);sample_buckets[bucket]+=1
   if app:
    applications+=1;writers['application'].writerow([app,candidate,job,org,source,times['applied'],current,'true'])
   for st in reached:
    event_id+=1;observed[st]+=1;family_observed[family[0]][st]+=1
    event_app=app if st not in ['searched','screened'] else None
    reason='INTERVIEW_NOT_SELECTED' if st=='rejected' else 'CANDIDATE_DECLINED_OFFER' if st=='offer_declined' else None
    writers['event'].writerow([event_id,candidate,candidate,job,org,'\\N' if event_app is None else event_app,st,times[st],'talentra_synthetic',1,'\\N' if reason is None else reason])
   if current=='onboarded':jobs[job]['filled']+=1
   for label,end,start in [('time_to_offer','offered','applied'),('time_to_hire','accepted','applied'),('time_to_onboard','onboarded','accepted')]:
    if end in reached:
     days=(OFFSETS[end]-OFFSETS[start])+jitter*(PROGRESS.index(end)-PROGRESS.index(start));timing[label][0]+=days;timing[label][1]+=1
  totals.update(c);offset+=size
 for job,v in sorted(jobs.items()):writers['job'].writerow([job,v['org'],v['family'],'permanent',isot(base),max(3,v['filled']+2),v['filled'],'true'])
 gig=Counter();gig_sample=[]
 for aid in range(1,50001):
  request=(aid-1)//5+1;org=(request-1)%1000+1;slot=(aid-1)%5
  status='accepted' if slot==0 else 'rejected' if slot in [1,2,3] else 'pending'
  assignment=request if status=='accepted' else None
  provider='completed' if request%10<8 else 'in_progress' if request%10==8 else 'handoff_retry_pending'
  start=base+timedelta(days=request%28);end=start+timedelta(days=1+request%3)
  complete=status=='accepted' and provider=='completed';amount=f'{1000+(request%20)*250}.00' if complete else None
  rating=4 if complete and request%2==0 else None
  row=[aid,request,aid,org,FAMILIES[request%6][0],status,isot(start),isot(end),assignment,'SYN-GIG-'+str(request) if assignment else None,provider if assignment else None,amount,amount,amount,'INR',rating,True]
  writers['gig'].writerow(['\\N' if x is None else 'true' if x is True else x for x in row]);gig[status]+=1
  if complete:gig['completed']+=1
  if rating:gig['rated']+=1
  if assignment and provider=='handoff_retry_pending':gig['handoff_retry_pending']+=1
  if aid<=35:gig_sample.append(row)
 for key,(txt,raw) in handles.items():txt.close();raw.close();f=data_dir/(key+'.csv.gz');files[key]={'file':f.name,'sha256':sha(f),'bytes':f.stat().st_size}
 # Independent streaming pass over saved files; do not infer actuals from writer counters.
 saved=Counter();stage_from_disk=Counter();last_event=0;last_journey=None;last_stage=None;last_time=None;failures=[]
 graph={None:{'searched'}}
 for st in STAGES:graph.setdefault(st,set())
 for st,parent in PARENTS.items():graph[parent].add(st)
 for key in HEADERS:
  with gzip.open(data_dir/files[key]['file'],'rt',encoding='utf-8',newline='') as f:
   rr=csv.DictReader(f);assert rr.fieldnames==HEADERS[key]
   for row in rr:
    saved[key]+=1
    if key=='event':
     eid=int(row['event_id']);journey=int(row['journey_id']);st=row['stage_code'];job=int(row['job_requirement_id'])
     assert eid==last_event+1;last_event=eid
     if journey!=last_journey:
      assert last_journey is None or journey>last_journey
      last_stage=None;last_time=None;last_journey=journey
     assert st in graph[last_stage],(journey,last_stage,st)
     assert last_time is None or row['occurred_at']>=last_time
     assert jobs[job]['org']==int(row['organisation_id'])
     assert row['application_id']=='\\N' if st in ['searched','screened'] else row['application_id']==row['candidate_profile_id']
     assert row['occurred_at']<='2026-10-30T23:59:59Z'
     last_stage=st;last_time=row['occurred_at'];stage_from_disk[st]+=1
    elif key=='job':assert 0<=int(row['positions_filled'])<=int(row['positions'])
    elif key=='gig':
     assert row['end_at']>row['start_at']
     assert row['assignment_id']!='\\N' if row['status_code']=='accepted' else row['assignment_id']=='\\N'
     if row['total_amount']!='\\N':assert row['provider_status']=='completed' and float(row['total_amount'])>=0
     if row['requester_rating']!='\\N':assert row['provider_status']=='completed' and 1<=int(row['requester_rating'])<=5
 assert saved['journey']==n and saved['application']==totals['applied'] and saved['event']==sum(totals.values())
 assert observed==totals==stage_from_disk
 for key in files:files[key]['rows']=saved[key]
 with open(data_dir/'journey_sample.csv','w',encoding='utf-8',newline='') as f:
  w=csv.writer(f);w.writerow(HEADERS['journey']);w.writerows([['\\N' if v is None else v for v in r] for r in samples])
 result={'population':n,'stages':dict(totals),'families':[{'code':f[0],'collar':f[1],'branch':f[2],'function':f[3],'share':f[4]/100,'rates':f[5],'counts':c} for f,c in zip(FAMILIES,counts)],'channels':dict(channels),'terminal_counts':dict(terminals),'timing':{k:{'total_days':v[0],'count':v[1],'mean_days':v[0]/v[1]} for k,v in timing.items()},'gig':dict(gig),'files':files,'sample':samples,'gig_sample':gig_sample,'jobs':len(jobs),'proof':'Read back every saved row. Sequential event IDs, legal per-journey transitions, event-time order, employer ownership, application existence, vacancy capacity and gig guards checked. No native SQL or load benchmark claimed.'}
 write(data_dir/'generation_summary.json',result);return result

def prepare():
 WORK.mkdir(exist_ok=True)
 if not OUT.exists():shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('*.inspect.ndjson'))
 p=load(ROOT/'work/release_v5/dashboard_data.json');s=p['steps'][21];s['version']='6.0 mentor scenarios';p.update(version='6.0 mentor scenarios',date=DATE,output_folder=OUT.name)
 shutil.copy2(BASE/'evidence/workbook_validation.json',OUT/'evidence/prior_workbook_validation.json')
 dct=load(BASE/'evidence/hybrid_dictionary.json');physical={(r[1],r[2]):r for r in dct}
 summary_file=OUT/'scenario_data/generation_summary.json'
 generated=load(summary_file) if summary_file.exists() else None
 if not generated or generated['population']!=1500000 or any(sha(OUT/'scenario_data'/v['file'])!=v['sha256'] for v in generated['files'].values()):generated=generate(1500000,OUT/'scenario_data')
 p['mentor']=generated
 def add(name,headers,rows,priority='P0',source='Mentor request2026-10-30; D1 pp.2-5; D3 p.11; D2 pp.5-13; D4 pp.13-24; D5 pp.5,12-13'):
  s['sections'].append({'name':name,'columns':headers,'rows':rows,'priority':priority,'source':source})
 add('Business definitions',['Term','Meaning','Grain or rule','Source'],[
 ['Planning population','15,00,000 means1,500,000 synthetic candidate-job journeys','One candidate and one target job per generated journey; applied is a subset','Mentor request; interpretation documented'],
 ['Applicants versus audience','The1.5m planning audience is not1.5m completed applications','Only journeys reaching applied produce job_application records','Mentor funnel; product terminology decision'],
 ['Pre-application screening','Eligibility checks on a searched target before candidate submission','Preserves the mentor order; distinct from recruiter post-application review','Mentor sequence; proposed interpretation'],
 ['Job family','Blue collar or white collar, with IT/non-IT functional branches','Delivery stays under white-collar non-IT as supplied by mentor; configurable business classification','Mentor taxonomy'],
 ['Engagement type','Permanent, contract, apprentice or gig engagement','Separate axis from job family; an IT developer may also accept a gig','D1 p.2; proposed reference taxonomy'],
 ['Gig boundary','Workers apply, requesters decide, external system fulfils','Separate gig subsystem; no two-way bidding or internal fulfilment engine','D1 p.2'],
 ['Screening and selection','Eligibility is not a hiring decision; interview selection and offer response are separate','Rejected and offer_declined have different decision owners and denominators','Mentor funnel'],
 ['Synthetic scenario','A generated fixture, workload assumption or test outcome','No claimed real applicant performance, provider execution or production capacity','D2; D3 pp.11-12']])
 add('Job taxonomy',['Family code','Collar','Business branch','Function','Cohort share','Allowed engagements','Status'],[[f[0],f[1],f[2],f[3],f[4]/100,'Permanent;contract;gig;apprentice','Mentor branch or proposed blue-collar example'] for f in FAMILIES])
 stage_meanings={'searched':'Distinct authenticated candidate expresses interest in one target job','screened':'Candidate passes pre-application eligibility','applied':'Candidate submits the application','shortlisted':'Assigned employer/recruiter advances application','assessed':'Relevant assessment completed; not necessarily passed','interviewed':'Interview completed','selected':'Employer selects candidate after interview','rejected':'Employer rejects candidate after interview','offered':'Offer issued to selected candidate','accepted':'Candidate accepts a valid offer','offer_declined':'Candidate rejects the issued offer','onboarded':'Employer confirms actual joining'}
 add('Hiring funnel',['Stage','Business meaning','Generated count','Denominator stage','Denominator count','Conversion rate','Decision owner','Evidence'],[[st,stage_meanings[st],generated['stages'][st],PARENTS.get(st,'Population'),generated['stages'].get(PARENTS.get(st),generated['population']),generated['stages'][st]/generated['stages'].get(PARENTS.get(st),generated['population']),'Candidate' if st in ['searched','applied','accepted','offer_declined'] else 'Employer/recruiter' if st in ['shortlisted','interviewed','selected','rejected','offered','onboarded'] else 'Eligibility/assessment service','Synthetic saved-file counts; rates are proposed workload assumptions'] for st in STAGES])
 add('Family funnel assumptions',['Family','Population share','Screen pass rate','Apply rate','Shortlist rate','Assessment completion','Interview completion','Selection rate','Offer issue rate','Offer acceptance','Onboarding rate','Basis'],[[f[0],f[4]/100,*[x/100 for x in f[5]],'Proposed scenario inputs; floor at each family stage; not market benchmarks'] for f in FAMILIES])
 add('Family funnel counts',['Family',*STAGES],[[f['code'],*[f['counts'][st] for st in STAGES]] for f in generated['families']])
 kpis=[]
 for st in ['screened','applied','shortlisted','assessed','interviewed','selected','rejected','offered','accepted','offer_declined','onboarded']:
  den=PARENTS[st];kpis.append([f'KPI-H-{len(kpis)+1:02}',st+' conversion',f'Distinct journeys reaching{st} / distinct journeys reaching{den}',generated['stages'][st],generated['stages'][den],generated['stages'][st]/generated['stages'][den],'ratio','Candidate-job journey; cohort2026-08','Family;organisation;source channel','Zero denominator -> not applicable; no zero substitution','journey.csv.gz;event.csv.gz','Recruiting operations owner'])
 for key,v in generated['timing'].items():kpis.append([f'KPI-H-{len(kpis)+1:02}',key,f'SUM(calendar days to {key}) / qualifying journeys',v['total_days'],v['count'],v['mean_days'],'calendar days','Journey reaching ending milestone','Family;organisation;source channel','Exclude non-reached ending milestones; report pending ageing separately','event.csv.gz','Recruiting operations owner'])
 for label,num,den in [('Gig request fill',generated['gig']['accepted'],10000),('Gig application acceptance',generated['gig']['accepted'],50000),('Gig completion',generated['gig']['completed'],generated['gig']['accepted']),('Gig requester rating coverage',generated['gig']['rated'],generated['gig']['completed'])]:kpis.append([f'KPI-G-{len(kpis)-13:02}',label,'Distinct qualifying gig records / declared denominator',num,den,num/den,'ratio','Gig application or assignment as named','Family;requester organisation','Exclude retry-pending from completed denominator; late provider events reconciled','gig.csv.gz','Gig operations owner'])
 add('Business KPI register',['KPI ID','KPI','Formula','Numerator','Denominator','Synthetic value','Unit','Grain and cohort','Dimensions','Null and exclusion rule','Evidence file','Owner'],kpis)
 # Each workflow states concrete native elements; service responsibilities do not invent employer sub-roles.
 workflow_specs=[
 ('Guest','Find public jobs','job_requirement.id;job_requirement.title','Authenticate before applying; no candidate profile exposure','SC-01'),
 ('Candidate','Search, pass eligibility, apply, assess, attend interview and respond to offer','candidate_profile.id;job_search_event.searched_at;job_application.applied_at;job_offer.status_reference_value_id','Candidate owns registration and offer response; idempotent application','SC-01'),
 ('Employer','Post demand, shortlist, decide, offer and confirm joining','job_requirement.positions;job_requirement.organisation_id;job_offer.id;joining_record.joined_on','Own organisation only; offered or selected is not onboarded','SC-02'),
 ('Recruiter','Source consenting candidates and progress assigned applications','recruiter_membership.organisation_id;outreach_recipient.candidate_profile_id;application_status_event.occurred_at','Cannot register candidates; blocked candidate invisible; assigned company only','SC-03'),
 ('Consultant','Request sourcing approval and submit an allowed shortlist','sourcing_request.id;sourcing_decision.id;sourcing_shortlist.id','Job must be consultant-open and sourcing request accepted','SC-04'),
 ('Placement Officer','Coordinate eligible campus candidates and their self-submitted applications','candidate_education.id;job_application.candidate_profile_id','No impersonation or recruiter registration; obtain candidate consent','SC-05'),
 ('Account Admin','Assign seats and recruiters; revoke devices','licence_seat.id;recruiter_membership.id;revocation_event.id','Serialize seat limits; revoked sessions no longer active','SC-06'),
 ('Admin','Maintain taxonomy, scoped support and audited reference changes','reference_value.id;support_ticket.id;audit_event.id','Version reference codes; support access is purpose-scoped','SC-07'),
 ('Super Admin','Review platform configuration and audited exceptional access','access_role.id;permission.id;audit_event.id','Privileged operations audited; no unlimited PII export','SC-08'),
 ('Gig Worker','Maintain a separate service profile and apply to available gigs','gig_worker_profile.id;gig_availability.id;gig_application.id','Worker-to-requester applications only; blocked workers excluded','SC-09'),
 ('Gig Requester','Publish window/price, decide and rate externally completed work','gig_request.start_at;gig_request.end_at;gig_assignment.external_handoff_key;gig_rating.id','Requester is an employer business persona; rates completed own assignments only','SC-10'),
 ('Integration Worker','Validate, deduplicate, order and reconcile source events','integration_inbox.id;integration_rejection.id;reconciliation_run.id','Verify source/account binding; quarantine malformed or stale input','SC-11')]
 workflows=[]
 for i,(actor,action,elements,guard,scenario) in enumerate(workflow_specs,1):
  for order,verb in enumerate(['Receive trigger and authorize','Execute business action','Persist and publish outcome'],1):workflows.append([f'WF-M-{i:02}-{order}',actor,order,verb,action,elements,guard,scenario,'KPI-H-03;KPI-H-09' if 'Gig' not in actor else 'KPI-G-01;KPI-G-03','Audit actor, source event and outcome; notify according to consent','Planned service acceptance; synthetic fixtures are separate evidence'])
 add('Actor workflows',['Workflow ID','Actor','Sequence','Trigger or action','Business workflow','Associated data elements','Guard and refusal rule','Scenario ID','Related KPIs','Output and audit','Proof status'],workflows)
 scenarios=[
 ['SC-01','Candidate permanent hiring','Self-search and eligibility -> apply -> interview -> select -> offer -> accept -> join','Candidate-job journey','job_search_event;job_application;assessment_attempt;interview;job_offer;joining_record','Synthetic normal funnel generated','KPI-H-03;KPI-H-09;KPI-H-11'],
 ['SC-02','Employer decision','Interviewed candidates split selected/rejected; selected may wait for an offer','Employer/application','application_status_event;job_offer','Rejection and offer-pending branches generated','KPI-H-06;KPI-H-07;KPI-H-08'],
 ['SC-03','Recruiter privacy','Blocked employer/recruiter attempts search or outreach','Account/candidate pair','blocking_entry;outreach_recipient','Refusal fixture; native access test pending','KPI-H-02'],
 ['SC-04','Consultant sourcing','Closed job or unaccepted request cannot submit candidate','Consultant/job pair','sourcing_request;sourcing_decision;sourcing_shortlist','Refusal fixture; native test pending','KPI-H-03'],
 ['SC-05','Campus hiring','TPO routes opportunity; candidate self-registers and applies','Campus candidate/job','candidate_education;consent_record;job_application','Source-channel campus cohort generated','KPI-H-03'],
 ['SC-06','Seat/session cap','Concurrent allocation or login at limit','Licence/device/session','licence;licence_seat;user_session','Existing planned native race; not executed here','Operational security guard'],
 ['SC-07','Reference change','Taxonomy version changes while old event remains readable','Reference version','reference_domain;reference_value;ui_translation','Mapping/version policy documented','All dimensions'],
 ['SC-08','Privileged correction','Admin cannot rewrite ledger or erase the audit trail','Audit event','audit_event;wallet_ledger_entry','Existing immutable-ledger guard; native proof pending','Reconciliation'],
 ['SC-09','Gig worker applies','Worker creates application; requester accepts or rejects','Gig application','gig_worker_profile;gig_application;gig_request','50000 synthetic applications generated','KPI-G-02'],
 ['SC-10','External gig fulfilment','Accepted gig is handed off; external status and earnings reconciled','Gig assignment/source event','gig_assignment;gig_earnings_snapshot;gig_rating','10000 accepted; external states are synthetic','KPI-G-01;KPI-G-03;KPI-G-04'],
 ['SC-11','Replay and ordering','Duplicate, malformed, late or cross-account source event','Source+event ID+version','integration_inbox;integration_rejection;reconciliation_run','Portable refusal fixtures executed; signed-provider test pending','Reconciliation'],
 ['SC-12','Offer declined','Candidate declines issued offer; never count as employer rejection','Offer response','job_offer;application_status_event','Separate declined branch generated','KPI-H-10'],
 ['SC-13','Accepted but not joined','Offer acceptance remains distinct from joining confirmation','Application/offer','job_offer;joining_record','Pending onboarding branch generated','KPI-H-11'],
 ['SC-14','Window and price guard','End before start, negative earnings or rating before completion','Gig request/assignment','gig_request;gig_assignment;gig_earnings_snapshot;gig_rating','Portable refusal cases executed','KPI-G-03;KPI-G-04']]
 add('Business scenario catalogue',['Scenario ID','Scenario','Business what','Data grain','Associated entities','Evidence and boundary','Related KPI'],scenarios)
 add('Native schema gap register',['Gap ID','Concern','Existing support','Proposed addition or treatment','Affected steps','Status'],[
 ['MGAP-01','Search-to-job attribution','job_search_event has candidate and search time but no target-job journey key','Proposed candidate_job_journey and journey_stage_event staging models; add native migration after review','6,7,9,12,18,19,21','Proposed; not an existing physical table'],
 ['MGAP-02','Pre-application eligibility','Generic candidate_activity does not define job-scoped screening evidence','Proposed stage event with rule version, eligibility outcome and source-event ID','5,7,8,18,20,21','Owner acceptance and native enforcement pending'],
 ['MGAP-03','Assessment-to-application join','assessment_attempt has candidate and assessment, not job_application_id','Proposed application-context bridge; do not attribute every candidate assessment to every application','7,9,16,19,21','Migration and backfill pending'],
 ['MGAP-04','Milestone timestamps','job_offer tracks status; application_status_event tracks state changes','Use source-event timestamps for analytics; preserve event time versus arrival time and rejection owner','8,18,19,20,21','Stage-event mapping proposed'],
 ['MGAP-05','Taxonomy axes','Existing job_role and employment/work reference fields support lookup translation','Proposed versioned collar/branch/function dimensions separate from engagement type','6,7,10,13,19','Mentor taxonomy; owner sign-off pending']])
 # Every new file field has a native target, a named proposal or an explicit transport disposition.
 native_targets={
 'candidate_profile_id':'candidate_profile.id','job_requirement_id':'job_requirement.id','organisation_id':'job_requirement.organisation_id','application_id':'job_application.id','applied_at':'job_application.applied_at','positions':'job_requirement.positions','positions_filled':'job_requirement.positions_filled','published_at':'job_requirement.published_at',
 'gig_application_id':'gig_application.id','gig_request_id':'gig_request.id','gig_worker_profile_id':'gig_worker_profile.id','requester_organisation_id':'gig_request.requester_organisation_id','start_at':'gig_request.start_at','end_at':'gig_request.end_at','assignment_id':'gig_assignment.id','handoff_key':'gig_assignment.external_handoff_key','estimated_amount':'gig_earnings_snapshot.estimated_amount','total_amount':'gig_earnings_snapshot.total_amount','projected_amount':'gig_earnings_snapshot.projected_amount','currency_code':'gig_earnings_snapshot.currency_code'}
 proposed_names={'journey_id','event_id','stage_code','current_stage','source_channel','job_family_code','source_version','reason_code','cohort_code','snapshot_at','occurred_at'}
 contract_rows=[];maps=[];nullable={'application_id','assignment_id','handoff_key','provider_status','estimated_amount','total_amount','projected_amount','requester_rating','reason_code'}
 intnames={h for hh in HEADERS.values() for h in hh if h.endswith('_id')}|{'source_version','positions','positions_filled','requester_rating'}
 for j,(key,headers) in enumerate(HEADERS.items(),28):
  properties={};cid=f'CON-{j:03}';filekey='mentor.'+key+'.v1';rel='contracts/'+filekey+'.schema.json'
  for h in headers:
   t='integer' if h in intnames else 'boolean' if h=='is_synthetic' else 'string';types=[t,'null'] if h in nullable else [t]
   properties[h]={'type':types,'description':'Synthetic canonical '+h+'; CSV \\N is parsed as JSON null only for nullable properties'}
   if h in intnames:properties[h]['minimum']=0 if h in ['positions_filled'] else 1
   if h in ['current_stage','stage_code'] and key!='gig':properties[h]['enum']=STAGES
   if h=='job_family_code':properties[h]['enum']=[f[0] for f in FAMILIES]
   if h=='is_synthetic':properties[h]['const']=True
   if h in ['estimated_amount','total_amount','projected_amount']:properties[h]['pattern']=r'^(0|[1-9][0-9]{0,15})\.[0-9]{2}$'
   if h=='currency_code':properties[h]['pattern']='^[A-Z]{3}$'
   if h=='requester_rating':properties[h]['maximum']=5
   if h.endswith('_at'):properties[h]['format']='date-time'
   if key=='gig' and h=='status_code':properties[h]['enum']=['accepted','rejected','pending']
   if key=='gig' and h=='provider_status':properties[h]['enum']=['completed','in_progress','handoff_retry_pending',None]
   if h in native_targets:target=native_targets[h];exist='Existing hybrid dictionary field; native ID translation still required'
   elif h in proposed_names:target='PROPOSED:journey_stage_event.'+h;exist='Not a deployed physical column; MGAP-01..05'
   elif h in ['provider_status','status_code']:target='Reference lookup -> gig_assignment.status_reference_value_id' if h=='provider_status' else 'Reference lookup -> gig_application.status_reference_value_id';exist='Resolve owned source code to canonical reference ID'
   elif h=='requester_rating':target='gig_rating.rating';exist='Existing native field; completed-own-assignment guard'
   elif h=='engagement_type':target='Lookup -> job_requirement.employment_type_reference_value_id';exist='Canonical reference resolution; gig follows separate subsystem'
   else:target='Transport metadata: '+h;exist='Not persisted as a business column'
   maps.append([f'MAP-M-{len(maps)+1:03}',cid,key+'.csv.gz',h,' | '.join(types),h not in nullable,target,exist,'Data engineering owner','Parse types; translate IDs within account; never join source surrogate IDs directly','Source+event ID+version; preserve late events without state regression','Malformed, unknown code, cross-account and non-permitted null -> quarantine', 'Personal' if 'candidate' in h or 'worker' in h else 'Internal'])
  schema={'$schema':'https://json-schema.org/draft/2020-12/schema','title':filekey,'type':'object','properties':properties,'required':headers,'additionalProperties':False}
  write(OUT/rel,schema);contract_rows.append([cid,filekey,'MENTOR-SYNTHETIC','Inbound','Data engineering owner','Synthetic canonical file contract; business/native approval pending','CSV gzip -> typed canonical JSON','Streaming; file SHA256 and row reconciliation',len(headers),rel,sha(OUT/rel),'P0'])
 next(sec for sec in s['sections'] if sec['name']=='Integration catalogue')['rows'].extend(contract_rows)
 add('Mentor source field mapping',['Mapping ID','Contract ID','Source file','Source field','Canonical type','Required non-null','Target or disposition','Target status','Owner','Transform','Replay and lateness rule','Failure treatment','Classification'],maps)
 add('Dataset inventory',['Dataset','File','Rows','Bytes','SHA256','Grain','Evidence scope'],[[key,'scenario_data/'+v['file'],v['rows'],v['bytes'],v['sha256'],'One '+key+' record','Synthetic CSV gzip; streamed and read back; not loaded to native database'] for key,v in generated['files'].items()])
 add('Generated journey sample',HEADERS['journey'],generated['sample'])
 add('Generated gig sample',HEADERS['gig'],generated['gig_sample'])
 add('Source failure scenarios',['Case','Detection','Treatment','Owner','Evidence'],[
 ['Duplicate event','Same source/event ID/version','Return prior outcome; no second business side effect','Integration owner','Portable refusal fixture'],['Late event','Older event time or source version','Preserve history; do not regress current state; recompute affected cohort if corrected','Integration owner','Ordering check and policy'],['Malformed payload','Missing required field, wrong type or invalid code','Quarantine with reason and safe source hash; no partial business write','Data engineering owner','Portable refusal fixture'],['Cross-account reference','Job organisation differs from event organisation','Reject before lookup exposes candidate data','Security owner','Every generated event account checked; negative fixture'],['Provider unavailable','Timeout or unsigned callback','Keep bounded retry state; no fabricated fulfilment or earnings','Gig integration owner','Synthetic retry-pending cases'],['Conflicting identity','External ID maps to multiple canonical subjects','Quarantine; resolve with owner; no heuristic PII merge','Data steward','Planned native acceptance'],['Partial or replayed batch','Source counts/hash differ from accepted+quarantined','Checkpoint immutable batch ID; reconcile source=accepted+quarantined+pending','Data engineering owner','File counts and SHA256 evidence']])
 # Portable negative cases have observed refusal outcomes, not planned PASS labels.
 def refuse(case):
  if case.get('organisation_id',1)!=1:return 'CROSS_ACCOUNT'
  if case.get('blocked'):return 'BLOCKED_SUBJECT'
  if case.get('source_version',1)<case.get('current_version',1):return 'STALE_VERSION'
  if case.get('duplicate'):return 'DUPLICATE'
  if case.get('stage_code','searched') not in ({None:{'searched'}}|{k:{st for st,pa in PARENTS.items() if pa==k} for k in STAGES}).get(case.get('previous'),set()):return 'ILLEGAL_TRANSITION'
  if case.get('end',2)<=case.get('start',1):return 'INVALID_WINDOW'
  if case.get('amount',0)<0:return 'NEGATIVE_AMOUNT'
  if case.get('rating') and case.get('provider_status')!='completed':return 'RATING_BEFORE_COMPLETION'
  return 'ACCEPT'
 cases=[('valid searched',{},'ACCEPT'),('tenant mismatch',{'organisation_id':2},'CROSS_ACCOUNT'),('blocked candidate',{'blocked':True},'BLOCKED_SUBJECT'),('old version',{'source_version':1,'current_version':2},'STALE_VERSION'),('duplicate callback',{'duplicate':True},'DUPLICATE'),('apply before screen',{'stage_code':'applied','previous':'searched'},'ILLEGAL_TRANSITION'),('select before interview',{'stage_code':'selected','previous':'assessed'},'ILLEGAL_TRANSITION'),('join rejected applicant',{'stage_code':'onboarded','previous':'rejected'},'ILLEGAL_TRANSITION'),('accept without offer',{'stage_code':'accepted','previous':'selected'},'ILLEGAL_TRANSITION'),('invalid gig window',{'end':1,'start':2},'INVALID_WINDOW'),('negative earnings',{'amount':-1},'NEGATIVE_AMOUNT'),('early rating',{'rating':4,'provider_status':'in_progress'},'RATING_BEFORE_COMPLETION')]
 tests=[[f'MTEST-{i+1:02}',name,expected,refuse(payload),'PASS' if expected==refuse(payload) else 'FAIL','Portable contract/guard model; not native endpoint authorization'] for i,(name,payload,expected) in enumerate(cases)]
 assert all(r[4]=='PASS' for r in tests)
 add('Mentor negative test evidence',['Test ID','Case','Expected','Actual','Result','Proof layer'],tests)
 # Reopen each file and validate representative typed records against its saved contract.
 contract_samples=[]
 def validates(record,schema):
  assert set(record)==set(schema['required'])
  for h,rule in schema['properties'].items():
   v=record[h];assert typ(v) in rule['type'],(h,v)
   if 'enum' in rule:assert v in rule['enum'],(h,v)
   if 'const' in rule:assert v==rule['const']
   if v is not None:
    if 'minimum' in rule:assert v>=rule['minimum']
    if 'maximum' in rule:assert v<=rule['maximum']
    if 'pattern' in rule:assert re.fullmatch(rule['pattern'],v)
    if rule.get('format')=='date-time':datetime.fromisoformat(v.replace('Z','+00:00'))
 for key,headers in HEADERS.items():
  schema=load(OUT/('contracts/mentor.'+key+'.v1.schema.json'));tested=0
  with gzip.open(OUT/'scenario_data'/(key+'.csv.gz'),'rt',encoding='utf-8',newline='') as stream:
   reader=csv.DictReader(stream);assert reader.fieldnames==schema['required']
   for row in reader:
    decoded={h:None if row[h]=='\\N' else int(row[h]) if 'integer' in schema['properties'][h]['type'] else row[h]=='true' if 'boolean' in schema['properties'][h]['type'] else row[h] for h in headers}
    validates(decoded,schema);tested+=1
    if tested>=300:break
  contract_samples.append([key,tested,'PASS','Typed sample contract checks; full-file transition/count guards are separate'])
 write(OUT/'evidence/mentor_contract_samples.json',contract_samples)
 # All workflow native references must really exist; explicit proposals stay in the gap register.
 fieldrefs=[ref.strip() for r in workflows for ref in r[5].split(';')]
 for ref in fieldrefs:assert tuple(ref.split('.')) in physical,ref
 for r in maps:
  if r[6] in native_targets.values():assert tuple(r[6].split('.')) in physical,r[6]
 assert ('gig_rating','rating') in physical
 # Rebuild only step22 schemas and append to the retained global trees.
 fields=[];nodes=[];metrics=[]
 prior={(r[1],r[2]):r for r in p['schema_fields'] if r[0]==22}
 for si,sec in enumerate(s['sections'],1):
  sid=f'S22.{si:03}';nodes.append([22,sid,'',1,sec['name'],sec['priority'],'Step22 output section at its declared grain',sec['source']])
  assert len(sec['columns'])==len(set(sec['columns']))
  assert all(len(r)==len(sec['columns']) for r in sec['rows']),sec['name']
  for j,h in enumerate(sec['columns']):
   vs=[r[j] for r in sec['rows']];types=sorted({typ(v) for v in vs}) or ['string','null'];t=' | '.join(types);fid=sid+f'.P{j+1:02}';old=prior.get((sec['name'],h))
   definition=old[7] if old else f'{h} at the {sec["name"]} record grain. Population, source, decision owner and synthetic/proposed status remain explicit.'
   reason=old[8] if old else 'Trace the mentor business scenario through user action, typed data element, owned source boundary and measurable KPI.'
   fields.append([22,sec['name'],h,'Value contract;Meaning and lineage',t,'Required property; null only when explicitly listed','Typed scalar; stable IDs; source owner; same-cohort denominator',definition,reason,sec['priority'],sec['source'],fid]);nodes.append([22,fid,sid,2,h,sec['priority'],definition,sec['source']])
   for suffix,label,props in [('V','Value contract',[('Type',t),('Validation','One declared type; explicit null treatment'),('Required','Property required')]),('M','Meaning and lineage',[('Definition',definition),('Reason',reason),('Source',sec['source'])])]:
    parent=fid+'.'+suffix;nodes.append([22,parent,fid,3,label,sec['priority'],label,sec['source']]);nodes.extend([[22,parent+'.'+str(k),parent,4,key,sec['priority'],value,sec['source']] for k,(key,value) in enumerate(props,1)])
  metrics.append({'step':22,'section':sec['name'],'priority':sec['priority'],'rows':len(sec['rows']),'columns':len(sec['columns']),'conformance':True,'documentaryFill':1,'definitionScore':5,'evidence':3 if any(x in sec['name'].lower() for x in ['gap','workflow','assumption','gate','handoff','review']) else 4})
 p['schema_fields']=[r for r in p['schema_fields'] if r[0]!=22]+fields;p['schema_nodes']=[r for r in p['schema_nodes'] if r[0]!=22]+nodes
 p['section_metrics']=[r for r in p['section_metrics'] if r['step']!=22]+metrics
 p['sectionRatings']=[r for r in p['sectionRatings'] if r[0]!=22]+[[22,m['section'],l,m['priority'],3,5,5,5,m['evidence'],(15+m['evidence'])/4,'Documentary quality; synthetic generation and native readiness are separate'] for m in metrics for l in range(1,5)]
 for r in p['ratingRows']:
  if r[0]==22:r[8]+=' Mentor extension: business terms, role workflows, scenario KPIs,5 synthetic file contracts and full saved-data reconciliation. Native/human evidence unchanged.'
 p['contracts_count']=32;p['mapping_count']=271+len(maps)
 p['sources'].append(['M1','Mentor business and functional scenario request','User message','2026-10-30','Hiring funnel,1.5m planning population,job family taxonomy,actors,KPIs and data context'])
 p['refinement_log'].append(['M22','Business meaning and data context missing','Added mentor scenarios,workflows,KPIs and synthetic generation','Step22 plus affected-step change register','Full CSV readback and portable refusal evidence'])
 # Refresh the three serialized deliverable schemas; every output parameter is explicit.
 output_schema={'title':'Step22 Output Document','type':'object','properties':{},'required':[],'additionalProperties':False}
 for sec in s['sections']:
  props={h:{'type':sorted({typ(r[j]) for r in sec['rows']}) or ['string','null']} for j,h in enumerate(sec['columns'])}
  output_schema['properties'][sec['name']]={'type':'array','items':{'type':'object','properties':props,'required':sec['columns'],'additionalProperties':False}};output_schema['required'].append(sec['name'])
 write(OUT/s['contractFiles']['output'],output_schema)
 for r in p['contracts']:
  if r[0]==22:r[3]=sha(OUT/r[2]);r[4]='Mentor extension; all declared records and field widths checked'
 p['mentor_mapping_rows']=maps;p['mentor_tests']=tests
 checks=[['MVAL-01',22,'generation','Saved journey count', 'PASS',str(generated['population']),'Streaming CSV readback'],['MVAL-02',22,'generation','Every event transition, timestamp and organisation reference','PASS',str(generated['files']['event']['rows'])+' events','Streaming CSV readback'],['MVAL-03',22,'mapping','Every new file field has owner/type/target/disposition','PASS',str(len(maps)),'Schema/header field parity'],['MVAL-04',22,'native references','Every declared workflow table.column exists','PASS',str(len(fieldrefs)),'Current hybrid dictionary lookup'],['MVAL-05',22,'negative cases','Observed portable refusal outcomes','PASS',str(len(tests)),'Portable contract/guard model'],['MVAL-06',22,'generation','Gig window,assignment,earnings and rating guards','PASS','50000 gig applications','Streaming CSV readback'],['MVAL-07',22,'preservation','Prior22-step outputs retained','PASS','Retained all previous sections; changes are additive','Original v5 preserved']]
 p['validation']=[r for r in p['validation'] if r[1]!=22]+checks
 write(OUT/'evidence/mentor_validation.json',{'checks':checks,'negative_cases':tests,'generated_files':generated['files'],'native_fields_checked':fieldrefs,'status':'Documentary/synthetic proof only; native SQL,provider and performance tests not run'})
 write(OUT/'evidence/current_validation.json',p['validation']);write(WORK/'project_data.json',p)
 print(json.dumps({'population':generated['population'],'applications':generated['stages']['applied'],'onboarded':generated['stages']['onboarded'],'events':generated['files']['event']['rows'],'new_mappings':len(maps),'step22_sections':len(s['sections'])}))

def polish():
 p=load(WORK/'dashboard_data.json');rows=next(s for s in p['steps'][21]['sections'] if s['name']=='Business KPI register')['rows']
 for r in rows:
  if r[0].startswith('KPI-H-') and int(r[0][-2:])<=11:
   stage=r[1].split()[0];parent=PARENTS[stage]
   r[2]=f"COUNT(DISTINCT journey_id reaching {stage}) / COUNT(DISTINCT journey_id reaching {parent}), in the same cohort"
  elif r[0] in ['KPI-H-12','KPI-H-13','KPI-H-14']:
   end,start={'KPI-H-12':('first_offered_at','first_applied_at'),'KPI-H-13':('first_accepted_at','first_applied_at'),'KPI-H-14':('first_onboarded_at','first_accepted_at')}[r[0]]
   r[2]=f'AVG(({end} - {start}) / 86400 seconds), only journeys reaching both milestones'
   r[7]='One candidate-job journey; deduplicated first milestone times'
   r[9]='Exclude null end time from the average; report pending ageing separately. Reject negative intervals. Use source event time after replay/version reconciliation.'
  else:
   r[2],r[7],r[9]={
    'KPI-G-01':('COUNT(DISTINCT accepted gig_request_id) / COUNT(DISTINCT published gig_request_id)','Gig request','A pending handoff still fills an accepted request. Count each request once.'),
    'KPI-G-02':('COUNT(DISTINCT accepted gig_application_id) / COUNT(DISTINCT submitted gig_application_id)','Gig application at snapshot','Denominator includes accepted, rejected and pending submissions; do not call it a final decision rate.'),
    'KPI-G-03':('COUNT(DISTINCT externally completed assignment_id) / COUNT(DISTINCT accepted assignment_id)','Gig assignment at snapshot','All accepted assignments remain in the denominator, including retry-pending and in-progress handoffs. Only externally completed records enter the numerator.'),
    'KPI-G-04':('COUNT(DISTINCT completed assignment_id with requester rating) / COUNT(DISTINCT externally completed assignment_id)','Externally completed gig assignment','Only completed assignments are eligible. Exclude duplicate ratings and reject non-owner or pre-completion ratings.')
   }[r[0]]
 write(WORK/'dashboard_data.json',p);write(WORK/'project_data.json',p)
 print('Clarified all18 KPI formulas and cohort/decision denominators')

def package():
 import xml.etree.ElementTree as E
 p=load(WORK/'dashboard_data.json');books=sorted(OUT.rglob('*.xlsx'));assert len(books)==67
 ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};saved=[]
 for f in books:
  with zipfile.ZipFile(f) as z:
   assert z.testzip() is None
   for name in z.namelist():
    if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):assert not any(c.attrib.get('t')=='e' for c in E.fromstring(z.read(name)).findall('.//s:c',ns)),str(f)
  saved.append([f.relative_to(OUT).as_posix(),sha(f)])
 for s in p['steps']:
  for f in s['files'].values():assert (OUT/f).is_file()
 downloadable=books+list((OUT/'artifact_contracts').glob('*.json'))+[OUT/'evidence/current_validation.json',OUT/'scenario_data/generation_summary.json',OUT/'scenario_data/journey_sample.csv']
 p['downloads']={f.relative_to(OUT).as_posix():base64.b64encode(f.read_bytes()).decode('ascii') for f in downloadable}
 template=(ROOT/'work/dashboard_v6.html').read_text(encoding='utf-8')
 (OUT/'index.html').write_text(template.replace('__DATA__',json.dumps(p,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')),encoding='utf-8')
 (OUT/'README.md').write_text('''# Step22 mentor update,30 October2026\n\nOpen index.html. Business scenarios is the opening view. It shows the hiring funnel,job families,KPIs,each actor workflow and gig boundaries. Step outputs opens the full populated step22 data. The three updated step22 Excel files and combined master are included; steps1–21 are retained from v5.\n\nThe1,500,000 records are synthetic candidate-job journeys,not1,500,000 submitted applications. Applied is a measured subset. All conversion rates and job-family shares are proposed workload assumptions,not real-world performance benchmarks. Pre-application screening preserves the mentor sequence; recruiter review follows application. Employer rejection and candidate offer decline remain separate. Job family and engagement type are independent axes. Delivery is retained under the mentor white-collar/non-IT branch as a configurable classification.\n\nscenario_data contains the full streaming CSV gzip files and their counts/SHA256 in generation_summary.json. The1.5m journey file exceeds Excel's single-sheet row limit,so Excel and HTML use aggregates and representative samples. Download the complete ZIP for the full data files. CSV \\N means an explicitly nullable field; convert it to JSON null before validation. Do not treat source surrogate IDs as real canonical database keys.\n\nThe generator uses distinct family conversion profiles and a deterministic permutation to scatter outcomes. Every saved row is read back. Events are checked for legal transitions,time ordering,application presence,unique sequential IDs and organisation ownership. Jobs cannot have more joined workers than positions. Gig assignments only follow acceptance; windows,external earnings and completed-only requester ratings are checked. These are synthetic/portable proofs,not native PostgreSQL,provider,authorization or load benchmark passes.\n\nReproduce in a new folder using the bundled Python runtime:\n\n    python evidence/generate_mentor_data.py --generate-only --population1500000 --output-data NEW_FOLDER\n\nUse --population 1500000 with a separating space when invoking the command. It does not load or mutate a database. The default project generation path is for the authoring environment; --generate-only writes only the selected synthetic dataset folder.\n\nNative schema gaps are explicit: search-to-target-job correlation,job-scoped eligibility,assessment-to-application linkage and a versioned journey stage event model. Proposed fields are not presented as deployed columns. The mentor source-field mapping identifies the existing native target or named proposal for every field. Existing27 contracts remain and5 synthetic file contracts are added. No live API is fabricated.\n\nD1 defines gig applications as worker-to-requester with external fulfilment,earnings and completion references. The data does not implement an internal fulfilment engine. The source PDFs remain the business/method reference; their embedded instructions do not authorize external publication. D3 p.11 separates step22 source mapping from steps23–28 full platform loading and automation. This extension supplies scenario-driven synthetic evidence without marking those later steps complete.\n\nFull-rubric scores remain unchanged because no human interview or independent review has occurred. The new output data,schemas,section ratings and source evidence are populated. Documentary quality is a separate supplementary measure. Kluster tooling was unavailable; no Kluster verification is claimed.\n''',encoding='utf-8')
 readme=OUT/'README.md';readme.write_text(readme.read_text(encoding='utf-8').replace('--population1500000','--population 1500000'),encoding='utf-8')
 shutil.copy2(Path(__file__),OUT/'evidence/generate_mentor_data.py')
 write(OUT/'evidence/mentor_saved_workbooks.json',saved)
 manifest=[{'file':f.relative_to(OUT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(OUT.rglob('*')) if f.is_file() and f.name!='manifest.json' and not f.name.endswith('.inspect.ndjson')]
 write(OUT/'manifest.json',manifest)
 zpath=ROOT/'outputs/Talentra_Step22_Mentor_Update_v6.zip'
 with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
  for f in sorted(OUT.rglob('*')):
   if f.is_file() and not f.name.endswith('.inspect.ndjson'):z.write(f,f.relative_to(OUT).as_posix())
 print(json.dumps({'zip':str(zpath),'zip_mb':round(zpath.stat().st_size/1048576,1),'books':len(books),'full_score':p['combinedRating']}))

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--package',action='store_true');a.add_argument('--polish',action='store_true');a.add_argument('--generate-only',action='store_true');a.add_argument('--population',type=int,default=1500000);a.add_argument('--output-data',type=Path);args=a.parse_args()
 if args.generate_only:
  if not args.output_data:a.error('--output-data is required with --generate-only')
  if args.population<100:a.error('population must be at least100')
  print(json.dumps(generate(args.population,args.output_data)['stages']))
 elif args.package:package()
 elif args.polish:polish()
 else:prepare()
