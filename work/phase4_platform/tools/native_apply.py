"""REL-01: apply the release SQL, in the documented order, to an empty PostgreSQL 18 database.

Stops at the first failing script and writes the outcome as evidence.
Usage: native_apply.py <database dir> <evidence json> [target db]
"""
import json
import os
import subprocess
import sys
import time

PSQL = r"C:\Program Files\PostgreSQL\18\bin\psql.exe"
ORDER = ["001_baseline", "003_seed", "002_controls", "004_verify", "005_scale_integration", "006_v3_vocab_controls"]
ENV = dict(os.environ, PGHOST="127.0.0.1", PGPORT="55432", PGUSER="talentra_owner", PGCLIENTENCODING="UTF8")


def psql(db, *args, timeout=1200):
    return subprocess.run(
        [PSQL, "-X", "-v", "ON_ERROR_STOP=1", "-d", db, *args],
        env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
    )


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    db_dir, evidence = sys.argv[1], sys.argv[2]
    db = sys.argv[3] if len(sys.argv) > 3 else "talentra_proof"
    psql("postgres", "-c", f"drop database if exists {db}")
    made = psql("postgres", "-c", f"create database {db}")
    if made.returncode:
        sys.exit(made.stderr)
    results = []
    for name in ORDER:
        start = time.time()
        r = psql(db, "-q", "-f", os.path.join(db_dir, name + ".sql"))
        errors = [l for l in r.stderr.splitlines() if "ERROR" in l or "FATAL" in l]
        results.append({"script": name + ".sql", "exit_code": r.returncode, "seconds": round(time.time() - start, 2),
                        "errors": errors[:5], "stderr_tail": r.stderr.splitlines()[-6:] if r.returncode else [],
                        "stdout_tail": r.stdout.splitlines()[-12:]})
        print(name, "exit", r.returncode, f"{results[-1]['seconds']}s")
        for e in errors[:5]:
            print("   ", e)
        for l in results[-1]["stderr_tail"]:
            print("   ", l)
        if r.returncode:
            break
    meta = psql(db, "-Atc", """select json_build_object(
      'server', version(),
      'tables', (select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
                 where c.relkind in ('r','p') and n.nspname not in ('pg_catalog','information_schema')),
      'indexes', (select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
                 where c.relkind='i' and n.nspname not in ('pg_catalog','information_schema','pg_toast')),
      'foreign_keys', (select count(*) from pg_constraint where contype='f'),
      'check_constraints', (select count(*) from pg_constraint c join pg_namespace n on n.oid=c.connamespace
                 where c.contype='c' and n.nspname not in ('pg_catalog','information_schema')),
      'triggers', (select count(*) from pg_trigger where not tgisinternal),
      'schemas', (select json_agg(nspname) from pg_namespace where nspname !~ '^pg_' and nspname<>'information_schema'))""")
    out = {"gate": "REL-01", "results": results,
           "passed": all(r["exit_code"] == 0 for r in results) and len(results) == len(ORDER),
           "metadata": json.loads(meta.stdout) if meta.returncode == 0 and meta.stdout.strip() else None}
    print(json.dumps(out["metadata"], indent=1))
    print("PASSED" if out["passed"] else "FAILED")
    os.makedirs(os.path.dirname(evidence), exist_ok=True)
    with open(evidence, "w", encoding="utf-8") as h:
        json.dump(out, h, indent=1)


if __name__ == "__main__":
    main()
