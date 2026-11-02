"""Measure what the native row-level controls cost per inserted status event (Step 25 throughput finding).

Inserts the same N synthetic events three ways inside transactions that are always rolled back:
all controls on; vocabulary trigger disabled (foreign keys only); every trigger disabled.
Nothing is committed. Usage: step25_trigger_cost.py --db NAME [--rows 100000] [--json OUT]
"""
import argparse
import re

from common import psql, write_json

CASES = [
    ("All controls (vocabulary trigger + 6 foreign keys)", ""),
    ("Foreign keys only (vocabulary trigger disabled for the measurement)",
     "ALTER TABLE application_status_event DISABLE TRIGGER trg_domain_application_status_event;"),
    ("No triggers (measurement floor)", "ALTER TABLE application_status_event DISABLE TRIGGER ALL;"),
]


def measure(db, rows):
    out = []
    for label, disable in CASES:
        script = f"""\\timing on
SET search_path = talentra;
BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;
CREATE TEMP TABLE src AS SELECT g, (SELECT min(id) FROM job_application) + (g % 1000) AS app
FROM generate_series(1, {rows}) g;
{disable}
\\echo MEASURE
INSERT INTO application_status_event (job_application_id, from_reference_value_id, to_reference_value_id,
       actor_app_user_id, occurred_at, created_by, updated_by)
SELECT app, 65, 70, 11, now(), 11, 11 FROM src;
ROLLBACK;
"""
        text = psql(db, input=script, timeout=3600)
        after = text.split("MEASURE", 1)[1]
        ms = float(re.search(r"Time: ([\d.]+) ms", after).group(1))
        out.append({"case": label, "rows": rows, "milliseconds": ms, "microseconds_per_row": round(ms * 1000 / rows, 1),
                    "rows_per_second": round(rows / (ms / 1000))})
    return out


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--db", required=True)
    a.add_argument("--rows", type=int, default=100_000)
    a.add_argument("--json")
    args = a.parse_args()
    res = measure(args.db, args.rows)
    for r in res:
        print(r)
    if args.json:
        write_json(args.json, res)


if __name__ == "__main__":
    main()
