"""Step 25 - Data Ingestion: validate, transform, load, quarantine, reconcile.

Processes one delivery folder (b001, b002, ...) produced in the four inbound contracts, in dependency order.
Each file runs in a single transaction, so a failure leaves no partial business write:
  1 stage     Python checks the CSV shape (wrong column count -> MALFORMED_ROW) and hashes each payload
  2 validate  set-based SQL gives every bad row exactly one reason (first failing rule wins)
  3 version   per external key: new / corrected (higher source_version) / exact re-send (duplicate) /
              same version with different content (KEY_REUSE) / lower version (STALE_VERSION)
  4 load      new rows are inserted into the baseline tables through their constraints and triggers;
              corrections and late status events go through the native update path (row_version, state edge
              and actor-role triggers), with talentra.actor_id set to the real actor
  5 quarantine  every rejected row becomes integration_inbox (quarantined) + integration_rejection(reason, field)
  6 reconcile reconciliation_run row whose CHECK enforces source = applied + rejected + duplicate + pending;
              the target table delta must equal the rows reported as inserted, or the file rolls back
A file whose content hash was already completed is skipped, so re-running a delivery is a no-op.
Applications and their status events are loaded together because an application's status is the end of
its event chain.

Usage: step25_ingest.py --db NAME --batch-dir DIR [--json OUT]
"""
import argparse
import csv
import gzip
import hashlib
import json
import time
from pathlib import Path

from common import DATA, MASTER_ID_BASE, SOURCE_SYSTEM, psql, write_json
from contracts import CONTRACTS

PLATFORM_ACCOUNT = 1
MIGRATION_USER = 11          # baseline app_user holding the integration_worker role
STAGING = DATA / "_staging"
CHUNK = 500_000              # rows per INSERT statement: RI checks fire per statement, bounding memory
SOURCE_IDS = {key: MASTER_ID_BASE + n + 1 for n, key in enumerate(
    ["legacy.candidate_account.v1", "legacy.job_requirement.v1", "legacy.job_application.v1",
     "legacy.application_status_event.v1"])}
LANGS = "('en', 'hi', 'ta')"


# ---------------------------------------------------------------------------------------------- staging
def stage_file(path, label):
    """Gzip CSV -> staging CSV with line_no and payload hash; malformed lines -> separate CSV."""
    STAGING.mkdir(parents=True, exist_ok=True)
    good = STAGING / f"{label}.csv"
    bad = STAGING / f"{label}.malformed.csv"
    rows = malformed = 0
    with gzip.open(path, "rt", encoding="utf-8", newline="") as src, \
            open(good, "w", encoding="utf-8", newline="") as g, open(bad, "w", encoding="utf-8", newline="") as b:
        r = csv.reader(src)
        header = next(r)
        gw, bw = csv.writer(g, lineterminator="\n"), csv.writer(b, lineterminator="\n")
        for line_no, row in enumerate(r, start=2):
            payload = "\x1f".join(row[2:])           # event_id and correlation_id are transport, not content
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            if len(row) != len(header):
                malformed += 1
                bw.writerow([line_no, digest, row[5] if len(row) > 5 else "\\N", row[0] if row else "\\N"])
            else:
                rows += 1
                gw.writerow([line_no, digest, *row])
    return header, good, bad, rows, malformed


def sql_path(p):
    return str(p).replace("\\", "/")


# ---------------------------------------------------------------------------------------------- SQL pieces
ENVELOPE = """
  WHEN nullif(s.external_key, '') IS NULL THEN 'MISSING_REQUIRED:external_key'
  WHEN nullif(s.event_id, '') IS NULL THEN 'MISSING_REQUIRED:event_id'
  WHEN length(s.external_key) > 255 THEN 'TOO_LONG:external_key'
  WHEN ingest.try_int(s.schema_version) IS NULL THEN 'INVALID_TYPE:schema_version'
  WHEN ingest.try_int(s.schema_version) <> 1 THEN 'UNSUPPORTED_VERSION:schema_version'
  WHEN ingest.try_bigint(s.source_version) IS NULL OR ingest.try_bigint(s.source_version) < 0
       THEN 'INVALID_TYPE:source_version'
  WHEN ingest.try_ts(s.occurred_at) IS NULL THEN 'INVALID_FORMAT:occurred_at'
  WHEN ingest.try_ts(s.occurred_at) > now() + interval '1 day' THEN 'OUT_OF_RANGE:occurred_at'"""


def begin(contract, label, file_name, sha, staged, malformed, header, var):
    """Open the transaction, skip completed files, register the batch file and stage rows (as :var_*)."""
    cols = ", ".join(f"{c} text" for c in header)
    return f"""
SELECT EXISTS (SELECT 1 FROM ingest.batch_file WHERE contract_key = '{contract}' AND file_sha256 = '{sha}'
               AND status = 'completed') AS {var}_done \\gset
\\if :{var}_done
INSERT INTO ingest.batch_file (batch_label, contract_key, file_name, file_sha256, status, finished_at)
VALUES ('{label}', '{contract}', '{file_name}', '{sha}', 'skipped_duplicate_file', clock_timestamp());
\\set {var}_bf NULL
\\else
INSERT INTO ingest.batch_file (batch_label, contract_key, file_name, file_sha256, status)
VALUES ('{label}', '{contract}', '{file_name}', '{sha}', 'completed') RETURNING id AS {var}_bf, started_at AS {var}_started \\gset
\\endif
CREATE TEMP TABLE {var}_s (line_no int, payload_sha256 char(64), {cols}) ON COMMIT DROP;
CREATE TEMP TABLE {var}_m (line_no int, payload_sha256 char(64), external_key text, event_id text) ON COMMIT DROP;
\\if :{var}_done
\\else
\\copy {var}_s from '{sql_path(staged)}' with (format csv, null '\\N')
\\copy {var}_m from '{sql_path(malformed)}' with (format csv, null '\\N')
\\endif
"""


