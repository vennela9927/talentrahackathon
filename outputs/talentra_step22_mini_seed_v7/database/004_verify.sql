-- Run with: psql -v ON_ERROR_STOP=1 -d talentra_proof -f database/004_verify.sql
SET search_path=talentra,public;
SELECT COUNT(*) AS baseline_tables FROM information_schema.tables
 WHERE table_schema='talentra' AND table_type='BASE TABLE';
SELECT COUNT(*) AS baseline_columns FROM information_schema.columns WHERE table_schema='talentra';
-- Native catalogue export for dictionary comparison (use psql --csv -c ... > metadata.csv).
SELECT table_name,column_name,data_type,is_nullable,character_maximum_length,numeric_precision,numeric_scale
 FROM information_schema.columns WHERE table_schema='talentra' ORDER BY table_name,ordinal_position;
DO $$
BEGIN
 BEGIN UPDATE job_requirement SET positions=0 WHERE id=1;
  RAISE EXCEPTION 'Expected positive-positions check';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN UPDATE licence SET max_device_per_user=0 WHERE id=1;
  RAISE EXCEPTION 'Expected positive-device-limit check';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN UPDATE audit_event SET action_code='tampered' WHERE id=1;
  RAISE EXCEPTION 'Expected append-only rejection';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM NOT LIKE 'BR-025%' THEN RAISE; END IF;
 END;
 BEGIN UPDATE app_user SET status_reference_value_id=(SELECT id FROM reference_value
  WHERE reference_domain_id<>(SELECT reference_domain_id FROM reference_field_binding
    WHERE table_name='app_user' AND column_name='status_reference_value_id') LIMIT 1) WHERE id=1;
  RAISE EXCEPTION 'Expected wrong-domain rejection';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM NOT LIKE 'BR-031%' THEN RAISE; END IF;
 END;
END $$;
SELECT 'Native smoke checks completed; concurrency and NFR cases require the stated separate runs' AS result;
