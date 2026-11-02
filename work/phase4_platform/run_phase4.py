"""Run and evidence Phase 4 steps 23-25 end to end at the Step 13 laptop-benchmark profile.

  0  REL-01: apply the released baseline to an empty PostgreSQL 18 database; dictionary drift check
  23 generate the bench dataset (seed 23) and check it against the Step 13 profile
  24 prove every seed set is re-runnable (dev, demo, test on a scratch database; bench master on the bench db)
  25 ingest b001, b002, b003 into the bench database, re-run b001 to prove it is a no-op, verify
Every result is written to evidence/*.json; progress goes to stdout.
Usage: run_phase4.py [--profile bench] [--db talentra_bench] [--keep-going]
"""
import argparse
import csv
import io
import json
import subprocess
import sys
import time
from pathlib import Path

from common import BASELINE, DATA, EVIDENCE, HERE, create_database, psql, query_json, read_json, write_json
import step23_profile_check
import step24_seed
import step25_ingest
import step25_verify

BUSINESS = ["talentra.app_user", "talentra.candidate_profile", "talentra.user_role", "talentra.job_requirement",
            "talentra.job_application", "talentra.application_status_event", "talentra.integration_inbox",
            "talentra.integration_rejection", "talentra.reconciliation_run", "ingest.key_map"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def fingerprints(db, tables):
    return {r["t"]: r["fp"] for r in query_json(
        db, "select t, ingest.table_fingerprint(t::regclass) fp from unnest(array[%s]) t"
            % ", ".join(f"'{t}'" for t in tables))}


def new_db(name):
    create_database(name)
    psql(name, "-f", str(HERE / "sql" / "007_ingestion_control.sql"))


def rel01(db):
    """Baseline on an empty database, the released smoke checks, and dictionary-vs-schema drift."""
    t = time.time()
    new_db(db)
    meta = psql(db, "--csv", "-f", str(BASELINE / "database" / "export_metadata.sql"))
    meta_path = EVIDENCE / "native_metadata.csv"
    meta_path.write_text(meta, encoding="utf-8")
    drift = subprocess.run([sys.executable, str(BASELINE / "database" / "check_dictionary.py"),
                            str(BASELINE / "evidence" / "dictionary_v3.json"), str(meta_path)],
                           capture_output=True, text=True)
    counts = query_json(db, """select
        (select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace
          where c.relkind = 'r' and n.nspname = 'talentra') as tables,
        (select count(*) from pg_constraint where contype = 'f' and connamespace = 'talentra'::regnamespace) as foreign_keys,
        (select count(*) from pg_constraint where contype = 'c' and connamespace = 'talentra'::regnamespace) as checks,
        (select count(*) from pg_trigger t join pg_class c on c.oid = t.tgrelid
          where not t.tgisinternal and c.relnamespace = 'talentra'::regnamespace) as triggers,
        version() as server""")[0]
    return {"database": db, "scripts": [f"{s}.sql" for s in
                                        ["001_baseline", "003_seed", "002_controls", "004_verify",
                                         "005_scale_integration", "006_v3_vocab_controls"]]
            + ["007_ingestion_control.sql (Phase 4 addition)"],
            "applied_cleanly": True, "smoke_checks_004": "passed (script raises on any failed check)",
            "dictionary_drift": json.loads(drift.stdout), "drift_exit_code": drift.returncode,
            "catalogue": counts, "seconds": round(time.time() - t, 1)}


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--profile", default="bench")
    a.add_argument("--db", default="talentra_bench")
    args = a.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    data = DATA / f"{args.profile}_seed23"
    summary = {"profile": args.profile, "started": time.strftime("%Y-%m-%d %H:%M:%S")}

    log("REL-01: baseline on empty PostgreSQL 18")
    summary["rel01"] = rel01(args.db)
    write_json(EVIDENCE / "rel01_native_baseline.json", summary["rel01"])
    log("REL-01 done", summary["rel01"]["catalogue"], "drift", summary["rel01"]["dictionary_drift"]["mismatches"])

    if not (data / "manifest.json").exists():
        log("Step 23: generating", args.profile)
        t = time.time()
        subprocess.run([sys.executable, str(HERE / "step23_generate.py"), "--profile", args.profile,
                        "--out", str(data)], check=True)
        log(f"Step 23 generated in {time.time() - t:.0f}s")
    log("Step 23: profile check")
    prof = step23_profile_check.profile_check(data)
    write_json(EVIDENCE / "step23_profile_check.json", prof)
    log(f"Step 23: {prof['passed']}/{prof['total']} checks pass")

    log("Step 24: seed re-run proofs")
    seeds = []
    new_db("talentra_seedproof")
    for env, master in [("test", None), ("dev", DATA / "dev_seed23"), ("demo", DATA / "demo_seed23")]:
        if master and not (master / "manifest.json").exists():
            subprocess.run([sys.executable, str(HERE / "step23_generate.py"), "--profile", env, "--out",
                            str(master)], check=True)
        db = "talentra_seedproof"
        new_db(db)
        first = step24_seed.seed(db, env, master)
        second = step24_seed.seed(db, env, master)
        fresh = "talentra_seedproof_b"
        new_db(fresh)
        other = step24_seed.seed(fresh, env, master)
        entry = {"env": env, "first_run_rows_changed": first["rows_changed"],
                 "second_run_rows_changed": second["rows_changed"],
                 "same_state_after_second_run": first["fingerprint"] == second["fingerprint"],
                 "same_state_on_a_fresh_database": first["fingerprint"] == other["fingerprint"],
                 "changes_first_run": first["changes"]}
        if env == "test":
            entry["golden_answers"] = step24_seed.check_golden(db)
        seeds.append(entry)
        log("Step 24", env, {k: v for k, v in entry.items() if k not in ("changes_first_run", "golden_answers")})
    psql("postgres", "-c", "drop database if exists talentra_seedproof with (force)")
    psql("postgres", "-c", "drop database if exists talentra_seedproof_b with (force)")
    first = step24_seed.seed(args.db, args.profile, data)
    second = step24_seed.seed(args.db, args.profile, data)
    seeds.append({"env": args.profile, "first_run_rows_changed": first["rows_changed"],
                  "second_run_rows_changed": second["rows_changed"],
                  "same_state_after_second_run": first["fingerprint"] == second["fingerprint"],
                  "changes_first_run": first["changes"]})
    log("Step 24", args.profile, seeds[-1]["second_run_rows_changed"], seeds[-1]["same_state_after_second_run"])
    write_json(EVIDENCE / "step24_seed_runs.json", seeds)

    log("Step 25: ingestion")
    runs = []
    for batch in ("b001", "b002", "b003"):
        t = time.time()
        runs += step25_ingest.ingest_dir(args.db, data / batch)
        log(f"Step 25 {batch} done in {time.time() - t:.0f}s")
    before = fingerprints(args.db, BUSINESS)
    t = time.time()
    rerun = step25_ingest.ingest_dir(args.db, data / "b001")
    after = fingerprints(args.db, BUSINESS)
    rerun_ok = all(r["status"] == "skipped_duplicate_file" for r in rerun) and \
        {k: v for k, v in before.items() if k != "talentra.reconciliation_run"} == \
        {k: v for k, v in after.items() if k != "talentra.reconciliation_run"}
    log(f"Step 25 re-run of b001: all skipped and state unchanged = {rerun_ok} ({time.time() - t:.0f}s)")
    write_json(EVIDENCE / "step25_ingestion_runs.json", {"runs": runs, "rerun_b001": rerun,
                                                         "rerun_state_unchanged": rerun_ok,
                                                         "fingerprints": after})
    log("Step 25: verify")
    ver = step25_verify.verify(args.db, data)
    write_json(EVIDENCE / "step25_verification.json", ver)
    sizes = query_json(args.db, """select c.relnamespace::regnamespace || '.' || c.relname as relation,
        pg_table_size(c.oid) as table_bytes, pg_indexes_size(c.oid) as index_bytes, s.n_live_tup as rows
        from pg_class c join pg_stat_user_tables s on s.relid = c.oid
        where pg_total_relation_size(c.oid) > 1000000 order by pg_total_relation_size(c.oid) desc""")
    summary.update({"step23_pass": prof["pass"], "step24_pass": all(s["second_run_rows_changed"] == 0 and
                                                                   s["same_state_after_second_run"] for s in seeds),
                    "step25_pass": ver["pass"] and rerun_ok, "database_bytes": int(psql(
                        args.db, "-Atc", f"select pg_database_size('{args.db}')").strip()),
                    "relation_sizes": sizes, "finished": time.strftime("%Y-%m-%d %H:%M:%S")})
    write_json(EVIDENCE / "phase4_summary.json", summary)
    log("DONE", {k: summary[k] for k in ("step23_pass", "step24_pass", "step25_pass", "database_bytes")})


if __name__ == "__main__":
    main()
