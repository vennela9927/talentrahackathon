"""Talentra discovery/model/proof evidence. Standard-library only; synthetic data."""
import csv, hashlib, json, random, re, sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'reproduced'
(ROOT / 'work').mkdir(parents=True, exist_ok=True)
OUT = ROOT
EVIDENCE = OUT / 'evidence'
EVIDENCE.mkdir(parents=True, exist_ok=True)
DATE = '2026-10-27'
sources = [
 ['D1','Talentra Database Design Hackathon Docket','1_Talentra-Database-Design-Hackathon-Docket.pdf','pp.2-6','Product requirements and scale. Delivery backlog is a different numbering system.'],
 ['D2','Data-Driven Development Framework','2_DATA-DRIVEN-DEVELOPMENT-FRAMEWORK.pdf','pp.5-13,19-20','Scenario richness before volume; evidence-led iteration. Pilot security exclusion does not override Talentra.'],
 ['D3','Data-Driven Development Lifecycle Detailed Playbook','3_Talencia Global - Data-Driven Development Lifecycle - Detailed Playbook.pdf','pp.4,6-10','Authoritative step numbering. Steps 1-16 only; G3 requires 17-21 and is not claimed.'],
 ['D4','Premium Talent Accelerator Student Learning Notes','4_Premium-Talent-Accelerator-Program-Student-Learning-Notes.pdf','pp.11,15-24,30-37,41','Nonlinear schemas, connected goals, QFE, field-level reasoning and peer review.'],
 ['D5','Control the Output Process Playbook v2','5_Talencia Global - Control the Output - Process Playbook v2.pdf','pp.5,8,12-13,17-22','L1-L4 hierarchy; eight dimensions; 0-5 scale; critical gates; independent review.'],
 ['W1','Naukri profile guidance','https://www.naukri.com/blog/how-to-set-your-naukri-profile/','Accessed '+DATE,'Candidate education, employment, key skills and profile data.'],
 ['W2','Naukri recruiter job posting','https://www.naukri.com/blog/recruiter-job-posting/','Accessed '+DATE,'Job posting, screening questions and responses.'],
 ['W3','foundit help','https://www.foundit.in/info/help','Accessed '+DATE,'Candidate profile/resume and search fields.'],
 ['W4','foundit privacy','https://www.foundit.in/info/privacy','Accessed '+DATE,'Candidate/employer information categories.'],
 ['W5','LinkedIn profile sections','https://www.linkedin.com/help/linkedin/answer/a564064','Accessed '+DATE,'Candidate profile field coverage.'],
 ['W6','LinkedIn company pages','https://business.linkedin.com/marketing-solutions/linkedin-pages','Accessed '+DATE,'Employer company information.'],
 ['W7','foundit formerly Monster','https://www.foundit.in/info/about-us','Accessed '+DATE,'India Monster comparison uses foundit and preserves the original benchmark label.'],
 ['W8','PostgreSQL 18 constraints','https://www.postgresql.org/docs/18/ddl-constraints.html','Accessed '+DATE,'FK, UNIQUE, CHECK and exclusion design reference.'],
 ['W9','PostgreSQL 18 locking','https://www.postgresql.org/docs/18/explicit-locking.html','Accessed '+DATE,'Row locking design for serialized limit checks.'],
]

steps = [
 ('Requirement Analysis Docket',1,'Every brief requirement has an ID, actor, source and an explicit disposition.'),
 ('Stakeholders, Personas and Roles',1,'All human/system actors and enforceable privileges are specified.'),
 ('Feature Discovery',1,'Features trace to requirements; three competitors have evidence or explicit unknowns.'),
 ('NFR Discovery',1,'Each quality target has a number, unit, measurement and source status.'),
 ('Business Workflow Analysis',1,'Every must-have feature maps to a workflow with exceptions and outputs.'),
 ('Entities Discovery',2,'Every workflow operation references a named entity with an owner.'),
 ('Attributes Discovery',2,'Every attribute has type, example, nullability and stored/derived status.'),
 ('Entity Lifecycle and State Machines',2,'All states have valid entry/exit or are explicitly terminal; illegal moves are tested.'),
 ('Database, Tables and Relationships Discovery',2,'Every relationship states optionality, both cardinalities and referential actions.'),
 ('Data Dictionary v1',2,'Fields have definitions, domains, ownership, examples, classification and rule links.'),
 ('Data Rules and Constraints Discovery',2,'Each rule has an ID, enforcement point, failure behaviour and tests.'),
 ('Data Classification and Privacy',2,'Personal/sensitive columns have masking, retention, consent and erasure designs.'),
 ('Data Volumetrics and Distribution Profile',3,'Each table has launch/year-1/year-3 volumes, distribution and reasoning.'),
 ('Sample Data Generation (Discovery)',3,'A seeded generator emits reproducible synthetic rows plus isolated invalid cases.'),
 ('Test Suite v1 - Data',3,'Every catalogue rule has positive and negative cases with actual results.'),
 ('Schema Coverage against Business Workflow',3,'Every workflow operation maps to storage, retrieval and audit or an owned gap.'),
]

req_specs = [
 ('Identity','Candidate','Register, authenticate and manage own profile','Registration succeeds only for the subject user; recruiter cannot create candidate accounts','identity',2),
 ('Profile','Candidate','Store personal and contact details','Names support Unicode; email normalized; phone follows E.164','profile',3),
 ('Profile','Candidate','Maintain education, experience, skills and languages','Each repeating group uses a child/junction entity','profile',3),
 ('Profile','Candidate','Create resume versions and use templates','Immutable version points to private object storage and a content hash','profile',3),
 ('Profile','Candidate','Record self-assessments, courses and projects','Assessment attempt, score and project outcomes retained separately','profile',3),
 ('Organisation','Employer','Register and verify employers and clients','Verification token, status and country-qualified identifier recorded','organisation',2),
 ('Organisation','Account Admin','Maintain account hierarchy and recruiter membership','Effective-dated membership constrains recruiter to their organisation','organisation',3),
 ('Jobs','Employer','Post requirements for all eight employment categories','Employment category, positions, publish state and consultant openness stored','jobs',2),
 ('Jobs','Employer','Attach questionnaires to requirements','Question type, order and per-application answers persist','jobs',2),
 ('Applications','Candidate','Search jobs and apply with status tracking','One application per candidate and requirement; history appended','jobs',2),
 ('Applications','Recruiter','Progress shortlist, interview, offer and joining','Only guarded transitions succeed and create status history','jobs',3),
 ('Sourcing','Recruiter','Source candidates and send bulk outreach','Blocked candidates are excluded before recipient creation and delivery','sourcing',2),
 ('Sourcing','Consultant','Request sourcing access and submit shortlists','Requirement must be open to consultants and request accepted','sourcing',2),
 ('Privacy','Candidate','Block employers, recruiters and consultants','Blocked party cannot search, view, download or message the candidate','identity',2),
 ('Credits','Employer','Recharge wallet and consume credits','Atomic debit and download/outreach event share idempotency key','commerce',2),
 ('Notifications','Candidate','Manage alerts, notification and privacy preferences','Opt-out is checked before enqueue and delivery','notifications',3),
 ('Support','Candidate','Open support tickets and browse FAQs','Ticket lifecycle and localized FAQ publication supported','notifications',2),
 ('Gig','Gig Worker','Maintain separate service and availability profile','Worker profile is distinct from candidate employment profile','gig',2),
 ('Gig','Requester','Create gigs with window and fixed or rate pricing','End follows start; monetary amount uses decimal and currency','gig',2),
 ('Gig','Gig Worker','Apply to a gig for requester decision','Applications flow worker to requester only','gig',2),
 ('Gig','Requester','Handoff accepted gig and reconcile external status','Store external assignment reference; no internal fulfilment engine','gig',2),
 ('Gig','Integration Worker','Import estimated, total and projected earnings','External source and refresh timestamp are mandatory','gig',2),
 ('Gig','Requester','Favourite, blacklist and rate workers','Only completed assignments can be rated by their requester','gig',2),
 ('Licensing','Account Admin','Allocate seats within explicit licence limits','Serialize allocation on licence row; positive seat/device limits','licensing',3),
 ('Licensing','Candidate','Login within active-session and device limits','Atomic lock/count/insert; expired or revoked sessions excluded','licensing',4),
 ('Licensing','Account Admin','Revoke devices and sessions with login history','Revocation ends sessions and records an audit event','licensing',4),
 ('Subscriptions','Account Admin','Subscribe, renew and cancel plans','Periods for one licence cannot overlap; entitlements versioned','commerce',3),
 ('Payments','Payment Worker','Record orders, payments, invoices and refunds','Reference-only gateway integration; no raw card/bank data','commerce',3),
 ('History','Recruiter','Record profile views and downloads','Append-only actor, subject, timestamp and debit reference','profile',3),
 ('History','Candidate','Record searches, application and profile activity','Events link subject to purpose and retention policy','profile',3),
 ('Community','Candidate','Publish posts, react and track referrals','Posts/reactions and referral events have clear ownership','notifications',3),
 ('Master data','Admin','Manage multilingual enumerations and locations','Lookup code, active flag, order and translated display names','master',4),
 ('Analytics','Analyst','Produce hiring and conversion analytics','Facts have declared grain, dimensions, source lineage and refresh','analytics',6),
 ('Audit','Auditor','Audit sensitive actions and system errors','Append-only event, actor, subject, outcome and correlation ID','identity',4),
 ('Standards','Data Engineer','Enforce all ten docket standard groups','Compliance register links standard to schema and enforcement','master',4),
 ('Integration','Integration Worker','Define failure, idempotency and ownership for external exchanges','Boundary register includes source of truth, retry and exchange audit','integration',5),
 ('Scale','Data Engineer','Design for 10 million candidates and 100 million applications','Full-scale sizing is a target; direct laptop benchmark is later scope','analytics',6),
]
requirements=[]
for i,(section,actor,statement,accept,module,page) in enumerate(req_specs,1):
 requirements.append(dict(id=f'REQ-{i:03}',section=section,actor=actor,statement=statement,acceptance=accept,module=module,priority='Should' if i in [4,5,17,30,31] else 'Must',source=f'D1 p.{page}',basis='Source requirement'))

decisions = [
 ['DEC-001','Step numbering','Use D3 steps 1-16; phase 3 is partial','Docket phases/backlogs are database delivery milestones, not these lifecycle steps','D3 pp.4,6-10','Adopted design'],
 ['DEC-002','Database provider','PostgreSQL 18','Relational integrity, row locking and exclusion constraints fit limits and period overlaps','W8; W9','Adopted design'],
 ['DEC-003','Gig boundary','Separate gig tables sharing identity, organisation and reference data','Different worker profile, one-way application and external fulfilment avoid nullable overload of job tables','D1 p.2','Adopted design'],
 ['DEC-004','Security precedence','Include docket security in discovery/model','D2 pilot defers security, but D1 product requires it and D3 step 12 explicitly includes it','D1 pp.2-4; D2 pp.4,19; D3 p.8','Resolved conflict'],
 ['DEC-005','Scale','Sample proof only at step 14; retain laptop/full-scale profiles','1M candidates/100K jobs/5M applications are later benchmark scope, not a completed benchmark here','D1 p.6; D3 pp.9,11','Scope boundary'],
 ['DEC-006','Retention','Proposed operational policy; owner approval required','Retention values are engineering assumptions, not legal conclusions','D1 p.4; ASSUMPTION','Proposed policy'],
 ['DEC-007','Unknown values','Use UNKNOWN in documents, SQL NULL with reason/domain in database','Prevents text sentinels in typed columns while making documentary unknowns explicit','D1 p.4; D5 p.9','Resolved representation'],
 ['DEC-008','Audit history','Immutable event content; erase personal payload through token vault','Deletion of identity mapping avoids silently rewriting an append-only event','D1 p.4; ASSUMPTION','Adopted design'],
 ['DEC-009','Enumeration domains','Shared typed lookup catalogue with reference-domain validation','Every fixed set has translated names and rejects use of a code from the wrong domain','D1 p.4','Adopted design'],
 ['DEC-010','Missing references','Do not invent docket Sections 8, 10 or 12','Supplied docket references KPI and NFR sections that are absent from its 12 pages','D1 pp.2,6,11','Source gap'],
]
questions=[
 ['Q-001','Product Owner','Approve latency, availability, RTO/RPO targets missing from supplied source','P0','Use proposed NFRs; no measured claim','Open'],
 ['Q-002','Privacy Owner','Approve consent bases, erasure exceptions and retention periods','P0','Implement configurable policy; synthetic data only','Open'],
 ['Q-003','Integration Owner','Provide payment and fulfilment event schemas and sandbox contracts','P1','Reference-only contracts; no live calls','Open'],
 ['Q-004','Mentor','Perform independent review and author understanding interview','P1','Unassessed dimensions remain zero in conservative scoring','Open'],
 ['Q-005','Product Owner','Confirm missing KPI catalogue and future employer sub-roles','P2','Candidate pipeline KPIs proposed; sub-roles explicitly deferred','Open'],
]
scope=[
 ['SCP-001','Included','Lifecycle steps 1-16','Schemas, scorecards, completed analysis/model/data proof and workflow coverage','D3 pp.6-9'],
 ['SCP-002','Excluded','Steps 17-46 and G3 sign-off','Refinement, baseline physical deployment, scale tests, product UI and release are outside the requested cap','D3 pp.10-21'],
 ['SCP-003','Included','All eleven Talentra data modules','Tier 1 mandatory and Tier 2 expected domains represented','D1 pp.3,6'],
 ['SCP-004','Excluded','Tier 3 optional domain expansion','Salary benchmarks, company reviews, trending snapshots and feature flags deferred','D1 p.3'],
 ['SCP-005','Excluded','Live external integrations and real PII','Only synthetic examples and integration references','D1 pp.2,5'],
 ['SCP-006','Included','Offline HTML ratings website','The requested project dashboard is a reporting artifact','User request item 4'],
]

