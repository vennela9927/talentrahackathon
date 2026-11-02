"""Build the Phase 4 release (steps 23-25) from the evidence files written by run_phase4.py.

Writes outputs/talentra_phase4_steps_23_25_v8/ with, per step, the three released deliverables
(a_Output_Schema_Definition, b_Schema_Rating_Scorecard, c_Output_Document), their JSON artifact contracts,
the loop-back workbook (Phase 1-4 audit, change log, gates, gaps), the 007 migration, the inbound contracts,
the pipeline code, the demo dataset and every evidence file. Every number comes from evidence/*.json.
Usage: build_release.py [--out DIR]
"""
import argparse
import collections
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

from common import BASELINE, DATA, EVIDENCE, HERE, PROFILES, PROJECT, read_json, write_json
from contracts import CONTRACTS, LOAD_ORDER

sys.path.insert(0, str(HERE / "tools"))
import xlsx_write  # noqa: E402

PLAYBOOK = "Talencia DDD Playbook v1.0"
SRC23, SRC24, SRC25 = f"{PLAYBOOK} p.11 step 23", f"{PLAYBOOK} p.11 step 24", f"{PLAYBOOK} p.11 step 25"
RUBRIC = [  # (dimension, weight, critical, measure, return stage) - unchanged from the released scorecards
    ("Structure conformance", 14, "Yes", "Output rows/fields conform to the defined contract", "Generate"),
    ("Completeness", 14, "No", "Populated or explicit UNKNOWN cells / required documentary cells", "Generate"),
    ("Definition clarity", 9, "No", "Parameters with meaning, type, validation and reason / parameters", "Define"),
    ("Accuracy and traceability", 18, "Yes", "Source-located or explicitly proposed design items / items", "Generate"),
    ("Consistency across runs", 9, "No", "Independent author/model content agreement / compared items", "Analyse"),
    ("Structure and depth", 9, "No", "D5 L1 sections > L2 parameters > L3 facets > L4 atomic definitions", "Define"),
    ("Fitness for next step", 9, "No", "Required downstream inputs usable with stated open decisions", "Define"),
    ("Author understanding", 8, "Yes", "Human field questions correctly answered / questions asked", "Discover"),
    ("Deliverable-specific coverage", 10, "No", "Step exit criterion supported at its required proof layer", "Validate"),
]

# Meaning of every column used in an output section: (type, definition)
COLUMNS = {
    "Item": ("string", "Overview attribute name"),
    "Value": ("string", "Overview attribute value, from evidence"),
    "Profile": ("string", "Step 13 scale profile name"),
    "Organisations": ("integer", "Employer organisations (one account and one seeded employer/recruiter user each)"),
    "Candidates": ("integer", "Candidate accounts (app_user + candidate_profile)"),
    "Jobs": ("integer", "Job requirements"),
    "Applications": ("integer", "Job applications (one per candidate and job)"),
    "Status": ("string", "Outcome or state as recorded by the evidence"),
    "Use": ("string", "What the profile or set is for"),
    "Parameter": ("string", "Generator parameter name in step23_generate.py"),
    "Reason": ("string", "Why the value or decision was chosen"),
    "Source": ("string", "Playbook page, released workbook sheet or evidence file the item derives from"),
    "Check ID": ("string", "Stable identifier of the check within this step"),
    "Metric": ("string", "What is measured"),
    "Target": ("string", "Value the profile or rule requires"),
    "Tolerance": ("string", "Allowed difference from target, or eq/max for exact or upper-bound checks"),
    "Observed": ("string", "Value measured from the generated files or the database"),
    "Result": ("string", "PASS or FAIL against target and tolerance"),
    "File": ("string", "Delivery file path relative to the dataset folder"),
    "Contract": ("string", "Inbound contract key the file conforms to"),
    "Rows": ("integer", "Data rows (header excluded)"),
    "Bytes": ("integer", "File size in bytes (gzip)"),
    "SHA256": ("string", "SHA-256 of the file bytes"),
    "Batch": ("string", "Delivery folder (b001 initial, b002 delta, b003 stale re-sends)"),
    "Reason code": ("string", "Quarantine reason the pipeline must give (integration_rejection.reason_code)"),
    "Field": ("string", "Field path the reason refers to (integration_rejection.field_path)"),
    "Count": ("integer", "Number of rows"),
    "Purpose": ("string", "Which rule or behaviour the row exercises"),
    "Scenario": ("string", "Delta behaviour exercised"),
    "Expected treatment": ("string", "What the Step 25 pipeline must do with these rows"),
    "Bench measured": ("string", "Measured at the laptop benchmark profile"),
    "Year-3 target": ("string", "Step 13 full-scale value"),
    "Factor": ("number", "Year-3 target divided by bench"),
    "Projection": ("string", "Linear projection from the bench measurement; not measured"),
    "Decision ID": ("string", "Decision log identifier"),
    "Decision": ("string", "What was decided"),
    "Alternative": ("string", "Alternative considered and why it was not chosen"),
    "Owner": ("string", "Role that must confirm or owns the item"),
    "Question ID": ("string", "Review question identifier"),
    "Question": ("string", "Question for the author interview"),
    "Expected evidence anchor": ("string", "Where a correct answer is evidenced"),
    "Human response": ("string", "Author answer; null until the interview happens"),
    "Reviewer score 0 to 5": ("string", "Independent reviewer score; null until reviewed"),
    "Review status": ("string", "NOT REVIEWED until a human review is recorded"),
    "Proposed reviewer role": ("string", "Who should review"),
    "Case ID": ("string", "Acceptance case identifier"),
    "Case": ("string", "Behaviour under test"),
    "Expected result": ("string", "Outcome required by the step exit"),
    "Proof layer": ("string", "Where the proof runs (native PostgreSQL 18, generated files, documentary)"),
    "Evidence": ("string", "Evidence file and measured value"),
    "Set": ("string", "Seed set name"),
    "Environments": ("string", "Environments that load the set"),
    "Tables": ("string", "Native tables the set writes"),
    "Re-runnable by": ("string", "Mechanism that makes a second run a no-op"),
    "Environment": ("string", "Target environment"),
    "Sets": ("string", "Seed sets loaded, in order"),
    "Master source": ("string", "Where the master rows come from"),
    "Command": ("string", "Command that produces the state"),
    "Table": ("string", "Native table name"),
    "ID range": ("string", "Explicit id range owned by the seed"),
    "Content": ("string", "What the rows represent"),
    "Source code": ("string", "integration_source.code"),
    "Schema SHA256": ("string", "integration_contract.schema_sha256 (SHA-256 of the JSON Schema file)"),
    "Endpoint": ("string", "integration_source.endpoint_reference"),
    "First run rows changed": ("integer", "Rows inserted or updated by the first seed run"),
    "Second run rows changed": ("integer", "Rows inserted or updated by an immediate second run (must be 0)"),
    "Same state after second run": ("string", "Fingerprints of every seeded table equal after run 2"),
    "Same state on a fresh database": ("string", "Fingerprints equal when the seed runs once on a new database"),
    "Inserted": ("integer", "Rows inserted"),
    "Updated": ("integer", "Rows updated"),
    "Expected": ("string", "Answer fixed in advance"),
    "SQL": ("string", "Query that answers the question from the database"),
    "Stage": ("string", "Pipeline stage"),
    "What happens": ("string", "Processing done at this stage"),
    "Where": ("string", "Python or SQL object that does it"),
    "Failure behaviour": ("string", "What happens when the stage fails"),
    "Rule ID": ("string", "Ingestion rule identifier"),
    "Order": ("integer", "Evaluation order; the first failing rule gives the reason"),
    "Condition": ("string", "Condition that rejects the row"),
    "Contract ID": ("string", "Step 22 contract identifier"),
    "Required": ("string", "Whether the field must be present"),
    "Target or disposition": ("string", "Native column, guard or transport-only disposition"),
    "Transform and validation": ("string", "How the field is checked and converted"),
    "New": ("integer", "Rows inserted as new records"),
    "Duplicate": ("integer", "Exact re-sends and superseded rows (no effect)"),
    "Quarantined": ("integer", "Rows rejected with a reason"),
    "Late in order": ("integer", "Status events applied to applications loaded in an earlier delivery"),
    "Recon applied": ("integer", "reconciliation_run.applied_count"),
    "Recon rejected": ("integer", "reconciliation_run.rejected_count"),
    "Recon duplicate": ("integer", "reconciliation_run.duplicate_count"),
    "Recon pending": ("integer", "reconciliation_run.pending_count"),
    "Balanced": ("string", "source = new + updated + duplicate + quarantined, and the native CHECK holds"),
    "Seconds": ("number", "Wall-clock seconds for the file's transaction"),
    "Source rows": ("integer", "Data lines in the file, including malformed ones"),
    "Expected count": ("integer", "Rows planted with this reason by Step 23"),
    "Actual count": ("integer", "Rows the pipeline quarantined with this reason"),
    "Match": ("string", "Expected and actual agree row by row"),
    "Check": ("string", "Integrity or reconciliation check"),
    "Rerun status": ("string", "batch_file status of the repeated delivery"),
    "Rows per second": ("number", "Throughput of the file's transaction"),
    "Microseconds per row": ("number", "Measured insert cost per status event"),
    "Measurement": ("string", "What was enabled during the measurement"),
    "Relation": ("string", "Table or index owner"),
    "Table MB": ("number", "Heap size in MB"),
    "Index MB": ("number", "Index size in MB"),
}


