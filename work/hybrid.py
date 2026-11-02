"""Reconcile two supplied Talentra artifacts without changing their source files.

openpyxl is used only for read-only extraction. Excel authoring is performed by
the separate artifact-tool builder. Source workbook assertions remain assertions.
"""
import copy,hashlib,json,re,sys,difflib
from pathlib import Path
from collections import Counter,defaultdict
import openpyxl

ROOT=Path(__file__).resolve().parents[1]
FRIEND=Path(r'C:\Users\gauta\Downloads\Talentra_Master_Lifecycle_Steps_01_to_21.xlsx')
BASE=ROOT/'outputs/talentra_steps_01_22_v3'
OUT=ROOT/'outputs/talentra_hybrid_v4'
WORK=ROOT/'work/hybrid_v4'
for p in [OUT,WORK,OUT/'evidence'] :p.mkdir(parents=True,exist_ok=True)
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def clean(v):
 if v is None:return ''
 return re.sub(r'[*`]', '',str(v)).strip()
def norm(v):return re.sub(r'[^a-z0-9]+',' ',clean(v).lower()).strip()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source_a=json.loads((ROOT/'work/dashboard_data_v3.json').read_text(encoding='utf-8'))
source_b_hash_before=digest(FRIEND)
source_a_hash_before=digest(BASE/'Talentra_Combined.xlsx')
wb=openpyxl.load_workbook(FRIEND,read_only=True,data_only=False)
archive=[];tables=[];prose=[];inventory=[]
for sheet in wb:
 rows=list(sheet.values);inventory.append([sheet.title,sheet.max_row,sheet.max_column,sum(any(v is not None for v in r) for r in rows)])
 heading='Workbook introduction';run=[]
 def flush():
  global run
  if not run:return
  hrow,header=run[0];width=max(i+1 for i,v in enumerate(header) if v is not None)
  columns=[clean(v) or 'Source column '+str(i+1) for i,v in enumerate(header[:width])]
  records=[dict(row=rn,values=list(rr[:width])) for rn,rr in run[1:]]
  tables.append(dict(id=f'B-T{len(tables)+1:03}',sheet=sheet.title,heading=heading,header_row=hrow,columns=columns,records=records))
  run=[]
 for rn,r in enumerate(rows,1):
  non=[v for v in r if v is not None]
  if non:archive.append([sheet.title,rn,heading,*list(r),*([None]*(11-len(r)))])
  if rn<5:continue
  if len(non)>=2:run.append((rn,r));continue
  flush()
  if len(non)==1:
   value=clean(non[0])
   is_heading=bool(re.match(r'^\d+[.)]\s|^ENT-\d+|^▶|^Open questions|^How to read|^Model$|^Scores$|^Deliverables$|^Gate Tracker$|^Gate G3 Exit|^Scoring status|^Build and Reproduction',value))
   if is_heading:heading=value
   prose.append(dict(sheet=sheet.title,row=rn,heading=heading,value=str(non[0]),kind='Heading' if is_heading else 'Source note'))
 flush()
wb.close()
save(WORK/'source_b_extract.json',dict(inventory=inventory,tables=tables,prose=prose,archive=archive))
if '--extract' in sys.argv:
 print('SOURCE TABLES')
 for t in tables:print(t['id'],t['sheet'],t['heading'][:48],len(t['records']),'; '.join(t['columns'])[:160])
print('EXTRACT',json.dumps(dict(source_sheets=len(inventory),blocks=len(tables),archive_rows=len(archive),data_rows=sum(len(t['records']) for t in tables))))
if '--extract' in sys.argv:sys.exit(0)

hybrid=copy.deepcopy(source_a)
physical=json.loads((BASE/'evidence/dictionary_v3.json').read_text())
a_by={(a['table'],a['column']):a for a in physical}
a_tables={a['table'] for a in physical}
def loc(t,r=None):return "B:"+t['sheet']+'!A'+str(r or t['header_row'])
def rows_of(sheet,first=None):return [t for t in tables if t['sheet']==sheet and (first is None or norm(t['columns'][0])==norm(first))]
def target_step(t):
 sheet=t['sheet'];h=t['heading'].lower();cols=' '.join(t['columns']).lower()
 if sheet.startswith('00_') or sheet in ['Phase3_Scorecards','Gate_G3_Victory_Audit']:return 0
 n=int(sheet[:2])
 if n==3:
  if 'integration' in h:return 22
  if 'classification' in h or 'retention' in h:return 12
  if 'access pattern' in h:return 4
  if 'volumetric' in h:return 13
  if 'quality' in h:return 14
  return 6
 if n==4:return 9
 if n==6 and ('workflow' in h or 'wf-' in h or 'entities touched' in cols):return 16
 return n
section_mapping=[]
for t in tables:
 step=target_step(t);t['canonical_step']=step
 section_mapping.append([t['id'],t['sheet'],t['heading'],len(t['records']),step or 'Review/source archive',hybrid['steps'][step-1]['title'] if step else 'Reported metrics and claims',loc(t),'Semantic mapping; source step numbering is not substituted'])

# Stable names are reconciled by semantics, never by the integer suffix of an ID.
aliases={'access_permission':'permission','access_role_permission':'role_permission','application':'job_application','application_status_history':'application_status_event','application_status_transition':'transition_rule','job_status_transition':'transition_rule','candidate_block':'blocking_entry','job_alert':'job_alert_preference','job_requirement_skill':'job_skill','organisation_member':'recruiter_membership','organisation_tax_identifier':'organisation_identifier','plan':'subscription_plan','profile_download':'profile_download_event','resume':'resume_version','screening_question':'job_question','subscription':'subscription_period','ui_label':'ui_label_definition','user_access_role':'user_role','user_credential':'credential','user_device':'registered_device','currency':'reference_value','language':'reference_value','wallet':'credit_account','wallet_ledger_entry':'credit_ledger_entry'}
dict_b=[]
for t in rows_of('19_Data_Dictionary_v2','Column'):
 table=re.search(r'▶\s*([a-z_]+)',t['heading']).group(1)
 for rec in t['records']:
  v=[clean(x) for x in rec['values']]
  dict_b.append(dict(table=table,column=v[0],business_name=v[1],type=v[2],nullable=v[3].lower().startswith('yes'),constraints=v[4],classification=v[5],definition_example=v[6],source=loc(t,rec['row']),block=t['id']))
b_tables={x['table'] for x in dict_b}
enum_tables={re.search(r'▶\s*([a-z_]+)',t['heading']).group(1) for t in rows_of('19_Data_Dictionary_v2','Column') if 'ENT-51' in t['heading']}
enum_tables.update(['currency','language'])
for table in enum_tables:
 if table not in ['industry','qualification']:aliases[table]='reference_value'
# The original design has typed master tables for industry and qualification.
entity_rows=[]
for table in sorted(b_tables):
 dest=aliases.get(table,table)
 mode='Lookup domain in reference_domain/reference_value' if table in enum_tables else 'Exact table name' if dest==table else 'Semantic alias / split responsibility'
 if table=='job_requirement_location':mode='Add proposed multi-location junction; keep primary city for compatibility'
 if table=='subscription':mode='Split into licence + subscription_period; retain explicit licence limits'
 if table=='notification':mode='Split into notification intent + notification_delivery + outbox_event'
 entity_rows.append([table,dest,mode,'Keep A physical contract; import B meaning after field mapping','B:19_Data_Dictionary_v2; A:current dictionary'])