actors_specs=[
 ('Super Admin','Platform ownership and emergency controls','Approve platform configuration; audited emergency access','Monthly','identity','REQ-034'),
 ('Admin','Master data and verification operations','Manage reference data; scoped verification','Daily','master','REQ-032'),
 ('Account Admin','Tenant seats and billing','Manage own organisation account, licence and subscription','Daily','licensing','REQ-024'),
 ('Guest','Evaluate public job opportunities','Read published public jobs only','Occasional','jobs','REQ-008'),
 ('Candidate','Build profile and find work','Maintain self; apply; block parties; control preferences','Daily','profile','REQ-001'),
 ('Employer','Publish requirements and hire','Own-organisation jobs; requester gig decisions','Daily','organisation','REQ-006'),
 ('Recruiter','Source and progress candidates','Assigned-company requirements only; no candidate registration','Daily','jobs','REQ-011'),
 ('Consultant','Source on approved open requirements','Accepted sourcing requests only','Daily','sourcing','REQ-013'),
 ('Placement Officer','Support a campus hiring cohort','Consented cohort reporting; no unrestricted candidate editing','Weekly','profile','REQ-008'),
 ('Gig Worker','Offer services and complete gigs','Own gig profile and applications','Daily','gig','REQ-018'),
 ('Requester','Select gig workers','Own gigs, favourites, blacklist and completed-gig ratings','Daily','gig','REQ-023'),
 ('Auditor','Review sensitive actions','Read-only redacted audit with purpose and access log','Weekly','identity','REQ-034'),
 ('Support Agent','Resolve tickets','Assigned tickets and masked account context','Daily','notifications','REQ-017'),
 ('Analyst','Inspect hiring KPIs','Aggregated or pseudonymized facts only','Weekly','analytics','REQ-033'),
 ('Integration Worker','Reconcile provider events','Service identity restricted to owned event types','Scheduled','integration','REQ-036'),
 ('Payment Worker','Reconcile payment status','Verify signed events; append payments and ledger entries','Event-driven','commerce','REQ-028'),
 ('Retention Worker','Apply approved erasure schedules','Erase or unlink expired personal data with evidence','Daily','identity','REQ-035'),
 ('Data Engineer','Own contracts and data quality','Version dictionary, datasets and rules','Daily','master','REQ-035'),
]
actors=[dict(id=f'ACT-{i:02}',name=a,goal=g,permission=p,frequency=f,module=m,requirement=r) for i,(a,g,p,f,m,r) in enumerate(actors_specs,1)]
permissions=[]
for i,a in enumerate(actors,1):
 permissions.append([f'PERM-{i:03}',a['name'],a['permission'],'Allow within scope','Database grants/RLS plus service authorization','Cross-tenant or non-owner attempts denied; audit outcome',a['requirement']])
permissions += [
 ['PERM-019','Recruiter','Register candidate on behalf','Deny','Registration service plus database writer role','Candidate self-registration principal must match subject','REQ-001'],
 ['PERM-020','Blocked party','Read blocked candidate through any endpoint','Deny','Central visibility policy for search/view/export/outreach','Block checked before each operation including send','REQ-014'],
 ['PERM-021','Consultant','Act on closed-to-consultants requirement','Deny','Transaction re-check of job_requirement.open_to_consultant','Reject stale authorization and log','REQ-013'],
 ['PERM-022','Application user','Update/delete ledger or audit history','Deny','Revoke UPDATE/DELETE; immutable storage interface','Correction is new event referencing original','REQ-034'],
]

module_names={'master':'Master data','profile':'Profile','jobs':'Jobs and Applications','identity':'Administration','organisation':'Organisation and account','gig':'Gig marketplace','licensing':'Licences seats devices sessions','sourcing':'Sourcing and consultant requests','commerce':'Subscriptions wallet payments downloads','notifications':'Notifications preferences community','analytics':'Analytics and reporting'}

# Compact model notation: name:type?@reference. Every FK target exists in this catalogue.
model_specs={
 'master': {
 'reference_domain':'code:code description:description',
 'reference_value':'reference_domain_id:id@reference_domain code:code label_key:code active:bool sort_order:count',
 'ui_translation':'label_key:code language_code:language translated_text:description',
 'country':'code:country name:person_name',
 'state':'country_id:id@country code:code name:person_name',
 'city':'state_id:id@state name:person_name latitude:latitude? longitude:longitude? coordinate_source:description?',
 'skill':'code:code name:person_name',
 'qualification':'code:code name:person_name',
 'industry':'code:code name:person_name',
 'job_role':'code:code name:person_name',
 },
 'identity': {
 'app_user':'email:email person_name:person_name status_reference_value_id:id@reference_value preferred_language:language',
 'credential':'app_user_id:id@app_user password_hash:secret changed_at:timestamp',
 'access_role':'code:code name:person_name',
 'permission':'code:code resource_name:code action_name:code',
 'user_role':'app_user_id:id@app_user access_role_id:id@access_role',
 'role_permission':'access_role_id:id@access_role permission_id:id@permission',
 'consent_record':'app_user_id:id@app_user purpose_reference_value_id:id@reference_value policy_version:code granted_at:timestamp revoked_at:timestamp?',
 'blocking_entry':'blocker_app_user_id:id@app_user blocked_app_user_id:id?@app_user blocked_organisation_id:id?@organisation',
 'audit_event':'actor_app_user_id:id?@app_user action_code:code subject_token:token outcome_reference_value_id:id@reference_value correlation_key:code occurred_at:timestamp',
 'system_error':'error_code:code correlation_key:code sanitized_message:description occurred_at:timestamp',
 'integration_event':'provider_code:code provider_event_key:code payload_hash:token status_reference_value_id:id@reference_value received_at:timestamp',
 },
 'organisation': {
 'account':'name:person_name status_reference_value_id:id@reference_value',
 'organisation':'account_id:id@account parent_organisation_id:id?@organisation name:person_name industry_id:id?@industry status_reference_value_id:id@reference_value',
 'organisation_location':'organisation_id:id@organisation city_id:id@city address_text:description',
 'organisation_identifier':'organisation_id:id@organisation country_id:id@country type_reference_value_id:id@reference_value identifier_token:token masked_identifier:code',
 'verification_record':'organisation_id:id@organisation provider_token:token outcome_reference_value_id:id@reference_value verified_at:timestamp?',
 'recruiter_membership':'organisation_id:id@organisation app_user_id:id@app_user valid_from:timestamp valid_to:timestamp?',
 'account_administrator':'account_id:id@account app_user_id:id@app_user valid_from:timestamp valid_to:timestamp?',
 },
 'profile': {
 'candidate_profile':'app_user_id:id@app_user city_id:id?@city headline:description? birth_date:date? status_reference_value_id:id@reference_value content_language:language',
 'candidate_contact':'candidate_profile_id:id@candidate_profile phone_number:phone? country_id:id?@country contact_email:email?',
 'candidate_education':'candidate_profile_id:id@candidate_profile qualification_id:id@qualification institution_name:person_name start_date:date end_date:date?',
 'candidate_experience':'candidate_profile_id:id@candidate_profile employer_name:person_name role_name:person_name start_date:date end_date:date?',
 'candidate_skill':'candidate_profile_id:id@candidate_profile skill_id:id@skill proficiency_reference_value_id:id@reference_value',
 'candidate_language':'candidate_profile_id:id@candidate_profile language_code:language proficiency_reference_value_id:id@reference_value',
 'resume_template':'code:code name:person_name template_object_key:object_key',
 'resume_version':'candidate_profile_id:id@candidate_profile resume_template_id:id?@resume_template version_number:count object_key:object_key content_hash:token content_language:language',
 'candidate_project':'candidate_profile_id:id@candidate_profile title:person_name role_name:person_name start_date:date end_date:date? outcome:description?',
 'assessment':'code:code name:person_name maximum_score:ratio',
 'assessment_attempt':'candidate_profile_id:id@candidate_profile assessment_id:id@assessment score:ratio completed_at:timestamp?',
 'course':'code:code name:person_name provider_name:person_name',
 'course_enrolment':'candidate_profile_id:id@candidate_profile course_id:id@course status_reference_value_id:id@reference_value enrolled_at:timestamp',
 'profile_completion':'candidate_profile_id:id@candidate_profile rule_version:code completion_percentage:percentage calculated_at:timestamp',
 'profile_view_event':'actor_app_user_id:id@app_user candidate_profile_id:id@candidate_profile viewed_at:timestamp',
 'candidate_activity':'candidate_profile_id:id@candidate_profile action_reference_value_id:id@reference_value occurred_at:timestamp',
 'candidate_bookmark':'actor_app_user_id:id@app_user candidate_profile_id:id@candidate_profile status_reference_value_id:id@reference_value',
 'referral':'referrer_app_user_id:id@app_user candidate_profile_id:id@candidate_profile referral_key:code',
 },
 'jobs': {
 'job_requirement':'organisation_id:id@organisation job_role_id:id@job_role employment_type_reference_value_id:id@reference_value work_type_reference_value_id:id@reference_value city_id:id?@city title:person_name description:body positions:count status_reference_value_id:id@reference_value publish_state_reference_value_id:id@reference_value open_to_consultant:bool salary_min:money? salary_max:money? currency_code:currency? salary_disclosure_reference_value_id:id@reference_value source_timezone:code content_language:language',
 'job_skill':'job_requirement_id:id@job_requirement skill_id:id@skill mandatory:bool',
 'job_question':'job_requirement_id:id@job_requirement question_text:description answer_type_reference_value_id:id@reference_value sort_order:count mandatory:bool',
 'job_application':'job_requirement_id:id@job_requirement candidate_profile_id:id@candidate_profile resume_version_id:id?@resume_version status_reference_value_id:id@reference_value applied_at:timestamp',
 'application_answer':'job_application_id:id@job_application job_question_id:id@job_question answer_text:description',
 'application_status_event':'job_application_id:id@job_application from_reference_value_id:id?@reference_value to_reference_value_id:id@reference_value actor_app_user_id:id@app_user occurred_at:timestamp',
 'candidate_shortlist':'job_requirement_id:id@job_requirement candidate_profile_id:id@candidate_profile owner_app_user_id:id@app_user',
 'interview':'job_application_id:id@job_application scheduled_at:timestamp status_reference_value_id:id@reference_value',
 'job_offer':'job_application_id:id@job_application offered_amount:money currency_code:currency expires_at:timestamp status_reference_value_id:id@reference_value',
 'joining_record':'job_application_id:id@job_application joined_on:date confirmed_by_app_user_id:id@app_user',
 'job_search_event':'candidate_profile_id:id?@candidate_profile search_text:description searched_at:timestamp',
 'job_bookmark':'candidate_profile_id:id@candidate_profile job_requirement_id:id@job_requirement',
 },
 'gig': {
 'gig_worker_profile':'app_user_id:id@app_user bio:description? status_reference_value_id:id@reference_value',
 'gig_service':'gig_worker_profile_id:id@gig_worker_profile skill_id:id@skill charge_amount:money currency_code:currency rate_unit_reference_value_id:id@reference_value',
 'gig_availability':'gig_worker_profile_id:id@gig_worker_profile start_at:timestamp end_at:timestamp source_timezone:code',
 'gig_request':'requester_organisation_id:id@organisation title:person_name start_at:timestamp end_at:timestamp price_amount:money currency_code:currency pricing_type_reference_value_id:id@reference_value status_reference_value_id:id@reference_value source_timezone:code',
 'gig_application':'gig_request_id:id@gig_request gig_worker_profile_id:id@gig_worker_profile status_reference_value_id:id@reference_value applied_at:timestamp',
 'gig_assignment':'gig_application_id:id@gig_application gig_worker_profile_id:id@gig_worker_profile start_at:timestamp end_at:timestamp external_handoff_key:token? status_reference_value_id:id@reference_value',
 'gig_project':'gig_worker_profile_id:id@gig_worker_profile gig_assignment_id:id?@gig_assignment title:person_name role_name:person_name start_date:date end_date:date? outcome:description?',
 'gig_worker_list_entry':'requester_organisation_id:id@organisation gig_worker_profile_id:id@gig_worker_profile list_type_reference_value_id:id@reference_value',
 'gig_rating':'gig_assignment_id:id@gig_assignment requester_app_user_id:id@app_user rating:rating comment_text:description?',
 'gig_earnings_snapshot':'gig_assignment_id:id@gig_assignment provider_reference:token estimated_amount:money total_amount:money projected_amount:money currency_code:currency reconciled_at:timestamp',
 },
 'licensing': {
 'licence':'account_id:id@account max_user_count:count max_device_per_user:count status_reference_value_id:id@reference_value',
 'licence_seat':'licence_id:id@licence app_user_id:id@app_user allocated_at:timestamp released_at:timestamp?',
 'registered_device':'app_user_id:id@app_user device_token:token registered_at:timestamp revoked_at:timestamp?',
 'user_session':'app_user_id:id@app_user registered_device_id:id@registered_device licence_id:id@licence started_at:timestamp last_activity_at:timestamp expires_at:timestamp ended_at:timestamp?',
 'login_attempt':'app_user_id:id?@app_user device_token:token outcome_reference_value_id:id@reference_value attempted_at:timestamp',
 'revocation_event':'app_user_id:id@app_user registered_device_id:id?@registered_device user_session_id:id?@user_session actor_app_user_id:id@app_user occurred_at:timestamp',
 },
 'sourcing': {
 'sourcing_request':'job_requirement_id:id@job_requirement consultant_app_user_id:id@app_user status_reference_value_id:id@reference_value requested_at:timestamp',
 'sourcing_decision':'sourcing_request_id:id@sourcing_request employer_app_user_id:id@app_user decision_reference_value_id:id@reference_value decided_at:timestamp',
 'sourcing_shortlist':'sourcing_request_id:id@sourcing_request candidate_shortlist_id:id@candidate_shortlist',
 'outreach_batch':'job_requirement_id:id@job_requirement actor_app_user_id:id@app_user idempotency_key:code status_reference_value_id:id@reference_value',
 'outreach_recipient':'outreach_batch_id:id@outreach_batch candidate_profile_id:id@candidate_profile wallet_ledger_entry_id:id?@wallet_ledger_entry status_reference_value_id:id@reference_value',
 },
 'commerce': {
 'subscription_plan':'code:code name:person_name price_amount:money currency_code:currency',
 'plan_entitlement':'subscription_plan_id:id@subscription_plan entitlement_reference_value_id:id@reference_value quantity:count',
 'subscription_period':'licence_id:id@licence subscription_plan_id:id@subscription_plan start_at:timestamp end_at:timestamp status_reference_value_id:id@reference_value',
 'payment_order':'account_id:id@account subscription_period_id:id?@subscription_period amount:money currency_code:currency idempotency_key:code status_reference_value_id:id@reference_value',
 'payment_event':'payment_order_id:id@payment_order provider_event_key:code provider_reference:token amount:money currency_code:currency status_reference_value_id:id@reference_value',
 'invoice':'payment_order_id:id@payment_order invoice_number:code total_amount:money currency_code:currency issued_at:timestamp',
 'invoice_line':'invoice_id:id@invoice line_number:count description:description line_amount:money currency_code:currency',
 'refund':'payment_order_id:id@payment_order original_payment_event_id:id@payment_event amount:money currency_code:currency idempotency_key:code status_reference_value_id:id@reference_value',
 'wallet':'account_id:id@account currency_code:currency',
 'wallet_ledger_entry':'wallet_id:id@wallet payment_event_id:id?@payment_event original_wallet_ledger_entry_id:id?@wallet_ledger_entry signed_amount:money currency_code:currency entry_type_reference_value_id:id@reference_value idempotency_key:code occurred_at:timestamp',
 'profile_download_event':'actor_app_user_id:id@app_user candidate_profile_id:id@candidate_profile wallet_ledger_entry_id:id@wallet_ledger_entry downloaded_at:timestamp idempotency_key:code',
 },
 'notifications': {
 'user_preference':'app_user_id:id@app_user language_code:language privacy_reference_value_id:id@reference_value',
 'notification_preference':'app_user_id:id@app_user channel_reference_value_id:id@reference_value enabled:bool',
 'job_alert_preference':'app_user_id:id@app_user job_role_id:id?@job_role city_id:id?@city enabled:bool',
 'notification':'recipient_app_user_id:id@app_user template_key:code purpose_reference_value_id:id@reference_value expires_at:timestamp',
 'notification_delivery':'notification_id:id@notification provider_reference:token? status_reference_value_id:id@reference_value attempted_at:timestamp',
 'community_post':'author_app_user_id:id@app_user body_text:body content_language:language status_reference_value_id:id@reference_value',
 'post_reaction':'community_post_id:id@community_post app_user_id:id@app_user reaction_reference_value_id:id@reference_value',
 'support_ticket':'requester_app_user_id:id@app_user assigned_app_user_id:id?@app_user subject:description status_reference_value_id:id@reference_value',
 'faq':'label_key:code answer_key:code status_reference_value_id:id@reference_value',
 'referral_event':'referral_id:id@referral event_reference_value_id:id@reference_value occurred_at:timestamp',
 'social_share_event':'app_user_id:id@app_user job_requirement_id:id@job_requirement channel_reference_value_id:id@reference_value shared_at:timestamp',
 },
 'analytics': {
 'an_dim_date':'calendar_date:date year_number:count month_number:count',
 'an_dim_candidate':'candidate_profile_id:id?@candidate_profile pseudonymous_key:token valid_from:timestamp valid_to:timestamp?',
 'an_dim_organisation':'organisation_id:id@organisation valid_from:timestamp valid_to:timestamp?',
 'an_fact_application':'job_application_id:id@job_application an_dim_date_id:id@an_dim_date an_dim_candidate_id:id@an_dim_candidate an_dim_organisation_id:id@an_dim_organisation event_count:count',
 'an_fact_credit':'wallet_ledger_entry_id:id@wallet_ledger_entry an_dim_date_id:id@an_dim_date signed_amount:money currency_code:currency',
 }
}