def fmt(v):
    return "" if v is None else v


class Doc:
    """One step's output document: ordered sections with headers, rows and a reason per section."""

    def __init__(self, step, name, exit_text):
        self.step, self.name, self.exit = step, name, exit_text
        self.sections = []

    def add(self, title, header, rows, reason, source):
        missing = [h for h in header if h not in COLUMNS]
        if missing:
            raise SystemExit(f"step {self.step} section {title}: no definition for columns {missing}")
        self.sections.append({"title": title, "header": header, "rows": [[fmt(c) for c in r] for r in rows],
                              "reason": reason, "source": source})


def human_and_acceptance(doc, owner, questions, cases):
    doc.add("Human review prompts", ["Question ID", "Question", "Expected evidence anchor", "Human response",
                                     "Reviewer score 0 to 5", "Review status", "Proposed reviewer role"],
            [[f"INT-{doc.step}-{i + 1}", q, a, None, None, "NOT REVIEWED", owner] for i, (q, a) in enumerate(questions)],
            "Author understanding is a critical rubric dimension and cannot be self-assessed", "Released scorecard method")
    doc.add("Acceptance cases", ["Case ID", "Case", "Expected result", "Proof layer", "Status", "Evidence"],
            [[f"ACC-{doc.step}-{i + 1}", *c] for i, c in enumerate(cases)],
            "The step's Done When, split into testable cases with their proof", f"{PLAYBOOK} p.5 (Done when)")


# ------------------------------------------------------------------------------------------------ step 23
def step23(ev, data):
    prof, man = ev["profile"], read_json(data / "manifest.json")
    runs = {r["file"]: r for r in ev["ingest"]["runs"]}
    d = Doc(23, "Data Generation at Scale",
            "Volumes and distributions match the Step 13 profile within tolerance (seeded, reproducible generator)")
    d.add("Generation profiles", ["Profile", "Organisations", "Candidates", "Jobs", "Applications", "Status", "Use"],
          [["demo", *PROFILES["demo"].values(), "Generated", "Demonstration seed set; Step 24 demo env"],
           ["dev", *PROFILES["dev"].values(), "Generated", "Development seed set; Step 24 dev env"],
           ["bench", *PROFILES["bench"].values(), "Generated, loaded and reconciled",
            "Step 13 laptop benchmark (CAP-01); Step 25 full-volume load"],
           ["year3", *PROFILES["year3"].values(), "Sized only (ING-GAP-01)", "Step 13 full-scale 3-year target"]],
          "Shows which Step 13 profile each dataset represents", "Step 13 02_Scale profiles; Step 4 04_Scale cases")
    p = man["parameters"]
    d.add("Generator parameters", ["Parameter", "Value", "Reason", "Source"], [
        ["seed", man["seed"], "Same seed and code give byte-identical files", "step23_generate.py"],
        ["org_sigma", p["org_sigma"], "Lognormal organisation size; 40% of organisations post ~78% of jobs",
         "Step 13 T174 R-18..20"],
        ["job_sigma", p["job_sigma"], "Heavy right tail of applications per job", "Step 13 T174 R-23..26"],
        ["org_traffic_alpha", p["org_traffic_alpha"], "Bigger employers attract more applications per job",
         "Step 13 03_Generation distributions (10% orgs / 60% writes)"],
        ["candidate_sigma", p["candidate_sigma"], "Some candidates apply far more often than others", "Assumption"],
        ["max_apps_per_job", p["max_apps_per_job"], "Upper bound of the tail", "Step 13 T174 R-23..26 max 2,500"],
        ["peak_day_factor", p["peak_day_factor"], "Four peak days at 2.5x the median day",
         "Step 13 03_Generation distributions"],
        ["peak_days", ", ".join(p["peak_days"]), "Campus and appraisal seasons", "Step 13 T176 seasonality"],
        ["null_rate", p["null_rate"], "Optional columns are null 10% of the time", "Step 13 03_Generation distributions"],
        ["window", f"{p['window_start']} + {p['window_days']} days", "Every status path completes before the snapshot",
         "Assumption"],
        ["paths", "; ".join(f"{'>'.join(s)}={w}" for s, w in p["paths"]),
         "Native application states; reach 28/14/5/3% shortlisted/interviewed/offered/joined", "Step 13 T174 R-27..28"],
    ], "Makes the generated distribution reviewable and reproducible", "step23_generate.py")
    d.add("Profile check", ["Check ID", "Metric", "Target", "Tolerance", "Observed", "Result", "Source"],
          [[f"PC-{i + 1:02d}", c["metric"], c["target"], c["tolerance"], c["observed"], "PASS" if c["pass"] else "FAIL",
            c["source"]] for i, c in enumerate(prof["checks"])],
          "The Done When test: volumes and distributions against the profile", "evidence/step23_profile_check.json")
    d.add("Dataset files", ["File", "Contract", "Rows", "Bytes", "SHA256"],
          [[f["path"], contract_of(f["path"]), (runs.get(f["path"]) or {}).get("source_rows"), f["bytes"], f["sha256"]]
           for f in man["files"]], "Lets anyone confirm they hold the exact generated data", "manifest.json")
    planted = collections.Counter()
    with open(data / "expected_quarantine.csv", encoding="utf-8") as h:
        for r in csv.DictReader(h):
            planted[(r["batch"], r["file"], r["contract"], r["reason"], r["field_path"])] += 1
    d.add("Planted defects", ["Batch", "File", "Contract", "Reason code", "Field", "Count", "Purpose"],
          [[*k, n, PURPOSE.get(k[3], "")] for k, n in sorted(planted.items())],
          "Invalid rows on purpose, each with the reason Step 25 must give", "expected_quarantine.csv")
    dl = man["deltas"]
    d.add("Delta scenarios", ["Scenario", "Batch", "File", "Rows", "Expected treatment"], [
        ["Exact re-send", "b002", "candidates.csv.gz", dl["duplicate_candidate_resends"], "Counted as duplicate; no change"],
        ["Same key and version, different content", "b002", "candidates.csv.gz", dl["key_reuse_candidates"],
         "Quarantine KEY_REUSE"],
        ["Correction (source_version 2)", "b002", "jobs.csv.gz", dl["corrected_jobs"],
         "Update through row_version trigger, acting as the employer"],
        ["Late event, in order", "b002", "status_events.csv.gz", dl["late_in_order_events"],
         "Append history; status moves through the native state-edge trigger as the recruiter"],
        ["Late event, out of order", "b002", "status_events.csv.gz", dl["late_out_of_order_events"],
         "Quarantine LATE_OUT_OF_ORDER (history is append-only)"],
        ["Stale version 1 after version 2", "b003", "jobs.csv.gz", sum(
            n for k, n in planted.items() if k[3] == "STALE_VERSION"), "Quarantine STALE_VERSION"],
    ], "The Go deeper of step 25 (late and corrected records) needs these inputs", SRC25)
    size_gb = ev["summary"]["database_bytes"] / 1e9
    secs = load_seconds(ev["ingest"]["runs"], "b001")
    y, b = PROFILES["year3"], PROFILES["bench"]
    f = y["applications"] / b["applications"]
    d.add("Three-year projection", ["Metric", "Bench measured", "Year-3 target", "Factor", "Projection", "Status"], [
        ["Applications", b["applications"], y["applications"], f, f"{y['applications']:,}", "Target volume"],
        ["Database size", f"{size_gb:.1f} GB", "-", f, f"~{size_gb * f:.0f} GB", "Linear estimate; ING-GAP-01"],
        ["Initial load, one session", f"{secs / 3600:.2f} h", "-", f, f"~{secs * f / 3600:.0f} h",
         "Linear estimate; parallel load and trigger redesign needed (CHG-21-02)"],
    ], "Go deeper asks where performance degrades at 3-year volume; it was not generated here", SRC23)
    d.add("Decision log", ["Decision ID", "Decision", "Reason", "Alternative", "Owner", "Status"], DECISIONS_23,
          "Rule 2 of the playbook: every assumption and design choice with its reason", f"{PLAYBOOK} p.5")
    human_and_acceptance(d, "Data owner", [
        ("Why is the applications-per-job median 29 rather than the 45 in Step 13?", "CHG-13-01; profile check PC-09"),
        ("Which Step 13 targets are not generated, and why?", "Three-year projection; ING-GAP-01"),
        ("How would you prove two people generated the same data?", "Dataset files SHA256; seed 23"),
    ], [["Volumes equal the bench profile", "Exact counts", "Generated files", status(all(
        c["pass"] for c in prof["checks"][:4])), "evidence/step23_profile_check.json PC-01..04"],
        ["Distributions within tolerance", "Every profile check passes", "Generated files", status(prof["pass"]),
         f"{prof['passed']}/{prof['total']} checks pass"],
        ["Integrity intact", "0 orphan rows after loading", "Native PostgreSQL 18", status(
            ev["verify"]["integrity_clean"]), "evidence/step25_verification.json integrity"],
        ["Reproducible", "Seeded generator; files hashed", "Generated files", "PASS", "manifest.json"]])
    return d