# Recover usable descriptions and examples from B's earlier dictionary. A
# placeholder in v2 does not override a meaningful definition in either source.
v1={}
for t in rows_of('10_Data_Dictionary_v1','Column'):
 prev=[p for p in prose if p['sheet']==t['sheet'] and p['row']<t['header_row'] and clean(p['value']) in b_tables]
 if not prev:continue
 table=clean(prev[-1]['value'])
 for r in t['records']:
  v=r['values']
  if len(v)>=9:v1[(table,clean(v[0]))]=dict(definition=clean(v[5]),example=clean(v[6]),owner=clean(v[8]),source=loc(t,r['row']))
domains={clean(r['values'][1]):dict(type=clean(r['values'][2]),rule=clean(r['values'][3])) for t in tables if t['id']=='B-T165' for r in t['records']}

column_alias={
 'app_user':{'account_status_id':'status_reference_value_id','preferred_language_id':'preferred_language'},
 'user_credential':{'password_changed_at':'changed_at'},
 'user_device':{'device_fingerprint_hash':'device_token','first_seen_at':'registered_at'},
 'user_session':{'user_device_id':'registered_device_id'},
 'organisation':{'legal_name':'name','verification_status_id':'status_reference_value_id'},
 'organisation_location':{'address_line':'address_text'},
 'organisation_tax_identifier':{'tax_identifier_type_id':'type_reference_value_id','identifier_hmac':'identifier_token','identifier_last4':'masked_identifier'},
 'candidate_profile':{'current_city_id':'city_id','profile_language_id':'content_language'},
 'candidate_experience':{'company_name':'employer_name','job_title':'role_name'},
 'candidate_skill':{'proficiency_level_id':'proficiency_reference_value_id'},
 'candidate_language':{'language_id':'language_code','proficiency_level_id':'proficiency_reference_value_id'},
 'resume':{'storage_key':'object_key','file_sha256':'content_hash','content_language_id':'content_language'},
 'job_requirement':{'description_language_id':'content_language','employment_type_id':'employment_type_reference_value_id','work_mode_id':'work_type_reference_value_id','salary_min_amount':'salary_min','salary_max_amount':'salary_max','salary_currency_id':'currency_code','salary_disclosure_id':'salary_disclosure_reference_value_id','positions_total':'positions','job_status_id':'status_reference_value_id','is_open_to_consultants':'open_to_consultant'},
 'job_requirement_skill':{'is_mandatory':'mandatory'},
 'screening_question':{'answer_type_id':'answer_type_reference_value_id','is_required':'mandatory'},
 'application':{'resume_id':'resume_version_id','application_status_id':'status_reference_value_id'},
 'application_answer':{'application_id':'job_application_id','screening_question_id':'job_question_id'},
 'application_status_history':{'application_id':'job_application_id','from_status_id':'from_reference_value_id','to_status_id':'to_reference_value_id','changed_at':'occurred_at'},
 'application_status_transition':{'from_status_id':'from_reference_value_id','to_status_id':'to_reference_value_id'},
 'job_status_transition':{'from_status_id':'from_reference_value_id','to_status_id':'to_reference_value_id'},
 'plan':{'price_currency_id':'currency_code'},
 'subscription':{'plan_id':'subscription_plan_id','starts_on':'start_at','ends_on':'end_at'},
 'payment_order':{'payment_status_id':'status_reference_value_id','currency_id':'currency_code'},
 'payment_event':{'payment_status_id':'status_reference_value_id','gateway_event_ref':'provider_event_key','currency_id':'currency_code'},
 'invoice':{'currency_id':'currency_code'},
 'profile_download':{'app_user_id':'actor_app_user_id'},
 'notification':{'app_user_id':'recipient_app_user_id','notification_category_id':'purpose_reference_value_id'},
 'notification_preference':{'is_enabled':'enabled','notification_channel_id':'channel_reference_value_id'},
 'audit_event':{'action':'action_code','entity_table':'subject_table','entity_id':'subject_id'},
 'system_error':{'message':'safe_message'},
 'country':{'iso2':'code'},
 'ui_translation':{'label_text':'translated_text'},
 'user_access_role':{},'access_role_permission':{'access_permission_id':'permission_id'}
}
cross={('app_user','phone_e164'):('candidate_contact','phone_number'),('app_user','phone_country_id'):('candidate_contact','country_id'),('candidate_profile','full_name'):('app_user','person_name'),('candidate_profile','profile_visibility_id'):('user_preference','privacy_reference_value_id'),('job_alert','candidate_profile_id'):('job_alert_preference','app_user_id'),('notification','provider_message_ref'):('notification_delivery','provider_reference'),('notification','notification_status_id'):('notification_delivery','status_reference_value_id'),('notification','sent_at'):('notification_delivery','attempted_at'),('notification','dedupe_key'):('outbox_event','event_key'),('notification','next_attempt_at'):('outbox_event','available_at'),('notification','attempt_count'):('outbox_event','attempt_count'),('wallet','balance_credits'):('credit_account','available_credit_count'),('wallet_ledger_entry','credits'):('credit_ledger_entry','signed_credit_count'),('wallet_ledger_entry','balance_after'):('credit_ledger_entry','balance_after_credit_count'),('wallet_ledger_entry','reverses_ledger_entry_id'):('credit_ledger_entry','original_credit_ledger_entry_id'),('wallet_ledger_entry','ledger_entry_type_id'):('credit_ledger_entry','entry_type_reference_value_id')}

