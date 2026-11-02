import fs from 'node:fs/promises';
import path from 'node:path';

export const ROOT = 'C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra';
export const BUILD = ROOT + '/work/step22_ppt';
export const PROJECT = ROOT + '/outputs/talentra_step22_mentor_v6';
const C = {ink:'#182B43',blue:'#345F96',teal:'#167568',muted:'#627187',paper:'#F5F7FA',line:'#D6E0EC',red:'#A74842',amber:'#825D23'};
const font='Aptos';
let notes=[];
function text(s,t,x,y,w,h,size=28,color=C.ink,bold=false,align='left'){
 const q=s.shapes.add({geometry:'textbox',name:t.slice(0,65),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 q.text=t;q.text.style={fontFamily:font,fontSize:size,color,bold,alignment:align,verticalAlignment:'middle',insets:0,wrap:'word'};return q;
}
function node(s,t,x,y,w=200,h=76,fill='#EAF0F7',color=C.ink){
 const q=s.shapes.add({geometry:'rect',name:t.replaceAll('\n',' '),position:{left:x,top:y,width:w,height:h},fill,line:{fill:C.line,width:1}});
 q.text=t;q.text.style={fontFamily:font,fontSize:24,color,bold:true,alignment:'center',verticalAlignment:'middle',insets:10,wrap:'word'};return q;
}
function connect(s,a,b,from='right',to='left',color=C.blue){return s.shapes.connect(a,b,{kind:'elbow',fromSide:from,toSide:to,line:{style:'solid',fill:color,width:2},tail:{type:'arrow',width:'med',length:'med'}});}
function table(s,headers,rows,widths,y=170,height=390,size=24){
 const values=[headers,...rows].map(r=>r.map(String));const t=s.tables.add({rows:values.length,columns:headers.length,left:64,top:y,width:1152,height,columnWidths:widths,values});
 for(let r=0;r<values.length;r++)for(let c=0;c<headers.length;c++){
  const cell=t.getCell(r,c);cell.fill=r===0?C.ink:(r%2?'#FFFFFF':'#EEF3F8');
  cell.text.style={fontFamily:font,fontSize:size,color:r===0?'#FFFFFF':C.ink,bold:r===0,insets:9,verticalAlignment:'middle',wrap:'word'};
 }
 t.borders.assign({fill:C.line,width:1,style:'solid'});return t;
}
function slide(p,title,sub,ref,script){
 const s=p.slides.add({width:1280,height:720});s.background.fill='#FFFFFF';
 text(s,title,64,42,1152,65,42,C.ink,true);
 if(sub)text(s,sub,64,112,1152,44,24,C.muted);
 text(s,ref,64,652,1090,42,16,C.muted);
 text(s,String(p.slides.items.length).padStart(2,'0'),1170,659,48,28,18,C.muted,false,'right');
 const full=`SPEAKING SCRIPT\n${script}\n\nFILE AND DEMONSTRATION REFERENCE\nProject folder: ${PROJECT}\n${ref}\n\nSource basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.`;
 s.speakerNotes.text=full;notes.push({slide:p.slides.items.length,title,notes:full});return s;
}
function lines(s,items,y=190,size=30,spacing=92){items.forEach((t,i)=>text(s,t,72,y+i*spacing,1128,74,size));}
export async function build(p){
 await fs.mkdir(BUILD,{recursive:true});
 const D=JSON.parse(await fs.readFile(ROOT+'/work/release_v6/dashboard_data.json','utf8'));
 const S=D.steps.find(s=>s.number===22);const sec=n=>S.sections.find(s=>s.name===n);notes=[];
 let s=slide(p,'Talentra: Step 22','Integration and Source Mapping','Mentor presentation • 30 October 2026'.replace(' • ',' / '),
 'Good morning, sir. This presentation explains Step 22 of Talentra. I will connect the business scenario to user workflows, generated data, source mappings and measurable results. The slides cover this step only. The Notes pane contains my explanation and exact project references.');
 text(s,'Business workflows\nand their data',72,226,1060,160,64,C.ink,true);
 text(s,'Hiring funnel, gig process, field mappings and evidence',72,434,1070,86,32,C.blue);
 text(s,'Synthetic scenario results with explicit implementation gaps',72,550,1100,55,25,C.muted);

 s=slide(p,'The purpose of Step 22','Every declared source field needs a meaning, owner and destination','C workbook: Overview, Integration catalogue, Source target mapping',
 'Steps 1 to 21 established the model. Step 22 explains how data crosses the system boundary. This diagram is the intended integration design. Source data passes contract and account checks, then maps to an existing target, an explicit proposal or a transport purpose. Business effects and reconciliation need durable records. Provider adapters and native execution remain pending.');
 const a=node(s,'Source files\nand providers',64,225,240,105),b=node(s,'Contract and\naccount checks',379,225,240,105),c=node(s,'Field mapping\nand transformation',694,225,240,105),d=node(s,'Canonical target\nor disposition',1009,225,207,105);
 connect(s,a,b);connect(s,b,c);connect(s,c,d);
 text(s,'32 contracts',72,400,460,70,40,C.blue,true);text(s,'326 field mappings',600,400,610,70,40,C.blue,true);
 text(s,'27 earlier contracts + 5 synthetic file contracts\n271 earlier mappings + 55 mentor mappings',72,495,1100,90,29);

 s=slide(p,'What one record means','The definition of the record controls the funnel and its KPIs','C workbook: 12_Business definitions, 23_Generated journey sample',
 'The mentor population is interpreted as 15 lakh synthetic candidate-job journeys. A journey begins before an application. An event records a milestone reached. An application exists only after submission. Screening means pre-application eligibility. The generated cohort uses one candidate and one target job per journey, but a production candidate can have multiple journeys.');
 table(s,['Record','Business meaning','Generated volume'],[
 ['Journey','One candidate against one target job','1,500,000'],['Event','One reached milestone or outcome','4,194,321'],['Application','One submitted job application','669,375']],[215,655,282],185,270,27);
 text(s,'Screening means eligibility before submission.\nEmployer rejection and candidate offer decline have different owners.',72,500,1120,100,29);

 s=slide(p,'Job families and engagement types','Function and engagement describe different parts of a job','C workbook: 13_Job taxonomy, 15_Family funnel assumptions',
 'White-collar jobs include IT development and testing, plus non-IT sales and delivery. Delivery follows the mentor classification as a configurable label. Warehouse and field service are proposed blue-collar examples. Engagement is an independent axis, so an IT developer can accept permanent, contract or gig work. The generated hiring and gig datasets remain separate scenarios.');
 const white=node(s,'White collar',350,180,230,65),blue=node(s,'Blue collar',918,180,250,65);
 const it=node(s,'IT',230,310,190,65),non=node(s,'Non-IT',530,310,190,65),bb=node(s,'Warehouse\nField service',917,368,252,110);
 connect(s,white,it,'bottom','top');connect(s,white,non,'bottom','top');connect(s,blue,bb,'bottom','top');
 const dev=node(s,'Development\nTesting',200,445,250,100),sales=node(s,'Sales\nDelivery',500,445,250,100);connect(s,it,dev,'bottom','top');connect(s,non,sales,'bottom','top');
 text(s,'Engagement: permanent, contract, gig or apprentice',72,583,1130,45,29,C.teal,true);

 s=slide(p,'Hiring workflow','Reached milestones and decision branches','C workbook: 14_Hiring funnel, 16_Family funnel counts',
 'Read the upper row from search to assessment, then the lower row from interview to onboarding. Eligibility screening precedes application. At the interview decision the employer selects or rejects. After an offer the candidate accepts or declines. Selected candidates can wait for an offer and accepted candidates can wait for onboarding. These are cumulative reached-stage counts, not mutually exclusive current-state totals.');
 const names=['Searched','Screened','Applied','Shortlisted','Assessed'];const top=names.map((n,i)=>node(s,n,64+i*236,205,208,66));top.slice(1).forEach((n,i)=>connect(s,top[i],n));
 const lower=['Interviewed','Selected','Offered','Accepted','Onboarded'].map((n,i)=>node(s,n,64+i*236,385,208,66));lower.slice(1).forEach((n,i)=>connect(s,lower[i],n));connect(s,top[4],lower[0],'bottom','top');
 const rej=node(s,'Employer rejected\n103,087',64,521,235,78,'#F8ECEB',C.red),decl=node(s,'Candidate declined\n7,086',536,521,235,78,'#F8ECEB',C.red);
 connect(s,lower[0],rej,'bottom','top',C.red);connect(s,lower[2],decl,'bottom','top',C.red);
 text(s,'Offer pending: 1,555\nOnboarding pending: 2,993',848,519,360,85,25,C.muted);

 s=slide(p,'Generated hiring results','15 lakh journeys produce 6.69 lakh submitted applications','C workbook: 14_Hiring funnel / scenario_data/generation_summary.json',
 'These results come from saved synthetic data. Each family has proposed conversion rates, so these are workload assumptions rather than market measurements. Selected plus employer rejected equals interviewed. Accepted plus declined equals offered. Do not add cumulative milestone counts to calculate the audience. Pending stages explain the differences between selected, offered, accepted and onboarded.');
 const st=D.mentor.stages;
 table(s,['Milestone','Journeys reaching it','Milestone','Journeys reaching it'],[
 ['Searched',st.searched.toLocaleString('en-IN'),'Interviewed',st.interviewed.toLocaleString('en-IN')],['Screened',st.screened.toLocaleString('en-IN'),'Selected',st.selected.toLocaleString('en-IN')],['Applied',st.applied.toLocaleString('en-IN'),'Offered',st.offered.toLocaleString('en-IN')],['Shortlisted',st.shortlisted.toLocaleString('en-IN'),'Accepted',st.accepted.toLocaleString('en-IN')],['Assessed',st.assessed.toLocaleString('en-IN'),'Onboarded',st.onboarded.toLocaleString('en-IN')]
 ],[270,306,270,306],178,350,28);
 text(s,'47,948 selected + 103,087 rejected = 151,035 interviewed\n39,307 accepted + 7,086 declined = 46,393 offered',72,554,1120,72,25,C.teal,true);

 s=slide(p,'Hiring responsibilities and associated data','Each actor has an action, an access boundary and an audit outcome','C workbook: 18_Actor workflows / Dashboard: Workflows for each actor',
 'The candidate owns registration, application and offer response. The recruiter can advance assigned applications within the correct organisation and must respect blocking. The employer issues offers and confirms joining. An integration worker validates source identity, deduplicates events and reconciles outcomes. These are documented service requirements. The portable fixtures do not prove endpoint authorization.');
 table(s,['Actor','Business action','Associated data'],[
 ['Candidate','Search, apply and respond to an offer','candidate_profile, job_application, job_offer'],['Recruiter','Shortlist assigned applicants','recruiter_membership, application_status_event'],['Employer','Issue offers and confirm joining','job_requirement, job_offer, joining_record'],['Integration worker','Validate, deduplicate and reconcile','integration_inbox, integration_rejection, reconciliation_run']
 ],[220,420,512],180,360,25);
 text(s,'Guard examples: own organisation, candidate consent, blocked visibility and valid state transitions',72,561,1120,62,27,C.blue,true);

 s=slide(p,'Gig workflow','The external system owns fulfilment and earnings outcomes','C workbook: 24_Generated gig sample, 17_Business KPI register',
 'Gig workers maintain their profile and availability, then apply to a requester. The requester accepts or rejects. Accepted applications have an assignment and an external handoff reference. The external system supplies status and earnings outcomes. Only completed assignments qualify for requester ratings. The 50,000 applications include 10,000 accepted, 30,000 rejected and 10,000 pending. Of the 10,000 accepted assignments, 8,000 completed and 4,000 received ratings. Retry-pending assignments remain in the completion denominator.');
 const g1=node(s,'Worker profile\nand availability',64,210,250,90),g2=node(s,'Worker\napplication',400,210,250,90),g3=node(s,'Requester\ndecision',736,210,250,90);connect(s,g1,g2);connect(s,g2,g3);
 const g4=node(s,'External handoff',736,390,250,80),g5=node(s,'Provider status\nand earnings',400,390,250,80),g6=node(s,'Requester rating\nafter completion',64,390,250,80);connect(s,g3,g4,'bottom','top');connect(s,g4,g5,'left','right');connect(s,g5,g6,'left','right');
 text(s,'50,000 applications     10,000 accepted     8,000 completed',72,546,1136,55,31,C.blue,true);
 text(s,'Completion: 80% of accepted assignments     Rating coverage: 50% of completed assignments',72,599,1136,42,24,C.muted);

 s=slide(p,'One field traced to its destination','Existing targets and proposed model changes retain separate status','C workbook: 21_Mentor source field mapping, rows 6–7 / contracts/mentor.journey.v1.schema.json',
 'MAP-M-002 maps candidate_profile_id from the journey source to candidate_profile.id. Native loading still requires identity translation within the account. MAP-M-001 maps journey_id to an explicitly proposed journey event structure. This makes the missing native support visible. Journey 3 in the sample is screened and has a null application identifier. The property is required in the payload but allows a null value. CSV backslash N becomes JSON null during parsing.');
 table(s,['Source field','Target or treatment','Status'],[
 ['candidate_profile_id','candidate_profile.id','Existing dictionary target. Translate source IDs within account.'],['journey_id','Proposed journey_stage_event.journey_id','Native migration and owner review pending.'],['application_id','Integer or null in the journey contract','Null represents a journey before application.']
 ],[275,425,452],180,320,26);
 text(s,'Example: journey 3 is screened and has no application yet',72,542,1120,70,31,C.teal,true);

 s=slide(p,'Integration failure workflow','The design records an explicit outcome for each failure class','C workbook: 03_Failure policy, 25_Source failure scenarios',
 'The source event first needs a valid account-bound identity and schema. A duplicate with the same key and hash returns its earlier durable outcome. The same key with a different hash is a conflict. Stale updates must not regress current state. Malformed or cross-account data is rejected or quarantined. Temporary provider failures remain pending with bounded retries. This is the proposed processing design with selected portable checks. Runtime adapters, signed callbacks and crash recovery still need proof.');
 const f1=node(s,'Receive source\nevent',64,200,220,90),f2=node(s,'Verify account\nand schema',374,200,220,90),f3=node(s,'Check key, hash\nand version',684,200,220,90),f4=node(s,'Map and record\ndurable outcome',994,200,222,90);connect(s,f1,f2);connect(s,f2,f3);connect(s,f3,f4);
 table(s,['Condition','Declared treatment'],[['Same key and same hash','Return prior outcome. Apply no second effect.'],['Changed hash or stale state update','Quarantine conflict or stale update for reconciliation.'],['Malformed or cross-account reference','Reject or quarantine before a business write.'],['Timeout or temporary provider failure','Keep pending. Retry with bounded backoff.']],[505,647],350,260,24);

 s=slide(p,'Business KPIs','The denominator and cohort explain the result','C workbook: 17_Business KPI register / Dashboard: Business KPIs',
 'The register contains 18 KPIs. Screened conversion is screened journeys divided by searched journeys. Offer acceptance uses issued offers as its denominator. Time to hire uses first application and first accepted offer, measured in calendar days. Pending cases without end timestamps do not enter completed-duration averages. The gig completion denominator includes all accepted assignments, including retry-pending and in-progress cases. Values shown are synthetic scenario results.');
 table(s,['Metric','Definition','Synthetic result'],[
 ['Screened conversion','Screened / searched','70.5%'],['Offer acceptance','Accepted / offered','84.7%'],['Time to hire','First accepted offer minus first application','About 24 calendar days'],['Gig completion','Completed / all accepted assignments','80.0%'],['Gig rating coverage','Rated completed / completed assignments','50.0%']
 ],[300,570,282],180,360,26);
 text(s,'Zero denominator means not applicable. Completed-duration averages exclude missing end times.',72,565,1120,60,26,C.muted);

 s=slide(p,'Generated data and validation','Saved-file checks and portable evidence have a defined scope','C workbook: 22_Dataset inventory, 26_Mentor negative test evidenc / evidence folder',
 'The five datasets contain 6,433,696 rows at different grains. Saved files were read back for count and declared invariant checks, including legal events, time ordering, organisation references and gig guards. JSON contract checks cover 300 typed samples per file, or 1,500 in total. The portable guard model has 12 expected outcomes, one positive and eleven refusal cases. A 1,000-journey repeated generation matched all five hashes. None of these establishes native PostgreSQL, API authorization, provider or production load performance.');
 table(s,['Dataset','Rows','Evidence'],Object.entries(D.mentor.files).map(([k,v])=>[v.file,v.rows.toLocaleString('en-IN'),'Saved CSV gzip, count and SHA256']),[445,230,477],175,315,26);
 text(s,'1,500 typed samples    12 portable cases    Full saved-file invariant checks',72,521,1140,52,29,C.blue,true);
 text(s,'Native database, concurrency, provider and load tests remain open',72,588,1140,38,26,C.muted);

 s=slide(p,'The three Step 22 deliverables','The output definition, assessment and populated records fit together','Step 22 folder: a_Output_Schema_Definition.xlsx, b_Schema_Rating_Scorecard.xlsx, c_Output_Document.xlsx',
 'The schema workbook defines required information. The scorecard assesses quality and evidence. The output workbook contains the populated records across 26 sections. The L1 to L4 hierarchy makes the definition inspectable. L1 is a section, L2 is a parameter, L3 separates value contract from meaning and lineage, and L4 states atomic type, validation and source properties. Priority marks importance separately from readiness. Artifact JSON schemas describe deliverables, while integration schemas describe exchanged payloads.');
 table(s,['Deliverable','Purpose'],[['Output Schema Definition','Required fields, types, L1–L4 and priorities'],['Schema Rating Scorecard','Dimensions, evidence, section scores and human review'],['Output Document','26 populated sections with mappings, scenarios and results']],[420,732],175,230,27);
 const lev=['L1\nSection','L2\nParameter','L3\nContract and meaning','L4\nAtomic properties'].map((t,i)=>node(s,t,72+i*293,477,260,96));lev.slice(1).forEach((q,i)=>connect(s,lev[i],q));

 s=slide(p,'Step 22 quality and production evidence','Documentary quality and full-rubric approval measure different things','B workbook: Summary, 90 Plus Closure, Human Review / C: Production release gates',
 'Step 22 scores 82.9 on the full rubric and 97.7 on the supplementary documentary measure. Schema and scorecard each have 83 full and 100 documentary. Output has 82.8 full and 95.4 documentary. Independent comparison and human understanding need real reviewer evidence. Conditional 90-plus targets remain targets. Native database, concurrency, authorization, load, recovery and provider evidence remain separate release requirements. These numbers describe Step 22 only.');
 table(s,['Step 22 deliverable','Full /100','Documentary /100'],[['Schema definition','83.0','100.0'],['Rating scorecard','83.0','100.0'],['Populated output','82.8','95.4'],['Step 22 combined','82.9','97.7']],[600,250,302],175,290,28);
 text(s,'Reviewer evidence remains pending',72,492,1120,53,34,C.blue,true);
 text(s,'Open runtime gates: database, concurrency, load, authorization, recovery and providers',72,556,1120,65,27);

 s=slide(p,'Five model gaps for the next implementation','The scenario identifies changes that need owner review and native migration','C workbook: 20_Native schema gap register / database/HYBRID_CHANGESET.md',
 'The scenario exposes five model concerns. Search needs target-job attribution. Eligibility needs job context. Assessments need application context. Analytics needs reliable milestone timestamps. Job taxonomy needs versioned dimensions distinct from engagement. The gap register records affected earlier steps and the proposal status. Production work should resolve these through accepted model changes, migrations, backfill, dictionary updates and tests. The deck does not claim these additions are deployed.');
 table(s,['Gap','Required meaning'],[['Search attribution','Connect a search to the target job and journey.'],['Eligibility evidence','Record screening for the particular job.'],['Assessment linkage','Connect an assessment to the correct application.'],['Milestone timestamps','Preserve source event time and arrival time.'],['Taxonomy dimensions','Version collar, branch and function separately from engagement.']],[360,792],180,380,28);
 text(s,'Status: proposals and implementation decisions remain open',72,586,1130,42,27,C.amber,true);

 s=slide(p,'Where to show each result in the dashboard','Business scenarios contains summaries. Step outputs contains the detailed records.','Open outputs/talentra_step22_mentor_v6/index.html in Chrome or Edge',
 'For the visual story, click Business scenarios in the top navigation. Show the funnel, gig workflow, taxonomy, actor selector and business KPIs. For detail, open Step outputs, choose Step 22 and use its section dropdown. The screenshot in the earlier conversation already showed the Business scenario catalogue. The Hiring funnel, Job taxonomy and Actor workflows are other choices in that same dropdown. The dashboard is an offline snapshot. Excel edits and planning inputs do not automatically refresh its saved results.');
 table(s,['Mentor topic','Dashboard location'],[['Hiring and gig diagrams','Business scenarios: Hiring funnel and Gig workflow'],['Job categories','Business scenarios: Job families and business context'],['User actions and data elements','Business scenarios: Workflows for each actor'],['Business KPI formulas','Business scenarios: Business KPIs'],['Definitions and detailed scenarios','Step outputs / Step 22 / Business definitions or Business scenario catalogue'],['Source mappings and samples','Step outputs / Step 22 / Mentor source field mapping or Generated journey sample']],[440,712],175,405,25);

 s=slide(p,'Reference: all 12 actors','36 workflow rows describe triggers, actions and recorded outcomes','C workbook: 18_Actor workflows / Dashboard actor dropdown',
 'This reference lists every actor in the mentor workflow register. Each actor has three rows for receiving and authorizing, executing the business action, and persisting and publishing the outcome. Some business personas share platform identities or roles. Do not interpret this catalogue as 12 newly implemented authorization roles. The exact fields, guards and proof status are in the workbook.');
 const actor=sec('Actor workflows').rows.filter(r=>r[2]===1);
 const short={'Guest':'Browse public jobs','Candidate':'Apply and respond to offers','Employer':'Post jobs and confirm joining','Recruiter':'Progress assigned applicants','Consultant':'Submit approved shortlists','Placement Officer':'Coordinate campus candidates','Account Admin':'Manage seats and revoke access','Admin':'Maintain scoped reference data','Super Admin':'Review exceptional access','Gig Worker':'Maintain profile and apply','Gig Requester':'Decide and rate completed work','Integration Worker':'Validate and reconcile events'};
 table(s,['Actor','Responsibility','Actor','Responsibility'],Array.from({length:6},(_,i)=>[actor[i][1],short[actor[i][1]],actor[i+6][1],short[actor[i+6][1]]]),[205,371,205,371],175,405,24);

 s=slide(p,'Reference: hiring conversion KPIs','Every ratio uses journeys from the same cohort','C workbook: 17_Business KPI register, KPI-H-01 to KPI-H-07',
 'These conversion rates use distinct candidate-job journeys reaching the named stage in the same cohort. They are not unique-person conversion rates across all jobs. A zero denominator is not applicable. The values arise from proposed family conversion profiles in the synthetic generation.');
 const ks=sec('Business KPI register').rows;
 table(s,['KPI','Numerator / denominator','Synthetic result'],ks.slice(0,7).map(r=>[r[1],`${Number(r[3]).toLocaleString('en-IN')} / ${Number(r[4]).toLocaleString('en-IN')}`,(Number(r[5])*100).toFixed(1)+'%']),[440,460,252],175,420,26);

 s=slide(p,'Reference: offers, joining and duration KPIs','Distinct milestones preserve the business meaning','C workbook: 17_Business KPI register, KPI-H-08 to KPI-H-14',
 'Offer issue uses selected journeys as the denominator. Offer acceptance and offer decline use offered journeys. Onboarding uses accepted journeys. Time to offer begins at application and ends at the first offer. Time to hire ends at the first accepted offer. Time to onboard begins at acceptance and ends at joining. Duration averages include only journeys reaching both milestones and use calendar days. Pending ageing requires a separate view.');
 table(s,['KPI','Definition','Synthetic result'],[
 ['Offered conversion','Offered / selected','96.8%'],['Accepted conversion','Accepted / offered','84.7%'],['Offer decline','Declined / offered','15.3%'],['Onboarded conversion','Onboarded / accepted','92.4%'],['Time to offer','First offer minus first application','21 calendar days'],['Time to hire','First acceptance minus first application','About 24 calendar days'],['Time to onboard','First joining minus first acceptance','About 9 calendar days']
 ],[350,530,272],175,420,25);

 s=slide(p,'Reference: gig KPIs and business scenarios','Four gig KPIs complete the 18-metric register','C workbook: 17_Business KPI register, 19_Business scenario catalogue',
 'Gig request fill is accepted requests divided by published requests, which is 100 percent in this constructed fixture. Application acceptance is 20 percent of all submitted applications at the snapshot, including pending submissions. Completion is 80 percent of all accepted assignments. Rating coverage is 50 percent of completed assignments. The scenario catalogue contains 14 scenarios with business meaning, grain, associated entities and evidence status. They cover both hiring and platform concerns.');
 table(s,['Gig KPI','Definition','Result'],[['Request fill','Accepted requests / published requests','100%'],['Application acceptance','Accepted applications / submitted applications','20%'],['Assignment completion','Externally completed / all accepted assignments','80%'],['Requester rating coverage','Rated completed / completed assignments','50%']],[345,620,187],172,270,25);
 const scenarios=sec('Business scenario catalogue').rows;
 text(s,'14 scenarios: hiring, employer decisions, privacy, sourcing and platform controls',72,472,1120,48,28,C.blue,true);
 text(s,scenarios.map(r=>r[0]).join(', '),72,533,1120,57,24,C.muted);
 // Preserve the complete scenario names and source locators in the notes.
 s.speakerNotes.append('\n\nALL BUSINESS SCENARIOS\n'+scenarios.map(r=>r[0]+': '+r[1]+'\nBusiness meaning: '+r[2]+'\nGrain: '+r[3]+'\nEntities: '+r[4]+'\nEvidence: '+r[5]).join('\n\n'));

 s=slide(p,'Files for the mentor demonstration','The complete project stays offline','Project folder and exact file paths appear in the speaker notes',
 'The released project folder contains the dashboard, the three Step 22 workbooks and the complete synthetic data. Open index.html in a browser. Keep the complete extracted folder together for dataset links. In PowerPoint use Presenter View or the Notes pane to read the script and file references. The main result of Step 22 is a clear relationship between business workflows, source data, target mappings, KPIs and evidence. Production acceptance still requires closing the registered runtime and owner-review gates.');
 lines(s,['Dashboard: index.html','Step 22 workbooks: steps/22_Integration_and_Source_Mapping/','Full generated data: scenario_data/','Payload contracts: contracts/','Checks and generator: evidence/'],190,30,76);
 s.speakerNotes.append('\n\nEXACT PATHS\n'+[PROJECT+'/index.html',PROJECT+'/steps/22_Integration_and_Source_Mapping/a_Output_Schema_Definition.xlsx',PROJECT+'/steps/22_Integration_and_Source_Mapping/b_Schema_Rating_Scorecard.xlsx',PROJECT+'/steps/22_Integration_and_Source_Mapping/c_Output_Document.xlsx',PROJECT+'/scenario_data',PROJECT+'/contracts',PROJECT+'/evidence',ROOT+'/outputs/Talentra_Step_22_Professional_Explanation_Script.md'].join('\n'));
 await fs.writeFile(BUILD+'/speaking_notes.md',notes.map(r=>`## ${r.slide}. ${r.title}\n\n${r.notes}`).join('\n\n'),'utf8');
 return {slides:p.slides.items.length,notes:notes.length};
}