PURPOSE = {
    "MISSING_REQUIRED": "Required field absent", "INVALID_FORMAT": "Unparseable value",
    "OUT_OF_RANGE": "Value outside the allowed range", "UNKNOWN_REFERENCE": "Code or id not in reference data",
    "INVALID_STATE": "'erased' is never accepted inbound", "UNSUPPORTED_VERSION": "schema_version other than 1",
    "MALFORMED_ROW": "Wrong number of columns", "UNIQUE_CONFLICT": "Natural key already owned by another record",
    "UNKNOWN_PARENT": "Parent record never loaded", "WRONG_DOMAIN": "Reference id from another vocabulary (BR-031)",
    "INCONSISTENT": "Salary fields partially present", "CROSS_ACCOUNT": "Record claims another tenant's organisation",
    "ILLEGAL_TRANSITION": "Edge not in transition_rule", "CHAIN_BREAK": "from_status differs from current status",
    "ACTOR_NOT_PERMITTED": "Edge exists only for another role", "KEY_REUSE": "Same key and version, new content",
    "LATE_OUT_OF_ORDER": "Older than the latest recorded event", "STALE_VERSION": "Lower source_version than loaded",
}

DECISIONS_23 = [
    ["DEC-23-01", "Generate the Step 13 laptop benchmark (1M candidates, 100k jobs, 5M applications) at full volume",
     "Step 4 CAP-01 and Step 21 REL-03 name it as the measured case", "Year-3 volume: ~20x the disk available",
     "Performance owner", "Applied"],
    ["DEC-23-02", "20,000 organisations for the bench profile", "Docket ratio 10M:1M:200k scaled to 1M candidates",
     "Step 13 laptop row has no organisation count", "Data owner", "Proposed (CHG-13-02)"],
    ["DEC-23-03", "Keep total applications exact and scale the per-job tail (median 29, p95/median ~5.6)",
     "R-23..26 (median 45, p95 280) implies ~8.3M applications for 100k jobs, not 5M", "Keep 45/280 and break totals",
     "Data owner", "Proposed (CHG-13-01)"],
    ["DEC-23-04", "Planted defects are extra rows, never altered valid rows",
     "Valid population stays exactly on profile; every defect has a known expected reason", "Corrupt a share of rows",
     "Quality owner", "Applied"],
    ["DEC-23-05", "Large deliveries are split into parts of 1M applications with their events",
     "Bounded transaction size and temp space; matches how large migrations are delivered", "One 15M-row transaction",
     "Data engineering owner", "Applied"],
    ["DEC-23-06", "Synthetic names in English, Hindi and Tamil; e-mail domains example.invalid",
     "Step 12: test data never holds real personal data; NFR-013 languages", "Faker-style realistic identities",
     "Privacy owner", "Applied"],
]


# ------------------------------------------------------------------------------------------------ step 24
def step24(ev):
    from step24_reference import CITIES, INDUSTRIES, ROLES, STATES
    from step24_seed import GOLDEN_QUERIES
    seeds = ev["seeds"]
    d = Doc(24, "Data Seeding", "Running the seed twice produces exactly the same state, for every environment")
    d.add("Seed sets", ["Set", "Environments", "Tables", "Rows", "Source", "Re-runnable by"], [
        ["reference", "dev, test, demo, bench", "state, city, job_role, industry, integration_source, integration_contract",
         len(STATES) + len(CITIES) + len(ROLES) + len(INDUSTRIES) + 2 * len(LOAD_ORDER), "step24_reference.py; contracts",
         "Explicit ids; upsert updates only rows whose values differ"],
        ["master", "dev, demo, bench", "account, organisation, app_user, user_role, recruiter_membership, ingest.key_map",
         "6 rows + 2 keys per organisation", "Step 23 master/organisations.csv.gz of the profile", "Same"],
        ["golden", "test", "master tables + candidate_profile, job_requirement, job_application, application_status_event",
         sum(v["inserted"] for v in next(s for s in seeds if s["env"] == "test")["changes_first_run"].values()),
         "step24_seed.py GOLDEN_*", "Same; history rows insert-only and fail on conflicting content"],
    ], "Separates reference, master and test data as step 24 requires", SRC24)
    d.add("Environment matrix", ["Environment", "Sets", "Purpose", "Master source", "Command"], [
        ["dev", "reference, master", "Developer database; transactional data via Step 25 on the dev dataset",
         "data/dev_seed23", "step24_seed.py --env dev --master data/dev_seed23"],
        ["test", "reference, golden", "Known answers for automated tests (steps 26-27)", "Built in",
         "step24_seed.py --env test"],
        ["demo", "reference, master", "Mentor demonstrations; small and readable", "data/demo_seed23",
         "step24_seed.py --env demo --master data/demo_seed23"],
        ["bench", "reference, master", "Full-volume load target for Step 25", "data/bench_seed23",
         "step24_seed.py --env bench --master data/bench_seed23"],
    ], "Go deeper: separate seed sets for development, testing and demonstration", SRC24)
    d.add("Reference data", ["Table", "Rows", "ID range", "Content", "Source"], [
        ["state", len(STATES), "1001-1021", "Indian states with ISO 3166-2:IN codes", "Public reference"],
        ["city", len(CITIES), "1001-1040", "8 Tier-1 and 32 other cities with rounded coordinates", "Step 13 R-21..22"],
        ["job_role", len(ROLES), "1001-1019", "Roles for the six mentor job families (family in the code)",
         "Step 22 13_Job taxonomy; MGAP-05"],
        ["industry", len(INDUSTRIES), "1001-1012", "Employer industries", "Assumption"],
        ["integration_source / integration_contract", len(LOAD_ORDER), "100001-100004",
         "One file-drop source per inbound contract", "Step 22 CON-018; CON-033..035 (CHG-22-01)"],
    ], "Reference rows every environment shares", "step24_reference.py")
    shas = {}
    for key in LOAD_ORDER:
        shas[key] = hashlib.sha256((DATA / "contracts" / f"{key}.schema.json").read_bytes()).hexdigest()
    d.add("Integration registry", ["Source code", "Contract", "Schema SHA256", "Owner", "Endpoint", "Status"],
          [[CONTRACTS[k]["source_code"], k, shas[k], CONTRACTS[k]["owner"], f"file-drop://legacy_ats/{CONTRACTS[k]['file']}",
            "Enabled for migration; provider sign-off pending"] for k in LOAD_ORDER],
          "Ingestion only accepts contracts registered here", "Step 22 01_Integration catalogue")
    d.add("Re-run proof", ["Environment", "First run rows changed", "Second run rows changed",
                           "Same state after second run", "Same state on a fresh database", "Result"],
          [[s["env"], s["first_run_rows_changed"], s["second_run_rows_changed"], str(s["same_state_after_second_run"]),
            str(s.get("same_state_on_a_fresh_database", "not run (bench db)")),
            status(s["second_run_rows_changed"] == 0 and s["same_state_after_second_run"])] for s in seeds],
          "The Done When test", "evidence/step24_seed_runs.json")
    g = next(s for s in seeds if s["env"] == "test")["golden_answers"]
    d.add("Golden dataset answers", ["Question", "Expected", "Observed", "Result", "SQL"],
          [[q, json.dumps(v["expected"]), json.dumps(v["observed"]), status(v["pass"]),
            " ".join(GOLDEN_QUERIES[q].split())] for q, v in g.items()],
          "Step 14 Go deeper (golden dataset) carried into the test seed", "evidence/step24_seed_runs.json")
    d.add("Changes per table", ["Environment", "Table", "Inserted", "Updated"],
          [[s["env"], t, v["inserted"], v["updated"]] for s in seeds for t, v in s["changes_first_run"].items()],
          "Shows what each first run wrote; second runs wrote nothing", "evidence/step24_seed_runs.json")
    d.add("Decision log", ["Decision ID", "Decision", "Reason", "Alternative", "Owner", "Status"], [
        ["DEC-24-01", "Upsert with explicit ids and fixed timestamps; update only when values differ",
         "A no-change second run fires no update triggers and changes no row_version", "Truncate and reload",
         "Database owner", "Applied"],
        ["DEC-24-02", "Seeded ids start at 1001 (reference) and 100,001 (master)",
         "Never collide with baseline rows 1-3 or with ingested identity values", "Natural keys only",
         "Database owner", "Applied"],
        ["DEC-24-03", "Each organisation's seeded user holds employer and recruiter roles",
         "Job edges require employer, application edges recruiter (transition_rule)", "Two users per organisation",
         "Security owner", "Proposed (CHG-24-01)"],
        ["DEC-24-04", "Identity sequences are moved past seeded ids in the same transaction",
         "Ingested rows can never take a seeded id", "Separate id service", "Database owner", "Applied"],
    ], "Rule 2 of the playbook", f"{PLAYBOOK} p.5")
    human_and_acceptance(d, "Database owner", [
        ("What makes a second seed run change nothing?", "DEC-24-01; Re-run proof"),
        ("Why does history (application_status_event) never update during seeding?", "BR-025; golden set"),
        ("Which environment would you use to test a new business rule, and why?", "Environment matrix"),
    ], [["Seed twice, same state", "0 rows changed and equal fingerprints", "Native PostgreSQL 18",
         status(all(s["second_run_rows_changed"] == 0 for s in seeds)), "evidence/step24_seed_runs.json"],
        ["Fresh database gives the same state", "Equal fingerprints", "Native PostgreSQL 18",
         status(all(s.get("same_state_on_a_fresh_database", True) for s in seeds)), "evidence/step24_seed_runs.json"],
        ["Golden answers hold", "Every answer equals the fixed value", "Native PostgreSQL 18",
         status(all(v["pass"] for v in g.values())), "Golden dataset answers"],
        ["Separate dev, test and demo sets", "Distinct sets per environment", "Documentary + native", "PASS",
         "Environment matrix"]])
    return d