special_definitions={
 ('credential','failed_attempt_count'):('Consecutive unsuccessful authentication attempts since the last successful login. Increment atomically and audit without storing supplied passwords.','integer','>=0; lockout threshold is configuration approved by security owner'),
 ('credential','locked_until'):('UTC instant before which normal authentication is denied. NULL means no current temporary lockout.','timestamptz','Must be derived from an audited lockout event; clear/reset only through trusted authentication flow'),
 ('candidate_profile','summary'):('Candidate-authored professional summary in content_language. Restrict visibility using the same predicate as the profile.','varchar(2000)','UTF-8; <=2000 characters; redact logs and include in erasure inventory'),
 ('candidate_profile','expected_salary_amount'):('Candidate expected compensation. NULL means undisclosed/unknown, distinguished by salary-disclosure lookup; never use zero for missing.','numeric(18,2)','>=0 with expected_salary_currency_code; configured currency precision'),
 ('candidate_profile','expected_salary_currency_code'):('ISO currency for expected compensation; not a count of profile credits.','char(3)','Required exactly when expected_salary_amount is populated'),
 ('candidate_profile','notice_period_days'):('Candidate-reported days before starting a new role. NULL means unknown; zero means immediately available.','integer','>=0; maximum is an owner-approved business limit'),
 ('candidate_profile','total_experience_months'):('Derived count of non-overlapping calendar months of candidate work history. Avoid double-counting concurrent jobs.','integer','Derived projection; source history is authoritative; same as-of date for comparisons'),
 ('candidate_profile','is_open_to_work'):('Candidate-selected availability flag subject to visibility consent and stale-status review.','boolean','NOT NULL default false; inactivity expiry requires product approval'),
 ('job_requirement','min_experience_months'):('Minimum required experience expressed in whole calendar months.','integer','>=0 and <=max_experience_months when both known'),
 ('job_requirement','max_experience_months'):('Maximum desired experience expressed in whole calendar months.','integer','>=min_experience_months; NULL means no upper bound'),
 ('job_requirement','positions_filled'):('Derived count of joined applications under a job lock, not a second manually editable capacity value.','integer','0..positions; join/reversal transaction must reconcile this projection'),
 ('credit_account','available_credit_count'):('Derived sum of immutable signed_credit_count entries in the account credit ledger. It is a dimensionless product entitlement, not currency money.','bigint','Derived only; never mix with wallet_ledger_entry.signed_amount'),
 ('credit_ledger_entry','signed_credit_count'):('Signed whole-number grant or consumption of product credits. Positive grants, negative consumption.','bigint','Append-only; serialise debit against credit_account and prevent negative available credits'),
 ('credit_ledger_entry','balance_after_credit_count'):('Optional reproducible post-entry balance snapshot for audit; immutable ledger sum remains authoritative.','bigint','>=0 and equals prior balance plus signed_credit_count within posting order'),
 ('credit_ledger_entry','original_credit_ledger_entry_id'):('Original credit ledger row reversed by this correction. NULL for ordinary entries.','bigint','FK credit_ledger_entry.id; one permitted reversal policy, no mutation of original'),
}
classification_rank={'Public':0,'Internal':1,'Personal':2,'Sensitive':3}
comparisons=[];field_rows=[];hybrid_dict=[];proposals={};enrichments=defaultdict(list)
def cmp(step,topic,a,b,agreement,source,conclusion):
 comparisons.append([f'CMP-{len(comparisons)+1:04}',step,topic,str(a),str(b),'Agree' if agreement else 'Different',source,conclusion])
def family(typ):
 typ=domains.get(typ,{}).get('type',typ).lower()
 if typ in ['smallint','integer','bigint','int','int4','int8']:return 'integer'
 if typ.startswith(('numeric','decimal')):return 'decimal'
 if typ in ['date','timestamptz','timestamp']:return 'temporal'
 if typ in ['boolean','bool']:return 'boolean'
 if typ=='bytea':return 'bytes'
 if typ=='tsvector':return 'search projection'
 return 'text' if typ=='text' or typ.startswith(('varchar','char')) or typ in domains else typ
def proposed_type(b):
 t=domains.get(b['type'],{}).get('type',b['type'])
 if t=='text':
  lim={'person_name':150,'short_text':200,'medium_text':2000,'long_text':20000,'email_address':254,'phone_e164':16,'lookup_code':80}.get(b['type'],2000)
  return 'varchar('+str(lim)+')'
 return 'bigint' if t in ['smallint','integer'] and (b['column'].endswith('_id') or b['column']=='id') else 'numeric(18,2)' if t=='numeric(14,2)' else t

for i,b in enumerate(dict_b,1):
 table=aliases.get(b['table'],b['table']);column=column_alias.get(b['table'],{}).get(b['column'],b['column'])
 if b['table'] in enum_tables and b['table'] not in ['industry','qualification']:
  table='reference_value';column={'is_active':'active','ui_label_id':'label_key'}.get(column,column)
 if b['table']=='currency' and b['column']=='minor_units':table,column='currency_definition','minor_units'
 if b['table']=='language' and b['column'] in ['native_name','is_ui_language']:table,column='language_definition',b['column']
 if (b['table'],b['column']) in cross:table,column=cross[(b['table'],b['column'])]
 if b['column']=='currency_id' and (table,'currency_code') in a_by:column='currency_code'
 if b['table']=='candidate_profile' and b['column']=='expected_salary_currency_id':column='expected_salary_currency_code'
 if b['table']=='candidate_profile' and b['column']=='salary_disclosure_id':column='salary_disclosure_reference_value_id'
 if b['table']=='job_alert' and b['column']=='is_active':column='enabled'
 if b['table']=='wallet' and b['column']=='organisation_id':column='account_id'
 if b['table']=='wallet_ledger_entry' and b['column']=='wallet_id':column='credit_account_id'
 if b['table']=='ui_translation' and b['column']=='ui_label_id':column='label_key'
 if b['table']=='ui_translation' and b['column']=='language_id':column='language_code'
 if b['table']=='notification' and b['column'] in ['payload','queued_at','delivered_at','failure_reason']:
  table,column={'payload':('outbox_event','payload_reference'),'queued_at':('outbox_event','created_at'),'delivered_at':('outbox_event','delivered_at'),'failure_reason':('delivery_attempt','error_code')}[b['column']]
 key=(table,column);existing=a_by.get(key)
 v=v1.get((b['table'],b['column']),{})
 definition=v.get('definition') or b['definition_example'].split(' (e.g.')[0]
 placeholder=not definition or bool(re.fullmatch(r'[—\-\s]+',definition))
 if placeholder:
  definition=special_definitions.get(key,('A '+b['business_name'].lower()+' value for '+table+'. Confirm detailed business meaning before physical migration.',None,None))[0]
  if column=='ui_label_id':definition='Proposed FK ui_label_definition.id for the translated display name of '+table+'. Authorisation continues to use the stable role/permission code, not translated text.'
  if column=='is_active':definition='Whether this '+table+' record may be selected for new operations. Historical references remain valid after deactivation.'
  if column=='sort_order':definition='Non-negative display ordering within the '+table+' catalogue. Use stable id/code as a tie-breaker; this value carries no currency precision or access privilege.'
 proposal_rule=domains.get(b['type'],{}).get('rule','Typed scalar with explicit null treatment, ownership and source lineage')
 status='Existing physical field'
 if existing:
  decision='Enrich existing canonical field; keep A physical type, owner and null rule'
  if key!=(b['table'],b['column']):decision='Map semantic alias/split to existing field; '+decision.lower()
  if b['column'].endswith('_id') and not column.endswith('_id'):decision+='; resolve source ID through lookup to canonical code/key, never copy the integer'
  if (b['table'],b['column']) in cross:decision+='; use the named parent/ownership join rather than assuming IDs are equal'
  typ=existing['type'];cls=existing['classification'];nullable=existing['nullable'];definition=existing['definition']+' Additional context: '+definition if not placeholder else existing['definition']
  enrichments[key].append(b)
  for step in [7,10,19]:
   cmp(step,table+'.'+column+' value kind',family(typ),family(b['type']),family(typ)==family(b['type']),b['source'],'Preserve exact A SQL type; compare semantic value family only')
  if b['classification'] in classification_rank:
   cmp(12,table+'.'+column+' sensitivity',cls,b['classification'],cls==b['classification'],b['source'],'Use stricter class when it is the same data concept; classification deltas remain visible')
 else:
  typ=proposed_type(b);cls=b['classification'] if b['classification'] in classification_rank else 'Internal';nullable=b['nullable'];status='Proposed hybrid field; migration and runtime proof pending'
  decision='Adopt additional design field; no claim of deployed column or inherited test pass'
  if key in special_definitions:definition,typ,proposal_rule=special_definitions[key]
  if b['column']=='search_vector':status='Proposed derived search projection';decision='Keep as a recomputable projection; do not treat an indexed vector as original candidate data'
  if b['table'] in enum_tables and b['column'] in ['native_name','is_ui_language','minor_units']:
   decision='Add typed language/currency metadata; never overload generic lookup sort_order or label_key'
  if key not in proposals:
   proposals[key]=dict(id=f'HATT-{len(proposals)+1:04}',table=table,column=column,type=typ,definition=definition,nullable=nullable,classification=cls,validation=proposal_rule,source=b['source'],owner=v.get('owner') or 'Domain owner to confirm',status=status,example=v.get('example') or 'UNKNOWN - source v2 example is absent',bsource=b)
 field_rows.append([f'MAP-H-{i:04}',b['table'],b['column'],table,column,b['type'],existing['type'] if existing else typ,decision,status,b['source'],definition,b['definition_example']])

