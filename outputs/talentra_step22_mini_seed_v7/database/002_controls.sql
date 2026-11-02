-- Talentra v2 controls. PostgreSQL18. Load001, then003, then002, then004.
-- This script is a native-engine checkpoint, not a claim that it has been run.
BEGIN;
SET search_path=talentra,public;
CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;

CREATE OR REPLACE FUNCTION talentra.lookup_id(p_table text,p_column text,p_code text)
RETURNS bigint LANGUAGE sql STABLE SECURITY DEFINER SET search_path=talentra,pg_catalog AS $$
 SELECT rv.id FROM reference_field_binding b
 JOIN reference_value rv ON rv.reference_domain_id=b.reference_domain_id
 WHERE b.table_name=p_table AND b.column_name=p_column AND rv.code=p_code
 AND rv.active AND rv.deleted_at IS NULL;
$$;
CREATE OR REPLACE FUNCTION talentra.actor_id() RETURNS bigint
LANGUAGE sql STABLE SET search_path=talentra,pg_catalog AS $$
 SELECT NULLIF(current_setting('talentra.actor_id',true),'')::bigint;
$$;
-- actor_id is set only by authenticated, trusted middleware. End users receive no DB credentials.
CREATE OR REPLACE FUNCTION talentra.has_role(p_actor bigint,p_code text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=talentra,pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM user_role ur JOIN access_role ar ON ar.id=ur.access_role_id
 WHERE ur.app_user_id=p_actor AND ar.code=p_code AND ur.deleted_at IS NULL AND ar.deleted_at IS NULL);
$$;
CREATE OR REPLACE FUNCTION talentra.current_member(p_actor bigint,p_org bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=talentra,pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM recruiter_membership m WHERE m.app_user_id=p_actor
 AND m.organisation_id=p_org AND m.deleted_at IS NULL AND m.valid_from<=CURRENT_TIMESTAMP
 AND (m.valid_to IS NULL OR m.valid_to>CURRENT_TIMESTAMP));
$$;
CREATE OR REPLACE FUNCTION talentra.not_blocked(p_actor bigint,p_candidate bigint,p_org bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=talentra,pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM candidate_profile c WHERE c.id=p_candidate AND c.deleted_at IS NULL
 AND NOT EXISTS(SELECT 1 FROM blocking_entry b WHERE b.blocker_app_user_id=c.app_user_id
 AND b.deleted_at IS NULL AND (b.blocked_app_user_id=p_actor OR b.blocked_organisation_id=p_org)));
$$;
CREATE OR REPLACE FUNCTION talentra.consultant_has_job(p_actor bigint,p_job bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=talentra,pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM sourcing_request sr JOIN reference_value rv ON rv.id=sr.status_reference_value_id
 WHERE sr.job_requirement_id=p_job AND sr.consultant_app_user_id=p_actor
 AND rv.code='accepted' AND sr.deleted_at IS NULL);
$$;
CREATE OR REPLACE FUNCTION talentra.enforce_reference_domain() RETURNS trigger
LANGUAGE plpgsql SET search_path=talentra,pg_catalog AS $$
DECLARE b record; v bigint;
BEGIN
 FOR b IN SELECT column_name,reference_domain_id FROM reference_field_binding
          WHERE table_name=TG_TABLE_NAME AND deleted_at IS NULL LOOP
  v:=NULLIF(to_jsonb(NEW)->>b.column_name,'')::bigint;
  IF v IS NOT NULL AND NOT EXISTS(SELECT 1 FROM reference_value
       WHERE id=v AND reference_domain_id=b.reference_domain_id AND active AND deleted_at IS NULL)
  THEN RAISE EXCEPTION 'BR-031 wrong or inactive vocabulary for %.%',TG_TABLE_NAME,b.column_name; END IF;
 END LOOP;
 RETURN NEW;
END; $$;