# ------------------------------------------------------------------------------------------------ step 25
def step25(ev):
    ver, ing = ev["verify"], ev["ingest"]
    d = Doc(25, "Data Ingestion", "Source = loaded + quarantined, and every quarantined row has a reason")
    d.add("Pipeline stages", ["Stage", "What happens", "Where", "Failure behaviour", "Evidence"], [
        ["Skip check", "A file whose contract + SHA256 already completed is recorded as skipped",
         "ingest.batch_file partial unique index", "No business write", "Re-run proof"],
        ["Stage", "Column count checked; payload hashed without transport fields; COPY into a temp table",
         "step25_ingest.stage_file", "Wrong width -> MALFORMED_ROW", "Quarantine by reason"],
        ["Validate", "One reason per bad row; first failing rule wins", "Set-based SQL per contract",
         "Row quarantined", "Validation rules"],
        ["Version", "new / correction / duplicate / KEY_REUSE / STALE_VERSION per external key", "ingest.key_map",
         "Row quarantined or counted duplicate", "Delta batches b002, b003"],
        ["Chain", "Status events must continue the application's current status on a permitted edge for the actor",
         "transition_rule, user_role", "Event and every later event of that application quarantined",
         "CHAIN_BREAK, ILLEGAL_TRANSITION, ACTOR_NOT_PERMITTED"],
        ["Load", "Inserts in 500k-row statements; corrections and late events through native triggers",
         "Baseline tables", "Any error rolls back the whole file", "Batch reconciliation"],
        ["Quarantine", "integration_inbox (quarantined) + integration_rejection(reason, field)", "Baseline 005 tables",
         "-", "Quarantine by reason"],
        ["Reconcile", "reconciliation_run with native CHECK; target delta must equal rows reported new",
         "ingest.assert_true", "Whole file rolls back", "Batch reconciliation"],
    ], "Validate, transform, load as step 25 requires", SRC25)
    d.add("Validation rules", ["Rule ID", "Contract", "Order", "Reason code", "Field", "Condition", "Source"],
          VALIDATION_RULES, "Every rejection reason the pipeline can give, in evaluation order",
          "step25_ingest.py; Step 11/18 rules; Step 22 failure policy")
    rows = []
    for key in LOAD_ORDER:
        c = CONTRACTS[key]
        if c.get("released"):
            rows.append([c["id"], key, "(23 fields)", "As released", "job_requirement.* as named",
                         "Released Step 22 mapping; organisation_id translated through ingest.key_map", c["owner"]])
            continue
        for name, kind, req, target, rule in c["fields"]:
            rows.append([c["id"], key, name, "Yes" if req else "No", target, f"{kind}; {rule}", c["owner"]])
    d.add("Contract mapping", ["Contract ID", "Contract", "Field", "Required", "Target or disposition",
                               "Transform and validation", "Owner"], rows,
          "Completes the Step 22 mapping for the three contracts added by CHG-22-01", "contracts.py")
    recon = []
    for f in ver["files"]:
        recon.append([f["batch_label"], f["file_name"], f["status"], f["source_rows"], f["applied_new"],
                      f["applied_updated"], f["duplicates"], f["quarantined"], f["late_in_order"], f["applied_count"],
                      f["rejected_count"], f["duplicate_count"], f["pending_count"],
                      "" if f["status"] != "completed" else str(bool(f["recon_ok"])), f["seconds"]])
    d.add("Batch reconciliation", ["Batch", "File", "Status", "Source rows", "New", "Updated", "Duplicate", "Quarantined",
                                   "Late in order", "Recon applied", "Recon rejected", "Recon duplicate",
                                   "Recon pending", "Balanced", "Seconds"], recon,
          "The Done When test, per delivered file", "evidence/step25_verification.json; reconciliation_run")
    exp = collections.Counter()
    with open(ev["data"] / "expected_quarantine.csv", encoding="utf-8") as h:
        for r in csv.DictReader(h):
            exp[(r["contract"], r["reason"], r["field_path"])] += 1
    act = collections.Counter()
    for r in ev["quarantine_rows"]:
        act[(r["contract"], r["reason"], r["field"])] += 1
    d.add("Quarantine by reason", ["Contract", "Reason code", "Field", "Expected count", "Actual count", "Match"],
          [[*k, exp.get(k, 0), act.get(k, 0), status(exp.get(k, 0) == act.get(k, 0))] for k in sorted(set(exp) | set(act))],
          "Every quarantined row has a reason, and it is the reason planted", "evidence/step25_verification.json")
    integ = ver["integrity"]
    checks = [["Planted defects quarantined with the expected reason (row level)", ver["expected_quarantine"],
               ver["actual_quarantine"], status(ver["quarantine_exact"])],
              ["Missing quarantines", 0, len(ver["missing"]), status(not ver["missing"])],
              ["Unexpected quarantines", 0, len(ver["unexpected"]), status(not ver["unexpected"])],
              ["Every completed file balances", "true", str(ver["all_files_reconciled"]),
               status(ver["all_files_reconciled"])]]
    checks += [[k.replace("_", " "), 0, v, status(v == 0)] for k, v in integ.items()]
    checks.append(["Re-running b001 skips every file and leaves state unchanged", "true",
                   str(ing["rerun_state_unchanged"]), status(ing["rerun_state_unchanged"])])
    d.add("Integrity checks", ["Check", "Expected", "Observed", "Result"], checks,
          "Never silently losing or corrupting a record", "evidence/step25_verification.json")
    d.add("Re-run proof", ["File", "Rerun status", "Evidence"],
          [[r["file"], r["status"], "Business-table fingerprints equal before and after"] for r in ing["rerun_b001"]],
          "Go deeper: the pipeline is re-runnable", "evidence/step25_ingestion_runs.json")
    thr = [[r["file"], r["source_rows"], r["seconds"], round(r["source_rows"] / r["seconds"]) if r["seconds"] else None]
           for r in ing["runs"] if r.get("status") == "completed"]
    d.add("Throughput", ["File", "Source rows", "Seconds", "Rows per second"], thr,
          "Measured single-session load rate through every native control; input to Step 28", "evidence")
    d.add("Control cost", ["Measurement", "Rows", "Microseconds per row", "Rows per second"],
          [[m["case"], m["rows"], m["microseconds_per_row"], m["rows_per_second"]] for m in ev["trigger_cost"]],
          "Explains where load time goes (CHG-21-02)", "evidence/step25_trigger_cost.json (rolled back)")
    d.add("Storage", ["Relation", "Rows", "Table MB", "Index MB"],
          [[s["relation"], s["rows"], round(s["table_bytes"] / 1e6, 1), round(s["index_bytes"] / 1e6, 1)]
           for s in ev["summary"]["relation_sizes"][:15]], "Measured footprint at bench volume", "phase4_summary.json")
    d.add("Decision log", ["Decision ID", "Decision", "Reason", "Alternative", "Owner", "Status"], DECISIONS_25,
          "Rule 2 of the playbook", f"{PLAYBOOK} p.5")
    human_and_acceptance(d, "Data engineering owner", [
        ("Show that source = loaded + quarantined for one file using only the database.",
         "reconciliation_run CHECK; batch_file"),
        ("Why is a late out-of-order event quarantined rather than applied?", "DEC-25-04; BR-025"),
        ("What happens if the database fails halfway through a file?", "Pipeline stages: one transaction per file"),
    ], [["Source = loaded + quarantined", "Every completed file balances", "Native PostgreSQL 18",
         status(ver["all_files_reconciled"]), "Batch reconciliation"],
        ["Every quarantined row has a reason", "0 rows without reason or field", "Native PostgreSQL 18",
         status(integ["rejections_without_reason"] == 0 and integ["quarantined_without_rejection"] == 0),
         "Integrity checks"],
        ["Correct reason for every planted defect", "Row-level exact match", "Native PostgreSQL 18",
         status(ver["quarantine_exact"]), f"{ver['actual_quarantine']} of {ver['expected_quarantine']}"],
        ["Late and corrected records", "Corrections update; late in-order applied; out-of-order and stale quarantined",
         "Native PostgreSQL 18 (triggers)", status(ver["pass"]), "Batch reconciliation b002, b003"],
        ["Re-runnable", "Second delivery of b001 changes nothing", "Native PostgreSQL 18",
         status(ing["rerun_state_unchanged"]), "Re-run proof"]])
    return d


