-- Talentra Phase 4 (steps 24-25): ingestion control schema. Additive; apply after 001,003,002,004,005,006.
-- Business data still lands only in the baseline tables, through their own constraints and triggers.
-- Quarantined records use the baseline integration_inbox + integration_rejection tables and every
-- delivery is reconciled into reconciliation_run, whose CHECK enforces source = applied+rejected+duplicate+pending.

BEGIN;

CREATE SCHEMA ingest;

-- One row per delivered file. A completed file is never processed twice (same contract + content hash).
CREATE TABLE ingest.batch_file (
  id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  batch_label        varchar(40)  NOT NULL,
  contract_key       varchar(150) NOT NULL,
  file_name          varchar(255) NOT NULL,
  file_sha256        char(64)     NOT NULL,
  status             varchar(30)  NOT NULL,
  source_rows        bigint,
  applied_new        bigint,
  applied_updated    bigint,
  duplicates         bigint,
  quarantined        bigint,
  late_in_order      bigint,
  reconciliation_run_id bigint REFERENCES talentra.reconciliation_run(id),
  started_at         timestamptz  NOT NULL DEFAULT clock_timestamp(),
  finished_at        timestamptz,
  CONSTRAINT ck_batch_file_status CHECK (status IN ('completed', 'skipped_duplicate_file')),
  CONSTRAINT ck_batch_file_reconciled CHECK (
    status <> 'completed' OR
    source_rows = applied_new + applied_updated + duplicates + quarantined)
);
CREATE UNIQUE INDEX uq_batch_file_completed ON ingest.batch_file (contract_key, file_sha256)
  WHERE status = 'completed';

-- Source key -> native id translation ("translate IDs within account; never join source surrogate IDs").
-- external_reference cannot hold app_user, job_application or status-event targets, hence this map.
CREATE TABLE ingest.key_map (
  entity          varchar(40)  NOT NULL,
  source_system   varchar(40)  NOT NULL,
  external_key    varchar(255) NOT NULL,
  native_id       bigint       NOT NULL,
  source_version  bigint       NOT NULL CHECK (source_version >= 0),
  payload_sha256  bytea        NOT NULL CHECK (octet_length(payload_sha256) = 32),
  batch_file_id   bigint REFERENCES ingest.batch_file(id),
  PRIMARY KEY (entity, source_system, external_key)
);
-- Reverse lookup (native id -> source key) is needed for actors and parents, not for history events
CREATE UNIQUE INDEX uq_key_map_native ON ingest.key_map (entity, source_system, native_id)
  WHERE entity <> 'status_event';

-- Safe casts for staged text: NULL when the value does not parse (pg_input_is_valid, PostgreSQL 16+)
CREATE FUNCTION ingest.try_int(t text) RETURNS integer LANGUAGE sql IMMUTABLE AS
  $$ SELECT CASE WHEN pg_input_is_valid(t, 'integer') THEN t::integer END $$;
CREATE FUNCTION ingest.try_bigint(t text) RETURNS bigint LANGUAGE sql IMMUTABLE AS
  $$ SELECT CASE WHEN pg_input_is_valid(t, 'bigint') THEN t::bigint END $$;
CREATE FUNCTION ingest.try_numeric(t text) RETURNS numeric LANGUAGE sql IMMUTABLE AS
  $$ SELECT CASE WHEN pg_input_is_valid(t, 'numeric') THEN t::numeric END $$;
CREATE FUNCTION ingest.try_bool(t text) RETURNS boolean LANGUAGE sql IMMUTABLE AS
  $$ SELECT CASE WHEN pg_input_is_valid(t, 'boolean') THEN t::boolean END $$;
CREATE FUNCTION ingest.try_date(t text) RETURNS date LANGUAGE sql STABLE AS
  $$ SELECT CASE WHEN t ~ '^\d{4}-\d{2}-\d{2}$' AND pg_input_is_valid(t, 'date') THEN t::date END $$;
-- Strict UTC ISO-8601 (the contract format), then a real calendar check
CREATE FUNCTION ingest.try_ts(t text) RETURNS timestamptz LANGUAGE sql STABLE AS
  $$ SELECT CASE WHEN t ~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$' AND pg_input_is_valid(t, 'timestamptz')
                 THEN t::timestamptz END $$;

-- Abort the surrounding transaction when a reconciliation invariant does not hold
CREATE FUNCTION ingest.assert_true(ok boolean, message text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  IF ok IS NOT TRUE THEN RAISE EXCEPTION 'ingestion invariant failed: %', message; END IF;
END $$;

-- Order-independent fingerprint of a table (row count + sum of 64-bit row hashes), used to prove that
-- seeds and re-runs leave identical state. Cheap enough for tens of millions of rows.
CREATE FUNCTION ingest.table_fingerprint(p_table regclass) RETURNS text
LANGUAGE plpgsql STABLE AS $$
DECLARE result text;
BEGIN
  EXECUTE format('SELECT count(*) || '':'' || coalesce(sum(hashtextextended(t::text, 0)::numeric), 0) FROM %s t',
                 p_table) INTO result;
  RETURN result;
END $$;

COMMIT;