def versioning(var, entity, extra_reason=""):
    """{var}_d: rows that passed validation, with their action; uses ingest.key_map for prior versions."""
    return f"""
CREATE TEMP TABLE {var}_d ON COMMIT DROP AS
SELECT x.*, CASE
    WHEN x.rank_in_version > 1 AND x.same_as_first THEN 'duplicate'
    WHEN x.rank_in_version > 1 THEN 'q:KEY_REUSE:source_version'
    WHEN x.sv < x.max_version THEN 'superseded'
    WHEN x.existing_id IS NULL THEN 'new'
    WHEN x.sv < x.existing_version THEN 'q:STALE_VERSION:source_version'
    WHEN x.sv = x.existing_version AND x.payload_sha256 = x.existing_sha THEN 'duplicate'
    WHEN x.sv = x.existing_version THEN 'q:KEY_REUSE:source_version'
    {extra_reason}
    ELSE 'update' END AS action
FROM (SELECT v.*, ingest.try_bigint(v.source_version) AS sv, ingest.try_ts(v.occurred_at) AS ts,
             k.native_id AS existing_id, k.source_version AS existing_version,
             encode(k.payload_sha256, 'hex') AS existing_sha,
             row_number() OVER (PARTITION BY v.external_key, v.source_version ORDER BY v.line_no) AS rank_in_version,
             v.payload_sha256 = first_value(v.payload_sha256) OVER (PARTITION BY v.external_key, v.source_version
                                                                    ORDER BY v.line_no) AS same_as_first,
             max(ingest.try_bigint(v.source_version)) OVER (PARTITION BY v.external_key) AS max_version
      FROM {var}_v v
      LEFT JOIN ingest.key_map k ON k.entity = '{entity}' AND k.source_system = '{SOURCE_SYSTEM}'
                                AND k.external_key = v.external_key
      WHERE v.reason IS NULL) x;
"""


def outcome(var):
    """{var}_r: one outcome per source line (new/update/duplicate/superseded/q:REASON:field)."""
    return f"""
CREATE TEMP TABLE {var}_r ON COMMIT DROP AS
SELECT x.line_no, CASE WHEN x.outcome LIKE 'q:%' THEN x.external_key END AS external_key,
       CASE WHEN x.outcome LIKE 'q:%' THEN x.payload_sha256 END AS payload_sha256, x.ts, x.sv, x.outcome
FROM (SELECT v.line_no, v.external_key, v.payload_sha256, ingest.try_ts(v.occurred_at) AS ts,
             ingest.try_bigint(v.source_version) AS sv, coalesce('q:' || v.reason, d.action) AS outcome
      FROM {var}_v v LEFT JOIN {var}_d d USING (line_no)
      UNION ALL
      SELECT m.line_no, m.external_key, m.payload_sha256, NULL, NULL, 'q:MALFORMED_ROW:$' FROM {var}_m m) x;
SELECT ingest.assert_true(NOT EXISTS (SELECT 1 FROM {var}_r WHERE outcome IS NULL), 'row without outcome');
DROP TABLE {var}_v;
"""


def keymap(var, entity, id_expr, where="d.action IN ('new', 'update')"):
    """Record source key -> native id; id_expr may use d (decided rows) and n (rows given a new id)."""
    return f"""
INSERT INTO ingest.key_map AS k (entity, source_system, external_key, native_id, source_version, payload_sha256, batch_file_id)
SELECT '{entity}', '{SOURCE_SYSTEM}', d.external_key, {id_expr}, d.sv, decode(d.payload_sha256, 'hex'), :{var}_bf
FROM {var}_d d LEFT JOIN {var}_n n ON n.line_no = d.line_no WHERE {where}
ON CONFLICT (entity, source_system, external_key) DO UPDATE
  SET source_version = EXCLUDED.source_version, payload_sha256 = EXCLUDED.payload_sha256,
      batch_file_id = EXCLUDED.batch_file_id;
"""


def finish(var, contract, file_name, table, extra_counts="0"):
    """Quarantine, reconcile, check the target delta and record the batch file; prints one JSON line."""
    return f"""
INSERT INTO talentra.integration_inbox (account_id, integration_contract_id, event_key, correlation_key, payload_sha256,
       payload_reference, source_version, occurred_at, received_at, status_reference_value_id, attempt_count,
       next_attempt_at, last_error_code, created_by, updated_by)
SELECT {PLATFORM_ACCOUNT}, {SOURCE_IDS[contract]}, 'bf' || :{var}_bf || ':L' || line_no,
       left(coalesce(nullif(external_key, ''), '?'), 150), payload_sha256,
       left(:'{var}_label' || '/{file_name}#L' || line_no, 255), greatest(coalesce(sv, 0), 0),
       coalesce(ts, :'{var}_started'::timestamptz), clock_timestamp(), 186, 0, clock_timestamp(),
       split_part(outcome, ':', 2), {MIGRATION_USER}, {MIGRATION_USER}
FROM {var}_r WHERE outcome LIKE 'q:%';
INSERT INTO talentra.integration_rejection (account_id, integration_inbox_id, reason_code, field_path, created_by, updated_by)
SELECT i.account_id, i.id, split_part(r.outcome, ':', 2), left(split_part(r.outcome, ':', 3), 255),
       {MIGRATION_USER}, {MIGRATION_USER}
FROM {var}_r r JOIN talentra.integration_inbox i
  ON i.account_id = {PLATFORM_ACCOUNT} AND i.integration_contract_id = {SOURCE_IDS[contract]}
 AND i.event_key = 'bf' || :{var}_bf || ':L' || r.line_no
WHERE r.outcome LIKE 'q:%';
SELECT count(*) AS {var}_src,
       count(*) FILTER (WHERE outcome = 'new') AS {var}_new,
       count(*) FILTER (WHERE outcome = 'update') AS {var}_upd,
       count(*) FILTER (WHERE outcome IN ('duplicate', 'superseded')) AS {var}_dup,
       count(*) FILTER (WHERE outcome LIKE 'q:%') AS {var}_q
FROM {var}_r \\gset
SELECT count(*) - :{var}_before AS {var}_delta FROM talentra.{table} \\gset
SELECT ingest.assert_true(:{var}_delta = :{var}_new + {extra_counts},
       '{table} grew by ' || :{var}_delta || ' but ' || (:{var}_new + {extra_counts}) || ' rows were reported new');
SELECT ingest.assert_true(:{var}_src = :{var}_new + :{var}_upd + :{var}_dup + :{var}_q,
       'source rows do not equal new + updated + duplicate + quarantined');
INSERT INTO talentra.reconciliation_run (account_id, integration_source_id, window_start, window_end, source_count,
       applied_count, rejected_count, duplicate_count, pending_count, completed_at, created_by, updated_by)
VALUES ({PLATFORM_ACCOUNT}, {SOURCE_IDS[contract]}, :'{var}_started', clock_timestamp(), :{var}_src,
        :{var}_new + :{var}_upd, :{var}_q, :{var}_dup, 0, clock_timestamp(), {MIGRATION_USER}, {MIGRATION_USER})
RETURNING id AS {var}_recon \\gset
UPDATE ingest.batch_file SET source_rows = :{var}_src, applied_new = :{var}_new, applied_updated = :{var}_upd,
       duplicates = :{var}_dup, quarantined = :{var}_q, late_in_order = :{var}_late,
       reconciliation_run_id = :{var}_recon, finished_at = clock_timestamp()
WHERE id = :{var}_bf;
"""