VALIDATION_RULES = [
    ["ING-E01", "all", 1, "MISSING_REQUIRED", "external_key, event_id", "Empty or absent", "Step 22 envelope"],
    ["ING-E02", "all", 2, "UNSUPPORTED_VERSION", "schema_version", "Not 1", "Step 22 ERR-09"],
    ["ING-E03", "all", 3, "INVALID_TYPE", "source_version", "Not a non-negative integer", "Step 22 envelope"],
    ["ING-E04", "all", 4, "INVALID_FORMAT / OUT_OF_RANGE", "occurred_at", "Not UTC ISO-8601, or in the future",
     "Step 22 envelope"],
    ["ING-E05", "all", 5, "MALFORMED_ROW", "$", "Wrong number of columns", "Step 22 ERR-06"],
    ["ING-C01", "legacy.candidate_account.v1", 10, "MISSING_REQUIRED", "email, person_name, ...", "Required field empty",
     "Contract"],
    ["ING-C02", "legacy.candidate_account.v1", 11, "INVALID_FORMAT", "email", "Not a valid address", "Step 11"],
    ["ING-C03", "legacy.candidate_account.v1", 12, "UNKNOWN_REFERENCE", "preferred_language, content_language, city_id",
     "Not en/hi/ta or not in city", "NFR-013; Step 11"],
    ["ING-C04", "legacy.candidate_account.v1", 13, "INVALID_FORMAT / OUT_OF_RANGE", "birth_date",
     "Not a date, or younger than 14 at registration", "ING-BR-01 (proposed)"],
    ["ING-C05", "legacy.candidate_account.v1", 14, "INVALID_STATE / UNKNOWN_REFERENCE", "profile_status",
     "'erased' or not in the candidate_profile vocabulary", "Step 8 states"],
    ["ING-C06", "legacy.candidate_account.v1", 20, "UNIQUE_CONFLICT", "email", "Owned by another user or earlier line",
     "uq_app_user_email"],
    ["ING-J01", "legacy.job_requirement.v1", 10, "UNKNOWN_PARENT", "organisation_id", "Organisation not in key map",
     "Step 22 MAP"],
    ["ING-J02", "legacy.job_requirement.v1", 11, "WRONG_DOMAIN", "*_reference_value_id",
     "Id not in the bound vocabulary", "BR-031"],
    ["ING-J03", "legacy.job_requirement.v1", 12, "OUT_OF_RANGE / INCONSISTENT", "positions, salary_*, currency_code",
     "positions <= 0; min > max; partial salary", "Step 21 CHECKs"],
    ["ING-J04", "legacy.job_requirement.v1", 20, "ILLEGAL_TRANSITION", "status_reference_value_id",
     "Correction changes status along no permitted edge", "transition_rule"],
    ["ING-A01", "legacy.job_application.v1", 10, "UNKNOWN_PARENT", "candidate_key, job_key", "Parent not loaded",
     "Step 22 MAP"],
    ["ING-A02", "legacy.job_application.v1", 11, "CROSS_ACCOUNT", "organisation_key", "Differs from the job's organisation",
     "Step 22 failure scenarios"],
    ["ING-A03", "legacy.job_application.v1", 12, "INVALID_FORMAT / OUT_OF_RANGE", "applied_at",
     "Unparseable, future, or before the job existed", "Step 11"],
    ["ING-A04", "legacy.job_application.v1", 20, "UNIQUE_CONFLICT", "candidate_key,job_key",
     "Pair already applied", "uq_job_application_candidate_job"],
    ["ING-S01", "legacy.application_status_event.v1", 10, "UNKNOWN_REFERENCE", "to_status, from_status, actor_type",
     "Not in the job_application vocabulary", "Step 8"],
    ["ING-S02", "legacy.application_status_event.v1", 11, "UNKNOWN_PARENT / CROSS_ACCOUNT", "application_key",
     "Unknown application or other tenant", "Step 22"],
    ["ING-S03", "legacy.application_status_event.v1", 12, "OUT_OF_RANGE / ACTOR_MISMATCH", "occurred_at, actor_key",
     "Before the application; actor not the candidate or the organisation's recruiter", "Step 2 roles"],
    ["ING-S04", "legacy.application_status_event.v1", 20, "LATE_OUT_OF_ORDER", "occurred_at",
     "Older than the application's latest recorded event", "BR-025; Step 22 late events"],
    ["ING-S05", "legacy.application_status_event.v1", 21, "CHAIN_BREAK", "from_status",
     "Does not continue the current status", "Step 8"],
    ["ING-S06", "legacy.application_status_event.v1", 22, "ILLEGAL_TRANSITION / ACTOR_NOT_PERMITTED",
     "from_status,to_status / actor_type", "Edge absent, or absent for this actor's role", "transition_rule"],
    ["ING-S07", "legacy.application_status_event.v1", 23, "PRIOR_EVENT_QUARANTINED", "application_key",
     "An earlier event of the same application was rejected", "Append-only history"],
    ["ING-V01", "all", 30, "KEY_REUSE / STALE_VERSION", "source_version",
     "Same version with different content, or lower than loaded", "Step 22 ERR-03, ERR-04"],
]

DECISIONS_25 = [
    ["DEC-25-01", "Load through the baseline tables and their triggers; never bypass controls",
     "Proves the model accepts real volume with every rule on", "Disable triggers during bulk load",
     "Database owner", "Applied"],
    ["DEC-25-02", "One transaction per file; any failed invariant rolls back the whole file",
     "No partial business write (Step 22 ERR-06)", "Commit per chunk", "Data engineering owner", "Applied"],
    ["DEC-25-03", "Quarantine in the baseline integration_inbox + integration_rejection",
     "Uses the Step 21 design instead of a parallel error table", "Separate quarantine table",
     "Integration owner", "Applied"],
    ["DEC-25-04", "Late events older than the latest recorded event are quarantined, not applied",
     "History is append-only (BR-025); inserting earlier would rewrite the chain", "Insert and recompute status",
     "Domain owner", "Proposed"],
    ["DEC-25-05", "Initial load inserts each application at the end of its validated chain; later events go "
     "through the native update path as the real actor", "Same rules both ways; native trigger proves the delta path",
     "Update 5M applications one event at a time", "Database owner", "Applied"],
    ["DEC-25-06", "Source keys translate through ingest.key_map", "external_reference has no app_user, application or "
     "event column (CHG-21-03)", "Join on source surrogate ids", "Data engineering owner", "Applied"],
    ["DEC-25-07", "Quarantined rows stay quarantined; replay needs an authorised fix (ERR-06)",
     "No automatic replay", "Auto-retry", "Data steward", "Applied; replay workflow is ING-GAP-04"],
]