CREATE OR REPLACE FUNCTION talentra.enforce_state_edge() RETURNS trigger
LANGUAGE plpgsql SET search_path=talentra,pg_catalog AS $$
DECLARE permitted boolean;
BEGIN
 IF NEW.status_reference_value_id IS DISTINCT FROM OLD.status_reference_value_id THEN
  SELECT EXISTS(SELECT 1 FROM transition_rule tr WHERE tr.entity_table=TG_TABLE_NAME
    AND tr.from_reference_value_id=OLD.status_reference_value_id
    AND tr.to_reference_value_id=NEW.status_reference_value_id AND tr.deleted_at IS NULL
    AND has_role(actor_id(),tr.actor_role_code)) INTO permitted;
  IF NOT permitted THEN RAISE EXCEPTION 'Illegal state edge or actor for %',TG_TABLE_NAME; END IF;
  -- Detailed guard_code pre/postconditions belong to the authenticated service transaction.
  -- A permitted edge alone never substitutes for that guard contract.
 END IF;
 RETURN NEW;
END; $$;

CREATE OR REPLACE FUNCTION talentra.reject_history_mutation() RETURNS trigger
LANGUAGE plpgsql SET search_path=talentra,pg_catalog AS $$
BEGIN RAISE EXCEPTION 'BR-025 append-only: % %',TG_TABLE_NAME,TG_OP; END; $$;

CREATE OR REPLACE FUNCTION talentra.reserve_gig_window() RETURNS trigger
LANGUAGE plpgsql SET search_path=talentra,pg_catalog AS $$
DECLARE state_code text;
BEGIN
 SELECT code INTO STRICT state_code FROM reference_value WHERE id=NEW.status_reference_value_id;
 NEW.blocks_window:=state_code IN ('pending_handoff','active');
 IF NEW.end_at<=NEW.start_at THEN RAISE EXCEPTION 'Gig window must have positive duration'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER trg_gig_reservation BEFORE INSERT OR UPDATE ON gig_assignment
FOR EACH ROW EXECUTE FUNCTION reserve_gig_window();
ALTER TABLE gig_assignment ADD CONSTRAINT ex_gig_worker_window
 EXCLUDE USING gist(gig_worker_profile_id WITH =,tstzrange(start_at,end_at,'[)') WITH &&)
 WHERE(blocks_window AND deleted_at IS NULL);
ALTER TABLE subscription_period ADD CONSTRAINT ck_subscription_positive_window CHECK(end_at>start_at);
ALTER TABLE subscription_period ADD CONSTRAINT ex_licence_subscription_window
 EXCLUDE USING gist(licence_id WITH =,tstzrange(start_at,end_at,'[)') WITH &&)
 WHERE(deleted_at IS NULL);

CREATE OR REPLACE FUNCTION talentra.enforce_seat_capacity() RETURNS trigger
LANGUAGE plpgsql SET search_path=talentra,pg_catalog AS $$
DECLARE cap integer; active_count integer;
BEGIN
 SELECT max_user_count INTO STRICT cap FROM licence WHERE id=NEW.licence_id FOR UPDATE;
 PERFORM 1 FROM app_user WHERE id=NEW.app_user_id FOR UPDATE;
 IF NEW.released_at IS NULL AND NEW.deleted_at IS NULL THEN
  SELECT COUNT(*) INTO active_count FROM licence_seat WHERE licence_id=NEW.licence_id
   AND released_at IS NULL AND deleted_at IS NULL AND id<>NEW.id;
  IF active_count>=cap THEN RAISE EXCEPTION 'BR-021 seat limit'; END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER trg_seat_capacity BEFORE INSERT OR UPDATE ON licence_seat
 FOR EACH ROW EXECUTE FUNCTION enforce_seat_capacity();