domains={
 'id':('bigint','64-bit surrogate identity',1,'Internal','Positive unique surrogate; natural keys are separate'),
 'code':('varchar(80)','Stable code, not a user label','synthetic_code','Internal','Nonempty; max 80; defined code namespace'),
 'description':('varchar(2000)','Bounded explanatory text','Synthetic example','Internal','UTF-8; max 2000 characters'),
 'person_name':('varchar(150)','Unicode name without word-order assumption','Asha Synthetic','Personal','UTF-8; 1-150 characters'),
 'email':('varchar(254)','Normalized electronic mail address','candidate001@example.invalid','Personal','Lowercase; max 254; basic shape; unique for login'),
 'phone':('varchar(16)','International telephone number','+15550000001','Personal','E.164 + followed by 8-15 digits; synthetic only'),
 'country':('char(2)','Country code','IN','Public','2 uppercase ASCII letters'),
 'language':('varchar(10)','Content/UI language code','en','Public','BCP47-style tag; supported languages in reference catalogue'),
 'currency':('char(3)','Monetary currency code','INR','Public','3 uppercase letters from currency reference domain'),
 'money':('numeric(18,2)','Fixed-precision monetary amount','100.00','Internal','No float; companion currency; signed only for ledger'),
 'percentage':('numeric(5,2)','Percentage from 0 through 100','80.00','Internal','0 <= value <= 100'),
 'ratio':('numeric(12,4)','Nonnegative assessment value','4.0000','Internal','0 <= score <= configured assessment maximum'),
 'rating':('smallint','Completed-gig rating',5,'Public','Integer 1 through 5'),
 'count':('integer','Integer quantity',1,'Internal','Nonnegative; positions and licence limits strictly positive'),
 'bool':('boolean','Explicit true/false flag',False,'Internal','NOT NULL; default false; enabling requires an explicit authorized setting'),
 'date':('date','Calendar date','2026-10-01','Personal','ISO 8601 date; no time'),
 'timestamp':('timestamptz','UTC instant','2026-10-27T00:00:00Z','Internal','ISO 8601 UTC; source timezone separately where meaningful'),
 'token':('varchar(255)','Opaque reference or cryptographic hash','synthetic_token_001','Sensitive','No raw national ID/card data; max255; encrypted provider references'),
 'secret':('varchar(255)','Credential hash, never plaintext','argon2id$synthetic_test_only','Sensitive','Argon2id hash; protected access; synthetic sample is not a real hash'),
 'object_key':('varchar(512)','Private object-store reference','synthetic/resume_001.pdf','Personal','Private object; signed access after authorization; max512'),
 'body':('text','Long-form authored content','Synthetic job or resume body','Internal','Unbounded text justified for description/body; sanitized display'),
 'latitude':('numeric(9,6)','Latitude in decimal degrees','12.971600','Public','-90 through 90; source required when coordinates present'),
 'longitude':('numeric(9,6)','Longitude in decimal degrees','77.594600','Public','-180 through 180; source required when coordinates present'),
}
immutable={'audit_event','system_error','integration_event','consent_record','application_status_event','profile_view_event','candidate_activity','login_attempt','revocation_event','payment_event','wallet_ledger_entry','profile_download_event','notification_delivery','referral_event','social_share_event','gig_earnings_snapshot'}
entities=[]; attributes=[]; relationships=[]
for module,tables in model_specs.items():
 for table,spec in tables.items():
  eid=f'ENT-{len(entities)+1:03}'
  retention='90 days' if any(w in table for w in ['session','login_attempt','search_event','activity','delivery','system_error']) else ('7 years proposed, tokenized' if table in immutable or module=='commerce' else 'Until erasure or 24 months inactivity')
  entities.append(dict(id=eid,table=table,module=module,definition=table.replace('_',' ').capitalize()+' records for '+module_names[module],owner=module_names[module]+' owner',deletion='Append-only with retention purge' if table in immutable else 'Soft delete plus scheduled erasure',retention=retention,requirement=next((r['id'] for r in requirements if r['module']==module),'REQ-036'),source='D1 pp.2-6; design decision DEC-002/003'))
  tokens=['id:id']+spec.split()+['created_at:timestamp','created_by:id?@app_user','updated_at:timestamp','updated_by:id?@app_user']
  if table not in immutable: tokens+=['deleted_at:timestamp?']
  for token in tokens:
   name,rest=token.split(':',1); dom,_,ref=rest.partition('@'); nullable='?' in dom; dom=dom.replace('?','')
   dtype,meaning,example,cl,validation=domains[dom]
   if name=='id': example=1
   if name.endswith('_reference_value_id'): validation+='; referenced value must belong to the declared field domain'
   null_reason=('Unknown until event occurs or optional user-supplied field; do not substitute zero/empty/NA' if nullable else 'Not nullable')
   if name in ['created_by','updated_by']: null_reason='NULL only for signed system/bootstrap operations; correlation identifies service principal'
   if name=='deleted_at': null_reason='NULL means active record; timestamp means excluded from default queries'
   if name in ['salary_min','salary_max','currency_code'] and table=='job_requirement': null_reason='NULL only when salary disclosure lookup says unknown or not_applicable'
   classification='Personal' if ref in ['app_user','candidate_profile','gig_worker_profile'] or name in ['birth_date','phone_number','contact_email','email','person_name'] or (name=='id' and table in ['app_user','candidate_profile','gig_worker_profile']) else cl
   if name=='name' and module in ['master','organisation','commerce']: classification='Public' if module=='master' else 'Internal'
   attr=dict(id=f'ATT-{len(attributes)+1:04}',entity_id=eid,table=table,column=name,type=dtype,domain=dom,nullable=nullable,null_reason=null_reason,example=example,definition=meaning+'; '+name.replace('_',' ')+' on '+table,classification=classification,storage='Stored',owner=module_names[module]+' owner',validation=validation,default='GENERATED BY DEFAULT AS IDENTITY' if name=='id' else ('false' if dom=='bool' else ('CURRENT_TIMESTAMP' if name in ['created_at','updated_at'] else 'No implicit default')),rule='BR-001; BR-002; BR-003; BR-004; BR-005',source='D1 p.4; DEC-002; DEC-009')
   attributes.append(attr)
   if ref:
    relationships.append(dict(id=f'REL-{len(relationships)+1:03}',child=table,column=name,parent=ref,child_to_parent='0..1' if nullable else '1',parent_to_child='0..N',optional=nullable,on_update='RESTRICT',on_delete='RESTRICT',enforcement='Database FOREIGN KEY',reason='Preserve history and explicit retention order',source='D1 p.4; DEC-002'))