# Complete the proposed tables with explicit surrogate keys, audit attributes
# and the relationships needed by the additional business fields.
support={
 'credit_account':[('id','bigint',False,'Surrogate credit account ID; natural ownership keys stay unique'),('account_id','bigint',False,'FK account.id; one active credit account per account and entitlement unit')],
 'credit_ledger_entry':[('id','bigint',False,'Surrogate immutable credit entry ID'),('credit_account_id','bigint',False,'FK credit_account.id; lock parent before consuming credits'),('idempotency_key','varchar(150)',False,'Unique together with credit_account_id; safe retry key'),('occurred_at','timestamptz',False,'UTC time of credit posting; deterministic posting order includes id')],
 'job_requirement_location':[('id','bigint',False,'Surrogate job-location row ID'),('job_requirement_id','bigint',False,'FK job_requirement.id'),('city_id','bigint',False,'FK city.id; unique(job_requirement_id,city_id)')],
 'currency_definition':[('id','bigint',False,'Surrogate currency metadata ID'),('currency_code','char(3)',False,'Unique ISO currency code; resolve only from the approved currency reference domain')],
 'language_definition':[('id','bigint',False,'Surrogate language metadata ID'),('language_code','varchar(10)',False,'Unique supported language tag; preserve configured fallback chain')],
 'ui_label_definition':[('id','bigint',False,'Surrogate UI label registry ID'),('label_key','varchar(80)',False,'Unique stable UI key; translations continue to reference the canonical key, never an arbitrary translation-row ID')],
}
for table,fields in support.items():
 fields+= [('created_at','timestamptz',False,'UTC creation time'),('created_by','bigint',True,'FK app_user.id; NULL only for documented bootstrap/system job'),('updated_at','timestamptz',False,'UTC last permitted change; immutable histories do not accept updates'),('updated_by','bigint',True,'FK app_user.id; NULL only for documented bootstrap/system job')]
 for column,typ,nullable,definition in fields:
  if (table,column) not in proposals:proposals[(table,column)]=dict(id=f'HATT-{len(proposals)+1:04}',table=table,column=column,type=typ,definition=definition,nullable=nullable,classification='Personal' if column in ['created_by','updated_by'] else 'Internal',validation='Proposed PK/FK/UNIQUE and stated lifecycle contract. Native migration and negative tests required.',source='Hybrid supporting design for mapped B concepts',owner='Owning domain team',status='Proposed hybrid supporting field; migration and runtime proof pending',example='UNKNOWN - synthetic fixture to be generated after migration contract approval')

# Current physical fields are all retained. Proposed additions have a separate
# status, so the hybrid cannot accidentally assert that a migration has run.
for a in physical:
 key=(a['table'],a['column']);bs=enrichments.get(key,[])
 bname=bs[0]['business_name'] if bs else a['column'].replace('_',' ').capitalize()
 desc=a['definition'];described=[v1.get((b['table'],b['column']),{}).get('definition') for b in bs]
 useful=[x for x in described if x and not re.fullmatch(r'[—\-\s]+',x)]
 if useful and norm(useful[0]) not in norm(desc):desc+=' Business context: '+useful[0]
 bclasses=[b['classification'] for b in bs if b['classification'] in classification_rank]
 cls=max([a['classification'],*bclasses],key=lambda x:classification_rank[x])
 hybrid_dict.append([a['id'],a['table'],a['column'],bname,a['type'],a['nullable'],a['null_reason'],desc,a['example'] if a['example'] is not None else 'NULL under stated optional event',cls,a['classification'],a['owner'],a['validation'],a['rule'],'Existing A physical field; any classification policy change needs approval','A:dictionary_v3.json '+a['id'], '; '.join(b['source'] for b in bs) or 'No B equivalent'])
for p in proposals.values():hybrid_dict.append([p['id'],p['table'],p['column'],p['column'].replace('_',' ').capitalize(),p['type'],p['nullable'],'NULL only under the stated optional event' if p['nullable'] else 'Not nullable',p['definition'],p['example'],p['classification'],'Not in A physical schema',p['owner'],p['validation'],'HBR-PENDING',p['status'],'Hybrid proposal',p['source']])
current_catalogue=json.loads((BASE/'evidence/catalogue_v3.json').read_text())
current_fk={(r['child'],r['column']):r['parent']+'.'+r.get('parent_column','id') for r in current_catalogue['relationships']}
current_retention={e['table']:e['retention'] for e in current_catalogue['entities']}
for row in hybrid_dict:
 key=(row[1],row[2]);a=a_by.get(key);p=proposals.get(key)
 if a:extras=[a['default'],current_fk.get(key,'No foreign key'),a.get('storage','Stored'),current_retention[row[1]]]
 else:
  fk=re.search(r'FK ([a-z_]+\.[a-z_]+)',p['definition']);derived=any(x in p['definition'].lower() for x in ['derived','projection','snapshot'])
  extras=['Identity proposed' if row[2]=='id' else 'false proposed; owner approval required' if row[4]=='boolean' else 'CURRENT_TIMESTAMP proposed' if row[2] in ['created_at','updated_at'] else 'No implicit default',fk.group(1) if fk else 'Proposal: validate exact FK/domain before migration','Derived/projection' if derived else 'Stored proposed','Inherit owning purpose-based policy; privacy/finance owner approval pending']
 row.extend(extras)

req_a=source_a['steps'][0]['sections'][0]['rows'];req_b=rows_of('01_Requirements_Register','req_id')[0]
requirements=[]
def token_score(a,b):
 stop={'the','a','an','and','or','to','of','in','for','on','with','by','from','is','are','must','every','all','only','be','as','has'}
 aa=set(norm(a).split())-stop;bb=set(norm(b).split())-stop
 return len(aa&bb)/len(aa|bb) if aa|bb else 0
for rec in req_b['records']:
 v=rec['values'];best=max(req_a,key=lambda r:token_score(v[1],r[3]));score=token_score(v[1],best[3])
 requirements.append(['B:'+str(v[0]),v[1],'A:'+best[0],best[3],round(score,3),'Related topic candidate; preserve both statements, not an assertion of equivalence',loc(req_b,rec['row'])])
