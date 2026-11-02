-- V3 native vocabulary and controls. Apply after005. Native execution NOT RUN.

BEGIN;

SET search_path=talentra,public;

INSERT INTO reference_domain (code,description) VALUES ('integration_direction','Version3 integration_direction vocabulary') ON CONFLICT (code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'inbound','v3.integration_direction.inbound',TRUE,1 FROM reference_domain WHERE code='integration_direction' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.integration_direction.inbound','en','inbound') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'outbound','v3.integration_direction.outbound',TRUE,2 FROM reference_domain WHERE code='integration_direction' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.integration_direction.outbound','en','outbound') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_domain (code,description) VALUES ('integration_event_status','Version3 integration_event_status vocabulary') ON CONFLICT (code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'received','v3.integration_event_status.received',TRUE,1 FROM reference_domain WHERE code='integration_event_status' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.integration_event_status.received','en','received') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'processing','v3.integration_event_status.processing',TRUE,2 FROM reference_domain WHERE code='integration_event_status' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.integration_event_status.processing','en','processing') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'applied','v3.integration_event_status.applied',TRUE,3 FROM reference_domain WHERE code='integration_event_status' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.integration_event_status.applied','en','applied') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'quarantined','v3.integration_event_status.quarantined',TRUE,4 FROM reference_domain WHERE code='integration_event_status' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.integration_event_status.quarantined','en','quarantined') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'dead_lettered','v3.integration_event_status.dead_lettered',TRUE,5 FROM reference_domain WHERE code='integration_event_status' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.integration_event_status.dead_lettered','en','dead lettered') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_domain (code,description) VALUES ('delivery_outcome','Version3 delivery_outcome vocabulary') ON CONFLICT (code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'success','v3.delivery_outcome.success',TRUE,1 FROM reference_domain WHERE code='delivery_outcome' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.delivery_outcome.success','en','success') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'retry','v3.delivery_outcome.retry',TRUE,2 FROM reference_domain WHERE code='delivery_outcome' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.delivery_outcome.retry','en','retry') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'permanent_failure','v3.delivery_outcome.permanent_failure',TRUE,3 FROM reference_domain WHERE code='delivery_outcome' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.delivery_outcome.permanent_failure','en','permanent failure') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'cancelled','v3.delivery_outcome.cancelled',TRUE,4 FROM reference_domain WHERE code='delivery_outcome' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.delivery_outcome.cancelled','en','cancelled') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_domain (code,description) VALUES ('erasure_task_status','Version3 erasure_task_status vocabulary') ON CONFLICT (code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'pending','v3.erasure_task_status.pending',TRUE,1 FROM reference_domain WHERE code='erasure_task_status' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.erasure_task_status.pending','en','pending') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'running','v3.erasure_task_status.running',TRUE,2 FROM reference_domain WHERE code='erasure_task_status' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.erasure_task_status.running','en','running') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'completed','v3.erasure_task_status.completed',TRUE,3 FROM reference_domain WHERE code='erasure_task_status' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.erasure_task_status.completed','en','completed') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'failed','v3.erasure_task_status.failed',TRUE,4 FROM reference_domain WHERE code='erasure_task_status' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.erasure_task_status.failed','en','failed') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_value (reference_domain_id,code,label_key,active,sort_order) SELECT id,'blocked','v3.erasure_task_status.blocked',TRUE,5 FROM reference_domain WHERE code='erasure_task_status' ON CONFLICT (reference_domain_id,code) DO NOTHING;

INSERT INTO ui_translation (label_key,language_code,translated_text) VALUES ('v3.erasure_task_status.blocked','en','blocked') ON CONFLICT (label_key,language_code) DO NOTHING;

INSERT INTO reference_field_binding (table_name,column_name,reference_domain_id) SELECT 'integration_contract','direction_reference_value_id',id FROM reference_domain WHERE code='integration_direction' ON CONFLICT (table_name,column_name) DO NOTHING;

