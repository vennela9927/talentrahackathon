# Talentra Step 22: mini and seed workflow sets
Prepared 2026-11-01. Open index.html and choose Mini and seed.

The mentor images specify a split into mini and seed versions, 27 actors, 168 workflow steps, smaller workflow-defined sets, job-family/gig rules and analytics for each set. The user authorized a proposed catalogue derived from the existing project.

## Scope and provenance
The 168 entries are workflow operations, not 168 D3 lifecycle steps. Preserve the requested lifecycle cap at step 22. The catalogue retains all 18 Step 2 personas and all 116 Step 5 operations, then adds 9 proposed actor contexts and 52 proposed detailed steps. These include external providers and business subroles, not 27 newly deployed RBAC roles. The original source owners are retained. The additions remain proposals awaiting owner review.

## Two versions
mini/core contains 120 linked hiring journeys selected for coverage across six families and ten current outcomes, plus 100 gig applications from 20 requests. Application, event and job subsets retain their source identifiers and references. It is deliberately balanced for explanation and testing. Its rates must not estimate the full seed cohort. Mini job positions_filled retains the source job snapshot, which includes joins outside the mini sample.

seed/core contains the existing five v6 synthetic files, with matching SHA256 values, including 1,500,000 candidate-job journeys. This is 15 lakh, not 15 million and not 1.5 million submitted applications. The applied subset is 669,375. No database import or production capacity proof is claimed.

Each version has 27 workflow folders. A folder contains a manifest, guarded example cases, emitted step-example references and analytics. Mini has six cases per workflow. Seed has sixty cases per workflow. The cases exercise a generic envelope guard: valid input, cross-account, missing required input, blocked subject, duplicate and stale version. They do not execute the native workflow business transactions. Domain-specific rules have separate positive and refusal functions and recorded outcomes. Dictionary scalar examples do not form complete joined database rows.

Both mini/sets and seed/sets contain six smaller physical family sets, with journey/gig files and analytics.json for each. Other shared core files are referenced by the workflow manifests rather than duplicated. catalogue/field_examples.json supplies associated data elements and typed source examples for all 168 steps. Proposed fields are explicit staging examples.

## Rules and analytics
catalogue/rules.json covers job family, collar/branch, engagement, identity ownership, account scope, blocking, hiring order, duplicate/version handling, gig direction/window/assignment, external earnings, completed-own rating, currency, consent, sourcing approval, vacancies and denominator semantics. Fifty portable positive/refusal cases are in evidence/mini_seed_rule_tests.json. Analytics for all 54 sets distinguish example counts from business-stage KPIs. Version analytics use saved-file readback. Full native SQL, authorization, provider and load gates remain open.

## Files
The original dashboard views and steps 1–21 workbooks remain available. The three updated Step 22 workbooks retain original tabs and add the mini/seed catalogue, rules and results. Prior v6 scores remain visible as carried-forward ratings; this addendum has not received a new independent/human assessment.

To reproduce the portable workflow fixture sets in a new folder, run:

    python evidence/reproduce_workflow_fixtures.py --output NEW_FOLDER

This bundled command uses only the released catalogue and dictionary. It regenerates all 54 workflow sets and rule tests, without modifying the release. The full split authoring script additionally needs the original v6 layout. Reproduced fixture files were compared byte-for-byte with the release. The generation uses no database or network. Do not run the legacy v6 generator without its --generate-only option: its default mode targets the authoring layout. Source fingerprints and verification results are in evidence.

The compact combined workbook retains all 22 steps as concatenated records plus typed mini/seed tabs. The complete original master is preserved at prior_v6/Talentra_Combined.xlsx. Guest participates in the public-search entry of WF-19 only. Workflow participation does not grant permission for the other actors' actions. The primary owners remain explicit in each step.

## Open and explain
1. Open index.html in Chrome or Edge. Choose Mini and seed.
2. Select Mini or Seed, then a workflow group, workflow or actor.
3. Use the Actor catalogue, Workflow steps, Business rules and Business analytics shortcuts.
4. In Step outputs, select Step 22 and a Mini Seed section to inspect the same records. In Schemas, select Step 22 and L1–L4.

The Step 22 Output workbook adds tabs 27–36. The schema workbook adds Mini Seed Definition and Mini Seed Hierarchy. The scorecard adds Mini Seed Evidence. Historical inventory paths scenario_data/*.csv.gz correspond to seed/core/*.csv.gz in this release. The release keeps the complete folder structure for data links.

Kluster tools were unavailable in this session. The recorded checks cover source preservation, contracts, data relationships, portable rules, reproducibility, saved workbooks and browser behavior. No Kluster review, native database execution or production load pass is claimed.
