"""Shared paths, PostgreSQL access and profile definitions for Phase 4 (steps 23-25)."""
import csv
import gzip
import hashlib
import io
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
BASELINE = PROJECT / "outputs" / "talentra_step22_mini_seed_v7"
DATA = HERE / "data"
EVIDENCE = HERE / "evidence"

PG_BIN = Path(r"C:\Program Files\PostgreSQL\18\bin")
PG_ENV = {
    "PGHOST": os.environ.get("TALENTRA_PGHOST", "127.0.0.1"),
    "PGPORT": os.environ.get("TALENTRA_PGPORT", "55432"),
    "PGUSER": os.environ.get("TALENTRA_PGUSER", "talentra_owner"),
    "PGCLIENTENCODING": "UTF8",
}
BASELINE_SQL = ["001_baseline", "003_seed", "002_controls", "004_verify",
                "005_scale_integration", "006_v3_vocab_controls"]

# Step 13 scale profiles. Organisation counts follow the docket ratio 10 candidates : 1 job : 0.2 organisations
# per 10 candidates (10M : 1M : 200k). Applications follow the Step 4/13 laptop case (CAP-01).
PROFILES = {
    "demo": {"organisations": 50, "candidates": 2_000, "jobs": 200, "applications": 10_000},
    "dev": {"organisations": 200, "candidates": 10_000, "jobs": 1_000, "applications": 50_000},
    "bench": {"organisations": 20_000, "candidates": 1_000_000, "jobs": 100_000, "applications": 5_000_000},
    # Sized only: the 3-year target is projected from bench measurements, not generated (see gap register).
    "year3": {"organisations": 200_000, "candidates": 10_000_000, "jobs": 1_000_000, "applications": 100_000_000},
}

SOURCE_SYSTEM = "legacy_ats"
# Native ID ranges owned by the Step 24 master seed. Ingested records take identity values above these.
MASTER_ID_BASE = 100_000


def psql(db, *args, input=None, timeout=None, check=True):
    """Run psql with ON_ERROR_STOP; return stdout. Raises with stderr on failure."""
    r = subprocess.run(
        [str(PG_BIN / "psql.exe"), "-X", "-q", "-v", "ON_ERROR_STOP=1", "-d", db, *args],
        env={**os.environ, **PG_ENV}, input=input, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )
    if check and r.returncode:
        raise RuntimeError(f"psql failed ({r.returncode}):\n{r.stderr[-4000:]}")
    return r.stdout


def scalar(db, sql):
    return psql(db, "-Atc", sql).strip()


def query_json(db, sql):
    """Return rows of a SELECT as a list of dicts."""
    out = psql(db, "-Atc", f"select coalesce(json_agg(q), '[]') from ({sql}) q")
    return json.loads(out)


def create_database(db, baseline_dir=BASELINE / "database"):
    """Fresh database with the released baseline applied in the documented order (REL-01)."""
    psql("postgres", "-c", f"drop database if exists {db} with (force)")
    psql("postgres", "-c", f"create database {db}")
    for name in BASELINE_SQL:
        psql(db, "-f", str(baseline_dir / f"{name}.sql"), timeout=600)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def open_csv_gz(path, header):
    """Text CSV writer over gzip, with \\N for null like the released seed files."""
    f = gzip.open(path, "wt", encoding="utf-8", newline="", compresslevel=6)
    w = csv.writer(f, lineterminator="\n")
    w.writerow(header)
    return f, w


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as h:
        json.dump(value, h, indent=1, ensure_ascii=False, default=str)
        h.write("\n")


def read_json(path):
    with open(path, encoding="utf-8") as h:
        return json.load(h)


def copy_in(db, table_sql, rows_iter, columns):
    """Stream rows into PostgreSQL with COPY FROM STDIN (CSV, \\N null)."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    for r in rows_iter:
        w.writerow(r)
    cmd = f"\\copy {table_sql} ({', '.join(columns)}) from stdin with (format csv, null '\\N')"
    return psql(db, "-c", cmd, input=buf.getvalue())