rules_b=[]
for t in tables:
 if t['sheet'] not in ['11_Data_Rules_v1','18_Business_Rules_v2']:continue
 for rec in t['records']:
  v=rec['values']
  if re.fullmatch(r'(?:BR|DR)-\d+',clean(v[0])):
   text=clean(v[2] if t['sheet'].startswith('18') else v[1]);rr=current_catalogue['rules']
   best=max(rr,key=lambda r:token_score(text,r.get('statement','')))
   rules_b.append(['B:'+clean(v[0]),text,'A:'+best['id'],best.get('statement',''),round(token_score(text,best.get('statement','')),3),'Candidate topical relation; do not join rules by number or inherit implementation',loc(t,rec['row'])])

# Source observations and numerical claims are not silently reclassified as
# executed evidence. These issues affect the hybrid conclusions explicitly.
placeholder_count=sum(bool(re.fullmatch(r'[—\-\s]+',b['definition_example'].split(' (e.g.')[0])) for b in dict_b)
decisions=[
 ['HDEC-001','Step numbering','B03 is data requirements and B04 is conceptual modelling','Map B03 sections to4/6/12/13/14/22; B04 to9; preserve D3 lifecycle numbering','Resolved mapping','B03/B04; D3 pp.6-11'],
 ['HDEC-002','Reported G3 victory versus open interview','B overview says passed; gate tracker says author interview pending','Keep G3 open for the hybrid. Do not copy a source-reported gate into a hybrid approval','Open evidence gate','B:00_Overview_Dashboard!E9; B:Gate_G3_Victory_Audit!F24'],
 ['HDEC-003','Provisional human score','B assigns D8=4 while interview is pending','Set hybrid human understanding to0 until actual interview evidence exists','Pending human interview','B:Phase3_Scorecards!A22; A ratings'],
 ['HDEC-004','Claimed live database validation','B reports PostgreSQL passes but attached workbook contains no DDL repository or raw run logs','Retain as source-reported evidence; it does not verify the A/hybrid schema','External evidence required','B:00_Overview_Dashboard!A3; B:G3 audit'],
 ['HDEC-005','Engine version conflict','B overview mentions PostgreSQL18; physical baseline says PostgreSQL16','Keep A PostgreSQL18 design target. Resolve B runtime version from missing run logs before transferring evidence','Resolved design; evidence open','B:21_Physical_Baseline!A12; B:00_Overview_Dashboard!A3'],
 ['HDEC-006','Dictionary description completeness',str(placeholder_count)+' of462 B-v2 definition/example rows use an em-dash definition','Use meaningful A definitions and available B-v1 descriptions; never count dash text as a complete definition','Resolved documentary enrichment','B:19_Data_Dictionary_v2; B:10_Data_Dictionary_v1'],
 ['HDEC-007','Object-count comparison','A has120 physical tables; B has73 including25 lookup tables','Map concepts and domains. Do not sum120+73 or rank model quality by table count','Resolved entity crosswalk','A physical_model_v3; B:19_Data_Dictionary_v2!A10:D13'],
 ['HDEC-008','Money versus credits','A wallet ledger uses monetary amounts/currency; B uses whole-number product credits','Model credit account/ledger separately as proposed design; never copy credit counts into money columns','Design addition; migration pending','B:wallet and wallet_ledger_entry; A wallet definitions'],
 ['HDEC-009','Tax and commercial policy','B hard-codes18% tax,5 credits per posting,1 credit per download and30-day access','Retain as proposed configurable policy. Require product/finance/privacy owner confirmation','Owner decision pending','B:18_Business_Rules_v2!A20:G30'],
 ['HDEC-010','Retention','A baseline inactivity proposal24months; B3years; audit7years','Keep competing policy proposals visible; no automatic legal-policy approval or arithmetic average','Privacy owner decision pending','A classification; B:18_Business_Rules_v2!A36:G36'],
 ['HDEC-011','Benchmark scope','B reports5.3ms search at dev10k; source docket requires measured laptop1m profiles','Preserve reported number with dataset qualifier. Keep laptop/full-scale tests pending','Performance evidence pending','B:Gate_G3_Victory_Audit!A43:D43; D1 sizing'],
 ['HDEC-012','Lookup strategy','B uses one table per vocabulary; A uses reference_domain/value bindings','Keep A domain-scoped lookup strategy; map B vocabulary concepts without duplicating physical enum tables','Resolved design mapping','A reference_field_binding; B dictionary'],
 ['HDEC-013','Licence structure','B treats subscription as licence; A separates licence limits from periods','Retain A licence+period model and bring B immutable sold-plan snapshot policy into the design register','Resolved design; implementation tests pending','A licence/subscription_period; B BR-17'],
 ['HDEC-014','Notification structure','B places intent, delivery and queue metadata on notification','Preserve A separation across notification, notification_delivery, outbox_event and delivery_attempt','Resolved field mapping','A current dictionary; B notification'],
 ['HDEC-015','Candidate identity duplication','B candidate full_name duplicates A app_user.person_name concept','Keep one canonical identity name; map candidate display to owning user rather than adding another authoritative name','Resolved field mapping','B candidate_profile.full_name; A app_user.person_name'],
 ['HDEC-016','Candidate registration authority','B allows staff registration at placement drives','Retain self-registration/no recruiter registration. Staff-assisted exception remains an explicit owner decision','Owner decision pending','B BR-02; D1 actor restrictions'],
 ['HDEC-017','Model provenance','User identifies A as GPT; B model might be Claude/Muse/other but is not recorded','Record A=GPT per user, B=unknown. Report cross-author artifact comparison, not confirmed named-model consensus','Provenance limitation recorded','User request; source metadata'],
 ['HDEC-018','Physical schema execution','Hybrid adds workbook design fields but has not executed a physical migration','Existing120-table A baseline stays the executed portable-design scope; proposed hybrid fields do not inherit its passes','Release gate open','A evidence; hybrid dictionary status'],
 ['HDEC-019','Step22','Only A has completed integration/source-mapping artifacts at canonical step22','Retain A contracts. B integration-boundary rows supplement ownership; no second field-level provider contract exists','Resolved scope','A step22; B03 section6'],
 ['HDEC-020','Source rule count','B reports275=28BR+247DR; the supplied rows have a smaller explicit catalogue','Report observed explicit rows separately from source-reported aggregate. Do not invent absent rules','Resolved counting method','B11; B18 overview'],
]