CREATE OR REPLACE FUNCTION talentra.enforce_session_capacity() RETURNS trigger
LANGUAGE plpgsql SET search_path=talentra,pg_catalog AS $$
DECLARE cap integer; active_count integer; live_licence boolean;
BEGIN
 SELECT l.max_device_per_user,(rv.code='active') INTO STRICT cap,live_licence
 FROM licence l JOIN reference_value rv ON rv.id=l.status_reference_value_id
 WHERE l.id=NEW.licence_id AND l.deleted_at IS NULL FOR UPDATE OF l;
 PERFORM 1 FROM app_user WHERE id=NEW.app_user_id FOR UPDATE;
 IF NEW.ended_at IS NULL AND NEW.expires_at>CURRENT_TIMESTAMP AND NEW.deleted_at IS NULL THEN
  IF NOT live_licence OR NOT EXISTS(SELECT 1 FROM licence_seat s WHERE s.licence_id=NEW.licence_id
   AND s.app_user_id=NEW.app_user_id AND s.released_at IS NULL AND s.deleted_at IS NULL)
   THEN RAISE EXCEPTION 'Inactive licence or missing active seat'; END IF;
  IF NOT EXISTS(SELECT 1 FROM registered_device d WHERE d.id=NEW.registered_device_id
   AND d.app_user_id=NEW.app_user_id AND d.revoked_at IS NULL AND d.deleted_at IS NULL)
   THEN RAISE EXCEPTION 'BR-023 device not owned/active'; END IF;
  SELECT COUNT(*) INTO active_count FROM user_session s WHERE s.app_user_id=NEW.app_user_id
   AND s.ended_at IS NULL AND s.expires_at>CURRENT_TIMESTAMP AND s.deleted_at IS NULL AND s.id<>NEW.id;
  IF active_count>=cap THEN RAISE EXCEPTION 'BR-022 active session limit'; END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER trg_session_capacity BEFORE INSERT OR UPDATE ON user_session
 FOR EACH ROW EXECUTE FUNCTION enforce_session_capacity();

CREATE OR REPLACE FUNCTION talentra.enforce_ledger_write() RETURNS trigger
LANGUAGE plpgsql SET search_path=talentra,pg_catalog AS $$
DECLARE balance numeric(18,2); wallet_currency text; kind text; original wallet_ledger_entry%ROWTYPE;
BEGIN
 SELECT currency_code INTO STRICT wallet_currency FROM wallet WHERE id=NEW.wallet_id FOR UPDATE;
 IF wallet_currency<>NEW.currency_code THEN RAISE EXCEPTION 'BR-050 currency mismatch'; END IF;
 SELECT code INTO STRICT kind FROM reference_value WHERE id=NEW.entry_type_reference_value_id;
 IF (kind='debit' AND NEW.signed_amount>=0) OR (kind='recharge' AND NEW.signed_amount<=0)
 THEN RAISE EXCEPTION 'BR-058 invalid credit/debit sign'; END IF;
 IF NEW.original_wallet_ledger_entry_id IS NOT NULL THEN
  SELECT * INTO STRICT original FROM wallet_ledger_entry WHERE id=NEW.original_wallet_ledger_entry_id;
  IF original.wallet_id<>NEW.wallet_id OR original.currency_code<>NEW.currency_code
    OR NEW.signed_amount<>-original.signed_amount THEN RAISE EXCEPTION 'BR-051 invalid reversal'; END IF;
 END IF;
 SELECT COALESCE(SUM(signed_amount),0) INTO balance FROM wallet_ledger_entry WHERE wallet_id=NEW.wallet_id;
 IF balance+NEW.signed_amount<0 THEN RAISE EXCEPTION 'BR-027 insufficient funds'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER trg_ledger_write BEFORE INSERT ON wallet_ledger_entry
 FOR EACH ROW EXECUTE FUNCTION enforce_ledger_write();
CREATE UNIQUE INDEX uq_wallet_ledger_entry_reversal ON wallet_ledger_entry(original_wallet_ledger_entry_id)
 WHERE original_wallet_ledger_entry_id IS NOT NULL;