def chunked(var_table, insert_sql):
    """Run an INSERT ... SELECT over {var_table} in CHUNK-sized slices of its rn column."""
    return f"""
DO $$ DECLARE lo bigint := 1; hi bigint; BEGIN
  SELECT coalesce(max(rn), 0) INTO hi FROM {var_table};
  WHILE lo <= hi LOOP
    EXECUTE format($q${insert_sql}$q$, lo, lo + {CHUNK} - 1);
    lo := lo + {CHUNK};
  END LOOP;
END $$;
"""


# ---------------------------------------------------------------------------------------------- candidates
def candidates_sql(v="c"):
    return f"""
SELECT count(*) AS {v}_before FROM talentra.candidate_profile \\gset
CREATE TEMP TABLE {v}_v ON COMMIT DROP AS
SELECT s.*, lower(s.email) AS email_norm, ps.id AS status_id, CASE
  {ENVELOPE}
  WHEN nullif(s.email, '') IS NULL THEN 'MISSING_REQUIRED:email'
  WHEN nullif(s.person_name, '') IS NULL THEN 'MISSING_REQUIRED:person_name'
  WHEN nullif(s.preferred_language, '') IS NULL THEN 'MISSING_REQUIRED:preferred_language'
  WHEN nullif(s.profile_status, '') IS NULL THEN 'MISSING_REQUIRED:profile_status'
  WHEN nullif(s.content_language, '') IS NULL THEN 'MISSING_REQUIRED:content_language'
  WHEN lower(s.email) !~ '^[a-z0-9._%+-]+@[a-z0-9-]+(\\.[a-z0-9-]+)+$' THEN 'INVALID_FORMAT:email'
  WHEN length(s.email) > 254 THEN 'TOO_LONG:email'
  WHEN length(s.person_name) > 150 THEN 'TOO_LONG:person_name'
  WHEN s.preferred_language NOT IN {LANGS} THEN 'UNKNOWN_REFERENCE:preferred_language'
  WHEN s.content_language NOT IN {LANGS} THEN 'UNKNOWN_REFERENCE:content_language'
  WHEN s.city_id IS NOT NULL AND ingest.try_bigint(s.city_id) IS NULL THEN 'INVALID_TYPE:city_id'
  WHEN s.city_id IS NOT NULL AND c.id IS NULL THEN 'UNKNOWN_REFERENCE:city_id'
  WHEN length(s.headline) > 2000 THEN 'TOO_LONG:headline'
  WHEN s.birth_date IS NOT NULL AND ingest.try_date(s.birth_date) IS NULL THEN 'INVALID_FORMAT:birth_date'
  WHEN ingest.try_date(s.birth_date) > (ingest.try_ts(s.occurred_at) - interval '14 years')::date
       THEN 'OUT_OF_RANGE:birth_date'
  WHEN s.profile_status = 'erased' THEN 'INVALID_STATE:profile_status'
  WHEN ps.id IS NULL THEN 'UNKNOWN_REFERENCE:profile_status'
END AS reason
FROM {v}_s s
LEFT JOIN talentra.city c ON c.id = ingest.try_bigint(s.city_id)
LEFT JOIN (SELECT rv.id, rv.code FROM talentra.reference_value rv JOIN talentra.reference_field_binding b
           ON b.reference_domain_id = rv.reference_domain_id AND b.table_name = 'candidate_profile'
          AND b.column_name = 'status_reference_value_id' WHERE rv.active) ps ON ps.code = s.profile_status;
DROP TABLE {v}_s;
{versioning(v, "candidate")}
-- An e-mail may belong to one account only: owned by another user, or claimed earlier in this file
UPDATE {v}_d d SET action = 'q:UNIQUE_CONFLICT:email'
FROM (SELECT line_no, row_number() OVER (PARTITION BY email_norm ORDER BY line_no) AS rk
      FROM {v}_d WHERE action IN ('new', 'update')) o
WHERE o.line_no = d.line_no AND d.action IN ('new', 'update') AND (o.rk > 1 OR EXISTS (
      SELECT 1 FROM talentra.app_user u WHERE u.email = d.email_norm AND u.id IS DISTINCT FROM
             (SELECT p.app_user_id FROM talentra.candidate_profile p WHERE p.id = d.existing_id)));
{outcome(v)}
CREATE TEMP TABLE {v}_n ON COMMIT DROP AS
SELECT d.*, row_number() OVER (ORDER BY line_no) AS rn,
       nextval(pg_get_serial_sequence('talentra.app_user', 'id')) AS user_id,
       nextval(pg_get_serial_sequence('talentra.candidate_profile', 'id')) AS profile_id
FROM {v}_d d WHERE action = 'new';
{chunked(v + "_n", f'''INSERT INTO talentra.app_user (id, email, person_name, status_reference_value_id,
   preferred_language, created_at, created_by, updated_at, updated_by)
 SELECT user_id, email_norm, person_name, 4, preferred_language, ts, {MIGRATION_USER}, ts, {MIGRATION_USER}
 FROM {v}_n WHERE rn BETWEEN %s AND %s''')}
{chunked(v + "_n", f'''INSERT INTO talentra.candidate_profile (id, app_user_id, city_id, headline, birth_date,
   status_reference_value_id, content_language, created_at, created_by, updated_at, updated_by, row_version)
 SELECT profile_id, user_id, ingest.try_bigint(city_id), headline, ingest.try_date(birth_date), status_id,
        content_language, ts, {MIGRATION_USER}, ts, {MIGRATION_USER}, 1
 FROM {v}_n WHERE rn BETWEEN %s AND %s''')}
{chunked(v + "_n", f'''INSERT INTO talentra.user_role (app_user_id, access_role_id, created_at, created_by,
   updated_at, updated_by)
 SELECT user_id, 5, ts, {MIGRATION_USER}, ts, {MIGRATION_USER} FROM {v}_n WHERE rn BETWEEN %s AND %s''')}
-- Corrections: native update path, acting as the candidate (state-edge trigger checks the role)
DO $$ DECLARE r record; BEGIN
  FOR r IN SELECT d.*, p.app_user_id FROM {v}_d d JOIN talentra.candidate_profile p ON p.id = d.existing_id
           WHERE d.action = 'update' ORDER BY d.line_no LOOP
    PERFORM set_config('talentra.actor_id', r.app_user_id::text, true);
    UPDATE talentra.app_user SET email = r.email_norm, person_name = r.person_name,
           preferred_language = r.preferred_language, updated_at = r.ts, updated_by = {MIGRATION_USER}
     WHERE id = r.app_user_id
       AND (email, person_name, preferred_language) IS DISTINCT FROM (r.email_norm, r.person_name, r.preferred_language);
    UPDATE talentra.candidate_profile SET city_id = ingest.try_bigint(r.city_id), headline = r.headline,
           birth_date = ingest.try_date(r.birth_date), status_reference_value_id = r.status_id,
           content_language = r.content_language, updated_at = r.ts, updated_by = {MIGRATION_USER},
           row_version = row_version + 1
     WHERE id = r.existing_id AND (city_id, headline, birth_date, status_reference_value_id, content_language)
           IS DISTINCT FROM (ingest.try_bigint(r.city_id), r.headline, ingest.try_date(r.birth_date), r.status_id,
                             r.content_language);
  END LOOP;
END $$;
{keymap(v, "candidate", "coalesce(d.existing_id, n.profile_id)")}
SELECT 0 AS {v}_late \\gset
"""