# Topic-level decisions are compared without claiming that different IDs or SQL
# aliases are disagreements. Both source statements and their locators are kept.
topic_checks=[
 (1,'Candidate population target','10 million','10M',True,'B:01_Requirements_Register!B9','Same stated scale anchor'),
 (1,'Candidate self-registration','No recruiter registration','No recruiter registration',True,'B:01_Requirements_Register','Shared mandatory boundary'),
 (1,'Gig fulfilment ownership','External fulfilment','External fulfilment',True,'B:04_Conceptual_Model!A34','Shared boundary; preserve A implemented design coverage'),
 (1,'UI scope','Out of scope','Out of scope',True,'B:01_Requirements_Register!B46','Shared source scope'),
 (2,'Product roles','Admin/candidate/employer/recruiter/consultant/TPO','Same named product actors',True,'B:02_Stakeholders_Roles','Map by role name; not actor ID'),
 (2,'Permissions enforcement','Trusted access layer/database','Database permissions and RLS',True,'B:02_Stakeholders_Roles','Same security requirement; actual implementation evidence differs'),
 (2,'Staff-assisted registration','Self-service boundary; exception unapproved','Staff may register at placement drive',False,'B:18_Business_Rules_v2!C11','HDEC-016 owner decision'),
 (4,'Latency scope','Proposed laptop-scale search500ms','Dev-scale50ms target and reported5.3ms',False,'B:03_Data_Requirements!A85:F99','Do not compare latency without equal workload and hardware'),
 (4,'Full-scale profiles','10000000','10000000',True,'B:13_Data_Volumetrics!B13','Same full-scale data target'),
 (5,'Candidate registration workflow','Candidate registration','Candidate registration',True,'B:05_Business_Workflows!B8','Same business workflow'),
 (5,'Privacy failure path','Blocked parties cannot view candidate','Blocked parties cannot view candidate',True,'B:18_Business_Rules_v2!C13','Shared invariant; retain revocation detail'),
 (5,'Notification failure recovery','Durable outbox and bounded retry','Same-transaction intent and retry',True,'B:18_Business_Rules_v2!C30','Combine failure paths while keeping queue model separated'),
 (6,'Gig decomposition','Separate gig subsystem','Separate gig subsystem',True,'B:04_Conceptual_Model!A34','Shared model decision'),
 (6,'Licence decomposition','Licence and period separate','Subscription is licence',False,'B:04_Conceptual_Model!B23','HDEC-013 retain A model'),
 (6,'Lookup decomposition','Domain/value registry','Per-vocabulary tables',False,'B:19_Data_Dictionary_v2','HDEC-012 normalize domains'),
 (8,'Illegal transitions','Explicit negative edges','Explicit negative edges',True,'B:08_State_Machines','Import negative scenarios after entity alias mapping'),
 (8,'Current state history','Append-only status events','Append-only status history',True,'B:18_Business_Rules_v2!C25','History concept agrees'),
 (8,'Job reopening','Canonical transition catalogue applies','Closed/filled are final',False,'B:17_Design_Refinements!A11:F11','State-edge difference requires product decision; do not union transitions'),
 (9,'Cardinality catalogue','Both directions stated','Both directions stated',True,'B:09_Logical_ER_Model','Map relationship meaning; preserve optionality differences'),
 (9,'Multiple job locations','One primary city field','Many-to-many job locations',False,'B:09_Logical_ER_Model','Propose junction and keep primary city for backward compatibility'),
 (11,'Constraint ownership','Rules name enforcement point','Rules name enforcement point',True,'B:11_Data_Rules_v1','Same contract requirement'),
 (11,'Concurrent limits','Transactional locks/database constraints','Transactional locks/database constraints',True,'B:18_Business_Rules_v2','Native races still need hybrid execution'),
 (12,'Sensitive identifiers','Opaque tokens; no raw values','HMAC plus last4; no raw values',True,'B:18_Business_Rules_v2!C19','Same minimization rule; token formats are not interchangeable'),
 (12,'Inactivity retention','24months proposed','3years proposed',False,'B:18_Business_Rules_v2!C36','HDEC-010 policy remains unapproved'),
 (13,'Full-scale applications','100000000','100000000',True,'B:13_Data_Volumetrics','Same target'),
 (13,'Laptop evidence','1m required; not executed here','10k reported measurement','Different'=='Agree','B:01_Requirements_Register!F43','Dev10k does not replace required laptop benchmark'),
 (13,'Storage figures','A partial planning inputs','B total178.4GB/235GB at differing scopes',False,'B:03_Data_Requirements!C70; B dashboard','Retain separate populations/units; do not average'),
 (14,'Scenario categories','Happy/edge/invalid/golden data','Happy/edge/invalid/golden data',True,'B:14_Sample_Data_Gen','Combine scenario catalogue; do not infer identical random generator'),
 (14,'Seed size','A1247rows across all tables','B30candidate proof anchor',False,'B:14_Sample_Data_Gen','Different dataset grains; retain both descriptions'),
 (15,'Negative rejection tests','Present at portable layer','Reported at native layer',True,'B:15_Test_Suite_v1_Data','Design agreement only; native execution transfer is not allowed'),
 (15,'Raw test artifacts available','A scripts and JSON supplied','B named SQL paths without files',False,'B:15_Test_Suite_v1_Data','A observed versus B reported evidence'),
 (16,'Workflow storage/retrieval/audit','All three mapped','All three mapped',True,'B:16_Schema_Coverage','Enrich A operation descriptions with B entry-point designs'),
 (16,'Operation identifiers','A OP-nnn','B n.n within WF contexts',False,'B:16_Schema_Coverage','Namespace and crosswalk; do not merge by numeric ID'),
 (17,'Refinement log','Change reason and affected object','Before/after and verifying test',True,'B:17_Design_Refinements','Adopt B before/after template in hybrid refinement'),
 (17,'Findings closure','Native evidence pending','14findings reported closed inV013',False,'B:17_Design_Refinements','Missing migrations/logs prevent inherited closure'),
 (18,'Immutable finance history','Append-only corrections','Append-only reversal records',True,'B:18_Business_Rules_v2!C27','Shared invariant; keep product credits separate from money'),
 (18,'Posting price','Configurable proposed product policy','Fixed5credits',False,'B:18_Business_Rules_v2!C20','Owner approval required; not a fixed schema constant'),
 (18,'Invoice tax','No universal tax constant approved','18%GST hard-coded',False,'B:18_Business_Rules_v2!C28','No automatic tax-policy adoption'),
 (20,'Data/business/NFR suite taxonomy','All covered in test plan','All covered in test plan',True,'B:20_Test_Suite_v2','Combine unique test definitions'),
 (20,'Target NFR pass evidence','Pending target-volume tests','All37NFRs reported passed',False,'B:20_Test_Suite_v2!A117:D154','Reported results lack attached benchmark and native logs'),
 (21,'Physical engine version','PostgreSQL18','PostgreSQL16 in baseline',False,'B:21_Physical_Baseline!A12','Resolve version from raw evidence; keep A target'),
 (21,'Forward-only migrations','Versioned migration and manual rollback','Forward-onlyV014+ afterfreeze',True,'B:21_Physical_Baseline','Adopt checksum/change-control policy as design'),
 (21,'Physical gate status','OPEN','B dashboardPASSED; BtrackerOPEN',False,'B:Gate_G3_Victory_Audit','Open hybrid release gate'),
 (22,'Source boundary taxonomy','Payment/identity/company/gig/legacy/messaging/social/geo/reference','Same nine boundary categories',True,'B:03_Data_Requirements!A114:F123','Boundary-level agreement only; B lacks field-level provider contracts'),
]
for row in topic_checks:cmp(*row)

# Populate the respective canonical step areas with full B tables. Exit-check,
# score and coverage claims remain in the source archive / reported-evidence tab.
imported=[];excluded=[]
def supplement(t):
 if not t['canonical_step']:return False
 return not any(s in t['heading'].lower() for s in ['exit test','exit criterion','verification header','coverage summary'])