# Cardinality overrides document uniqueness beyond ordinary foreign keys.
one_to_one={('candidate_profile','app_user_id'),('gig_worker_profile','app_user_id'),('credential','app_user_id'),('profile_completion','candidate_profile_id'),('joining_record','job_application_id'),('gig_assignment','gig_application_id'),('gig_rating','gig_assignment_id'),('user_preference','app_user_id'),('an_fact_application','job_application_id'),('an_fact_credit','wallet_ledger_entry_id')}
for rel in relationships:
 if (rel['child'],rel['column']) in one_to_one:
  rel['parent_to_child']='0..1'; rel['enforcement']+=' plus UNIQUE child foreign key'

def rule(rule_id,title,statement,table,mechanism,positive,negative,validator,req='REQ-035',proof='Python contract'):
 return dict(id=rule_id,title=title,statement=statement,table=table,enforcement=mechanism,positive=positive,negative=negative,validator=validator,requirement=req,proof=proof,source='D1 p.4; DEC-002')

rules=[
 rule('BR-001','Naming','All table and column names are defined singular snake_case','all','DDL review + catalogue validator','candidate_profile','Candidate Profiles',lambda x: bool(re.fullmatch(r'[a-z][a-z0-9_]*',x))),
 rule('BR-002','Surrogate identity','Every row has positive bigint surrogate id','all','PRIMARY KEY GENERATED IDENTITY',1,0,lambda x:type(x) is int and x>0),
 rule('BR-003','Foreign key integrity','All referenced parent IDs must exist','all','Database FOREIGN KEY',[1,[1,2]],[3,[1,2]],lambda x:x[0] in x[1],proof='SQLite database'),
 rule('BR-004','Required values','Mandatory attributes reject null','all','NOT NULL','present',None,lambda x:x is not None,proof='SQLite database'),
 rule('BR-005','Bounded text','Bounded text respects domain length','all','VARCHAR limits + contract validation',['Asha',150],['A'*151,150],lambda x:len(x[0])<=x[1]),
 rule('BR-006','Unique email','Login email is lowercase, shaped and at most 254 characters','app_user','UNIQUE email plus CHECK/service normalization','a@example.invalid','A@EXAMPLE.INVALID',lambda x:bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',x)) and x==x.lower() and len(x)<=254,req='REQ-001'),
 rule('BR-007','E.164 phone','Telephone has plus and 8-15 digits','candidate_contact','CHECK plus phone validation','+15550000001','555-0001',lambda x:bool(re.fullmatch(r'\+[1-9][0-9]{7,14}',x)),req='REQ-002'),
 rule('BR-008','Date range','End must be on or after start; NULL end allowed only for ongoing records','candidate_experience, candidate_education','CHECK on dates',['2026-01-01','2026-02-01'],['2026-02-01','2026-01-01'],lambda x:x[1] is None or x[1]>=x[0]),
 rule('BR-009','Money pairing','Monetary values use fixed precision and a companion currency','all money fields','NUMERIC(18,2), currency FK/check',['100.00','INR'],['100.001','INR'],lambda x:bool(re.fullmatch(r'-?\d{1,16}\.\d{2}',x[0])) and bool(re.fullmatch(r'[A-Z]{3}',x[1])),req='REQ-015'),
 rule('BR-010','Salary ordering','Disclosed minimum must not exceed maximum','job_requirement','CHECK salary_min <= salary_max',[100,200],[200,100],lambda x:x[0]<=x[1],req='REQ-008',proof='SQLite database'),
 rule('BR-011','Positive positions','A requirement offers at least one position','job_requirement','CHECK positions > 0',1,0,lambda x:type(x) is int and x>0,req='REQ-008',proof='SQLite database'),
 rule('BR-012','One application','Candidate and requirement pair is unique','job_application','UNIQUE(candidate_profile_id,job_requirement_id)',[[1,1],[[1,2]]],[[1,1],[[1,1]]],lambda x:x[0] not in x[1],req='REQ-010',proof='SQLite database'),
 rule('BR-013','Tenant isolation','Recruiter acts only on own company requirements','job_requirement,recruiter_membership','RLS/service predicate with effective membership',[1,1],[1,2],lambda x:x[0]==x[1],req='REQ-007'),
 rule('BR-014','Candidate self-registration','Recruiter cannot register candidate on behalf','app_user,candidate_profile','Registration service + restricted writer role',['candidate',1,1],['recruiter',1,2],lambda x:x[0]=='candidate' and x[1]==x[2],req='REQ-001'),
 rule('BR-015','Block precedence','Blocked party never receives profile visibility','blocking_entry','Shared authorization predicate + transaction recheck',[False,True],[True,True],lambda x:not x[0] and x[1],req='REQ-014'),
 rule('BR-016','Consultant eligibility','Consultant requires open job plus accepted request','sourcing_request','Lock requirement, recheck openness and accepted request',[True,'accepted'],[False,'accepted'],lambda x:x[0] and x[1]=='accepted',req='REQ-013'),
 rule('BR-017','Gig direction','Only worker applies to requester gig','gig_application','Service privilege + relation design','worker_to_requester','requester_to_worker',lambda x:x=='worker_to_requester',req='REQ-020'),
 rule('BR-018','Gig overlap','Active worker assignments use nonoverlapping half-open windows','gig_assignment','PostgreSQL btree_gist exclusion; active status predicate',[[1,2],[2,3]],[[1,3],[2,4]],lambda x:not(x[0][0]<x[1][1] and x[1][0]<x[0][1]),req='REQ-021'),
 rule('BR-019','Completed gig rating','Only requester rates completed assignment','gig_rating','Authorized transaction verifies assignment and actor',['completed',1,1],['accepted',1,1],lambda x:x[0]=='completed' and x[1]==x[2],req='REQ-023'),
 rule('BR-020','Licence limits','Seat and device limits are positive integers','licence','CHECK max_user_count > 0 AND max_device_per_user > 0',[3,2],[3,0],lambda x:all(type(y) is int and y>0 for y in x),req='REQ-024',proof='SQLite database'),
 rule('BR-021','Seat allocation','Active allocated seat count remains below limit before insert','licence_seat','SELECT licence FOR UPDATE then count+insert in one transaction',[2,3],[3,3],lambda x:x[0]<x[1],req='REQ-024'),
 rule('BR-022','Session limit','Unexpired unrevoked session count stays below per-user limit','user_session','Lock licence then user in fixed order; expire, count, insert atomically',[1,2],[2,2],lambda x:x[0]<x[1],req='REQ-025'),
 rule('BR-023','Device ownership','Session device belongs to session user','user_session,registered_device','Composite UNIQUE device(id,app_user_id) + composite FK',[1,1],[1,2],lambda x:x[0]==x[1],req='REQ-025'),
 rule('BR-024','Subscription overlap','Licence subscription periods cannot overlap','subscription_period','EXCLUDE licence WITH =, tstzrange WITH &&',[[1,2],[2,3]],[[1,3],[2,4]],lambda x:not(x[0][0]<x[1][1] and x[1][0]<x[0][1]),req='REQ-027'),
 rule('BR-025','Append-only history','Payment, ledger, audit and history records cannot mutate','wallet_ledger_entry,audit_event,payment_event','REVOKE UPDATE/DELETE plus immutable trigger; privileged retention job','insert','update',lambda x:x=='insert',req='REQ-034',proof='SQLite database'),
 rule('BR-026','Idempotent events','Provider/key duplicate does not produce another side effect','integration_event,payment_event','UNIQUE(provider_code,provider_event_key) and outbox transaction',['evt2',['evt1']],['evt1',['evt1']],lambda x:x[0] not in x[1],req='REQ-036'),
 rule('BR-027','Wallet funds','A debit cannot overdraw the same-currency wallet','wallet_ledger_entry','Lock wallet; sum ledger; conditional append debit',[100,40],[100,101],lambda x:x[0]>=x[1],req='REQ-015'),
 rule('BR-028','Refund limit','Cumulative successful refunds cannot exceed captured payment','refund','Lock original payment; sum succeeded refunds in same currency',[100,80,20],[100,80,21],lambda x:x[1]+x[2]<=x[0],req='REQ-028'),
 rule('BR-029','Invoice reconciliation','Invoice total equals sum of line amounts by currency','invoice,invoice_line','Deferred constraint trigger within invoice transaction',[100,[60,40]],[101,[60,40]],lambda x:x[0]==sum(x[1]),req='REQ-028'),
 rule('BR-030','Notification consent','Delivery allowed only with purpose consent and channel enabled','notification_delivery','Service authorization before enqueue and again before send',[True,True],[True,False],lambda x:all(x),req='REQ-016'),
 rule('BR-031','Lookup domain','Status/reference value must belong to expected domain','reference_value','Composite domain-aware FK or database trigger',['application_status','application_status'],['gig_status','application_status'],lambda x:x[0]==x[1]),
 rule('BR-032','Sensitive references','Raw card, bank and national identifier data is not stored','credential,verification_record,payment_event','Token-only contracts and forbidden-field rejection',{'provider_token':'synthetic'},{'card_number':'4111111111111111'},lambda x:not any(k in x for k in ['card_number','bank_account','national_id']),req='REQ-028'),
 rule('BR-033','Percentage range','Profile completion percentage is 0 through 100','profile_completion','CHECK completion_percentage BETWEEN 0 AND 100',100,101,lambda x:0<=x<=100),
 rule('BR-034','Blocking target','Exactly one blocked user or organisation target is present','blocking_entry','CHECK num_nonnulls(target_user,target_org)=1',[1,None],[1,2],lambda x:sum(y is not None for y in x)==1,req='REQ-014'),
 rule('BR-035','Temporal session','Start <= last activity < expiry; ended sessions are excluded','user_session','CHECK timestamp order plus active-session transaction',[1,2,3],[2,1,3],lambda x:x[0]<=x[1]<x[2],req='REQ-025'),
 rule('BR-036','External earnings','Earnings carry source reference and refreshed timestamp','gig_earnings_snapshot','NOT NULL provider_reference,reconciled_at',['provider1','2026-10-27'],['','2026-10-27'],lambda x:all(bool(y) for y in x),req='REQ-022'),
]

lifecycle_specs={
 'job_requirement': [('draft','published','Employer','verified organisation and valid positions'),('published','paused','Employer','own organisation'),('paused','published','Employer','still valid'),('published','closed','Employer','hiring complete'),('paused','closed','Employer','cancelled'),('draft','closed','Employer','cancelled')],
 'job_application': [('applied','shortlisted','Recruiter','own-company job and visible candidate'),('shortlisted','interviewed','Recruiter','interview recorded'),('interviewed','offered','Recruiter','approved offer exists'),('offered','joined','Recruiter','candidate accepted and joining recorded'),('applied','rejected','Recruiter','reason required'),('shortlisted','rejected','Recruiter','reason required'),('interviewed','rejected','Recruiter','reason required'),('offered','rejected','Recruiter','declined or expired'),('applied','withdrawn','Candidate','self'),('shortlisted','withdrawn','Candidate','self'),('interviewed','withdrawn','Candidate','self'),('offered','withdrawn','Candidate','self')],
 'gig_application':[('applied','accepted','Requester','worker available; not blacklisted'),('applied','rejected','Requester','reason'),('applied','withdrawn','Gig Worker','self')],
 'gig_assignment':[('pending_handoff','active','Integration Worker','idempotent external acceptance'),('pending_handoff','cancelled','Requester','handoff cancelled'),('active','completed','Integration Worker','external completion event'),('active','cancelled','Integration Worker','external cancellation')],
 'subscription_period':[('pending','active','Payment Worker','successful verified payment'),('pending','cancelled','Account Admin','before activation'),('active','expired','Integration Worker','period end reached'),('active','cancelled','Account Admin','cancellation policy')],
 'payment_order':[('created','pending','Payment Worker','provider accepted'),('pending','succeeded','Payment Worker','signed capture event'),('pending','failed','Payment Worker','provider failure'),('created','cancelled','Account Admin','no capture')],
 'sourcing_request':[('requested','accepted','Employer','job open to consultants'),('requested','declined','Employer','reason'),('requested','withdrawn','Consultant','self'),('accepted','closed','Employer','requirement closed')],
 'support_ticket':[('open','in_progress','Support Agent','assigned'),('in_progress','resolved','Support Agent','resolution recorded'),('resolved','closed','Candidate','confirmed or timeout'),('resolved','in_progress','Candidate','reopened')],
 'candidate_profile':[('draft','active','Candidate','required data and consent'),('active','hidden','Candidate','privacy choice'),('hidden','active','Candidate','consent current'),('draft','erased','Retention Worker','erasure request'),('active','erased','Retention Worker','erasure after dependencies'),('hidden','erased','Retention Worker','erasure after dependencies')],
 'user_session':[('active','expired','Integration Worker','expiry reached'),('active','revoked','Account Admin','audited revocation'),('active','ended','Candidate','logout')],
}
transitions=[]; states=[]
for table,moves in lifecycle_specs.items():
 names=sorted(set(x for a,b,_,_ in moves for x in [a,b])); origins={a for a,b,_,_ in moves}; destinations={b for a,b,_,_ in moves}
 for name in names: states.append([table,name,'Initial' if name not in destinations else ('Terminal' if name not in origins else 'Intermediate'),'Final' if name not in origins else 'Outgoing transition defined','D3 p.7; design'])
 for a,b,actor,guard in moves: transitions.append(dict(id=f'TRN-{len(transitions)+1:03}',table=table,from_state=a,to_state=b,actor=actor,guard=guard,postcondition='Append state event and audit atomically',source='D1 pp.2-4; design'))
for t in lifecycle_specs:
 allowed={(a,b) for a,b,_,_ in lifecycle_specs[t]}; terminal=next((s[1] for s in states if s[0]==t and s[2]=='Terminal'),None)
 if terminal:
  first=sorted(allowed)[0]
  initial=next(s[1] for s in states if s[0]==t and s[2]=='Initial')
  rules.append(rule(f'BR-{len(rules)+1:03}','Lifecycle '+t,'Only listed transitions are allowed',t,'State-transition service + locked row',list(first),[terminal,initial],lambda x,permitted=allowed:tuple(x) in permitted,req='REQ-011'))

feature_rows=[]
for i,r in enumerate(requirements,1):
 feature_rows.append([f'FEAT-{i:03}',r['section'],r['statement'],r['actor'],r['priority'],r['id'],f'GOAL-{1 if r["module"] in ["profile","jobs","sourcing"] else (2 if r["module"] in ["gig","commerce"] else 3):02}',r['acceptance'],'D1; derived feature inventory'])
goals=[['GOAL-01','Improve candidate retention and hiring visibility','Application conversion by stage; repeat activity rate','Candidate and Employer','REQ-001; REQ-010; REQ-033','Baseline UNKNOWN; owner sets target','D1 p.2; proposed metrics'],['GOAL-02','Support accountable gig and credit revenue','Reconciled gig handoffs; idempotent credit events','Requester and Account Admin','REQ-015; REQ-021; REQ-028','Zero duplicate charge; no internal gig fulfilment','D1 p.2; design'],['GOAL-03','Enforce trustworthy access and scale-ready data','Blocked visibility violations; limit breaches; orphan rows','Auditor and Data Engineer','REQ-014; REQ-024; REQ-037','Zero violations in contract proof; target-volume proof later','D1 pp.2-6']]

competitor=[]
bench=[
 ('Candidate identity/contact','app_user; candidate_contact','W1','W3; W4','W5'),
 ('Education and work history','candidate_education; candidate_experience','W1','W3; W4','W5'),
 ('Skills and career profile','candidate_skill; job_role','W1','W3','W5'),
 ('Resume and projects','resume_version; candidate_project','W1','W3','W5'),
 ('Employer company profile','organisation; organisation_location','W2','W4','W6'),
 ('Job posting and candidate response','job_requirement; job_application','W2','W3','UNKNOWN - not verified in selected source'),
 ('Gig handoff and external earnings','gig_assignment; gig_earnings_snapshot','UNKNOWN - no evidence selected','UNKNOWN - no evidence selected','UNKNOWN - no evidence selected'),
 ('Seat/device transactional enforcement','licence; user_session','UNKNOWN - internal implementation unavailable','UNKNOWN - internal implementation unavailable','UNKNOWN - internal implementation unavailable'),
]
for domain,tables,n,f,l in bench:
 for name,evidence in [('Naukri',n),('Monster / foundit India',f),('LinkedIn',l)]:
  competitor.append([name,domain,'Observed public coverage' if not evidence.startswith('UNKNOWN') else 'UNKNOWN',evidence,tables,'Match at concept level' if not evidence.startswith('UNKNOWN') else 'Talentra design requirement; competitor absence NOT claimed',DATE])

nfr_specs=[
 ('Scale','Candidate population',10000000,'profiles','D1 p.6','Count and storage/cardinality plan at full scale','Source target'),
 ('Scale','Job population',1000000,'requirements','D1 p.6','Count full dataset after scale generation','Source target'),
 ('Scale','Application population',100000000,'applications','D1 p.6','Count full dataset; inspect indexes and partitions','Source target'),
 ('Performance','Candidate search p95',500,'milliseconds','ASSUMPTION','Warm/cold 30-run benchmark at laptop scale; record hardware and plan','Proposed target'),
 ('Performance','Profile fetch p95',200,'milliseconds','ASSUMPTION','30-run point lookup benchmark with authorization','Proposed target'),
 ('Performance','Concurrent active users',1000,'users','ASSUMPTION','Load test with 80% read / 20% write mix','Proposed target'),
 ('Reliability','Availability',99.9,'percent/month','ASSUMPTION','Synthetic monitoring success minutes / eligible minutes','Proposed target'),
 ('Recovery','RTO',60,'minutes','ASSUMPTION','Restore backup into empty environment and time service readiness','Proposed target'),
 ('Recovery','RPO',15,'minutes','ASSUMPTION','Compare latest recoverable transaction timestamp to failure time','Proposed target'),
 ('Security','Cross-tenant or blocked disclosure',0,'violations','D1 p.2','Negative tests over search/view/download/outreach and tenant scope','Source invariant'),
 ('Integrity','Duplicate charge or overdraft',0,'violations','D1 p.4; design','Replay events and race concurrent debits; contract tests now, DB races later','Derived invariant'),
 ('Integrity','Orphan references',0,'rows','D1 p.4','Foreign-key checks over every relationship','Source invariant'),
 ('Localization','Initial supported UI languages',3,'languages','ASSUMPTION','English/Hindi/Tamil key and fallback checks','Proposed target'),
 ('Accessibility','Critical dashboard keyboard journeys',100,'percent','ASSUMPTION','Navigate filters/details/downloads using keyboard only','Proposed target'),
 ('Maintainability','Rule positive/negative coverage',100,'percent','D3 p.9','Count covered rules / rule catalogue','Source requirement'),
 ('Privacy','Personal columns with policy',100,'percent','D3 p.8','Dictionary join to privacy register with no missing policy','Source requirement'),
 ('Audit','Sensitive operations recorded',100,'percent','D1 p.2','Compare sensitive operation events with audit correlation IDs','Source requirement'),
]
nfrs=[[f'NFR-{i:03}',*row,'Not benchmarked at target volume'] for i,row in enumerate(nfr_specs,1)]

# Workflow inventory is deliberately at operation grain, so storage/read/audit coverage can be verified.
workflow_specs=[
 ('Candidate onboarding','Candidate','Self-registration','app_user,credential,candidate_profile,consent_record','Reject recruiter-created identity; duplicate login','REQ-001'),
 ('Profile maintenance','Candidate','Profile save','candidate_profile,candidate_contact,candidate_education,candidate_experience,candidate_skill,candidate_language,resume_version,candidate_project,assessment_attempt,course_enrolment,profile_completion','Unknown salary stays typed NULL; erasure request','REQ-002;REQ-003;REQ-004;REQ-005'),
 ('Employer onboarding','Employer','Organisation submission','account,organisation,organisation_location,organisation_identifier,verification_record,recruiter_membership,account_administrator','Verification unavailable: pending with retry','REQ-006;REQ-007'),
 ('Job publication','Employer','Publish request','job_requirement,job_skill,job_question','Unverified employer or invalid salary rejected','REQ-008;REQ-009'),
 ('Candidate application','Candidate','Apply to published job','job_search_event,job_bookmark,job_application,application_answer,application_status_event','Duplicate apply; closed job; unanswered required question','REQ-010'),
 ('Hiring pipeline','Recruiter','Advance application','candidate_shortlist,interview,job_offer,joining_record,application_status_event','Illegal transition; expired offer; withdrawn application','REQ-011'),
 ('Consultant sourcing','Consultant','Request access to requirement','sourcing_request,sourcing_decision,sourcing_shortlist,candidate_shortlist','Job closes to consultants before submission','REQ-013'),
 ('Bulk outreach','Recruiter','Send batch','outreach_batch,outreach_recipient,wallet,wallet_ledger_entry','Candidate blocks actor after batching; insufficient credits','REQ-012;REQ-015'),
 ('Visibility blocking','Candidate','Block party','blocking_entry,candidate_profile,profile_view_event,candidate_bookmark','Existing caches and export links must reauthorize','REQ-014;REQ-029'),
 ('Gig marketplace','Gig Worker','Worker applies to gig','gig_worker_profile,gig_service,gig_availability,gig_request,gig_application,gig_assignment,gig_project','Reverse-direction bid rejected; overlapping assignment','REQ-018;REQ-019;REQ-020;REQ-021'),
 ('Gig reconciliation','Integration Worker','External handoff callback','gig_assignment,gig_earnings_snapshot,gig_rating,gig_worker_list_entry,integration_event','Provider down; duplicate or out-of-order completion','REQ-022;REQ-023'),
 ('Seat and login','Account Admin','Allocate seat or start session','licence,licence_seat,registered_device,user_session,login_attempt,revocation_event','Concurrent final seat; expired session; revoked device','REQ-024;REQ-025;REQ-026'),
 ('Subscriptions and payments','Payment Worker','Payment callback or renewal','subscription_plan,plan_entitlement,subscription_period,payment_order,payment_event,invoice,invoice_line,refund,wallet,wallet_ledger_entry','Duplicate capture; overlapping period; excessive refund','REQ-027;REQ-028'),
 ('Profile download','Recruiter','Download request','profile_download_event,wallet_ledger_entry,profile_view_event','Blocked user; retry uses same idempotency key','REQ-029;REQ-015'),
 ('Preferences and alerts','Candidate','Preference change or job alert','user_preference,notification_preference,job_alert_preference,notification,notification_delivery','Consent revoked before delivery; provider unavailable','REQ-016'),
 ('Community and support','Support Agent','Post or ticket request','community_post,post_reaction,support_ticket,faq,referral,referral_event,social_share_event,candidate_activity','Abusive content; ticket reopen; repeated referral event','REQ-017;REQ-030;REQ-031'),
 ('Governance and analytics','Data Engineer','Scheduled refresh','reference_domain,reference_value,ui_translation,country,state,city,skill,qualification,industry,job_role,access_role,permission,user_role,role_permission,an_dim_date,an_dim_candidate,an_dim_organisation,an_fact_application,an_fact_credit,system_error,audit_event','Missing translation falls back; stale dimensions flagged','REQ-032;REQ-033;REQ-034;REQ-035;REQ-037'),
 ('Integration and retention','Retention Worker','Scheduled reconciliation or erasure','integration_event,consent_record,candidate_profile,audit_event','Provider retries; expired retention; financial token unlink','REQ-036'),
]
workflow_sequences=[
 'Candidate self-registers > normalize login > verify identity channel > capture consent > create own profile > audit',
 'Authorize owner > edit repeating profile sections > validate domains > version resume > recalculate completion > append activity',
 'Create account > register organisation > store tokenized identifiers > request verification > verify outcome > map recruiters',
 'Employer drafts requirement > add skills/questions > validate salary and positions > verify organisation > publish',
 'Search published jobs > inspect questions > select own resume > answer required questions > insert unique application > append applied event',
 'Shortlist visible candidate > schedule interview > record interview > issue offer > record acceptance and joining > append every status event',
 'Consultant requests access > employer accepts/declines > recheck consultant openness > submit candidate shortlist > close on job closure',
 'Recruiter selects own-company job > filter blocked candidates > create batch > lock wallet > debit once > recheck consent/block > enqueue delivery',
 'Candidate selects party > create user/company block > invalidate visibility cache > exclude search/view/export/outreach > append denied-read evidence',
 'Worker creates separate gig profile > declares service/rate/availability > requester posts gig > worker applies > requester accepts > validate nonoverlap > create handoff',
 'Persist external handoff key > ingest idempotent provider event > reconcile assignment status > snapshot external earnings > requester rates completed gig',
 'Lock licence > allocate available seat > register owned device > lock user > expire stale sessions > count active sessions > admit or deny > audit/revoke',
 'Choose plan > create nonoverlapping period > create payment order > verify provider capture > append payment and credit > issue invoice > bound cumulative refunds',
 'Authorize recruiter and candidate visibility > lock wallet > reuse idempotency key or append debit > append download event > issue short-lived object access',
 'Update language/privacy/channel preference > match published job alert > check purpose consent > enqueue notification > recheck opt-out > record provider delivery',
 'Create post or support ticket > moderate or assign > append reaction/referral events > resolve/reopen ticket > localize FAQ > record candidate activity',
 'Version reference codes/translations > apply role grants > refresh conformed dimensions > load facts at declared grain > aggregate KPIs > record failures',
 'Receive external or retention trigger > validate version/policy > reconcile or quarantine > unlink expired personal tokens > purge authorized data > append evidence',
]
workflows=[]; operations=[]
for i,(name,actor,trigger,tablelist,exception,req) in enumerate(workflow_specs,1):
 wid=f'WF-{i:02}'; tables=tablelist.split(',')
 workflows.append([wid,name,actor,trigger,workflow_sequences[i-1],exception,'Committed result or explicit rejection',req,'Design derived from D1 pp.2-6'])
 for j,table in enumerate(tables,1):
  fields=[a['column'] for a in attributes if a['table']==table and a['column'] not in ['id','created_at','created_by','updated_at','updated_by','deleted_at']]
  linked_rules=[r['id'] for r in rules if table in r['table'].replace(' ','').split(',')]
  operations.append([f'{wid}.{j:02}',wid,actor,f'Persist and retrieve {table.replace("_"," ")} for {name.lower()}',table,', '.join(fields[:6])+'; '+(', '.join(linked_rules) if linked_rules else 'BR-001 through BR-005'),'id lookup; scope by '+(fields[0] if fields else 'owner')+' and visibility policy','audit_event; action_code, actor, subject_token, correlation_key','Designed coverage','Data module owner',req])

integration_specs=[
 ('Payment gateway','Gateway owns payment settlement','payment_event provider reference/status/amount; no card data','Pending; bounded retry and reconciliation','provider + provider_event_key'),
 ('Identity verifier','Verifier owns identity outcome','verification_record token/outcome; no raw national ID','Pending verification; no false success','provider + request token'),
 ('Company verifier','Verifier owns registration status','organisation_identifier token; verification_record','Keep pending; retry without enabling publication','provider + verification request'),
 ('Gig fulfilment','External system owns fulfilment and earnings','gig_assignment handoff key; gig_earnings_snapshot','Pending handoff; reconcile stale events by version','provider + external event key'),
 ('Legacy systems','Legacy is source until field-level cutover','Source keys in integration_event; target by approved mapping','Quarantine conflicting update; no blind overwrite','source system + source record + version'),
 ('Messaging provider','Talentra owns intent/preferences; provider owns delivery','notification_delivery provider reference/status','Retry with cap; expire obsolete messages; check opt-out','notification + channel + attempt key'),
 ('Social sharing','External network owns post','social_share_event outbound metadata only','Report link failure; do not claim post success','share request key'),
 ('Geolocation','Provider owns coordinates/place reference','city coordinates and source','Optional lookup unavailable; keep known location','provider + place reference'),
 ('Review/salary source','External provider owns reference data','Reference only; source and refresh date if stretch added','Do not serve stale as current; optional scope','source + refresh version'),
]
integrations=[[f'INT-{i:02}',*row,'integration_event + correlation_key; redact secrets','D1 p.5; proposed contract'] for i,row in enumerate(integration_specs,1)]

volumes=[]
for e in entities:
 t=e['table']; m=e['module']
 if t in ['candidate_profile','app_user','an_dim_candidate']: launch,y1,y3=100000,1000000,10000000
 elif t=='job_requirement': launch,y1,y3=10000,100000,1000000
 elif t in ['job_application','an_fact_application']: launch,y1,y3=250000,5000000,100000000
 elif t=='application_status_event': launch,y1,y3=750000,15000000,300000000
 elif t in ['audit_event','candidate_activity','notification_delivery','integration_event','job_search_event','profile_view_event']: launch,y1,y3=500000,10000000,200000000
 elif m=='master': launch,y1,y3=100,120,150
 else: launch,y1,y3=10000,100000,1000000
 volumes.append([t,launch,y1,y3,0.1 if any(a['nullable'] for a in attributes if a['table']==t) else 0,'Top 10% organisations drive 60% writes' if m in ['jobs','sourcing','commerce','notifications'] else 'Long-tail geography and skill popularity',2.5,'Planning assumption; 2.5x peak-day factor', 'D1 p.6 anchors only candidate/job/application targets; all other table counts ASSUMPTION'])

privacy=[]
entity_map={e['table']:e for e in entities}
for a in attributes:
 cl=a['classification']; personal=cl in ['Personal','Sensitive']
 privacy.append([a['id'],a['table'],a['column'],cl,'Mask by default; reveal to purpose-authorized owner' if personal else 'Show within declared tenant/public scope','Tokenization and encrypted vault; TLS in transit' if cl=='Sensitive' else ('Encrypted storage and TLS; private object access' if personal else 'TLS and standard storage controls'),entity_map[a['table']]['retention'],'Consent/purpose check' if personal else 'No personal consent dependency','Unlink token or erase personal field under retention workflow' if personal else 'Retain nonpersonal aggregate','Audit reads and writes' if personal else 'Audit privileged writes','Proposed policy; privacy owner approval Q-002','D1 p.4; D3 p.8; DEC-006'])

def run_contract_tests():
 tests=[]
 for r in rules:
  for label,payload,expected in [('positive',r['positive'],True),('negative',r['negative'],False)]:
   actual=bool(r['validator'](payload))
   tests.append([f'TC-{len(tests)+1:04}',r['id'],r['table'],label,json.dumps(payload,ensure_ascii=False),'Accept' if expected else 'Reject','Accept' if actual else 'Reject','PASS' if actual==expected else 'FAIL','Python contract validator',r['requirement'],'Executed '+DATE])
 # Use actual state pairs, including all allowed transitions and one prohibited transition per state.
 for table,moves in lifecycle_specs.items():
  allowed={(a,b) for a,b,_,_ in moves}
  for a,b,actor,guard in moves:
   tests.append([f'TC-{len(tests)+1:04}','TRN',table,'positive',f'{a} -> {b}','Accept','Accept' if (a,b) in allowed else 'Reject','PASS','Transition catalogue check','REQ-011','Executed '+DATE])
  names=sorted(set(a for a,b,_,_ in moves)|set(b for a,b,_,_ in moves))
  for s in names:
   target=next((v for v in names if v!=s and (s,v) not in allowed),s)
   actual=(s,target) in allowed
   tests.append([f'TC-{len(tests)+1:04}','TRN',table,'negative',f'{s} -> {target}','Reject','Accept' if actual else 'Reject','FAIL' if actual else 'PASS','Known-state illegal transition check','REQ-011','Executed '+DATE])
 return tests

def run_sqlite_proof():
 con=sqlite3.connect(':memory:'); con.execute('PRAGMA foreign_keys=ON')
 con.executescript('''CREATE TABLE candidate_profile(id INTEGER PRIMARY KEY, name TEXT NOT NULL);
 CREATE TABLE job_requirement(id INTEGER PRIMARY KEY, positions INTEGER NOT NULL CHECK(positions>0), salary_min INTEGER, salary_max INTEGER,CHECK(salary_min<=salary_max));
 CREATE TABLE job_application(id INTEGER PRIMARY KEY,candidate_profile_id INTEGER NOT NULL REFERENCES candidate_profile(id),job_requirement_id INTEGER NOT NULL REFERENCES job_requirement(id),UNIQUE(candidate_profile_id,job_requirement_id));
 CREATE TABLE licence(id INTEGER PRIMARY KEY,max_user_count INTEGER CHECK(max_user_count>0),max_device_per_user INTEGER CHECK(max_device_per_user>0));
 CREATE TABLE wallet_ledger_entry(id INTEGER PRIMARY KEY,signed_amount INTEGER NOT NULL);
 CREATE TRIGGER immutable_update BEFORE UPDATE ON wallet_ledger_entry BEGIN SELECT RAISE(ABORT,'append only'); END;
 CREATE TRIGGER immutable_delete BEFORE DELETE ON wallet_ledger_entry BEGIN SELECT RAISE(ABORT,'append only'); END;''')
 results=[]
 cases=[('BR-004','positive',"INSERT INTO candidate_profile VALUES(1,'Synthetic')",True),('BR-004','negative','INSERT INTO candidate_profile VALUES(2,NULL)',False),('BR-010','positive','INSERT INTO job_requirement VALUES(1,1,100,200)',True),('BR-010','negative','INSERT INTO job_requirement VALUES(2,1,200,100)',False),('BR-011','positive','INSERT INTO job_requirement VALUES(3,2,NULL,NULL)',True),('BR-011','negative','INSERT INTO job_requirement VALUES(4,0,NULL,NULL)',False),('BR-003','positive','INSERT INTO job_application VALUES(1,1,1)',True),('BR-003','negative','INSERT INTO job_application VALUES(2,999,1)',False),('BR-012','positive','INSERT INTO job_application VALUES(3,1,3)',True),('BR-012','negative','INSERT INTO job_application VALUES(4,1,1)',False),('BR-020','positive','INSERT INTO licence VALUES(1,3,2)',True),('BR-020','negative','INSERT INTO licence VALUES(2,3,0)',False),('BR-025','positive','INSERT INTO wallet_ledger_entry VALUES(1,100)',True),('BR-025','negative','UPDATE wallet_ledger_entry SET signed_amount=200 WHERE id=1',False),('BR-025','negative','DELETE FROM wallet_ledger_entry WHERE id=1',False)]
 for i,(rid,kind,sql,expected) in enumerate(cases,1):
  try: con.execute(sql); actual=True; detail='Statement committed'
  except sqlite3.IntegrityError as ex: actual=False; detail=str(ex)
  results.append([f'DB-{i:03}',rid,kind,sql,'Accept' if expected else 'Reject','Accept' if actual else 'Reject','PASS' if actual==expected else 'FAIL',detail,'SQLite portable subset; not PostgreSQL certification'])
 con.close(); return results

def generate_samples(seed=20261027):
 rng=random.Random(seed); samples={}
 # Stable identifiers 1..n make every FK resolve; row 1 serves as system bootstrap identity.
 for e in entities:
  table=e['table']; n=12 if table in ['app_user','candidate_profile','job_requirement','job_application'] else 3
  rows=[]
  for i in range(1,n+1):
   row={}
   for a in [x for x in attributes if x['table']==table]:
    col=a['column']; dom=a['domain']; val=a['example']
    if col=='id': val=i
    elif col in ['created_by','updated_by']: val=1
    elif a['nullable']: val=None
    elif col.endswith('_id'): val=1
    elif dom in ['code','token','object_key']: val=str(val)+f'_{i:03}'
    elif dom=='email': val=f'{table}{i:03}@example.invalid'
    elif col=='person_name': val=['Asha Synthetic','किरण नमूना','மாதிரி பயனர்'][rng.randrange(3)]
    elif col=='code' and table=='country': val=['IN','US','GB'][i-1]
    if col in ['max_user_count','max_device_per_user','positions']: val=3
    if col in ['end_at','expires_at']: val='2026-10-28T00:00:00Z'
    if col in ['created_at','updated_at','started_at','last_activity_at','start_at']: val='2026-10-27T00:00:00Z'
    if col=='signed_amount': val='100.00' if i==1 else '-10.00'
    # Unique FK ownership examples.
    if (table,col) in one_to_one: val=i
    if col.endswith('_id') and col not in ['created_by','updated_by']:
     rel=next((r for r in relationships if r['child']==table and r['column']==col),None)
     if rel and not a['nullable'] and (table,col) not in one_to_one: val=i if i<=3 else 1
    if table=='job_application' and col=='candidate_profile_id': val=i
    if table=='resume_version' and col=='version_number': val=i
    if table=='wallet_ledger_entry' and col=='wallet_id': val=1
    if table=='wallet_ledger_entry' and col=='payment_event_id': val=1 if i==1 else None
    if table=='blocking_entry' and col=='blocked_app_user_id': val=i+1
    if table=='revocation_event' and col=='registered_device_id': val=i
    row[col]=val
   rows.append(row)
  samples[table]=rows
 # Generate real enum domains/values, including every lifecycle state and business category.
 enum_domains={}
 for a in attributes:
  if a['column'].endswith('_reference_value_id'):
   key=a['table']+'.'+a['column']
   values=['active','inactive','pending']
   if a['column']=='status_reference_value_id' and a['table'] in lifecycle_specs:
    values=sorted({v for move in lifecycle_specs[a['table']] for v in move[:2]})
   if a['column']=='employment_type_reference_value_id': values=['gig','general_staffing','professional_staffing','permanent','apprentice','campus','consultant','managed_remote']
   if a['column']=='salary_disclosure_reference_value_id': values=['unknown','not_applicable','disclosed']
   if a['column']=='list_type_reference_value_id': values=['favourite','blacklist']
   if a['column']=='pricing_type_reference_value_id': values=['fixed','rate']
   enum_domains[key]=values
 def audit_row(base): return dict(base,created_at='2026-10-27T00:00:00Z',created_by=1,updated_at='2026-10-27T00:00:00Z',updated_by=1,deleted_at=None)
 samples['reference_domain']=[]; samples['reference_value']=[]; samples['ui_translation']=[]
 lookup={}
 for did,(key,values) in enumerate(enum_domains.items(),1):
  samples['reference_domain'].append(audit_row(dict(id=did,code=key.replace('.','_'),description='Allowed values for '+key)))
  lookup[key]=[]
  for order,code in enumerate(values,1):
   vid=len(samples['reference_value'])+1; lookup[key].append(vid); label=f'{key}.{code}'
   samples['reference_value'].append(audit_row(dict(id=vid,reference_domain_id=did,code=code,label_key=label,active=True,sort_order=order)))
   for lang in ['en','hi','ta']:
    samples['ui_translation'].append(audit_row(dict(id=len(samples['ui_translation'])+1,label_key=label,language_code=lang,translated_text=code.replace('_',' ') if lang=='en' else ('नमूना '+code if lang=='hi' else 'மாதிரி '+code))))
 for key,ids in lookup.items():
  table,col=key.split('.')
  for i,row in enumerate(samples[table]): row[col]=ids[i%len(ids)]
 return samples

samples=generate_samples()
sample_json=json.dumps(samples,ensure_ascii=False,sort_keys=True,indent=2)
sample_hash=hashlib.sha256(sample_json.encode()).hexdigest()
repro_hash=hashlib.sha256(json.dumps(generate_samples(),ensure_ascii=False,sort_keys=True,indent=2).encode()).hexdigest()
fk_issues=[]
for rel in relationships:
 for row in samples[rel['child']]:
  val=row[rel['column']]
  if val is not None and val not in {p['id'] for p in samples[rel['parent']]}: fk_issues.append([rel['id'],row['id'],val])
tests=run_contract_tests(); db_tests=run_sqlite_proof()
rules_export=[{k:v for k,v in r.items() if k!='validator'} for r in rules]
for r in rules_export: r['proof']='Python contract executed; SQLite subset where listed; PostgreSQL integration pending'

invalid=[]
for r in rules:
 invalid.append([f'BAD-{len(invalid)+1:03}',r['id'],r['table'],json.dumps(r['negative'],ensure_ascii=False),'Reject',r['statement'],'Isolated fixture; never mixed into valid sample'])
scenarios=[
 ['SCN-01','Happy path','Candidate applies and joins','applied > shortlisted > interviewed > offered > joined','WF-05;WF-06','All allowed transitions','Synthetic contract transitions executed'],
 ['SCN-02','Business variant','Consultant access accepted then job closes','Recheck job openness at operation time','WF-07','BR-016','Positive and negative rule fixtures executed'],
 ['SCN-03','Boundary','Final available seat/device','Active count limit-1 succeeds; limit fails','WF-12','BR-021;BR-022','Contract executed; concurrent PostgreSQL test pending'],
 ['SCN-04','Invalid','Orphan/duplicate application','Unknown parent and duplicate pair rejected','WF-05','BR-003;BR-012','SQLite negative insertion proof executed'],
 ['SCN-05','Gig','Adjacent versus overlapping assignment','Half-open windows permit adjacency; reject overlap','WF-10','BR-018','Contract proof; PostgreSQL exclusion execution pending'],
 ['SCN-06','Payment','Duplicate capture and excessive refund','One ledger side effect; refund sum <= captured','WF-13','BR-026;BR-028','Contract proof; provider integration pending'],
 ['SCN-07','Privacy','Candidate blocks queued outreach sender','Recheck block before delivery','WF-08;WF-09','BR-015;BR-030','Policy predicate proof; endpoint integration pending'],
 ['SCN-08','Localization','Unicode names and missing translation','Store original Unicode and use default label fallback','WF-17','BR-005;BR-031','Synthetic Unicode samples generated'],
 ['SCN-09','Migration-style','Legacy missing status or duplicate identity','Quarantine, record reason and reconcile input counts','WF-18','BR-004;BR-026','Fixture only; ETL execution outside step cap'],
 ['SCN-10','Golden query','Known application count and wallet balance','12 applications; wallet ledger signed total 80.00 INR','WF-05;WF-13','BR-012;BR-027','Dataset computed golden answers'],
]

gaps=[
 ['GAP-01','All workflows','Runtime authorization and audit instrumentation','Logical coverage exists; no deployed service endpoints in steps 1-16','Platform Engineer','Step 21/27+','Open integration evidence'],
 ['GAP-02','WF-10;WF-12;WF-13','PostgreSQL concurrency/exclusion behaviour','Contract and portable tests do not prove concurrent database transactions','Database Engineer','Step 20/21','Open engine evidence'],
 ['GAP-03','All workflows','Independent peer and author-understanding review','No human review or interview has occurred','Mentor','Next checkpoint','Open review'],
 ['GAP-04','WF-17','Full-scale analytics/performance proof','Source KPI/latency details absent; proposed targets and grains supplied','Analytics Owner','Steps 23/28-30','Deferred beyond cap'],
]

compliance=[]
for group,mechanism in [
 ('1 Naming','snake_case singular catalogue; defined abbreviations an_=analytics, id=identifier; primary id; FK deviations for role-qualified references recorded'),
 ('2 Keys and constraints','bigint surrogate keys, FK actions, unique business keys and locking designs'),
 ('3 Standard domains','Typed domain registry, numeric money/currency, UTC timestamps, translated lookup codes'),
 ('4 Audit and lifecycle','Four audit columns on business tables; lifecycle/retention; immutable event writer'),
 ('5 Nullability','Per-column justification; salary disclosure distinguishes unknown/not_applicable'),
 ('6 Sensitive classification','Each column classified Public/Internal/Personal/Sensitive with masking and policy'),
 ('7 Multilingual','UTF-8 content language; translation key/language and default fallback'),
 ('8 Physical names','an_ analytics prefix; idx_table_column; uq_table_column; future p_table_yyyymm partitions'),
 ('9 Licences/devices/sessions','Positive limits; locks; active unexpired sessions; audited revocation'),
 ('10 Money/history','Immutable ledger/history, reversal reference, nonoverlapping subscription design')]:
 compliance.append([group,'Designed; runtime verification pending',mechanism,'No PostgreSQL DDL deployment claimed','D1 p.4'])
deviations=[
 ['DEV-01','Role-qualified foreign key names','blocker_app_user_id / actor_app_user_id / requester_organisation_id','Same parent appears in different roles; prefix makes meaning unambiguous','Documented departure from literal FK naming; all targets explicit','D1 p.4; design'],
 ['DEV-02','System actor audit foreign keys','created_by/updated_by use the mandated names, not app_user_id suffix','Source explicitly requires these names; nullable only for bootstrap/system principal','Service principal recorded by correlation; no invented human actor','D1 p.4; design'],
 ['DEV-03','Analytical entity naming','an_dim_* and an_fact_* use standard analytical prefixes','Satisfies physical-object distinction; dim/fact abbreviations defined','Not OLTP denormalization; grain explicitly documented','D1 p.4; design'],
]

def section(name,columns,rows,priority='P1',source='D3; D5',specific='Semantic coverage'):
 return dict(name=name,columns=columns,rows=rows,priority=priority,source=source,specific=specific)
def vals(dicts,keys):return [[d[k] for k in keys] for d in dicts]

sections={
 1:[section('Requirements',['Requirement ID','Section','Actor','Statement','Acceptance','Module','Priority','Source','Basis'],vals(requirements,['id','section','actor','statement','acceptance','module','priority','source','basis']),'P0','D1 pp.2-6','Source coverage'),section('Scope',['Scope ID','Disposition','Topic','Boundary','Source'],scope,'P0'),section('Decisions',['Decision ID','Topic','Decision','Reason','Source','Status'],decisions,'P0'),section('Questions',['Question ID','Owner','Question','Priority','Working treatment','Status'],questions,'P1')],
 2:[section('Personas',['Actor ID','Actor','Goal','Permission','Frequency','Module','Requirement ID'],vals(actors,['id','name','goal','permission','frequency','module','requirement']),'P0','D1 p.2'),section('Permissions',['Permission ID','Actor','Operation','Decision','Enforcement','Failure behaviour','Requirement ID'],permissions,'P0'),section('Goals',['Goal ID','Outcome','Metric','Stakeholders','Requirement IDs','Target','Source'],goals,'P1','D4 pp.23,32')],
 3:[section('Features',['Feature ID','Domain','Capability','Actor','Priority','Requirement ID','Goal ID','Acceptance','Source'],feature_rows,'P0'),section('Competitor matrix',['Competitor','Data domain','Evidence status','Source ID','Talentra mapping','Comparison','As of'],competitor,'P1','D1 p.3; W1-W7'),section('Discovery decisions',['Decision ID','Topic','Decision','Reason','Source','Status'],[decisions[2],['DEC-011','Competitor uncertainty','Do not claim superiority on unverified internal features','Public field documentation proves concepts, not proprietary schema internals','W1-W7','Adopted design']],'P1')],
 4:[section('NFR register',['NFR ID','Category','Metric','Target','Unit','Source','Test method','Basis','Evidence status'],nfrs,'P0','D1 p.6; D3 p.6'),section('Sizing assumptions',['Question ID','Owner','Question','Priority','Working treatment','Status'],[questions[0],questions[1]],'P0')],
 5:[section('Workflow maps',['Workflow ID','Workflow','Actor','Trigger','Sequence','Exceptions','Output','Requirement IDs','Source'],workflows,'P0','D1 p.2; D3 p.6'),section('Workflow operations',['Operation ID','Workflow ID','Actor','Operation','Entity','Data contract','Retrieval','Audit','Coverage','Owner','Requirement IDs'],operations,'P0'),section('Integration boundaries',['Boundary ID','Boundary','Source of truth','Stored versus referenced','Failure behaviour','Idempotency','Audit','Source'],integrations,'P1','D1 p.5')],
 6:[section('Entity catalogue',['Entity ID','Table','Module','Definition','Owner','Deletion','Retention','Requirement ID','Source'],vals(entities,['id','table','module','definition','owner','deletion','retention','requirement','source']),'P0'),section('Module coverage',['Module','Owner','Entity count','Tier','Source'],[[module_names[m],module_names[m]+' owner',sum(e['module']==m for e in entities),'Tier 1 and Tier 2 expected','D1 pp.3,6'] for m in module_names],'P0'),section('Design deviations',['Deviation ID','Topic','Decision','Reason','Risk treatment','Source'],deviations,'P1')],
 7:[section('Attributes',['Attribute ID','Entity ID','Table','Column','Type','Domain','Nullable','Null reason','Example','Stored or derived','Source'],vals(attributes,['id','entity_id','table','column','type','domain','nullable','null_reason','example','storage','source']),'P0'),section('Derived metrics',['Metric','Expression','Grain','Storage decision','Source'],[['Wallet balance','SUM(signed_amount) by wallet and currency','wallet + currency','Derived from immutable ledger; no second editable balance','D1 pp.3-4; design'],['Application conversion','Stage count / applied cohort count','organisation + cohort + stage','Analytical calculation; denominator and window declared','D4 p.16; proposed'],['Profile completeness','versioned required-field weights','candidate + rule version','Snapshot with calculated_at; recomputable','D1 p.3; design']],'P1')],
 8:[section('States',['Entity','State','State role','Exit rule','Source'],states,'P0'),section('Transitions',['Transition ID','Entity','From state','To state','Actor','Guard','Postcondition','Source'],vals(transitions,['id','table','from_state','to_state','actor','guard','postcondition','source']),'P0'),section('Illegal transitions',['Entity','From state','To state','Expected','Reason'],[[t,s[1],next((v[1] for v in states if v[0]==t and v[1]!=s[1] and (s[1],v[1]) not in {(a,b) for a,b,_,_ in lifecycle_specs[t]}),s[1]),'Reject','Known states, prohibited edge; replay idempotency is handled separately'] for t in lifecycle_specs for s in states if s[0]==t],'P0')],
 9:[section('Relationships',['Relationship ID','Child table','Foreign key','Parent table','Child to parent','Parent to child','Optional','On update','On delete','Enforcement','Reason','Source'],vals(relationships,['id','child','column','parent','child_to_parent','parent_to_child','optional','on_update','on_delete','enforcement','reason','source']),'P0'),section('Normalization',['Area','Decision','Functional dependency','History','Tradeoff','Source'],[['Profile','Child tables for multivalued fields','candidate ID determines core; education/skill each has own row','Resume versions and activity events separate','More joins preserve atomicity','D1 p.3; design'],['Jobs','Requirement and application distinct','Application ID determines status, candidate and job','Append-only status events','Current state cache must reconcile to events','D1 pp.2-3; design'],['Gig','Separate subsystem with shared identity','Gig application relates one worker to one request','External handoff and earnings snapshots','Cross-job reporting uses conformed dimensions','DEC-003'],['Commerce','Ledger is authoritative','Ledger ID determines signed money/currency and original reference','Never overwrite; reversal entry','Balance calculation requires indexed aggregation','D1 p.4; design'],['Analytics','Star schema is explicit denormalization','Fact application one row per application; fact credit one row per ledger event','Type-2 candidate and organisation dimensions','Refresh and privacy unlink handled independently','D1 p.6; proposed grains']],'P1')],
 10:[section('Dictionary',['Attribute ID','Table','Column','Business definition','Type','Domain','Nullable','Null reason','Default','Validation','Example','Classification','Owner','Rule IDs','Source'],vals(attributes,['id','table','column','definition','type','domain','nullable','null_reason','default','validation','example','classification','owner','rule','source']),'P0'),section('Domains',['Domain','Type','Definition','Example','Default class','Validation'],[[k,*v] for k,v in domains.items()],'P0')],
 11:[section('Rules',['Rule ID','Title','Statement','Table','Enforcement','Requirement ID','Proof status','Source'],vals(rules_export,['id','title','statement','table','enforcement','requirement','proof','source']),'P0'),section('Compliance',['Rule group','Status','Mechanism','Verification boundary','Source'],compliance,'P0'),section('Constraints',['Constraint kind','Applies to','Definition','Concurrency design','Source'],[['Unique','app_user','email','Database UNIQUE; normalized before write','D1 p.4'],['Unique','job_application','candidate_profile_id, job_requirement_id','Database UNIQUE','D1 p.4'],['Unique','reference_value','reference_domain_id, code','Database UNIQUE','DEC-009'],['Unique','ui_translation','label_key, language_code','Database UNIQUE','D1 p.4'],['Unique','wallet_ledger_entry','wallet_id, idempotency_key','Lock wallet before debit','D1 p.4'],['Exclusion','subscription_period','licence_id and half-open timestamp period','btree_gist exclusion; test in PostgreSQL later','W8'],['Exclusion','gig_assignment','worker_id and active assignment period','btree_gist exclusion; status-predicate design','W8'],['Seat limit','licence_seat','active allocated users <= licence max','Lock licence; count active seats; insert; audit','W9'],['Session limit','user_session','active sessions <= per-user limit','Lock licence then app_user; expire stale rows; recheck device revocation and owner; count; insert','W9']],'P0')],
 12:[section('Classification',['Attribute ID','Table','Column','Class','Masking','Encryption','Retention','Purpose and consent','Erasure','Audit','Policy status','Source'],privacy,'P0'),section('Retention decisions',['Decision ID','Topic','Decision','Reason','Source','Status'],[decisions[5],decisions[7]],'P0'),section('Threat controls',['Threat','Affected workflow','Control','Negative evidence','Remaining test','Source'],[['Cross-tenant read','WF-06;WF-08','Membership and visibility predicate','BR-013/015 contract tests','Endpoint and RLS integration','D1 p.2'],['Duplicate money event','WF-13','Unique key + atomic ledger append','BR-026 contract test','Provider callback replay in PostgreSQL','D1 pp.4-5'],['Concurrent session overflow','WF-12','Serialize count/insert on owning rows','BR-022 boundary fixtures','Two-connection concurrent login race','D1 p.4'],['PII persistence after erasure','WF-18','Token unlink plus retention purge','Column policy coverage','End-to-end erasure and restore controls','D3 p.8']],'P1')],
 13:[section('Volumetrics',['Table','Launch rows','Year 1 rows','Year 3 rows','Nullable share assumption','Skew','Peak factor','Reason','Source'],volumes,'P0'),section('Scale profiles',['Profile','Candidates','Jobs','Applications','Status','Source'],[['Discovery sample',12,12,12,'Generated here','D3 p.9; sample assumption'],['Laptop benchmark',1000000,100000,5000000,'Planned later; not loaded','D1 p.6'],['Full-scale target',10000000,1000000,100000000,'Design target; not benchmarked','D1 p.6']],'P0'),section('Generation distributions',['Dimension','Distribution','Tolerance','Reason','Source'],[['Candidate names','English/Hindi/Tamil synthetic names',0,'Unicode and UI-language coverage','ASSUMPTION'],['Organisation traffic','10% organisations / 60% writes',0.05,'Stress tenant hotspots','ASSUMPTION'],['Optional columns','10% null where allowed',0.02,'Planning profile; sample contains explicit nulls','ASSUMPTION'],['Peak traffic','2.5x baseline',0.1,'Hiring event burst design','ASSUMPTION']],'P1')],
 14:[section('Sample manifest',['Table','Row count','File','Seed','Dataset hash','Status'],[[t,len(rows),'evidence/sample_data.json',20261027,sample_hash,'Generated synthetic structural sample'] for t,rows in samples.items()],'P0'),section('Scenarios',['Scenario ID','Category','Situation','Expected','Workflow IDs','Rule IDs','Evidence'],scenarios,'P0','D2 pp.9-11; D3 p.9'),section('Invalid fixtures',['Fixture ID','Rule ID','Table','Payload','Expected','Reason','Isolation'],invalid,'P0'),section('Golden answers',['Query ID','Question','Expected value','Dataset scope','Method'],[['GOLD-01','Application count',len(samples['job_application']),'job_application','Count generated rows'],['GOLD-02','Wallet signed balance INR',80,'wallet_ledger_entry','100.00 - 10.00 - 10.00'],['GOLD-03','Unknown FK references',len(fk_issues),'All generated rows','Compare every FK to parent ID set'],['GOLD-04','Reproducible seed hash match',sample_hash==repro_hash,'Full JSON dataset','SHA256 of two independent deterministic generations']],'P0')],
 15:[section('Contract tests',['Test ID','Rule ID','Table','Case','Fixture','Expected','Actual','Result','Layer','Requirement ID','Run'],tests,'P0'),section('Database subset',['Test ID','Rule ID','Case','SQL','Expected','Actual','Result','Detail','Limitation'],db_tests,'P0'),section('Test coverage',['Rule ID','Positive tests','Negative tests','Coverage','Runtime boundary'],[[r['id'],sum(t[1]==r['id'] and t[3]=='positive' for t in tests),sum(t[1]==r['id'] and t[3]=='negative' for t in tests),'Both cases executed','Python contract; PostgreSQL enforcement not certified'] for r in rules],'P0'),section('Execution limits',['Gap ID','Workflow','Missing proof','Reason','Owner','Next stage','Status'],gaps[:2],'P1')],
 16:[section('Workflow coverage',['Operation ID','Workflow ID','Actor','Operation','Entity','Data contract','Retrieval','Audit','Coverage','Owner','Requirement IDs'],operations,'P0'),section('Gap register',['Gap ID','Workflow','Missing proof','Reason','Owner','Next stage','Status'],gaps,'P0'),section('Gate assessment',['Gate','Scope','Evidence','Decision','Remaining requirement','Source'],[['G1','Steps 1-5','Requirements/actors/NFRs/workflows populated','Analysis prepared; owner confirmation open','Approve proposed NFRs and independent review','D3 p.6'],['G2','Steps 6-12','Dictionary/rules/privacy populated','Model prepared; independent review open','Approve retention and engine integration design','D3 p.8'],['G3','Steps 13-21','Only steps 13-16 requested here','NOT REACHED','Complete steps 17-21, suite v2 and PostgreSQL DDL baseline','D3 p.10']],'P0')],
}

# Output schemas: one schema per step, with typed fields grouped into an explicit four-level tree.
def field_type(col,rows,idx):
 values=[r[idx] for r in rows if r[idx] is not None]
 if values and all(type(v) is bool for v in values): return 'boolean'
 if values and all(type(v) in [int,float] for v in values): return 'decimal' if any(type(v) is float for v in values) else 'integer'
 return 'text'
schema_nodes=[]; schema_fields=[]
for step,secs in sections.items():
 for si,sec in enumerate(secs,1):
  root=f'S{step:02}.{si:02}'; schema_nodes.append([step,root,'',1,sec['name'],sec['priority'],'Major output section',sec['source']])
  groups={}
  for j,col in enumerate(sec['columns']):
   group='Identity' if any(x in col for x in [' ID','Table','Entity','Column','Actor','Module','Domain']) else ('Evidence' if any(x in col for x in ['Source','Proof','Result','Actual','Expected','Status','Coverage','Run','Basis']) else 'Definition and behaviour')
   if group not in groups:
    groups[group]=f'{root}.{len(groups)+1}'; schema_nodes.append([step,groups[group],root,2,group,sec['priority'],'Related parameter group',sec['source']])
   fid=f'{groups[group]}.{j+1:02}'; dtype=field_type(col,sec['rows'],j)
   schema_nodes.append([step,fid,groups[group],3,col,sec['priority'],'Single field in '+sec['name'],sec['source']])
   for suffix,label,value in [('a','Data type',dtype),('b','Requiredness','Required documentary field'),('c','Validation','One scalar; explicit UNKNOWN permitted in text with reason'),('d','Provenance',sec['source'])]:
    schema_nodes.append([step,fid+'.'+suffix,fid,4,label,sec['priority'],value,sec['source']])
   schema_fields.append([step,sec['name'],group,col,dtype,'Atomic','Required','One scalar; document lists use explicit delimited IDs',f'{col} in {sec["name"]}',f'Needed to use and validate {sec["name"].lower()}',sec['priority'],sec['source'],str(sec['rows'][0][j])[:400] if sec['rows'] else 'UNKNOWN - no rows',fid])

summary=dict(entity_count=len(entities),attribute_count=len(attributes),relationship_count=len(relationships),rule_count=len(rules),workflow_count=len(workflows),operation_count=len(operations),sample_rows=sum(map(len,samples.values())),sample_hash=sample_hash,reproducible=sample_hash==repro_hash,foreign_key_issues=len(fk_issues),contract_tests=len(tests),contract_passed=sum(t[7]=='PASS' for t in tests),database_tests=len(db_tests),database_passed=sum(t[6]=='PASS' for t in db_tests),logical_coverage=sum(o[4] in entity_map for o in operations)/len(operations))
data=dict(date=DATE,sources=sources,steps=[dict(number=i,title=s[0],phase=s[1],exit=s[2],sections=sections[i]) for i,s in enumerate(steps,1)],schema_nodes=schema_nodes,schema_fields=schema_fields,summary=summary,questions=questions)
(ROOT/'work'/'project_data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(EVIDENCE/'sample_data.json').write_bytes(sample_json.encode('utf-8'))
(EVIDENCE/'invalid_fixtures.json').write_text(json.dumps(invalid,ensure_ascii=False,indent=2),encoding='utf-8')
(EVIDENCE/'test_results.json').write_text(json.dumps({'contract_tests':tests,'sqlite_database_tests':db_tests,'summary':summary},ensure_ascii=False,indent=2),encoding='utf-8')
(EVIDENCE/'catalogue.json').write_text(json.dumps({'entities':entities,'attributes':attributes,'relationships':relationships,'rules':rules_export,'transitions':transitions},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