# ---------------------------------------------------------------------------------------------- jobs
JOB_REFS = ["employment_type_reference_value_id", "work_type_reference_value_id", "status_reference_value_id",
            "publish_state_reference_value_id", "salary_disclosure_reference_value_id"]
JOB_REQUIRED = ["organisation_id", "job_role_id", *JOB_REFS, "title", "description", "positions",
                "open_to_consultant", "source_timezone", "content_language"]
JOB_INTS = ["organisation_id", "job_role_id", "city_id", "positions", *JOB_REFS]


def jobs_sql(v="j"):
    required = "\n".join(f"  WHEN nullif(s.{c}, '') IS NULL THEN 'MISSING_REQUIRED:{c}'" for c in JOB_REQUIRED)
    ints = "\n".join(f"  WHEN s.{c} IS NOT NULL AND ingest.try_bigint(s.{c}) IS NULL THEN 'INVALID_TYPE:{c}'"
                     for c in JOB_INTS)
    domains = "\n".join(f"""  WHEN NOT EXISTS (SELECT 1 FROM refdom r WHERE r.column_name = '{c}'
                     AND r.id = ingest.try_bigint(s.{c})) THEN 'WRONG_DOMAIN:{c}'""" for c in JOB_REFS)
    return f"""
SELECT count(*) AS {v}_before FROM talentra.job_requirement \\gset
CREATE TEMP TABLE refdom ON COMMIT DROP AS
SELECT b.column_name, rv.id FROM talentra.reference_field_binding b
JOIN talentra.reference_value rv ON rv.reference_domain_id = b.reference_domain_id
WHERE b.table_name = 'job_requirement' AND rv.active AND rv.deleted_at IS NULL AND b.deleted_at IS NULL;
CREATE TEMP TABLE tz ON COMMIT DROP AS SELECT name FROM pg_timezone_names;
CREATE TEMP TABLE {v}_v ON COMMIT DROP AS
SELECT s.*, o.native_id AS org_id, CASE
  {ENVELOPE}
{required}
{ints}
  WHEN ingest.try_bool(s.open_to_consultant) IS NULL THEN 'INVALID_TYPE:open_to_consultant'
  WHEN o.native_id IS NULL THEN 'UNKNOWN_PARENT:organisation_id'
  WHEN NOT EXISTS (SELECT 1 FROM talentra.job_role jr WHERE jr.id = ingest.try_bigint(s.job_role_id))
       THEN 'UNKNOWN_REFERENCE:job_role_id'
  WHEN s.city_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM talentra.city c WHERE c.id = ingest.try_bigint(s.city_id))
       THEN 'UNKNOWN_REFERENCE:city_id'
{domains}
  WHEN length(s.title) > 255 THEN 'TOO_LONG:title'
  WHEN ingest.try_bigint(s.positions) <= 0 THEN 'OUT_OF_RANGE:positions'
  WHEN (s.salary_min IS NOT NULL AND ingest.try_numeric(s.salary_min) IS NULL)
    OR (s.salary_max IS NOT NULL AND ingest.try_numeric(s.salary_max) IS NULL) THEN 'INVALID_TYPE:salary_min'
  WHEN NOT ((s.salary_min IS NULL AND s.salary_max IS NULL AND s.currency_code IS NULL)
         OR (s.salary_min IS NOT NULL AND s.salary_max IS NOT NULL AND s.currency_code IS NOT NULL))
       THEN 'INCONSISTENT:' || CASE WHEN s.currency_code IS NULL THEN 'currency_code' ELSE 'salary_min' END
  WHEN s.currency_code !~ '^[A-Z]{{3}}$' THEN 'INVALID_FORMAT:currency_code'
  WHEN ingest.try_numeric(s.salary_min) < 0 OR ingest.try_numeric(s.salary_min) > ingest.try_numeric(s.salary_max)
       THEN 'OUT_OF_RANGE:salary_min'
  WHEN NOT EXISTS (SELECT 1 FROM tz WHERE tz.name = s.source_timezone) THEN 'UNKNOWN_REFERENCE:source_timezone'
  WHEN s.content_language NOT IN {LANGS} THEN 'UNKNOWN_REFERENCE:content_language'
END AS reason
FROM {v}_s s
LEFT JOIN ingest.key_map o ON o.entity = 'organisation' AND o.source_system = '{SOURCE_SYSTEM}'
                          AND o.external_key = s.organisation_id;
DROP TABLE {v}_s;
{versioning(v, "job")}
-- A correction that changes status must follow a permitted job_requirement edge
UPDATE {v}_d d SET action = 'q:ILLEGAL_TRANSITION:status_reference_value_id'
FROM talentra.job_requirement j
WHERE d.action = 'update' AND j.id = d.existing_id
  AND j.status_reference_value_id <> ingest.try_bigint(d.status_reference_value_id)
  AND NOT EXISTS (SELECT 1 FROM talentra.transition_rule t WHERE t.entity_table = 'job_requirement'
                  AND t.from_reference_value_id = j.status_reference_value_id
                  AND t.to_reference_value_id = ingest.try_bigint(d.status_reference_value_id) AND t.deleted_at IS NULL);
{outcome(v)}
CREATE TEMP TABLE {v}_n ON COMMIT DROP AS
SELECT d.*, row_number() OVER (ORDER BY line_no) AS rn,
       nextval(pg_get_serial_sequence('talentra.job_requirement', 'id')) AS job_id
FROM {v}_d d WHERE action = 'new';
{chunked(v + "_n", f'''INSERT INTO talentra.job_requirement (id, organisation_id, job_role_id,
   employment_type_reference_value_id, work_type_reference_value_id, city_id, title, description, positions,
   status_reference_value_id, publish_state_reference_value_id, open_to_consultant, salary_min, salary_max,
   currency_code, salary_disclosure_reference_value_id, source_timezone, content_language, created_at, created_by,
   updated_at, updated_by, row_version)
 SELECT job_id, org_id, job_role_id::bigint, employment_type_reference_value_id::bigint,
        work_type_reference_value_id::bigint, ingest.try_bigint(city_id), title, description, positions::int,
        status_reference_value_id::bigint, publish_state_reference_value_id::bigint, open_to_consultant::boolean,
        ingest.try_numeric(salary_min), ingest.try_numeric(salary_max), currency_code,
        salary_disclosure_reference_value_id::bigint, source_timezone, content_language, ts, {MIGRATION_USER}, ts,
        {MIGRATION_USER}, 1
 FROM {v}_n WHERE rn BETWEEN %s AND %s''')}
-- Corrections act as the organisation's employer user (job_requirement edges require that role)
DO $$ DECLARE r record; BEGIN
  FOR r IN SELECT d.* FROM {v}_d d WHERE d.action = 'update' ORDER BY d.line_no LOOP
    PERFORM set_config('talentra.actor_id', r.org_id::text, true);
    UPDATE talentra.job_requirement SET job_role_id = r.job_role_id::bigint,
           employment_type_reference_value_id = r.employment_type_reference_value_id::bigint,
           work_type_reference_value_id = r.work_type_reference_value_id::bigint,
           city_id = ingest.try_bigint(r.city_id), title = r.title, description = r.description,
           positions = r.positions::int, status_reference_value_id = r.status_reference_value_id::bigint,
           publish_state_reference_value_id = r.publish_state_reference_value_id::bigint,
           open_to_consultant = r.open_to_consultant::boolean, salary_min = ingest.try_numeric(r.salary_min),
           salary_max = ingest.try_numeric(r.salary_max), currency_code = r.currency_code,
           salary_disclosure_reference_value_id = r.salary_disclosure_reference_value_id::bigint,
           source_timezone = r.source_timezone, content_language = r.content_language,
           updated_at = r.ts, updated_by = {MIGRATION_USER}, row_version = row_version + 1
     WHERE id = r.existing_id;
  END LOOP;
END $$;
{keymap(v, "job", "coalesce(d.existing_id, n.job_id)")}
SELECT 0 AS {v}_late \\gset
"""