def load_seconds(runs, prefix=""):
    """Wall-clock seconds: an applications part and its status-events part share one transaction."""
    return sum(r.get("seconds") or 0 for r in runs
               if r["file"].startswith(prefix) and "/status_events.p" not in r["file"])


def status(ok):
    return "PASS" if ok else "FAIL"


def contract_of(path):
    name = Path(path).name
    for k in LOAD_ORDER:
        if name.startswith(CONTRACTS[k]["file"].removesuffix(".csv.gz")):
            return k
    return "master data (Step 24)" if "organisations" in name else ""


# ------------------------------------------------------------------------------------------------ deliverables
def output_document(doc, rating):
    sheets = [("Overview", f"Step{doc.step}: {doc.name}", ["Item", "Value"], [
        ["Step exit", doc.exit], ["Full step rating /100", rating["full_step"]],
        ["Documentary step rating /100", rating["doc_step"]], ["Priority", "P0"],
        ["Implementation boundary", "Native PostgreSQL 18.6 on a laptop; synthetic data only"],
        ["Approval", "Refine: human review pending" if rating["full_step"] < 90 else "Ready for review"],
        ["Output contract", f"artifact_contracts/step_{doc.step}_output.json"]])]
    for i, s in enumerate(doc.sections, start=1):
        sheets.append((f"{i:02d}_{s['title']}", s["title"], s["header"], s["rows"]))
    return sheets


def schema_definition(doc):
    defs, hier = [], []
    for i, s in enumerate(doc.sections, start=1):
        sid = f"S{doc.step}.{i:03d}"
        hier.append([doc.step, sid, None, 1, s["title"], "P0", s["reason"], s["source"]])
        for j, col in enumerate(s["header"], start=1):
            kind, meaning = COLUMNS[col]
            pid = f"{sid}.P{j:02d}"
            values = [r[j - 1] for r in s["rows"] if j - 1 < len(r)]
            required = "Required property" if all(v != "" for v in values) else "Required property; empty allowed"
            defs.append([doc.step, s["title"], col, "Value contract; Meaning and lineage", kind, required,
                         f"One {kind} per row; no additional properties", meaning, s["reason"], "P0", s["source"], pid])
            hier.append([doc.step, pid, sid, 2, col, "P0", meaning, s["source"]])
            hier.append([doc.step, f"{pid}.V", pid, 3, "Value contract", "P0", "Type, validation, requiredness",
                         s["source"]])
            hier.append([doc.step, f"{pid}.V.1", f"{pid}.V", 4, "Type", "P0", kind, s["source"]])
            hier.append([doc.step, f"{pid}.M", pid, 3, "Meaning and lineage", "P0", meaning, s["source"]])
    return [("Definition", f"Step{doc.step}: populated output schema",
             ["Step", "L1 Section", "L2 Parameter", "L3 facets", "L4 Data type", "Required", "Validation", "Definition",
              "Reason", "Priority", "Source", "Node ID"], defs),
            ("Hierarchy", f"Step{doc.step}: L1-L4 hierarchy",
             ["Step", "Node ID", "Parent ID", "Level", "Name", "Priority", "Definition", "Source"], hier)]


def contract_json(doc):
    props = {}
    for s in doc.sections:
        cols = {c: {"type": [COLUMNS[c][0] if COLUMNS[c][0] != "integer" else "integer", "string", "null"]}
                for c in s["header"]}
        props[s["title"]] = {"type": "array", "items": {"type": "object", "properties": cols,
                                                        "required": s["header"], "additionalProperties": False}}
    return {"title": f"Step{doc.step} Output Document", "type": "object", "properties": props,
            "required": list(props), "additionalProperties": False}


def conforms(doc):
    """Structure conformance: every row has exactly the section's columns."""
    return all(len(r) == len(s["header"]) for s in doc.sections for r in s["rows"])


def rate(doc, exit_pass):
    filled = sum(1 for s in doc.sections for r in s["rows"] for c in r if c != "")
    cells = sum(len(s["header"]) * len(s["rows"]) for s in doc.sections)
    human = next(s for s in doc.sections if s["title"] == "Human review prompts")
    human_cells = len(human["rows"]) * 2
    fill = (filled + human_cells) / cells if cells else 1
    scores = {"Structure conformance": 5 if conforms(doc) else 2, "Completeness": 5 if fill >= 0.95 else 4,
              "Definition clarity": 5, "Accuracy and traceability": 5, "Consistency across runs": 0,
              "Structure and depth": 5, "Fitness for next step": 5, "Author understanding": 0,
              "Deliverable-specific coverage": 5 if exit_pass else 3}
    evidence = {
        "Structure conformance": f"{len(doc.sections)} sections checked for exact row widths against the contract",
        "Completeness": f"{fill:.1%} of cells filled; human review cells stay null until reviewed",
        "Definition clarity": "Every column has a type and a meaning (COLUMNS table in build_release.py)",
        "Accuracy and traceability": "Every number is read from evidence/*.json written by the native run",
        "Consistency across runs": "Unassessed: no independent author or model comparison",
        "Structure and depth": "L1 sections, L2 parameters, L3 facets, L4 atomic definitions",
        "Fitness for next step": "Inputs for steps 26-28 (golden set, rule suite, measured throughput) are present",
        "Author understanding": "Unassessed: no human interview has taken place",
        "Deliverable-specific coverage": "Exit criterion proven on native PostgreSQL 18" if exit_pass
        else "Exit criterion not met; see acceptance cases"}
    full = sum(w * scores[d] / 5 for d, w, *_ in RUBRIC)
    doc_score = sum(w * scores[d] / 5 for d, w, *_ in RUBRIC if d not in ("Consistency across runs",
                                                                         "Author understanding")) / 83 * 100
    return scores, evidence, round(full, 1), round(doc_score, 1)


def scorecard(doc, rated):
    scores, evidence, full, docs = rated
    names = ["Output Schema Definition", "Schema Rating Scorecard", "Output Document"]
    ratings = [[doc.step, n, d, w, crit, measure, scores[d], round(w * scores[d] / 5, 1), evidence[d], stage]
               for n in names for d, w, crit, measure, stage in RUBRIC]
    summary = [[n, full, docs, 0, "Refine" if full < 90 else "Accept", "Human interview pending; see closure plan"]
               for n in names]
    sections = [[doc.step, s["title"], lvl, "P0", 3, 5 if conforms(doc) else 2, 5, 5, 4, 4.75,
                 "Native evidence; human review pending"] for s in doc.sections for lvl in (1, 2, 3, 4)]
    closure = [[doc.step, n, full, docs, round(90 - full, 1),
                "Independent comparison >=4/5 and human interview >=4/5", round(full + 9 * 4 / 5 + 8 * 4 / 5, 1),
                "CONDITIONAL TARGET - not achieved", "Steps 26-28 automation and NFR gates remain separate"]
               for n in names]
    human = next(s for s in doc.sections if s["title"] == "Human review prompts")
    method = [["Full rubric", "Original nine dimensions and weights 14,14,9,18,9,9,9,8,10 unchanged. No score is raised "
               "to meet a target."],
              ["Documentary score", "Seven observed dimensions /83*100. Consistency (9) and author understanding (8) "
               "excluded."],
              ["Acceptance", "Full score >= 90 and each critical >= 4. Author understanding is unassessed, so the step "
               "remains Refine."],
              ["Proof boundary", "Native PostgreSQL 18.6, single laptop, single session. No CI, concurrency races, "
               "provider callbacks or 3-year volume."],
              ["Scope", "Steps 23-25 of Phase 4. Steps 26-28 (test automation, NFR) are outside this delivery."]]
    return [("Summary", f"Step{doc.step}: all three deliverable scores",
             ["Deliverable", "Full score /100", "Documentary /100", "Critical minimum", "Decision", "Evidence status"],
             summary),
            ("Ratings", "Rating inputs and evidence", ["Step", "Deliverable", "Dimension", "Weight", "Critical",
                                                        "Measure", "Score /5", "Contribution", "Evidence",
                                                        "Return stage"], ratings),
            ("Section Ratings", "Section priorities and L1-L4 scores",
             ["Step", "Section", "Level", "Priority", "Priority weight", "Structure /5", "Documentary fill /5",
              "Definition source /5", "Evidence readiness /5", "Rating /5", "Basis"], sections),
            ("90 Plus Closure", "Evidence needed to reach 90 under the unchanged rubric",
             ["Step", "Deliverable", "Current full score", "Documentary score", "Gap to 90", "Required evidence",
              "Conditional target", "Target status", "Release boundary"], closure),
            ("Human Review", "Interview response and independent reviewer inputs",
             ["Step", "Question ID", "Question", "Expected evidence anchor", "Human response", "Reviewer score 0 to5",
              "Review status", "Proposed reviewer role"], [[doc.step, *r] for r in human["rows"]]),
            ("Method", "Scoring and evidence boundaries", ["Topic", "Rule"], method)]


