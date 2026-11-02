## 1. Talentra: Step 22

SPEAKING SCRIPT
Good morning, sir. This presentation explains Step 22 of Talentra. I will connect the business scenario to user workflows, generated data, source mappings and measurable results. The slides cover this step only. The Notes pane contains my explanation and exact project references.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
Mentor presentation / 30 October 2026

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 2. The purpose of Step 22

SPEAKING SCRIPT
Steps 1 to 21 established the model. Step 22 explains how data crosses the system boundary. This diagram is the intended integration design. Source data passes contract and account checks, then maps to an existing target, an explicit proposal or a transport purpose. Business effects and reconciliation need durable records. Provider adapters and native execution remain pending.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: Overview, Integration catalogue, Source target mapping

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 3. What one record means

SPEAKING SCRIPT
The mentor population is interpreted as 15 lakh synthetic candidate-job journeys. A journey begins before an application. An event records a milestone reached. An application exists only after submission. Screening means pre-application eligibility. The generated cohort uses one candidate and one target job per journey, but a production candidate can have multiple journeys.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 12_Business definitions, 23_Generated journey sample

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 4. Job families and engagement types

SPEAKING SCRIPT
White-collar jobs include IT development and testing, plus non-IT sales and delivery. Delivery follows the mentor classification as a configurable label. Warehouse and field service are proposed blue-collar examples. Engagement is an independent axis, so an IT developer can accept permanent, contract or gig work. The generated hiring and gig datasets remain separate scenarios.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 13_Job taxonomy, 15_Family funnel assumptions

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 5. Hiring workflow

SPEAKING SCRIPT
Read the upper row from search to assessment, then the lower row from interview to onboarding. Eligibility screening precedes application. At the interview decision the employer selects or rejects. After an offer the candidate accepts or declines. Selected candidates can wait for an offer and accepted candidates can wait for onboarding. These are cumulative reached-stage counts, not mutually exclusive current-state totals.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 14_Hiring funnel, 16_Family funnel counts

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 6. Generated hiring results

SPEAKING SCRIPT
These results come from saved synthetic data. Each family has proposed conversion rates, so these are workload assumptions rather than market measurements. Selected plus employer rejected equals interviewed. Accepted plus declined equals offered. Do not add cumulative milestone counts to calculate the audience. Pending stages explain the differences between selected, offered, accepted and onboarded.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 14_Hiring funnel / scenario_data/generation_summary.json

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 7. Hiring responsibilities and associated data

SPEAKING SCRIPT
The candidate owns registration, application and offer response. The recruiter can advance assigned applications within the correct organisation and must respect blocking. The employer issues offers and confirms joining. An integration worker validates source identity, deduplicates events and reconciles outcomes. These are documented service requirements. The portable fixtures do not prove endpoint authorization.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 18_Actor workflows / Dashboard: Workflows for each actor

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 8. Gig workflow

SPEAKING SCRIPT
Gig workers maintain their profile and availability, then apply to a requester. The requester accepts or rejects. Accepted applications have an assignment and an external handoff reference. The external system supplies status and earnings outcomes. Only completed assignments qualify for requester ratings. The 50,000 applications include 10,000 accepted, 30,000 rejected and 10,000 pending. Of the 10,000 accepted assignments, 8,000 completed and 4,000 received ratings. Retry-pending assignments remain in the completion denominator.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 24_Generated gig sample, 17_Business KPI register

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 9. One field traced to its destination

SPEAKING SCRIPT
MAP-M-002 maps candidate_profile_id from the journey source to candidate_profile.id. Native loading still requires identity translation within the account. MAP-M-001 maps journey_id to an explicitly proposed journey event structure. This makes the missing native support visible. Journey 3 in the sample is screened and has a null application identifier. The property is required in the payload but allows a null value. CSV backslash N becomes JSON null during parsing.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 21_Mentor source field mapping, rows 6–7 / contracts/mentor.journey.v1.schema.json

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 10. Integration failure workflow

SPEAKING SCRIPT
The source event first needs a valid account-bound identity and schema. A duplicate with the same key and hash returns its earlier durable outcome. The same key with a different hash is a conflict. Stale updates must not regress current state. Malformed or cross-account data is rejected or quarantined. Temporary provider failures remain pending with bounded retries. This is the proposed processing design with selected portable checks. Runtime adapters, signed callbacks and crash recovery still need proof.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 03_Failure policy, 25_Source failure scenarios

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 11. Business KPIs

SPEAKING SCRIPT
The register contains 18 KPIs. Screened conversion is screened journeys divided by searched journeys. Offer acceptance uses issued offers as its denominator. Time to hire uses first application and first accepted offer, measured in calendar days. Pending cases without end timestamps do not enter completed-duration averages. The gig completion denominator includes all accepted assignments, including retry-pending and in-progress cases. Values shown are synthetic scenario results.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 17_Business KPI register / Dashboard: Business KPIs

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 12. Generated data and validation

SPEAKING SCRIPT
The five datasets contain 6,433,696 rows at different grains. Saved files were read back for count and declared invariant checks, including legal events, time ordering, organisation references and gig guards. JSON contract checks cover 300 typed samples per file, or 1,500 in total. The portable guard model has 12 expected outcomes, one positive and eleven refusal cases. A 1,000-journey repeated generation matched all five hashes. None of these establishes native PostgreSQL, API authorization, provider or production load performance.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 22_Dataset inventory, 26_Mentor negative test evidenc / evidence folder

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 13. The three Step 22 deliverables