for t in tables:
 if not supplement(t):excluded.append([t['id'],t['canonical_step'] or 0,'Retained as source-reported claims/archive; not active hybrid approval',loc(t)]);continue
 step=t['canonical_step'];number=len([x for x in imported if x[0]==step])+1
 if t['sheet']=='19_Data_Dictionary_v2' and t['columns'][0]=='Column':
  excluded.append([t['id'],19,'Normalized into Hybrid Dictionary and Attribute Map; raw cells preserved in B archive',loc(t)]);continue
 # B older dictionary and per-table attribute blocks are normalized into the
 # hybrid register. Do not add hundreds of nearly identical presentation tabs.
 if t['sheet'] in ['07_Attribute_Lists','10_Data_Dictionary_v1']:
  excluded.append([t['id'],step,'Normalized into attribute mapping; source data retained verbatim in archive',loc(t)]);continue
 name='B '+t['id'][2:]+' '+t['heading'][:36]
 def namespace_refs(value):
  if not isinstance(value,str):return value
  return re.sub(r'(?<![A-Z0-9:])((?:REQ|BR|DR|TC|WF|FR|ENT|FND)-[A-Z0-9-]+)',r'B:\1',value)
 hybrid['steps'][step-1]['sections'].append(dict(name=name,columns=t['columns']+['Source locator','Evidence status'],rows=[[namespace_refs(v) for v in r['values']]+[loc(t,r['row']),'Source B design/report; not independently executed in hybrid'] for r in t['records']],priority='P0' if step in [4,8,11,12,18,20,21,22] else 'P1',source='B supplied workbook '+loc(t)))
 imported.append([step,t['id'],t['heading'],len(t['records']),name,loc(t)])

dictionary_columns=['Attribute ID','Table','Column','Business name','SQL type','Nullable','Null reason','Definition','Example','Hybrid class','A physical class','Owner','Validation','Rule IDs','Implementation status','A provenance','B provenance','Default','Foreign key target','Storage','Retention']
def addsection(n,name,cols,rows):hybrid['steps'][n-1]['sections'].append(dict(name=name,columns=cols,rows=rows,priority='P0',source='Hybrid reconciliation of A v3 and supplied B workbook'))
addsection(6,'Hybrid entity crosswalk',['B table','Canonical table','Relationship','Decision','Provenance'],entity_rows)
addsection(1,'Hybrid requirement crosswalk',['B requirement ID','B statement','Related A requirement','A statement','Lexical similarity','Mapping confidence','B source'],requirements)
addsection(7,'Hybrid attribute mapping',['Mapping ID','B table','B column','Canonical table','Canonical column','B type','Hybrid type','Decision','Implementation status','B source','Hybrid meaning','B v2 definition example'],field_rows)
for i,x in enumerate(hybrid['steps'][18]['sections']):
 if x['name']=='Dictionary v3':hybrid['steps'][18]['sections'][i]=dict(name='Hybrid Dictionary',columns=dictionary_columns,rows=hybrid_dict,priority='P0',source='A dictionary_v3 plus normalized B dictionary_v1/v2')
addsection(17,'Hybrid decision log',['Decision ID','Topic','Finding','Hybrid treatment','Status','Evidence locator'],decisions)
addsection(18,'Hybrid rule crosswalk',['B rule ID','B statement','Related A rule','A statement','Lexical similarity','Mapping confidence','B source'],rules_b)
for step in range(1,23):
 rows=[r for r in comparisons if r[1]==step]
 if rows:addsection(step,'Cross-source comparison',['Comparison ID','Step','Decision or field','A value','B value','Agreement','B locator','Hybrid conclusion'],rows)

# Source claims are separately readable. Source A checks retain their layer and
# date; no old PASS is relabelled as a newly run hybrid data test.
claims=[]
for t in tables:
 if t['canonical_step']==0 or 'exit test' in t['heading'].lower() or 'coverage summary' in t['heading'].lower():
  for r in t['records']:claims.append([t['id'],loc(t,r['row']),t['heading'],json.dumps(dict(zip(t['columns'],r['values'])),ensure_ascii=False),'Reported by source B; raw supporting files not supplied','Not transferred to hybrid release approval'])
stats=Counter(r[8] for r in field_rows)
compare_stats=[]
for step in range(1,23):
 raw=[r for r in comparisons if r[1]==step];units=defaultdict(list)
 for r in raw:units[r[2]].append(r)
 rr=list(units.values());agree=sum(all(x[5]=='Agree' for x in unit) for unit in rr);den=len(rr)
 ratio=agree/den if den else None
 score=5 if ratio is not None and ratio>=.98 else 4 if ratio is not None and ratio>=.9 else 3 if ratio is not None and ratio>=.75 else 2 if ratio is not None and ratio>=.5 else 1 if ratio is not None and ratio>0 else 0
 if den<5:score=min(score,2)
 compare_stats.append([step,den,agree,den-agree,ratio if ratio is not None else 'Unassessed',score,'Unique comparison concepts; repeated lookup templates counted once. Fewer than5 concepts capped at2/5. Cross-author evidence, model B unknown.'])

# Derive all new output schemas from the populated hybrid sections. L1-L4
# definitions reference data grain and reconciliation status rather than labels.
schema_fields=[];nodes=[];section_metrics=[]
old_fields={(r[0],r[1],r[2]):r for r in source_a['schema_fields']}
for step in hybrid['steps']:
 for si,s in enumerate(step['sections'],1):
  sid=f'H{step["number"]:02}.{si:03}';src=s['source'];priority=s['priority'];nodes.append([step['number'],sid,'',1,s['name'],priority,'Canonical output section with documented source/evidence status',src])
  for j,h in enumerate(s['columns']):
   old=old_fields.get((step['number'],s['name'],h));vals=[r[j] for r in s['rows'] if r[j] is not None]
   typ=old[4] if old else 'boolean' if vals and all(type(x)==bool for x in vals) else 'integer' if vals and all(type(x)==int for x in vals) else 'decimal' if vals and all(type(x) in [int,float] for x in vals) else 'text'
   definition=old[8] if old else {'B locator':'Exact original workbook cell/row used for this decision.','Agreement':'Agreement before reconciliation on the declared normalized concept; Different remains visible.','Implementation status':'Existing A physical field or proposed hybrid design awaiting migration and runtime proof.','B provenance':'Original source B dictionary cell locator; No B equivalent means A-only coverage.','Hybrid class':'Conservative privacy classification for the same semantic field; any physical-policy change is pending.'}.get(h,'At the '+s['name']+' record grain, '+h.lower()+' records the source value, mapped design decision or explicit evidence status. Do not convert source-reported claims into an observed result.')
   reason=old[9] if old else 'Make the hybrid decision traceable, typed and usable by the owning lifecycle step without losing the original source meaning.'
   fid=sid+f'.P{j+1:02}';nodes.append([step['number'],fid,sid,2,h,priority,definition,src])
   for suffix,facet,props in [('V','Value contract',[('Type',typ),('Validation','One typed scalar; documentary NULL/UNKNOWN explicit; schema field name fixed')]),('M','Meaning and lineage',[('Definition',definition),('Reason',reason),('Source',src)])]:
    gid=fid+'.'+suffix;nodes.append([step['number'],gid,fid,3,facet,priority,facet,src])
    for k,(label,val) in enumerate(props,1):nodes.append([step['number'],gid+'.'+str(k),gid,4,label,priority,val,src])
   schema_fields.append([step['number'],s['name'],h,'Value contract; Meaning and lineage',typ,'Required documentary field','Typed scalar; NULL only with stated meaning',definition,reason,priority,src,fid])
  section_metrics.append([step['number'],s['name'],priority,len(s['rows']),len(s['columns']),all(len(r)==len(s['columns']) for r in s['rows'])])