CREATE TRIGGER trg_v3_vocabulary_integration_contract BEFORE INSERT OR UPDATE ON integration_contract FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();

INSERT INTO reference_field_binding (table_name,column_name,reference_domain_id) SELECT 'integration_inbox','status_reference_value_id',id FROM reference_domain WHERE code='integration_event_status' ON CONFLICT (table_name,column_name) DO NOTHING;

CREATE TRIGGER trg_v3_vocabulary_integration_inbox BEFORE INSERT OR UPDATE ON integration_inbox FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();

INSERT INTO reference_field_binding (table_name,column_name,reference_domain_id) SELECT 'delivery_attempt','outcome_reference_value_id',id FROM reference_domain WHERE code='delivery_outcome' ON CONFLICT (table_name,column_name) DO NOTHING;

CREATE TRIGGER trg_v3_vocabulary_delivery_attempt BEFORE INSERT OR UPDATE ON delivery_attempt FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();

INSERT INTO reference_field_binding (table_name,column_name,reference_domain_id) SELECT 'erasure_task','status_reference_value_id',id FROM reference_domain WHERE code='erasure_task_status' ON CONFLICT (table_name,column_name) DO NOTHING;

CREATE TRIGGER trg_v3_vocabulary_erasure_task BEFORE INSERT OR UPDATE ON erasure_task FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();

INSERT INTO reference_field_binding (table_name,column_name,reference_domain_id) SELECT 'candidate_verification','outcome_reference_value_id',reference_domain_id FROM reference_field_binding WHERE table_name='verification_record' AND column_name='outcome_reference_value_id' ON CONFLICT (table_name,column_name) DO NOTHING;

CREATE TRIGGER trg_v3_vocabulary_candidate_verification BEFORE INSERT OR UPDATE ON candidate_verification FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();

CREATE TRIGGER trg_v3_immutable_delivery_attempt BEFORE UPDATE OR DELETE ON delivery_attempt FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();

CREATE FUNCTION enforce_v3_revision() RETURNS trigger LANGUAGE plpgsql SET search_path=talentra,pg_catalog AS $$ BEGIN IF NEW.row_version <> OLD.row_version + 1 THEN RAISE EXCEPTION 'BR-070 row_version must advance by exactly one'; END IF; RETURN NEW; END; $$;

CREATE TRIGGER trg_v3_revision_candidate_profile BEFORE UPDATE ON candidate_profile FOR EACH ROW EXECUTE FUNCTION enforce_v3_revision();

CREATE TRIGGER trg_v3_revision_job_requirement BEFORE UPDATE ON job_requirement FOR EACH ROW EXECUTE FUNCTION enforce_v3_revision();

CREATE TRIGGER trg_v3_revision_job_application BEFORE UPDATE ON job_application FOR EACH ROW EXECUTE FUNCTION enforce_v3_revision();

CREATE TRIGGER trg_v3_revision_gig_assignment BEFORE UPDATE ON gig_assignment FOR EACH ROW EXECUTE FUNCTION enforce_v3_revision();

CREATE TRIGGER trg_v3_revision_licence BEFORE UPDATE ON licence FOR EACH ROW EXECUTE FUNCTION enforce_v3_revision();

CREATE TRIGGER trg_v3_revision_user_session BEFORE UPDATE ON user_session FOR EACH ROW EXECUTE FUNCTION enforce_v3_revision();

CREATE TRIGGER trg_v3_revision_subscription_period BEFORE UPDATE ON subscription_period FOR EACH ROW EXECUTE FUNCTION enforce_v3_revision();

CREATE TRIGGER trg_v3_revision_support_ticket BEFORE UPDATE ON support_ticket FOR EACH ROW EXECUTE FUNCTION enforce_v3_revision();

-- Caller must still use WHERE id=:id AND row_version=:expected_version and check one affected row.

-- Worker, adapter identity, lease fencing and erasure completion are trusted runtime contracts.

COMMIT;