CREATE OR REPLACE FUNCTION talentra.enforce_refund_limit() RETURNS trigger
LANGUAGE plpgsql SET search_path=talentra,pg_catalog AS $$
DECLARE captured payment_event%ROWTYPE; previous numeric(18,2); captured_status text; new_status text;
BEGIN
 SELECT * INTO STRICT captured FROM payment_event WHERE id=NEW.original_payment_event_id FOR UPDATE;
 SELECT code INTO captured_status FROM reference_value WHERE id=captured.status_reference_value_id;
 SELECT code INTO new_status FROM reference_value WHERE id=NEW.status_reference_value_id;
 IF captured.payment_order_id<>NEW.payment_order_id OR captured.currency_code<>NEW.currency_code
 OR captured_status<>'succeeded' THEN RAISE EXCEPTION 'BR-056 invalid captured payment/currency'; END IF;
 SELECT COALESCE(SUM(r.amount),0) INTO previous FROM refund r JOIN reference_value rv ON rv.id=r.status_reference_value_id
 WHERE r.original_payment_event_id=captured.id AND r.id<>NEW.id AND rv.code IN ('pending','succeeded') AND r.deleted_at IS NULL;
 IF new_status IN ('pending','succeeded') AND previous+NEW.amount>captured.amount
 THEN RAISE EXCEPTION 'BR-028 refund exceeds capture'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER trg_refund_limit BEFORE INSERT OR UPDATE ON refund
 FOR EACH ROW EXECUTE FUNCTION enforce_refund_limit();

CREATE OR REPLACE FUNCTION talentra.check_invoice_total() RETURNS trigger
LANGUAGE plpgsql SET search_path=talentra,pg_catalog AS $$
DECLARE target_id bigint; declared numeric(18,2); actual numeric(18,2); currency text;
BEGIN
 IF TG_TABLE_NAME='invoice' THEN target_id:=COALESCE(NEW.id,OLD.id);
 ELSE target_id:=COALESCE(NEW.invoice_id,OLD.invoice_id); END IF;
 SELECT total_amount,currency_code INTO declared,currency FROM invoice WHERE id=target_id;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT COALESCE(SUM(line_amount),0) INTO actual FROM invoice_line WHERE invoice_id=target_id;
 IF actual<>declared OR EXISTS(SELECT 1 FROM invoice_line WHERE invoice_id=target_id AND currency_code<>currency)
 THEN RAISE EXCEPTION 'BR-029 invoice does not reconcile'; END IF;
 RETURN NULL;
END; $$;
CREATE CONSTRAINT TRIGGER trg_invoice_total AFTER INSERT OR UPDATE ON invoice
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_invoice_total();
CREATE CONSTRAINT TRIGGER trg_invoice_line_total AFTER INSERT OR UPDATE OR DELETE ON invoice_line
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_invoice_total();

CREATE OR REPLACE FUNCTION talentra.check_sourcing_request() RETURNS trigger
LANGUAGE plpgsql SET search_path=talentra,pg_catalog AS $$
DECLARE opened boolean;
BEGIN
 SELECT open_to_consultant INTO STRICT opened FROM job_requirement WHERE id=NEW.job_requirement_id FOR UPDATE;
 IF NOT opened THEN RAISE EXCEPTION 'BR-016 job is closed to consultants'; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER trg_sourcing_open BEFORE INSERT OR UPDATE ON sourcing_request
 FOR EACH ROW EXECUTE FUNCTION check_sourcing_request();

