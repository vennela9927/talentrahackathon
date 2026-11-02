# Talentra Phase 4: steps 23-25 (v8)

Builds on `talentra_step22_mini_seed_v7` (steps 1-22, unchanged). This release adds Data Generation at Scale (23),
Data Seeding (24) and Data Ingestion (25), and records what Phase 4 found about steps 1-22.

Start with `loop_back/Phase4_Audit_Change_Log_and_Gates.xlsx`: sheet 1 audits every step 1-25 against the
playbook's Done When.

## Results (native PostgreSQL 18.6, laptop)

| Step | Exit test | Result |
|---|---|---|
| 21 (REL-01) | DDL runs cleanly on an empty database | 120 tables, 494 foreign keys, 95 triggers; 004 smoke checks pass; dictionary drift 0 of 1250 columns |
| 23 | Volumes and distributions within tolerance | 37/37 profile checks pass |
| 24 | Seeding twice gives the same state | PASS: dev, test, demo, bench; second run changes 0 rows |
| 25 | Source = loaded + quarantined; every quarantined row has a reason | PASS: 29,650 of 29,650 planted defects quarantined with the exact expected reason, 0 unexpected |

Loaded through every native constraint and trigger: 1,000,000 candidates, 100,000 jobs,
5,000,000 applications and 10,787,863 status events, in 2.4 hours (one session).

Rubric scores (unchanged method): step 23 83.0, step 24 83.0,
step 25 80.2 /100. All stay **Refine**: independent comparison and the author interview
are unassessed, as in steps 1-22.

## Not done here
Steps 26-28 (test automation in CI, NFR at volume), the 3-year volume (10M/1M/100M), concurrency races,
provider-signed deliveries and the quarantine replay workflow. See `04_Gap register`.

## Reproduce
Needs PostgreSQL 18 and Python 3.12 with numpy and pandas. From `tools/` (set TALENTRA_PGPORT etc. if needed):

    python run_phase4.py --profile bench --db talentra_bench     # REL-01, steps 23, 24, 25 with evidence
    python step25_trigger_cost.py --db talentra_bench --json ../evidence/step25_trigger_cost.json
    python build_release.py                                      # rebuild these workbooks

The bench dataset (~0.7 GB) is not included; seed 23 regenerates it byte-for-byte
(SHA-256 in `evidence/bench_dataset_manifest.json`). The small demo dataset is in `sample_data/`.
`database/007_ingestion_control.sql` applies after the six released scripts in `database/RUN_ORDER.md`.