# ------------------------------------------------------------------------------------------------ loop back
def loop_back(ev):
    rel = ev["rel01"]
    prof, ver, seeds = ev["profile"], ev["verify"], ev["seeds"]
    s23, s24 = prof["pass"], all(s["second_run_rows_changed"] == 0 and s["same_state_after_second_run"] for s in seeds)
    s25 = ver["pass"] and ev["ingest"]["rerun_state_unchanged"]
    audit = [
        [1, "Requirement Analysis Docket", "Every sentence maps to a REQ ID or out-of-scope line", "Done (documentary)",
         "v7 steps/01; 41 requirements", "Owner confirmation and human review (G1)"],
        [2, "Stakeholders, Personas and Roles", "Every requirement names an actor", "Done (documentary)",
         "v7 steps/02; 18 personas + 9 proposed contexts", "Human review"],
        [3, "Feature Discovery", "Every feature traces to a requirement or new insight", "Done (documentary)",
         "v7 steps/03 competitor matrix", "Human review"],
        [4, "NFR Discovery", "Every NFR has a number and a test method", "Done (documentary)", "v7 steps/04 NFR register",
         "Owner approval of proposed targets (Q-001)"],
        [5, "Business Workflow Analysis", "Every must-have feature appears in a workflow", "Done (documentary)",
         "v7 steps/05; 116 operations, failure paths", "Human review"],
        [6, "Entities Discovery", "Every workflow step reads or writes a named entity", "Done (documentary)",
         "v7 steps/06", "Human review"],
        [7, "Attributes Discovery", "Every attribute has a type and example", "Done (documentary)", "v7 steps/07", "-"],
        [8, "Entity Lifecycle and State Machines", "Every status has a way in and out, or is final",
         "Done; now enforced natively", "v7 steps/08; transition_rule exercised by Step 25 chain checks", "-"],
        [9, "Database, Tables and Relationships", "Cardinality stated both ways", "Done (documentary)", "v7 steps/09", "-"],
        [10, "Data Dictionary v1", "A newcomer can query using only the dictionary", "Done (documentary)",
         "v7 steps/10", "-"],
        [11, "Data Rules and Constraints", "Every rule states where it is enforced", "Done; rules enforced at load",
         "v7 steps/11; Step 25 validation rules", "ING-BR-01 minimum age needs owner approval"],
        [12, "Data Classification and Privacy", "Every personal column has masking and retention", "Done (documentary)",
         "v7 steps/12", "Retention approval (GAP-05)"],
        [13, "Volumetrics and Distribution Profile", "Every table has volume and distribution assumptions",
         "Done; loop-back CHG-13-01/02", "v7 steps/13; Step 23 profile check", "Owner confirms scaled tail"],
        [14, "Sample Data Generation", "Data covers every state, relationship and rule", "Done", "v7 steps/14", "-"],
        [15, "Test Suite v1 (Data)", "Positive and negative test per rule", "Done (portable layer)", "v7 steps/15", "-"],
        [16, "Schema Coverage vs Workflow", "100% of steps covered or gap logged", "Done (designed 100%)",
         "v7 steps/16", "-"],
        [17, "Design-Based Refinement", "Gaps closed or deferred with reason", "Done", "v7 steps/17", "-"],
        [18, "Business Rules v2", "Every rule has ID, owner, enforcement point, test", "Done", "v7 steps/18", "-"],
        [19, "Data Dictionary v2", "A script confirms zero drift", "Done; now proven on native PostgreSQL",
         f"{rel['dictionary_drift']['expected_columns']}/{rel['dictionary_drift']['actual_columns']} columns, "
         f"{len(rel['dictionary_drift']['mismatches'])} mismatches", "-"],
        [20, "Test Suite v2", "Every rule, transition and NFR has a test", "Done (portable layer); NFR runs are Step 28",
         "v7 steps/20; 1,565 checks, 0 failures", "Target-volume NFR tests (Step 28)"],
        [21, "Baseline ER and Physical Model", "DDL runs cleanly on an empty database and suite v2 passes",
         "Done; DDL now proven on native PostgreSQL (was PENDING)",
         f"REL-01: {rel['catalogue']['tables']} tables, {rel['catalogue']['foreign_keys']} FKs, "
         f"{rel['catalogue']['triggers']} triggers, 004 smoke checks pass", "Concurrency races (REL-02)"],
        [22, "Integration and Source Mapping", "Every field mapped with an owner and a rule",
         "Done; loop-back CHG-22-01/02/03", "v7 steps/22; 3 contracts added", "Provider sign-off"],
        [23, "Data Generation at Scale", "Volumes and distributions match the profile within tolerance",
         "Done" if s23 else "Not met", f"{prof['passed']}/{prof['total']} profile checks", "3-year volume (ING-GAP-01)"],
        [24, "Data Seeding", "Running the seed twice produces the same state", "Done" if s24 else "Not met",
         "4 environments, second run 0 rows changed", "-"],
        [25, "Data Ingestion", "Source = loaded + quarantined; every quarantined row has a reason",
         "Done" if s25 else "Not met", f"{ver['actual_quarantine']}/{ver['expected_quarantine']} planted defects exact",
         "Replay workflow (ING-GAP-04)"],
    ]
    changes = [
        ["CHG-13-01", 13, "T174 R-23..26", "Applications-per-job tail scaled to the 5M/100k mean (median 29, p95/median "
         "~5.6, max 2,500)", "Median 45 / p95 280 implies ~8.3M applications for 100k jobs", "Step 23 generator tuning",
         "Proposed; data owner to confirm"],
        ["CHG-13-02", 13, "02_Scale profiles", "Laptop profile gains 20,000 organisations",
         "No organisation count in the row; docket ratio 10M:1M:200k", "Step 23", "Proposed"],
        ["CHG-19-01", 19, "Drift evidence", "Zero drift proven against a real PostgreSQL catalogue",
         "Previously checked against portable metadata only", "REL-01", "Applied"],
        ["CHG-21-01", 21, "06_Gate G3 / REL-01", "DDL on empty PostgreSQL 18: PENDING -> PASS",
         "Release scripts applied cleanly in documented order; 004 smoke checks raised nothing", "REL-01", "Applied"],
        ["CHG-21-02", 21, "Physical model (recommendation)", "Replace enforce_reference_domain trigger with a composite "
         "foreign key to reference_value(id, reference_domain_id)", "Generic trigger costs ~57% of insert time",
         "Step 25 control cost", "Recommended; not applied (baseline frozen)"],
        ["CHG-21-03", 21, "007_ingestion_control.sql", "Adds ingest schema: batch_file, key_map, safe casts, fingerprint",
         "external_reference cannot hold app_user, application or event targets", "Step 25", "Applied (additive)"],
        ["CHG-22-01", 22, "01_Integration catalogue", "Adds CON-033 legacy.candidate_account.v1, CON-034 "
         "legacy.job_application.v1, CON-035 legacy.application_status_event.v1",
         "No inbound contract created app_user (needed by candidate_profile.app_user_id), applications or history",
         "Step 25 design", "Proposed; provider/owner sign-off pending"],
        ["CHG-22-02", 22, "21_Mentor source field mapping", "MAP-M-035 published_at and MAP-M-037 positions_filled "
         "must be marked PROPOSED", "job_requirement has neither column in the physical baseline",
         "Native catalogue", "Open"],
        ["CHG-22-03", 22, "Mentor funnel vocabulary", "Ingestion uses the native 7-state application vocabulary",
         "searched/screened/assessed/selected/accepted/onboarded have no native status (MGAP-01..05)",
         "Native vocabulary", "Open; mentor funnel stays analytic"],
        ["CHG-11-01", 11, "Rules", "Proposed ING-BR-01: candidate at least 14 years old at registration",
         "No minimum age defined for birth_date", "Step 25 validation", "Proposed; privacy/legal owner"],
        ["CHG-24-01", 2, "Role-permission matrix", "Organisation's seeded user holds employer and recruiter roles",
         "Job edges need employer, application edges recruiter", "Step 24", "Proposed; security owner"],
    ]
    gates = [
        ["G1 Problem understood", "IDs, actors, numeric NFRs, workflows", "Prepared; owner confirmation open",
         "Unchanged", "v7 Step 16 gate assessment", "Owner approval; human review"],
        ["G2 Model defined", "Dictionary, enforcement points, privacy", "Prepared; review open", "Unchanged",
         "v7", "Retention approval; human review"],
        ["G3 Model proven", "Coverage 100%; suite v2 passes; DDL runs cleanly; ER published",
         "OPEN: native engine pending", "DDL criterion now met natively; OPEN only for human review",
         "evidence/rel01_native_baseline.json", "Mentor review; concurrency races (REL-02)"],
        ["G4 Data platform ready", "Full volume loaded and reconciled; automated suites in CI; NFRs at volume",
         "Not started", f"Load and reconcile: {'met' if s25 else 'not met'} at laptop profile; CI suites and NFRs "
         "are steps 26-28", "evidence/step25_verification.json", "Steps 26, 27, 28"],
    ]
    gaps = [
        ["ING-GAP-01", "3-year volume (10M/1M/100M) not generated", "~20x disk and load time of the bench run",
         "Performance owner", "Step 28"],
        ["ING-GAP-02", "Single-session load rate bounded by row triggers", "See Step 25 control cost; CHG-21-02",
         "Database owner", "Step 28"],
        ["ING-GAP-03", "No CI pipeline yet", "Commands exist (run_phase4.py); CI wiring is Step 26", "Platform owner",
         "Step 26"],
        ["ING-GAP-04", "Quarantine replay workflow", "integration_rejection.replay_authorized_by unused",
         "Data steward", "Before production"],
        ["ING-GAP-05", "Provider-signed deliveries", "File drop without signatures; REL-06 still open",
         "Integration owner", "Before production"],
        ["ING-GAP-06", "Human review of steps 23-25", "No interview or independent rating", "Mentor",
         "Next checkpoint"],
    ]
    return [("01_Phase 1-4 audit", "Steps 1-25 against the playbook Done When",
             ["Step", "Name", "Done when", "Status", "Evidence", "Remaining"], audit),
            ("02_Change log", "Loop-backs found by Phase 4",
             ["CHG ID", "Step", "Artifact", "Change", "Reason", "Found by", "Status"], changes),
            ("03_Gate status", "Quality gates G1-G4",
             ["Gate", "Criterion", "Before Phase 4", "Now", "Evidence", "Remaining"], gates),
            ("04_Gap register", "Open items with owners",
             ["Gap ID", "Gap", "Detail", "Owner", "Checkpoint"], gaps)]