CREATE TRIGGER trg_domain_account BEFORE INSERT OR UPDATE ON "account" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_app_user BEFORE INSERT OR UPDATE ON "app_user" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_application_status_event BEFORE INSERT OR UPDATE ON "application_status_event" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_audit_event BEFORE INSERT OR UPDATE ON "audit_event" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_candidate_activity BEFORE INSERT OR UPDATE ON "candidate_activity" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_candidate_bookmark BEFORE INSERT OR UPDATE ON "candidate_bookmark" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_candidate_language BEFORE INSERT OR UPDATE ON "candidate_language" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_candidate_profile BEFORE INSERT OR UPDATE ON "candidate_profile" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_candidate_skill BEFORE INSERT OR UPDATE ON "candidate_skill" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_community_post BEFORE INSERT OR UPDATE ON "community_post" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_consent_record BEFORE INSERT OR UPDATE ON "consent_record" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_course_enrolment BEFORE INSERT OR UPDATE ON "course_enrolment" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_faq BEFORE INSERT OR UPDATE ON "faq" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_gig_application BEFORE INSERT OR UPDATE ON "gig_application" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_gig_assignment BEFORE INSERT OR UPDATE ON "gig_assignment" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_gig_request BEFORE INSERT OR UPDATE ON "gig_request" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_gig_service BEFORE INSERT OR UPDATE ON "gig_service" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_gig_worker_list_entry BEFORE INSERT OR UPDATE ON "gig_worker_list_entry" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_gig_worker_profile BEFORE INSERT OR UPDATE ON "gig_worker_profile" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_integration_event BEFORE INSERT OR UPDATE ON "integration_event" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_interview BEFORE INSERT OR UPDATE ON "interview" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_job_application BEFORE INSERT OR UPDATE ON "job_application" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_job_offer BEFORE INSERT OR UPDATE ON "job_offer" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_job_question BEFORE INSERT OR UPDATE ON "job_question" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_job_requirement BEFORE INSERT OR UPDATE ON "job_requirement" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_licence BEFORE INSERT OR UPDATE ON "licence" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_login_attempt BEFORE INSERT OR UPDATE ON "login_attempt" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_notification BEFORE INSERT OR UPDATE ON "notification" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_notification_delivery BEFORE INSERT OR UPDATE ON "notification_delivery" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_notification_preference BEFORE INSERT OR UPDATE ON "notification_preference" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_organisation BEFORE INSERT OR UPDATE ON "organisation" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_organisation_identifier BEFORE INSERT OR UPDATE ON "organisation_identifier" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_outreach_batch BEFORE INSERT OR UPDATE ON "outreach_batch" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_outreach_recipient BEFORE INSERT OR UPDATE ON "outreach_recipient" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_payment_event BEFORE INSERT OR UPDATE ON "payment_event" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_payment_order BEFORE INSERT OR UPDATE ON "payment_order" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_plan_entitlement BEFORE INSERT OR UPDATE ON "plan_entitlement" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_post_reaction BEFORE INSERT OR UPDATE ON "post_reaction" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_referral_event BEFORE INSERT OR UPDATE ON "referral_event" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_refund BEFORE INSERT OR UPDATE ON "refund" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_social_share_event BEFORE INSERT OR UPDATE ON "social_share_event" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_sourcing_decision BEFORE INSERT OR UPDATE ON "sourcing_decision" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_sourcing_request BEFORE INSERT OR UPDATE ON "sourcing_request" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_subscription_period BEFORE INSERT OR UPDATE ON "subscription_period" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_support_ticket BEFORE INSERT OR UPDATE ON "support_ticket" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_user_preference BEFORE INSERT OR UPDATE ON "user_preference" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_verification_record BEFORE INSERT OR UPDATE ON "verification_record" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_domain_wallet_ledger_entry BEFORE INSERT OR UPDATE ON "wallet_ledger_entry" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();
CREATE TRIGGER trg_state_candidate_profile BEFORE UPDATE OF status_reference_value_id ON "candidate_profile" FOR EACH ROW EXECUTE FUNCTION enforce_state_edge();
CREATE TRIGGER trg_state_gig_application BEFORE UPDATE OF status_reference_value_id ON "gig_application" FOR EACH ROW EXECUTE FUNCTION enforce_state_edge();
CREATE TRIGGER trg_state_gig_assignment BEFORE UPDATE OF status_reference_value_id ON "gig_assignment" FOR EACH ROW EXECUTE FUNCTION enforce_state_edge();
CREATE TRIGGER trg_state_job_application BEFORE UPDATE OF status_reference_value_id ON "job_application" FOR EACH ROW EXECUTE FUNCTION enforce_state_edge();
CREATE TRIGGER trg_state_job_requirement BEFORE UPDATE OF status_reference_value_id ON "job_requirement" FOR EACH ROW EXECUTE FUNCTION enforce_state_edge();
CREATE TRIGGER trg_state_payment_order BEFORE UPDATE OF status_reference_value_id ON "payment_order" FOR EACH ROW EXECUTE FUNCTION enforce_state_edge();
CREATE TRIGGER trg_state_sourcing_request BEFORE UPDATE OF status_reference_value_id ON "sourcing_request" FOR EACH ROW EXECUTE FUNCTION enforce_state_edge();
CREATE TRIGGER trg_state_subscription_period BEFORE UPDATE OF status_reference_value_id ON "subscription_period" FOR EACH ROW EXECUTE FUNCTION enforce_state_edge();
CREATE TRIGGER trg_state_support_ticket BEFORE UPDATE OF status_reference_value_id ON "support_ticket" FOR EACH ROW EXECUTE FUNCTION enforce_state_edge();
CREATE TRIGGER trg_immutable_consent_record BEFORE UPDATE OR DELETE ON "consent_record" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_audit_event BEFORE UPDATE OR DELETE ON "audit_event" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_system_error BEFORE UPDATE OR DELETE ON "system_error" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_integration_event BEFORE UPDATE OR DELETE ON "integration_event" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_profile_view_event BEFORE UPDATE OR DELETE ON "profile_view_event" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_candidate_activity BEFORE UPDATE OR DELETE ON "candidate_activity" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_application_status_event BEFORE UPDATE OR DELETE ON "application_status_event" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_gig_earnings_snapshot BEFORE UPDATE OR DELETE ON "gig_earnings_snapshot" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_login_attempt BEFORE UPDATE OR DELETE ON "login_attempt" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_revocation_event BEFORE UPDATE OR DELETE ON "revocation_event" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_payment_event BEFORE UPDATE OR DELETE ON "payment_event" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_wallet_ledger_entry BEFORE UPDATE OR DELETE ON "wallet_ledger_entry" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_profile_download_event BEFORE UPDATE OR DELETE ON "profile_download_event" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_notification_delivery BEFORE UPDATE OR DELETE ON "notification_delivery" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_referral_event BEFORE UPDATE OR DELETE ON "referral_event" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
CREATE TRIGGER trg_immutable_social_share_event BEFORE UPDATE OR DELETE ON "social_share_event" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();