SPEAKING SCRIPT
The schema workbook defines required information. The scorecard assesses quality and evidence. The output workbook contains the populated records across 26 sections. The L1 to L4 hierarchy makes the definition inspectable. L1 is a section, L2 is a parameter, L3 separates value contract from meaning and lineage, and L4 states atomic type, validation and source properties. Priority marks importance separately from readiness. Artifact JSON schemas describe deliverables, while integration schemas describe exchanged payloads.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
Step 22 folder: a_Output_Schema_Definition.xlsx, b_Schema_Rating_Scorecard.xlsx, c_Output_Document.xlsx

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 14. Step 22 quality and production evidence

SPEAKING SCRIPT
Step 22 scores 82.9 on the full rubric and 97.7 on the supplementary documentary measure. Schema and scorecard each have 83 full and 100 documentary. Output has 82.8 full and 95.4 documentary. Independent comparison and human understanding need real reviewer evidence. Conditional 90-plus targets remain targets. Native database, concurrency, authorization, load, recovery and provider evidence remain separate release requirements. These numbers describe Step 22 only.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
B workbook: Summary, 90 Plus Closure, Human Review / C: Production release gates

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 15. Five model gaps for the next implementation

SPEAKING SCRIPT
The scenario exposes five model concerns. Search needs target-job attribution. Eligibility needs job context. Assessments need application context. Analytics needs reliable milestone timestamps. Job taxonomy needs versioned dimensions distinct from engagement. The gap register records affected earlier steps and the proposal status. Production work should resolve these through accepted model changes, migrations, backfill, dictionary updates and tests. The deck does not claim these additions are deployed.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 20_Native schema gap register / database/HYBRID_CHANGESET.md

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 16. Where to show each result in the dashboard

SPEAKING SCRIPT
For the visual story, click Business scenarios in the top navigation. Show the funnel, gig workflow, taxonomy, actor selector and business KPIs. For detail, open Step outputs, choose Step 22 and use its section dropdown. The screenshot in the earlier conversation already showed the Business scenario catalogue. The Hiring funnel, Job taxonomy and Actor workflows are other choices in that same dropdown. The dashboard is an offline snapshot. Excel edits and planning inputs do not automatically refresh its saved results.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
Open outputs/talentra_step22_mentor_v6/index.html in Chrome or Edge

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 17. Reference: all 12 actors

SPEAKING SCRIPT
This reference lists every actor in the mentor workflow register. Each actor has three rows for receiving and authorizing, executing the business action, and persisting and publishing the outcome. Some business personas share platform identities or roles. Do not interpret this catalogue as 12 newly implemented authorization roles. The exact fields, guards and proof status are in the workbook.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 18_Actor workflows / Dashboard actor dropdown

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 18. Reference: hiring conversion KPIs

SPEAKING SCRIPT
These conversion rates use distinct candidate-job journeys reaching the named stage in the same cohort. They are not unique-person conversion rates across all jobs. A zero denominator is not applicable. The values arise from proposed family conversion profiles in the synthetic generation.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 17_Business KPI register, KPI-H-01 to KPI-H-07

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 19. Reference: offers, joining and duration KPIs

SPEAKING SCRIPT
Offer issue uses selected journeys as the denominator. Offer acceptance and offer decline use offered journeys. Onboarding uses accepted journeys. Time to offer begins at application and ends at the first offer. Time to hire ends at the first accepted offer. Time to onboard begins at acceptance and ends at joining. Duration averages include only journeys reaching both milestones and use calendar days. Pending ageing requires a separate view.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 17_Business KPI register, KPI-H-08 to KPI-H-14

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 20. Reference: gig KPIs and business scenarios

SPEAKING SCRIPT
Gig request fill is accepted requests divided by published requests, which is 100 percent in this constructed fixture. Application acceptance is 20 percent of all submitted applications at the snapshot, including pending submissions. Completion is 80 percent of all accepted assignments. Rating coverage is 50 percent of completed assignments. The scenario catalogue contains 14 scenarios with business meaning, grain, associated entities and evidence status. They cover both hiring and platform concerns.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
C workbook: 17_Business KPI register, 19_Business scenario catalogue

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.

## 21. Files for the mentor demonstration

SPEAKING SCRIPT
The released project folder contains the dashboard, the three Step 22 workbooks and the complete synthetic data. Open index.html in a browser. Keep the complete extracted folder together for dataset links. In PowerPoint use Presenter View or the Notes pane to read the script and file references. The main result of Step 22 is a clear relationship between business workflows, source data, target mappings, KPIs and evidence. Production acceptance still requires closing the registered runtime and owner-review gates.

FILE AND DEMONSTRATION REFERENCE
Project folder: C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra/outputs/talentra_step22_mentor_v6
Project folder and exact file paths appear in the speaker notes

Source basis: saved v6 Step 22 workbooks, scenario_data/generation_summary.json and evidence files. All scenario values are synthetic. Step 22 is the start of Phase 4. Steps 23–28 remain outside scope.