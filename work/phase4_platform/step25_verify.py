"""Step 25 exit checks for a database that ingested a Step 23 dataset.

  * every quarantined row has a reason and field path (integration_rejection is NOT NULL on both)
  * quarantine matches the planted defects exactly: same batch, contract, line and reason, nothing extra
  * every batch file reconciles: source = new + updated + duplicate + quarantined, and its
    reconciliation_run row satisfies the native CHECK (source = applied + rejected + duplicate + pending)
  * referential integrity of the loaded data (no orphan rows) and status = end of each application's history
Usage: step25_verify.py --db NAME --data DIR [--json OUT]
"""
import argparse
import csv
import json
from pathlib import Path

from common import query_json, write_json


def actual_quarantine(db):
    return query_json(db, """
        select b.batch_label as batch, b.file_name as file, b.contract_key as contract,
               split_part(i.event_key, ':L', 2)::int as line,
               r.reason_code as reason, r.field_path as field, i.correlation_key as external_key
        from talentra.integration_rejection r
        join talentra.integration_inbox i on i.id = r.integration_inbox_id
        join ingest.batch_file b on 'bf' || b.id = split_part(i.event_key, ':L', 1)""")


def verify(db, data_dir):
    data_dir = Path(data_dir)
    with open(data_dir / "expected_quarantine.csv", encoding="utf-8") as h:
        expected = {(r["batch"], r["file"], int(r["line"]), r["reason"], r["field_path"])
                    for r in csv.DictReader(h)}
    actual_rows = actual_quarantine(db)
    actual = {(r["batch"], r["file"], r["line"], r["reason"], r["field"]) for r in actual_rows}
    missing, unexpected = sorted(expected - actual), sorted(actual - expected)

    files = query_json(db, """
        select b.batch_label, b.contract_key, b.file_name, b.status, b.source_rows, b.applied_new, b.applied_updated,
               b.duplicates, b.quarantined, b.late_in_order,
               r.source_count, r.applied_count, r.rejected_count, r.duplicate_count, r.pending_count,
               (r.source_count = r.applied_count + r.rejected_count + r.duplicate_count + r.pending_count) as recon_ok,
               extract(epoch from b.finished_at - b.started_at)::numeric(10,1) as seconds
        from ingest.batch_file b left join talentra.reconciliation_run r on r.id = b.reconciliation_run_id
        order by b.id""")
    completed = [f for f in files if f["status"] == "completed"]
    reconciled = all(f["recon_ok"] and f["source_rows"] == f["applied_new"] + f["applied_updated"] + f["duplicates"]
                     + f["quarantined"] and f["quarantined"] == f["rejected_count"] for f in completed)

    integrity = query_json(db, """
        select
          (select count(*) from talentra.job_application a
             where not exists (select 1 from talentra.candidate_profile c where c.id = a.candidate_profile_id)
                or not exists (select 1 from talentra.job_requirement j where j.id = a.job_requirement_id)) as orphan_applications,
          (select count(*) from talentra.application_status_event e
             where not exists (select 1 from talentra.job_application a where a.id = e.job_application_id)) as orphan_events,
          (select count(*) from talentra.candidate_profile c
             where not exists (select 1 from talentra.app_user u where u.id = c.app_user_id)) as orphan_profiles,
          (select count(*) from talentra.job_application a
             join lateral (select e.to_reference_value_id from talentra.application_status_event e
                           where e.job_application_id = a.id order by e.occurred_at desc, e.id desc limit 1) last on true
             where last.to_reference_value_id <> a.status_reference_value_id) as status_not_end_of_history,
          (select count(*) from talentra.integration_rejection where reason_code is null or field_path = '') as rejections_without_reason,
          (select count(*) from talentra.integration_inbox i where i.status_reference_value_id = 186
             and not exists (select 1 from talentra.integration_rejection r where r.integration_inbox_id = i.id)) as quarantined_without_rejection""")[0]

    by_reason = {}
    for r in actual_rows:
        k = f"{r['contract'].split('.')[1]}:{r['reason']}"
        by_reason[k] = by_reason.get(k, 0) + 1
    result = {
        "expected_quarantine": len(expected), "actual_quarantine": len(actual),
        "missing": [list(m) for m in missing[:50]], "unexpected": [list(u) for u in unexpected[:50]],
        "quarantine_exact": not missing and not unexpected,
        "files": files, "all_files_reconciled": reconciled,
        "integrity": integrity, "integrity_clean": all(v == 0 for v in integrity.values()),
        "quarantine_by_reason": dict(sorted(by_reason.items())),
    }
    result["pass"] = result["quarantine_exact"] and reconciled and result["integrity_clean"]
    return result


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--db", required=True)
    a.add_argument("--data", required=True, type=Path)
    a.add_argument("--json", type=Path)
    args = a.parse_args()
    r = verify(args.db, args.data)
    print(json.dumps({k: v for k, v in r.items() if k != "files"}, indent=1))
    if args.json:
        write_json(args.json, r)


if __name__ == "__main__":
    main()