# ---------------------------------------------------------------------------------------------- applications + events
def applications_sql(a="a", e="e"):
    return f"""
SELECT count(*) AS {a}_before FROM talentra.job_application \\gset
SELECT count(*) AS {e}_before FROM talentra.application_status_event \\gset
CREATE TEMP TABLE {a}_v ON COMMIT DROP AS
SELECT s.line_no, s.payload_sha256, s.external_key, s.event_id, s.occurred_at, s.source_version,
       ck.native_id AS candidate_id, jk.native_id AS job_id, j.organisation_id AS job_org_id,
       ok.native_id AS claimed_org_id, ingest.try_ts(s.applied_at) AS applied_ts, CASE
  {ENVELOPE}
  WHEN nullif(s.candidate_key, '') IS NULL THEN 'MISSING_REQUIRED:candidate_key'
  WHEN nullif(s.job_key, '') IS NULL THEN 'MISSING_REQUIRED:job_key'
  WHEN nullif(s.organisation_key, '') IS NULL THEN 'MISSING_REQUIRED:organisation_key'
  WHEN nullif(s.applied_at, '') IS NULL THEN 'MISSING_REQUIRED:applied_at'
  WHEN ck.native_id IS NULL THEN 'UNKNOWN_PARENT:candidate_key'
  WHEN jk.native_id IS NULL THEN 'UNKNOWN_PARENT:job_key'
  WHEN ok.native_id IS DISTINCT FROM j.organisation_id THEN 'CROSS_ACCOUNT:organisation_key'
  WHEN ingest.try_ts(s.applied_at) IS NULL THEN 'INVALID_FORMAT:applied_at'
  WHEN ingest.try_ts(s.applied_at) > now() + interval '1 day' OR ingest.try_ts(s.applied_at) < j.created_at
       THEN 'OUT_OF_RANGE:applied_at'
END AS reason
FROM {a}_s s
LEFT JOIN ingest.key_map ck ON ck.entity = 'candidate' AND ck.source_system = '{SOURCE_SYSTEM}' AND ck.external_key = s.candidate_key
LEFT JOIN ingest.key_map jk ON jk.entity = 'job' AND jk.source_system = '{SOURCE_SYSTEM}' AND jk.external_key = s.job_key
LEFT JOIN talentra.job_requirement j ON j.id = jk.native_id
LEFT JOIN ingest.key_map ok ON ok.entity = 'organisation' AND ok.source_system = '{SOURCE_SYSTEM}'
                           AND ok.external_key = s.organisation_key;
DROP TABLE {a}_s;
{versioning(a, "application")}
-- One application per candidate and job: already in the database, or claimed earlier in this file
UPDATE {a}_d d SET action = 'q:UNIQUE_CONFLICT:candidate_key,job_key'
FROM (SELECT line_no, row_number() OVER (PARTITION BY candidate_id, job_id ORDER BY line_no) AS rk
      FROM {a}_d WHERE action IN ('new', 'update')) o
WHERE o.line_no = d.line_no AND d.action IN ('new', 'update') AND (o.rk > 1 OR EXISTS (
      SELECT 1 FROM talentra.job_application x WHERE x.candidate_profile_id = d.candidate_id
         AND x.job_requirement_id = d.job_id AND x.id IS DISTINCT FROM d.existing_id));
-- Applications are immutable once loaded except through status events
UPDATE {a}_d SET action = 'q:IMMUTABLE_RECORD:source_version' WHERE action = 'update';
{outcome(a)}
CREATE TEMP TABLE {a}_n ON COMMIT DROP AS
SELECT d.line_no, d.external_key, d.candidate_id, d.job_id, d.job_org_id, d.applied_ts, d.ts,
       row_number() OVER (ORDER BY line_no) AS rn,
       nextval(pg_get_serial_sequence('talentra.job_application', 'id')) AS app_id
FROM {a}_d d WHERE action = 'new';

-- Every application an event may refer to: loaded before, or new in this delivery
CREATE TEMP TABLE apps_known ON COMMIT DROP AS
SELECT n.external_key AS app_key, n.app_id, n.candidate_id, n.job_org_id AS org_id, n.applied_ts,
       true AS is_new, NULL::bigint AS base_status, '-infinity'::timestamptz AS base_ts
FROM {a}_n n
UNION ALL
SELECT k.external_key, k.native_id, x.candidate_profile_id, j.organisation_id, x.applied_at,
       false, x.status_reference_value_id,
       coalesce((SELECT max(h.occurred_at) FROM talentra.application_status_event h WHERE h.job_application_id = x.id),
                '-infinity')
FROM ingest.key_map k JOIN talentra.job_application x ON x.id = k.native_id
JOIN talentra.job_requirement j ON j.id = x.job_requirement_id
WHERE k.entity = 'application' AND k.source_system = '{SOURCE_SYSTEM}'
  AND k.external_key IN (SELECT application_key FROM {e}_s);
CREATE INDEX ON apps_known (app_key);
ANALYZE apps_known;

CREATE TEMP TABLE status_code ON COMMIT DROP AS
SELECT rv.id, rv.code FROM talentra.reference_value rv JOIN talentra.reference_field_binding b
  ON b.reference_domain_id = rv.reference_domain_id
WHERE b.table_name = 'job_application' AND b.column_name = 'status_reference_value_id' AND rv.active;
CREATE TEMP TABLE edges ON COMMIT DROP AS
SELECT t.from_reference_value_id AS from_id, t.to_reference_value_id AS to_id, t.actor_role_code AS role
FROM talentra.transition_rule t WHERE t.entity_table = 'job_application' AND t.deleted_at IS NULL;
CREATE TEMP TABLE recruiters ON COMMIT DROP AS
SELECT DISTINCT app_user_id, organisation_id FROM talentra.recruiter_membership WHERE deleted_at IS NULL;
CREATE TEMP TABLE actor_roles ON COMMIT DROP AS
SELECT DISTINCT ur.app_user_id, ar.code FROM talentra.user_role ur JOIN talentra.access_role ar ON ar.id = ur.access_role_id
WHERE ur.deleted_at IS NULL AND ar.code IN ('candidate', 'recruiter');
CREATE INDEX ON actor_roles (app_user_id, code);
ANALYZE recruiters, actor_roles;

CREATE TEMP TABLE {e}_v ON COMMIT DROP AS
SELECT s.line_no, s.payload_sha256, s.external_key, s.event_id, s.occurred_at, s.source_version, s.actor_type,
       k.app_id, k.is_new, k.base_status, k.base_ts, fs.id AS from_id, ts_.id AS to_id,
       CASE s.actor_type WHEN 'candidate' THEN cp.app_user_id WHEN 'recruiter' THEN rk.native_id END AS actor_user_id,
       CASE
  {ENVELOPE}
  WHEN nullif(s.application_key, '') IS NULL THEN 'MISSING_REQUIRED:application_key'
  WHEN nullif(s.to_status, '') IS NULL THEN 'MISSING_REQUIRED:to_status'
  WHEN nullif(s.actor_type, '') IS NULL THEN 'MISSING_REQUIRED:actor_type'
  WHEN nullif(s.actor_key, '') IS NULL THEN 'MISSING_REQUIRED:actor_key'
  WHEN ts_.id IS NULL THEN 'UNKNOWN_REFERENCE:to_status'
  WHEN s.from_status IS NOT NULL AND fs.id IS NULL THEN 'UNKNOWN_REFERENCE:from_status'
  WHEN s.actor_type NOT IN ('candidate', 'recruiter') THEN 'UNKNOWN_REFERENCE:actor_type'
  WHEN k.app_id IS NULL THEN 'UNKNOWN_PARENT:application_key'
  WHEN ok.native_id IS DISTINCT FROM k.org_id THEN 'CROSS_ACCOUNT:organisation_key'
  WHEN ingest.try_ts(s.occurred_at) < k.applied_ts THEN 'OUT_OF_RANGE:occurred_at'
  WHEN s.actor_type = 'candidate' AND (ak.external_key IS DISTINCT FROM s.actor_key) THEN 'ACTOR_MISMATCH:actor_key'
  WHEN s.actor_type = 'recruiter' AND rm.app_user_id IS NULL THEN 'ACTOR_MISMATCH:actor_key'
END AS reason
FROM {e}_s s
LEFT JOIN apps_known k ON k.app_key = s.application_key
LEFT JOIN status_code fs ON fs.code = s.from_status
LEFT JOIN status_code ts_ ON ts_.code = s.to_status
LEFT JOIN ingest.key_map ok ON ok.entity = 'organisation' AND ok.source_system = '{SOURCE_SYSTEM}'
                           AND ok.external_key = s.organisation_key
LEFT JOIN talentra.candidate_profile cp ON cp.id = k.candidate_id
LEFT JOIN ingest.key_map ak ON ak.entity = 'candidate' AND ak.source_system = '{SOURCE_SYSTEM}' AND ak.native_id = k.candidate_id
LEFT JOIN ingest.key_map rk ON rk.entity = 'recruiter' AND rk.source_system = '{SOURCE_SYSTEM}'
                           AND rk.external_key = s.actor_key
LEFT JOIN recruiters rm ON rm.app_user_id = rk.native_id AND rm.organisation_id = k.org_id;
DROP TABLE {e}_s;
{versioning(e, "status_event")}
-- History is append-only: a changed or re-versioned event key is never applied over the original
UPDATE {e}_d SET action = 'q:KEY_REUSE:source_version' WHERE action = 'update';
-- Late events older than the application's latest recorded event would rewrite history: quarantine
UPDATE {e}_d SET action = 'q:LATE_OUT_OF_ORDER:occurred_at' WHERE action = 'new' AND ts < base_ts;

-- Chain check: each event must start where the previous one ended, on a permitted edge for its actor's role
CREATE TEMP TABLE chain ON COMMIT DROP AS
SELECT x.*, CASE
  WHEN x.expected_from IS DISTINCT FROM x.from_id THEN 'CHAIN_BREAK:from_status'
  WHEN x.expected_from IS NULL THEN CASE WHEN x.to_id = (SELECT id FROM status_code WHERE code = 'applied')
                                          AND x.actor_type = 'candidate' AND x.has_role THEN NULL
                                         WHEN x.to_id = (SELECT id FROM status_code WHERE code = 'applied')
                                          AND x.actor_type = 'candidate' THEN 'ACTOR_NOT_PERMITTED:actor_type'
                                         ELSE 'ILLEGAL_TRANSITION:from_status,to_status' END
  WHEN NOT x.edge_any THEN 'ILLEGAL_TRANSITION:from_status,to_status'
  WHEN NOT x.edge_for_role OR NOT x.has_role THEN 'ACTOR_NOT_PERMITTED:actor_type'
END AS reason
FROM (SELECT d.line_no, d.app_id, row_number() OVER w AS seq,
             coalesce(lag(d.to_id) OVER w, d.base_status) AS expected_from, d.from_id, d.to_id, d.actor_type,
             EXISTS (SELECT 1 FROM edges g WHERE g.from_id = d.from_id AND g.to_id = d.to_id) AS edge_any,
             EXISTS (SELECT 1 FROM edges g WHERE g.from_id = d.from_id AND g.to_id = d.to_id
                     AND g.role = d.actor_type) AS edge_for_role,
             ar.app_user_id IS NOT NULL AS has_role
      FROM {e}_d d LEFT JOIN actor_roles ar ON ar.app_user_id = d.actor_user_id AND ar.code = d.actor_type
      WHERE d.action = 'new'
      WINDOW w AS (PARTITION BY d.app_id ORDER BY d.ts, d.line_no)) x;
-- After the first rejected event, nothing later in that application's chain can be applied
UPDATE chain c SET reason = 'PRIOR_EVENT_QUARANTINED:application_key'
FROM (SELECT app_id, min(seq) AS first_bad FROM chain WHERE reason IS NOT NULL GROUP BY app_id) f
WHERE c.app_id = f.app_id AND c.seq > f.first_bad;
UPDATE {e}_d d SET action = 'q:' || c.reason FROM chain c WHERE c.line_no = d.line_no AND c.reason IS NOT NULL;
DROP TABLE chain;
{outcome(e)}

-- New applications start at the end of their valid chain (insert path; edges were validated above)
CREATE TEMP TABLE final_status ON COMMIT DROP AS
SELECT DISTINCT ON (d.app_id) d.app_id, d.to_id, d.ts FROM {e}_d d
WHERE d.action = 'new' AND d.is_new ORDER BY d.app_id, d.ts DESC, d.line_no DESC;
CREATE INDEX ON final_status (app_id);
ANALYZE final_status;
{chunked(a + "_n", f'''INSERT INTO talentra.job_application (id, job_requirement_id, candidate_profile_id,
   resume_version_id, status_reference_value_id, applied_at, created_at, created_by, updated_at, updated_by,
   row_version)
 SELECT n.app_id, n.job_id, n.candidate_id, NULL, coalesce(f.to_id, 65), n.applied_ts, n.ts, {MIGRATION_USER},
        coalesce(f.ts, n.ts), {MIGRATION_USER}, 1
 FROM {a}_n n LEFT JOIN final_status f ON f.app_id = n.app_id WHERE n.rn BETWEEN %s AND %s''')}
{keymap(a, "application", "n.app_id", "d.action = 'new'")}
CREATE TEMP TABLE {e}_n ON COMMIT DROP AS
SELECT d.line_no, d.external_key, d.sv, d.payload_sha256, d.app_id, d.from_id, d.to_id, d.actor_user_id, d.ts,
       row_number() OVER (ORDER BY d.app_id, d.ts, d.line_no) AS rn,
       nextval(pg_get_serial_sequence('talentra.application_status_event', 'id')) AS event_id_native
FROM {e}_d d WHERE d.action = 'new' AND d.is_new;
{chunked(e + "_n", f'''INSERT INTO talentra.application_status_event (id, job_application_id,
   from_reference_value_id, to_reference_value_id, actor_app_user_id, occurred_at, created_at, created_by,
   updated_at, updated_by)
 SELECT event_id_native, app_id, from_id, to_id, actor_user_id, ts, ts, {MIGRATION_USER}, ts, {MIGRATION_USER}
 FROM {e}_n WHERE rn BETWEEN %s AND %s''')}
-- Late events for applications loaded earlier: append history, then move status through the native trigger
-- (enforce_state_edge checks the edge and the actor's role; row_version must advance by exactly one)
CREATE TEMP TABLE {e}_late ON COMMIT DROP AS
SELECT d.line_no, d.external_key, d.sv, d.payload_sha256, d.app_id, d.from_id, d.to_id, d.actor_user_id, d.ts,
       nextval(pg_get_serial_sequence('talentra.application_status_event', 'id')) AS event_id_native
FROM {e}_d d WHERE d.action = 'new' AND NOT d.is_new;
DO $$ DECLARE r record; BEGIN
  FOR r IN SELECT * FROM {e}_late ORDER BY app_id, ts, line_no LOOP
    INSERT INTO talentra.application_status_event (id, job_application_id, from_reference_value_id,
           to_reference_value_id, actor_app_user_id, occurred_at, created_at, created_by, updated_at, updated_by)
    VALUES (r.event_id_native, r.app_id, r.from_id, r.to_id, r.actor_user_id, r.ts, clock_timestamp(),
            {MIGRATION_USER}, clock_timestamp(), {MIGRATION_USER});
    PERFORM set_config('talentra.actor_id', r.actor_user_id::text, true);
    UPDATE talentra.job_application SET status_reference_value_id = r.to_id, updated_at = r.ts,
           updated_by = r.actor_user_id, row_version = row_version + 1
     WHERE id = r.app_id;
  END LOOP;
END $$;
INSERT INTO ingest.key_map (entity, source_system, external_key, native_id, source_version, payload_sha256, batch_file_id)
SELECT 'status_event', '{SOURCE_SYSTEM}', external_key, event_id_native, sv, decode(payload_sha256, 'hex'), :{e}_bf
FROM {e}_n
UNION ALL
SELECT 'status_event', '{SOURCE_SYSTEM}', external_key, event_id_native, sv, decode(payload_sha256, 'hex'), :{e}_bf
FROM {e}_late;
SELECT 0 AS {a}_late \\gset
SELECT count(*) AS {e}_late FROM {e}_late \\gset
"""