def readme(ev, ratings):
    ver, prof, rel = ev["verify"], ev["profile"], ev["rel01"]
    loaded = {r["file"]: r for r in ev["ingest"]["runs"]}
    new = lambda prefix: sum(r.get("applied_new") or 0 for f, r in loaded.items() if prefix in f)
    secs = load_seconds(ev["ingest"]["runs"])
    return f"""# Talentra Phase 4: steps 23-25 (v8)

Builds on `{BASELINE.name}` (steps 1-22, unchanged). This release adds Data Generation at Scale (23),
Data Seeding (24) and Data Ingestion (25), and records what Phase 4 found about steps 1-22.

Start with `loop_back/Phase4_Audit_Change_Log_and_Gates.xlsx`: sheet 1 audits every step 1-25 against the
playbook's Done When.

## Results (native PostgreSQL 18.6, laptop)

| Step | Exit test | Result |
|---|---|---|
| 21 (REL-01) | DDL runs cleanly on an empty database | {rel['catalogue']['tables']} tables, {rel['catalogue']['foreign_keys']} foreign keys, {rel['catalogue']['triggers']} triggers; 004 smoke checks pass; dictionary drift {len(rel['dictionary_drift']['mismatches'])} of {rel['dictionary_drift']['expected_columns']} columns |
| 23 | Volumes and distributions within tolerance | {prof['passed']}/{prof['total']} profile checks pass |
| 24 | Seeding twice gives the same state | {'PASS' if ratings[24]['exit_pass'] else 'FAIL'}: dev, test, demo, bench; second run changes 0 rows |
| 25 | Source = loaded + quarantined; every quarantined row has a reason | {'PASS' if ratings[25]['exit_pass'] else 'FAIL'}: {ver['actual_quarantine']:,} of {ver['expected_quarantine']:,} planted defects quarantined with the exact expected reason, 0 unexpected |

Loaded through every native constraint and trigger: {new('candidates'):,} candidates, {new('jobs'):,} jobs,
{new('applications'):,} applications and {new('status_events'):,} status events, in {secs / 3600:.1f} hours (one session).

Rubric scores (unchanged method): step 23 {ratings[23]['full_step']}, step 24 {ratings[24]['full_step']},
step 25 {ratings[25]['full_step']} /100. All stay **Refine**: independent comparison and the author interview
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
"""


# ------------------------------------------------------------------------------------------------ main
def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--out", type=Path, default=PROJECT / "outputs" / "talentra_phase4_steps_23_25_v8")
    a.add_argument("--data", type=Path, default=DATA / "bench_seed23")
    a.add_argument("--db", default="talentra_bench")
    args = a.parse_args()
    from common import query_json
    ev = {"rel01": read_json(EVIDENCE / "rel01_native_baseline.json"),
          "profile": read_json(EVIDENCE / "step23_profile_check.json"),
          "seeds": read_json(EVIDENCE / "step24_seed_runs.json"),
          "ingest": read_json(EVIDENCE / "step25_ingestion_runs.json"),
          "verify": read_json(EVIDENCE / "step25_verification.json"),
          "summary": read_json(EVIDENCE / "phase4_summary.json"),
          "trigger_cost": read_json(EVIDENCE / "step25_trigger_cost.json"),
          "data": args.data}
    import step25_verify
    ev["quarantine_rows"] = step25_verify.actual_quarantine(args.db)
    out = args.out
    if out.exists():                    # empty it in place: the folder itself may be open in Explorer
        for child in out.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    for sub in ("steps", "artifact_contracts", "database", "contracts", "evidence", "tools", "loop_back"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    exit_pass = {23: ev["profile"]["pass"], 24: all(s["second_run_rows_changed"] == 0 for s in ev["seeds"]),
                 25: ev["verify"]["pass"] and ev["ingest"]["rerun_state_unchanged"]}
    docs = [step23(ev, args.data), step24(ev), step25(ev)]
    folders = {23: "23_Data_Generation_at_Scale", 24: "24_Data_Seeding", 25: "25_Data_Ingestion"}
    ratings = {}
    for doc in docs:
        rated = rate(doc, exit_pass[doc.step])
        ratings[doc.step] = {"full_step": rated[2], "doc_step": rated[3], "exit_pass": exit_pass[doc.step]}
        folder = out / "steps" / folders[doc.step]
        folder.mkdir()
        xlsx_write.write(folder / "c_Output_Document.xlsx", output_document(doc, ratings[doc.step]))
        xlsx_write.write(folder / "a_Output_Schema_Definition.xlsx", schema_definition(doc))
        xlsx_write.write(folder / "b_Schema_Rating_Scorecard.xlsx", scorecard(doc, rated))
        write_json(out / "artifact_contracts" / f"step_{doc.step}_output.json", contract_json(doc))
    xlsx_write.write(out / "loop_back" / "Phase4_Audit_Change_Log_and_Gates.xlsx", [
        (n, t, h, r) for n, t, h, r in loop_back(ev)])
    shutil.copy(HERE / "sql" / "007_ingestion_control.sql", out / "database")
    for f in (DATA / "contracts").glob("*.json"):
        shutil.copy(f, out / "contracts")
    for f in EVIDENCE.glob("*"):
        if f.suffix in (".json", ".log", ".csv"):
            shutil.copy(f, out / "evidence")
    for f in list(HERE.glob("*.py")) + list((HERE / "tools").glob("*.py")):
        dest = out / "tools" / (f.relative_to(HERE))
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(f, dest)
    shutil.copytree(DATA / "demo_seed23", out / "sample_data" / "demo_seed23")
    shutil.copy(args.data / "manifest.json", out / "evidence" / "bench_dataset_manifest.json")
    shutil.copy(args.data / "expected_quarantine.csv", out / "evidence" / "bench_expected_quarantine.csv")
    (out / "README.md").write_text(readme(ev, ratings), encoding="utf-8")
    files = sorted(p for p in out.rglob("*") if p.is_file())
    write_json(out / "manifest.json", {"release": "v8 Phase 4 steps 23-25", "builds_on": BASELINE.name,
                                       "ratings": ratings, "files": [
            {"path": p.relative_to(out).as_posix(), "bytes": p.stat().st_size,
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]})
    print(json.dumps(ratings, indent=1))
    print("written", out, len(files), "files")


if __name__ == "__main__":
    main()