# Independent extraction/merge verification uses actual source cells and IDs.
tests=[]
def check(name,expected,actual):tests.append([name,expected,actual,'PASS' if expected==actual else 'FAIL'])
check('Source B dictionary physical fields extracted',462,len(dict_b))
check('Every B field has exactly one attribute mapping',462,len(field_rows))
check('Unique B field source identities',462,len({(x['table'],x['column']) for x in dict_b}))
check('Every A physical field retained',len(physical),sum(r[14].startswith('Existing') for r in hybrid_dict))
check('Unique hybrid dictionary keys',len(hybrid_dict),len({(r[1],r[2]) for r in hybrid_dict}))
check('Every proposed field remains marked proposed',len(proposals),sum(not r[14].startswith('Existing') for r in hybrid_dict))
check('Every imported table has semantic step',True,all(1<=r[0]<=22 for r in imported))
check('Source B03 access patterns remapped to canonical NFR step',4,next(t['canonical_step'] for t in tables if t['id']=='B-T015'))
check('Source B03 integrations remapped to canonical step22',22,next(t['canonical_step'] for t in tables if t['id']=='B-T017'))
check('Hybrid schema row conformance',True,all(r[5] for r in section_metrics))
check('No source A step dropped',22,len(hybrid['steps']))
check('No source A section dropped',True,all(len(s['sections'])>=len(source_a['steps'][i]['sections']) for i,s in enumerate(hybrid['steps'])))
check('Source B input hash unchanged',source_b_hash_before,digest(FRIEND))
check('Source A workbook hash unchanged',source_a_hash_before,digest(BASE/'Talentra_Combined.xlsx'))
check('Every semantic comparison preserves both values',True,all(r[3] and r[4] and r[6] for r in comparisons))
check('Every B requirement ID namespaced',39,len({r[0] for r in requirements}))
check('No money/credit table conflation',True,all(r[3] in ['credit_account','credit_ledger_entry'] for r in field_rows if r[1] in ['wallet','wallet_ledger_entry']))
check('Currency minor units never mapped to sort_order',True,all(r[4]!='sort_order' for r in field_rows if r[1]=='currency' and r[2]=='minor_units'))
check('UI label registry IDs never mapped to translation IDs',True,all(r[3]=='ui_label_definition' for r in field_rows if r[1]=='ui_label'))
check('Hybrid default/FK/storage/retention width',True,all(len(r)==len(dictionary_columns) for r in hybrid_dict))
if any(r[3]=='FAIL' for r in tests):save(OUT/'evidence/hybrid_merge_checks.json',tests);raise RuntimeError('Hybrid merge verification failed')

hybrid.update(version='4.0 hybrid',date='2026-10-28',steps=hybrid['steps'],schema_fields=schema_fields,schema_nodes=nodes,section_metrics=section_metrics)
scorecard_comparison=[]
a_weights=[14,14,9,18,9,9,9,8,10];b_weights=[15,15,10,20,5,5,10,10,10]
for i in range(9):
 for prop,av,bv in [('Criterion meaning','Core criterion '+str(i+1),'Core criterion '+str(i+1)),('Weight',a_weights[i],b_weights[i]),('Critical',i in [0,3,7],i in [0,3,7])]:scorecard_comparison.append(['D'+str(i+1),prop,av,bv,av==bv,'B:Phase3_Scorecards!A8:F18; A frozen rubric'])
card_ratio=sum(r[4] for r in scorecard_comparison)/len(scorecard_comparison)
card_score=5 if card_ratio>=.98 else 4 if card_ratio>=.9 else 3 if card_ratio>=.75 else 2 if card_ratio>=.5 else 1 if card_ratio>0 else 0
consistency={}
for step in range(1,23):
 output_score=compare_stats[step-1][5]
 for kind in ['Output Schema Definition','Schema Rating Scorecard','Output Document']:
  consistency[(step,kind)]=0 if kind=='Output Schema Definition' else card_score if kind=='Schema Rating Scorecard' and 13<=step<=21 else 0 if kind=='Schema Rating Scorecard' else output_score
expected_steps=[]
for s in source_a['steps']:
 scores=[s['deliverableScores'][i]+9*consistency[(s['number'],kind)]/5 for i,kind in enumerate(['Output Schema Definition','Schema Rating Scorecard','Output Document'])]
 expected_steps.append([s['number'],s['phase'],s['title'],s['priority'],3 if s['priority']=='P0' else 2,*s['deliverableScores'],s['score'],*scores,.25*scores[0]+.25*scores[1]+.5*scores[2]])
expected_overall=sum(r[4]*r[12] for r in expected_steps)/sum(r[4] for r in expected_steps)
result=dict(project=hybrid,source_a_summary=dict(score=source_a['combinedRating'],tables=len(a_tables),columns=len(physical),source_file='Talentra_Combined.xlsx',sha256=digest(BASE/'Talentra_Combined.xlsx')),
 source_b_summary=dict(file=FRIEND.name,sha256=digest(FRIEND),sheets=len(inventory),tables=len(b_tables),dictionary_columns=len(dict_b),placeholder_definitions=placeholder_count,reported_output_score=93,author_interview='Pending; source provisional4 is not accepted as observed',model='Unknown'),
 source_inventory=inventory,source_archive=archive,section_mapping=section_mapping,imported=imported,excluded=excluded,entity_mapping=entity_rows,attribute_mapping=field_rows,dictionary=hybrid_dict,dictionary_columns=dictionary_columns,proposed=list(proposals.values()),decisions=decisions,comparisons=comparisons,comparison_stats=compare_stats,source_claims=claims,tests=tests,requirement_crosswalk=requirements,rule_crosswalk=rules_b,
 original_source_a_ratings=source_a['ratingRows'],original_source_a_steps=[dict(step=s['number'],score=s['score'],deliverables=s['deliverableScores'],priority=s['priority']) for s in source_a['steps']],scorecard_comparison=scorecard_comparison,card_consistency_score=card_score,consistency_inputs=[[n,k,v] for (n,k),v in consistency.items()],expected_steps=expected_steps,expected_overall=expected_overall)
save(WORK/'hybrid_data.json',result)
save(OUT/'evidence/hybrid_merge_checks.json',tests)
save(OUT/'evidence/source_fingerprints.json',dict(source_a=result['source_a_summary'],source_b=result['source_b_summary']))
save(OUT/'evidence/proposed_fields.json',list(proposals.values()))
print('HYBRID',json.dumps(dict(original_fields=len(physical),hybrid_fields=len(hybrid_dict),proposals=len(proposals),imported_tables=len(imported),comparison_rows=len(comparisons),source_b_placeholder_definitions=placeholder_count,checks=len(tests),comparison_scores=[x[:6] for x in compare_stats])))
