"""Step 24 - Data Seeding.

Loads the seed sets for one environment into a database that already has the baseline + 007 applied:
  reference  states, cities, job roles, industries, inbound integration sources and contracts (all envs)
  master     accounts, organisations, one recruiter each with role and membership (dev / demo / bench,
             from the Step 23 master file of that profile)
  golden     a small hand-built test dataset with known answers (test env only)

Every row has an explicit id and fixed timestamps. Each table is upserted and only updated when a value
differs, so a second run changes nothing; the run prints per-table insert/update counts and a state
fingerprint. Usage: step24_seed.py --db NAME --env dev|test|demo|bench [--master DIR] [--json OUT]
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

from common import DATA, MASTER_ID_BASE, SOURCE_SYSTEM, psql, query_json, write_json
from contracts import CONTRACTS, LOAD_ORDER, write_schemas
from step24_reference import INDUSTRY_IDS, reference_rows

STAMP = "2026-11-01T00:00:00Z"
SYSTEM_USER = 1                  # baseline seed user that owns reference data
PLATFORM_ACCOUNT = 1             # baseline account that owns the migration integrations
ROLE = {"candidate": 5, "employer": 6, "recruiter": 7}
ACCOUNT_STATUS = {"active": 1}
APP_USER_STATUS = {"active": 4}
ORG_STATUS = {"pending": 119, "verified": 120, "suspended": 121}
PROFILE_STATUS = {"active": 18, "draft": 19, "hidden": 21}
APP_STATUS = {"applied": 65, "interviewed": 66, "joined": 67, "offered": 68, "rejected": 69, "shortlisted": 70,
              "withdrawn": 71}
GOLDEN_BASE = 200_000

ENV_SETS = {"dev": ["reference", "master"], "demo": ["reference", "master"], "bench": ["reference", "master"],
            "test": ["reference", "golden"]}


class Table:
    def __init__(self, name, columns, rows, conflict=("id",), versioned=False, append_only=False):
        self.name, self.columns, self.rows = name, list(columns), [tuple(r) for r in rows]
        self.conflict, self.versioned, self.append_only = list(conflict), versioned, append_only


def sha(*parts):
    """SHA256 of the parts, in PostgreSQL bytea hex input form (key_map.payload_sha256)."""
    return "\\x" + hashlib.sha256("\x1f".join("" if p is None else str(p) for p in parts).encode()).hexdigest()


def reference_set():
    tables = [Table(t, cols, rows) for t, (cols, rows) in reference_rows(STAMP).items()]
    shas = write_schemas(DATA / "contracts")
    sources, contracts = [], []
    for n, key in enumerate(LOAD_ORDER):
        c = CONTRACTS[key]
        sid = MASTER_ID_BASE + n + 1
        sources.append((sid, PLATFORM_ACCOUNT, c["source_code"], c["owner"],
                        f"file-drop://{SOURCE_SYSTEM}/{c['file']}", "none:file-drop-without-credentials", True, 1,
                        3_600_000, STAMP, SYSTEM_USER, STAMP, SYSTEM_USER))
        contracts.append((sid, PLATFORM_ACCOUNT, sid, key, 1, 181, shas[key], 262_144, STAMP, None,
                          STAMP, SYSTEM_USER, STAMP, SYSTEM_USER))
    tables.append(Table("integration_source", ["id", "account_id", "code", "owner_role", "endpoint_reference",
                                               "secret_reference", "enabled", "max_inflight", "timeout_ms",
                                               "created_at", "created_by", "updated_at", "updated_by"], sources))
    tables.append(Table("integration_contract", ["id", "account_id", "integration_source_id", "contract_key",
                                                 "schema_version", "direction_reference_value_id", "schema_sha256",
                                                 "max_payload_bytes", "effective_at", "retired_at", "created_at",
                                                 "created_by", "updated_at", "updated_by"], contracts))
    return tables


def master_tables(orgs):
    """orgs: dicts with organisation_key, account_name, organisation_name, industry_code, status_code,
    recruiter_email, recruiter_name, created_at."""
    acc, org, users, roles, members, keys = [], [], [], [], [], []
    for o in orgs:
        k = int(o["organisation_key"])
        i = MASTER_ID_BASE + k
        acc.append((i, o["account_name"], ACCOUNT_STATUS["active"], o["created_at"], SYSTEM_USER, o["created_at"],
                    SYSTEM_USER))
        org.append((i, i, None, o["organisation_name"], INDUSTRY_IDS[o["industry_code"]], ORG_STATUS[o["status_code"]],
                    o["created_at"], SYSTEM_USER, o["created_at"], SYSTEM_USER))
        users.append((i, o["recruiter_email"], o["recruiter_name"], APP_USER_STATUS["active"], "en", o["created_at"],
                      SYSTEM_USER, o["created_at"], SYSTEM_USER))
        # The organisation's seeded user both recruits (application edges) and administers jobs (employer edges)
        roles.append((i, i, ROLE["recruiter"], o["created_at"], SYSTEM_USER, o["created_at"], SYSTEM_USER))
        roles.append((i + 1_000_000, i, ROLE["employer"], o["created_at"], SYSTEM_USER, o["created_at"], SYSTEM_USER))
        members.append((i, i, i, o["created_at"], None, o["created_at"], SYSTEM_USER, o["created_at"], SYSTEM_USER))
        keys.append(("organisation", SOURCE_SYSTEM, str(k), i, 1, sha(*o.values()), None))
        keys.append(("recruiter", SOURCE_SYSTEM, f"ORG-{k:06d}", i, 1, sha(*o.values()), None))
    audit = ["created_at", "created_by", "updated_at", "updated_by"]
    return [
        Table("account", ["id", "name", "status_reference_value_id"] + audit, acc),
        Table("organisation", ["id", "account_id", "parent_organisation_id", "name", "industry_id",
                               "status_reference_value_id"] + audit, org),
        Table("app_user", ["id", "email", "person_name", "status_reference_value_id", "preferred_language"] + audit,
              users),
        Table("user_role", ["id", "app_user_id", "access_role_id"] + audit, roles),
        Table("recruiter_membership", ["id", "organisation_id", "app_user_id", "valid_from", "valid_to"] + audit,
              members),
        Table("ingest.key_map", ["entity", "source_system", "external_key", "native_id", "source_version",
                                 "payload_sha256", "batch_file_id"], keys,
              conflict=("entity", "source_system", "external_key")),
    ]


def master_set(master_dir):
    with gzip.open(Path(master_dir) / "master" / "organisations.csv.gz", "rt", encoding="utf-8", newline="") as h:
        return master_tables(list(csv.DictReader(h)))


# ---------------------------------------------------------------------------------------------- golden
GOLDEN_ORGS = [
    {"organisation_key": "900001", "account_name": "Golden Account A", "organisation_name": "Golden Employer A",
     "industry_code": "it_services", "status_code": "verified", "recruiter_email": "recruiter.a@golden.example.invalid",
     "recruiter_name": "Golden Recruiter A", "created_at": "2025-06-01T00:00:00Z"},
    {"organisation_key": "900002", "account_name": "Golden Account B", "organisation_name": "Golden Employer B",
     "industry_code": "logistics", "status_code": "verified", "recruiter_email": "recruiter.b@golden.example.invalid",
     "recruiter_name": "Golden Recruiter B", "created_at": "2025-06-01T00:00:00Z"},
    {"organisation_key": "900003", "account_name": "Golden Account C", "organisation_name": "Golden Employer C",
     "industry_code": "retail", "status_code": "pending", "recruiter_email": "recruiter.c@golden.example.invalid",
     "recruiter_name": "Golden Recruiter C", "created_at": "2025-06-01T00:00:00Z"},
]
# (candidate n, language, city, status)
GOLDEN_CANDIDATES = [(1, "en", 1001, "active"), (2, "hi", 1005, "active"), (3, "ta", 1004, "active"),
                     (4, "en", None, "hidden"), (5, "en", 1002, "active"), (6, "hi", 1003, "draft")]
# (job n, org key, role, city, positions, salary)
GOLDEN_JOBS = [(1, 900001, 1001, 1001, 2, (1_200_000, 1_800_000)), (2, 900001, 1005, 1003, 1, None),
               (3, 900002, 1014, 1002, 20, (180_000, 240_000)), (4, 900003, 1008, 1005, 3, (300_000, 450_000))]
# (application n, candidate, job, path) - every native status and every permitted edge appears at least once
GOLDEN_APPS = [
    (1, 1, 1, ["applied", "shortlisted", "interviewed", "offered", "joined"]),
    (2, 2, 1, ["applied", "shortlisted", "interviewed", "rejected"]),
    (3, 3, 1, ["applied", "rejected"]),
    (4, 1, 2, ["applied", "withdrawn"]),
    (5, 4, 2, ["applied", "shortlisted", "withdrawn"]),
    (6, 5, 3, ["applied", "shortlisted", "interviewed", "offered", "withdrawn"]),
    (7, 6, 3, ["applied"]),
    (8, 2, 4, ["applied", "shortlisted"]),
    (9, 3, 3, ["applied", "shortlisted", "interviewed", "withdrawn"]),
    (10, 5, 4, ["applied", "shortlisted", "rejected"]),
    (11, 1, 3, ["applied", "shortlisted", "interviewed"]),
    (12, 4, 4, ["applied", "shortlisted", "interviewed", "offered", "rejected"]),
]
# Questions any test can ask of the golden set, with the answer fixed in advance
GOLDEN_ANSWERS = {
    "applications": 12,
    "applications_by_status": {"applied": 1, "shortlisted": 1, "interviewed": 1, "offered": 0, "joined": 1,
                               "rejected": 4, "withdrawn": 4},
    "status_events": 39,
    "applications_by_organisation": {"Golden Employer A": 5, "Golden Employer B": 4, "Golden Employer C": 3},
    "joined_by_organisation": {"Golden Employer A": 1},
    "reached_shortlisted": 9, "reached_interviewed": 6, "reached_offered": 3,
    "candidates_with_applications": 6, "jobs_without_applications": 0,
    "withdrawn_by_candidate_events": 4, "recruiter_events": 23,
}

# SQL that answers each golden question from the seeded database (compared with GOLDEN_ANSWERS)
GOLDEN_QUERIES = {
    "applications": "select count(*) from job_application where id > 200000 and id < 300000",
    "applications_by_status": """select json_object_agg(v.code, coalesce(n, 0)) from reference_value v
        left join (select status_reference_value_id s, count(*) n from job_application where id between 200001 and 299999
                   group by 1) a on a.s = v.id where v.reference_domain_id = 22""",
    "status_events": "select count(*) from application_status_event where id between 200001 and 299999",
    "applications_by_organisation": """select json_object_agg(o.name, n) from (select j.organisation_id, count(*) n
        from job_application a join job_requirement j on j.id = a.job_requirement_id where a.id between 200001 and 299999
        group by 1) x join organisation o on o.id = x.organisation_id""",
    "joined_by_organisation": """select json_object_agg(o.name, n) from (select j.organisation_id, count(*) n
        from job_application a join job_requirement j on j.id = a.job_requirement_id where a.id between 200001 and 299999
        and a.status_reference_value_id = 67 group by 1) x join organisation o on o.id = x.organisation_id""",
    "reached_shortlisted": "select count(distinct job_application_id) from application_status_event where id between 200001 and 299999 and to_reference_value_id = 70",
    "reached_interviewed": "select count(distinct job_application_id) from application_status_event where id between 200001 and 299999 and to_reference_value_id = 66",
    "reached_offered": "select count(distinct job_application_id) from application_status_event where id between 200001 and 299999 and to_reference_value_id = 68",
    "candidates_with_applications": "select count(distinct candidate_profile_id) from job_application where id between 200001 and 299999",
    "jobs_without_applications": """select count(*) from job_requirement j where j.id between 200001 and 299999
        and not exists (select 1 from job_application a where a.job_requirement_id = j.id)""",
    "withdrawn_by_candidate_events": """select count(*) from application_status_event e join job_application a
        on a.id = e.job_application_id join candidate_profile c on c.id = a.candidate_profile_id
        where e.id between 200001 and 299999 and e.to_reference_value_id = 71 and e.actor_app_user_id = c.app_user_id""",
    "recruiter_events": """select count(*) from application_status_event e join recruiter_membership m
        on m.app_user_id = e.actor_app_user_id where e.id between 200001 and 299999""",
}


def check_golden(db):
    """Answer every golden question from the database and compare with the answers fixed in advance."""
    out = {}
    for name, sql in GOLDEN_QUERIES.items():
        got = json.loads(psql(db, "-Atc", f"set search_path = talentra; {sql}").strip().splitlines()[-1] or "null")
        expected = GOLDEN_ANSWERS[name]
        if isinstance(expected, dict):
            got = {k: v for k, v in (got or {}).items() if v or k in expected}
        out[name] = {"expected": expected, "observed": got, "pass": got == expected}
    return out


def golden_set():
    tables = master_tables(GOLDEN_ORGS)
    audit = ["created_at", "created_by", "updated_at", "updated_by"]
    users, profiles, roles, jobs, apps, events, keys = [], [], [], [], [], [], []
    for n, lang, city, status in GOLDEN_CANDIDATES:
        i = GOLDEN_BASE + n
        users.append((i, f"golden.candidate{n}@golden.example.invalid", f"Golden Candidate {n}", 4, lang,
                      "2025-07-01T00:00:00Z", SYSTEM_USER, "2025-07-01T00:00:00Z", SYSTEM_USER))
        profiles.append((i, i, city, f"Golden headline {n}", f"199{n}-01-15", PROFILE_STATUS[status], lang,
                         "2025-07-01T00:00:00Z", SYSTEM_USER, "2025-07-01T00:00:00Z", SYSTEM_USER, 1))
        roles.append((i, i, ROLE["candidate"], "2025-07-01T00:00:00Z", SYSTEM_USER, "2025-07-01T00:00:00Z", SYSTEM_USER))
        keys.append(("candidate", "golden", f"G-CAN-{n}", i, 1, sha("cand", n), None))
    for n, org_key, role, city, positions, salary in GOLDEN_JOBS:
        i = GOLDEN_BASE + n
        lo, hi = salary or (None, None)
        jobs.append((i, MASTER_ID_BASE + org_key, role, 84, 99, city, f"Golden job {n}", f"Golden job {n} description",
                     positions, 98, 90, False, lo, hi, "INR" if salary else None, 94 if salary else 92,
                     "Asia/Kolkata", "en", "2025-08-01T00:00:00Z", SYSTEM_USER, "2025-08-01T00:00:00Z", SYSTEM_USER, 1))
        keys.append(("job", "golden", f"G-JOB-{n}", i, 1, sha("job", n), None))
    ev = GOLDEN_BASE
    for n, cand, job, path in GOLDEN_APPS:
        i = GOLDEN_BASE + n
        org_key = next(j[1] for j in GOLDEN_JOBS if j[0] == job)
        apps.append((i, GOLDEN_BASE + job, GOLDEN_BASE + cand, None, APP_STATUS[path[-1]], f"2025-09-{n:02d}T09:00:00Z",
                     f"2025-09-{n:02d}T09:00:00Z", SYSTEM_USER, f"2025-09-{n:02d}T09:00:00Z", SYSTEM_USER, 1))
        keys.append(("application", "golden", f"G-APP-{n}", i, 1, sha("app", n), None))
        prev = None
        for step, s in enumerate(path):
            ev += 1
            actor = GOLDEN_BASE + cand if s in ("applied", "withdrawn") else MASTER_ID_BASE + org_key
            when = f"2025-{9 + step // 2:02d}-{n + step * 2:02d}T10:00:00Z"
            events.append((ev, i, APP_STATUS[prev] if prev else None, APP_STATUS[s], actor, when, when, SYSTEM_USER,
                           when, SYSTEM_USER))
            keys.append(("status_event", "golden", f"G-APP-{n}-E{step + 1}", ev, 1, sha("ev", n, step), None))
            prev = s
    tables[2].rows += users                                       # app_user
    tables[3].rows += roles                                       # user_role
    tables[5].rows += keys                                        # key_map
    tables[5:5] = [
        Table("candidate_profile", ["id", "app_user_id", "city_id", "headline", "birth_date",
                                    "status_reference_value_id", "content_language"] + audit + ["row_version"],
              profiles, versioned=True),
        Table("job_requirement", ["id", "organisation_id", "job_role_id", "employment_type_reference_value_id",
                                  "work_type_reference_value_id", "city_id", "title", "description", "positions",
                                  "status_reference_value_id", "publish_state_reference_value_id",
                                  "open_to_consultant", "salary_min", "salary_max", "currency_code",
                                  "salary_disclosure_reference_value_id", "source_timezone", "content_language"]
              + audit + ["row_version"], jobs, versioned=True),
        Table("job_application", ["id", "job_requirement_id", "candidate_profile_id", "resume_version_id",
                                  "status_reference_value_id", "applied_at"] + audit + ["row_version"], apps,
              versioned=True),
        Table("application_status_event", ["id", "job_application_id", "from_reference_value_id",
                                           "to_reference_value_id", "actor_app_user_id", "occurred_at"] + audit,
              events, append_only=True),
    ]
    return tables


# ---------------------------------------------------------------------------------------------- loader
def csv_block(rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    for r in rows:
        w.writerow(["\\N" if v is None else ("t" if v is True else "f" if v is False else v) for v in r])
    return buf.getvalue()


def upsert_sql(t, n):
    target = t.name if "." in t.name else f"talentra.{t.name}"
    stage = f"seed_stage_{n}"
    cols = ", ".join(t.columns)
    sql = [f"CREATE TEMP TABLE {stage} AS SELECT {cols} FROM {target} WHERE false;",
           f"COPY {stage} ({cols}) FROM STDIN WITH (FORMAT csv, NULL '\\N');", csv_block(t.rows) + "\\."]
    if t.append_only:
        # History is immutable: insert missing rows, and fail if a seeded id holds different content.
        sql.append(f"""DO $$ BEGIN IF EXISTS (SELECT 1 FROM {stage} s JOIN {target} x USING ({', '.join(t.conflict)})
              WHERE ({', '.join('s.' + c for c in t.columns)}) IS DISTINCT FROM ({', '.join('x.' + c for c in t.columns)}))
              THEN RAISE EXCEPTION 'seed conflicts with immutable history in {t.name}'; END IF; END $$;""")
        sql.append(f"""WITH u AS (INSERT INTO {target} ({cols}) SELECT {cols} FROM {stage}
              ON CONFLICT ({', '.join(t.conflict)}) DO NOTHING RETURNING 1)
              SELECT '{t.name}', count(*), 0 FROM u;""")
        return "\n".join(sql)
    upd = [c for c in t.columns if c not in t.conflict and c != "row_version"]
    set_list = ", ".join(f"{c} = EXCLUDED.{c}" for c in upd)
    if t.versioned:
        set_list += f", row_version = {target}.row_version + 1"
    differs = f"({', '.join(target + '.' + c for c in upd)}) IS DISTINCT FROM ({', '.join('EXCLUDED.' + c for c in upd)})"
    sql.append(f"""WITH u AS (INSERT INTO {target} ({cols}) SELECT {cols} FROM {stage}
          ON CONFLICT ({', '.join(t.conflict)}) DO UPDATE SET {set_list} WHERE {differs}
          RETURNING (xmax = 0) AS inserted)
          SELECT '{t.name}', count(*) FILTER (WHERE inserted), count(*) FILTER (WHERE NOT inserted) FROM u;""")
    return "\n".join(sql)


def seed(db, env, master_dir=None):
    tables = []
    for s in ENV_SETS[env]:
        tables += reference_set() if s == "reference" else golden_set() if s == "golden" else master_set(master_dir)
    script = ["\\set ON_ERROR_STOP 1", "\\pset format unaligned", "\\pset tuples_only on", "BEGIN;",
              "SET search_path = talentra, public;"]
    script += [upsert_sql(t, n) for n, t in enumerate(tables)]
    # Identity sequences continue after the seeded ids, so ingested rows never collide with seeds
    for t in sorted({t.name for t in tables if "." not in t.name}):
        script.append(f"SELECT 'seq', setval(pg_get_serial_sequence('talentra.{t}', 'id'), "
                      f"greatest((SELECT max(id) FROM talentra.{t}), 1)), 0;")
    script.append("COMMIT;")
    out = psql(db, input="\n".join(script) + "\n", timeout=3600)
    changes = {}
    for line in out.splitlines():
        parts = line.split("|")
        if len(parts) == 3 and parts[0] != "seq":
            ins, upd = int(parts[1]), int(parts[2])
            prev = changes.get(parts[0], (0, 0))
            changes[parts[0]] = (prev[0] + ins, prev[1] + upd)
    names = sorted({t.name for t in tables})
    fp = {r["t"]: r["fp"] for r in query_json(db, "select t, ingest.table_fingerprint(t::regclass) fp from unnest("
                                              f"array[{', '.join(repr(n if '.' in n else 'talentra.' + n) for n in names)}]) t")}
    return {"env": env, "sets": ENV_SETS[env], "changes": {k: {"inserted": v[0], "updated": v[1]}
                                                        for k, v in sorted(changes.items())},
            "rows_changed": sum(a + b for a, b in changes.values()), "fingerprint": fp}


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--db", required=True)
    a.add_argument("--env", choices=sorted(ENV_SETS), required=True)
    a.add_argument("--master", type=Path, help="Step 23 output folder holding master/organisations.csv.gz")
    a.add_argument("--json", type=Path)
    args = a.parse_args()
    if "master" in ENV_SETS[args.env] and not args.master:
        raise SystemExit(f"--master is required for env {args.env}")
    result = seed(args.db, args.env, args.master)
    print(json.dumps({k: v for k, v in result.items() if k != "fingerprint"}, indent=1))
    if args.json:
        write_json(args.json, result)


if __name__ == "__main__":
    main()