# ---------------------------------------------------------------------------------------------- runner
PLAN = [  # (contract, var, sql builder, target table)
    ("legacy.candidate_account.v1", "c", candidates_sql, "candidate_profile"),
    ("legacy.job_requirement.v1", "j", jobs_sql, "job_requirement"),
]


def run_script(db, parts):
    script = "\n".join(["\\set ON_ERROR_STOP 1", "\\pset format unaligned", "\\pset tuples_only on", "BEGIN;",
                        "SET LOCAL search_path = talentra, public;", "SET CONSTRAINTS ALL IMMEDIATE;",
                        "SET LOCAL work_mem = '256MB';", *parts, "COMMIT;"])
    return psql(db, input=script, timeout=6 * 3600)


def file_result(db, contract, sha):
    rows = json.loads(psql(db, "-Atc", f"""select coalesce(json_agg(b order by id desc), '[]') from ingest.batch_file b
        where contract_key = '{contract}' and file_sha256 = '{sha}'"""))
    return rows[0] if rows else None


def ingest_dir(db, batch_dir):
    batch_dir = Path(batch_dir)
    label = batch_dir.name
    results = []

    def prepare(contract, var, path):
        if path is None or not path.exists():
            return None
        header, good, bad, n, m = stage_file(path, f"{label}_{var}")
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        return {"contract": contract, "var": var, "path": path, "sha": sha, "header": header, "good": good,
                "bad": bad, "rows": n, "malformed": m}

    def body(p):
        # skipped files still run the block; every statement then sees empty staging tables
        return (begin(p["contract"], label, p["path"].name, p["sha"], p["good"], p["bad"], p["header"], p["var"])
                + f"\\set {p['var']}_label {label}\n")

    def guard(p, sql):
        return f"\\if :{p['var']}_done\n\\else\n{sql}\n\\endif\n"

    def cleanup(*staged_parts):
        for p in staged_parts:
            if p:
                p["good"].unlink(missing_ok=True)
                p["bad"].unlink(missing_ok=True)

    def files(contract):
        stem = CONTRACTS[contract]["file"].removesuffix(".csv.gz")
        return sorted(batch_dir.glob(f"{stem}*.csv.gz"))

    for contract, var, builder, table in PLAN:
        for path in files(contract):
            p = prepare(contract, var, path)
            t = time.time()
            run_script(db, [body(p), guard(p, builder(var) + finish(var, contract, p["path"].name, table))])
            cleanup(p)
            results.append({**file_result(db, contract, p["sha"]), "seconds": round(time.time() - t, 1),
                            "file": f"{label}/{p['path'].name}"})
            print(json.dumps({k: results[-1].get(k) for k in ("file", "source_rows", "quarantined", "seconds")}),
                  flush=True)

    # Applications and status events share one transaction per part (same suffix, e.g. .p01);
    # either file may be absent from a delivery.
    combined = [("a", "legacy.job_application.v1", "job_application"),
                ("e", "legacy.application_status_event.v1", "application_status_event")]
    parts_by_suffix = {}
    for v, contract, _ in combined:
        stem = CONTRACTS[contract]["file"].removesuffix(".csv.gz")
        for path in files(contract):
            parts_by_suffix.setdefault(path.name[len(stem):], {})[v] = path
    for suffix in sorted(parts_by_suffix):
        results += ingest_pair(db, label, combined, parts_by_suffix[suffix], prepare, body, guard, cleanup)
    return results