-- RLS principal is supplied by trusted middleware; clients cannot connect as the runtime role.
DO $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='talentra_runtime') THEN
  CREATE ROLE talentra_runtime NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
 ELSIF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='talentra_runtime' AND (rolsuper OR rolbypassrls OR rolcanlogin)) THEN
  RAISE EXCEPTION 'Existing talentra_runtime role is unsafe; use a dedicated proof instance';
 END IF;
END $$;
REVOKE ALL ON SCHEMA talentra FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA talentra FROM PUBLIC;
GRANT USAGE ON SCHEMA talentra TO talentra_runtime;
ALTER TABLE job_requirement ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_requirement FORCE ROW LEVEL SECURITY;
CREATE POLICY job_scope ON job_requirement FOR SELECT TO talentra_runtime USING (
 deleted_at IS NULL AND (
  (has_role(actor_id(),'recruiter') AND current_member(actor_id(),organisation_id))
  OR (NOT has_role(actor_id(),'recruiter') AND NOT has_role(actor_id(),'consultant')
      AND (status_reference_value_id=lookup_id('job_requirement','status_reference_value_id','published')
           OR current_member(actor_id(),organisation_id)))
  OR (has_role(actor_id(),'consultant') AND open_to_consultant AND consultant_has_job(actor_id(),id))));
GRANT SELECT ON job_requirement TO talentra_runtime;
-- PII tables and credentials retain no direct runtime grant. Purpose-gated service interfaces are later work.
REVOKE ALL ON credential,candidate_contact,audit_event,wallet_ledger_entry,payment_event FROM talentra_runtime;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA talentra FROM PUBLIC;
GRANT EXECUTE ON FUNCTION actor_id(),has_role(bigint,text),current_member(bigint,bigint),lookup_id(text,text,text),consultant_has_job(bigint,bigint)
 TO talentra_runtime;
COMMIT;