def ingest_pair(db, label, combined, paths, prepare, body, guard, cleanup):
    results = []
    staged = {v: prepare(contract, v, paths.get(v)) for v, contract, _ in combined}
    if any(staged.values()):
        t = time.time()
        parts = [body(staged[v]) if staged[v] else _empty_stage(v) for v, _, _ in combined]
        parts.append("SELECT :'a_done'::boolean AND :'e_done'::boolean AS ae_all_done \\gset")
        block = applications_sql("a", "e")
        for v, contract, table in combined:
            if staged[v]:
                block += guard(staged[v], finish(v, contract, staged[v]["path"].name, table))
        parts.append(f"\\if :ae_all_done\n\\else\n{block}\\endif\n")
        run_script(db, parts)
        cleanup(*staged.values())
        secs = round(time.time() - t, 1)
        for v, contract, _ in combined:
            p = staged[v]
            if p:
                results.append({**file_result(db, contract, p["sha"]), "seconds": secs,
                                "file": f"{label}/{p['path'].name}"})
                print(json.dumps({k: results[-1].get(k) for k in ("file", "source_rows", "quarantined", "seconds")}),
                      flush=True)
    return results


def _empty_stage(var):
    """Stand-in for a contract file that is not part of this delivery: empty stage, nothing to record."""
    from step23_generate import APPLICATION_HEADER, EVENT_HEADER
    header = APPLICATION_HEADER if var == "a" else EVENT_HEADER
    cols = ", ".join(f"{c} text" for c in header)
    return (f"CREATE TEMP TABLE {var}_s (line_no int, payload_sha256 char(64), {cols}) ON COMMIT DROP;\n"
            f"CREATE TEMP TABLE {var}_m (line_no int, payload_sha256 char(64), external_key text, event_id text)"
            f" ON COMMIT DROP;\n\\set {var}_done true\n\\set {var}_bf NULL\n")


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--db", required=True)
    a.add_argument("--batch-dir", required=True, type=Path)
    a.add_argument("--json", type=Path)
    args = a.parse_args()
    res = ingest_dir(args.db, args.batch_dir)
    for r in res:
        print(json.dumps({k: r.get(k) for k in ("file", "status", "source_rows", "applied_new", "applied_updated",
                                                "duplicates", "quarantined", "late_in_order", "seconds")}))
    if args.json:
        write_json(args.json, res)


if __name__ == "__main__":
    main()
