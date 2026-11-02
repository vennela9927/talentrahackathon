"""Physical PostgreSQL controls and diagrams for the Talentra v2 baseline."""
import html, json, re
from collections import defaultdict
from pathlib import Path

CONTROLS = r'''-- Talentra v2 controls. PostgreSQL18. Load001, then003, then002, then004.
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
 SELECT EXISTS(SELECT1 FROM user_role ur JOIN access_role ar ON ar.id=ur.access_role_id
 WHERE ur.app_user_id=p_actor AND ar.code=p_code AND ur.deleted_at IS NULL AND ar.deleted_at IS NULL);
$$;
CREATE OR REPLACE FUNCTION talentra.current_member(p_actor bigint,p_org bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=talentra,pg_catalog AS $$
 SELECT EXISTS(SELECT1 FROM recruiter_membership m WHERE m.app_user_id=p_actor
 AND m.organisation_id=p_org AND m.deleted_at IS NULL AND m.valid_from<=CURRENT_TIMESTAMP
 AND (m.valid_to IS NULL OR m.valid_to>CURRENT_TIMESTAMP));
$$;
CREATE OR REPLACE FUNCTION talentra.not_blocked(p_actor bigint,p_candidate bigint,p_org bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=talentra,pg_catalog AS $$
 SELECT EXISTS(SELECT1 FROM candidate_profile c WHERE c.id=p_candidate AND c.deleted_at IS NULL
 AND NOT EXISTS(SELECT1 FROM blocking_entry b WHERE b.blocker_app_user_id=c.app_user_id
 AND b.deleted_at IS NULL AND (b.blocked_app_user_id=p_actor OR b.blocked_organisation_id=p_org)));
$$;
CREATE OR REPLACE FUNCTION talentra.consultant_has_job(p_actor bigint,p_job bigint) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=talentra,pg_catalog AS $$
 SELECT EXISTS(SELECT1 FROM sourcing_request sr JOIN reference_value rv ON rv.id=sr.status_reference_value_id
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
  IF v IS NOT NULL AND NOT EXISTS(SELECT1 FROM reference_value
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
  SELECT EXISTS(SELECT1 FROM transition_rule tr WHERE tr.entity_table=TG_TABLE_NAME
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
 PERFORM1 FROM app_user WHERE id=NEW.app_user_id FOR UPDATE;
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
 PERFORM1 FROM app_user WHERE id=NEW.app_user_id FOR UPDATE;
 IF NEW.ended_at IS NULL AND NEW.expires_at>CURRENT_TIMESTAMP AND NEW.deleted_at IS NULL THEN
  IF NOT live_licence OR NOT EXISTS(SELECT1 FROM licence_seat s WHERE s.licence_id=NEW.licence_id
   AND s.app_user_id=NEW.app_user_id AND s.released_at IS NULL AND s.deleted_at IS NULL)
   THEN RAISE EXCEPTION 'Inactive licence or missing active seat'; END IF;
  IF NOT EXISTS(SELECT1 FROM registered_device d WHERE d.id=NEW.registered_device_id
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
 IF actual<>declared OR EXISTS(SELECT1 FROM invoice_line WHERE invoice_id=target_id AND currency_code<>currency)
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

-- RLS principal is supplied by trusted middleware; clients cannot connect as the runtime role.
DO $$ BEGIN
 IF NOT EXISTS(SELECT1 FROM pg_roles WHERE rolname='talentra_runtime') THEN
  CREATE ROLE talentra_runtime NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
 ELSIF EXISTS(SELECT1 FROM pg_roles WHERE rolname='talentra_runtime' AND (rolsuper OR rolbypassrls OR rolcanlogin)) THEN
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
'''

VERIFY=r'''-- Run with: psql -v ON_ERROR_STOP=1 -d talentra_proof -f database/004_verify.sql
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
    WHERE table_name='app_user' AND column_name='status_reference_value_id') LIMIT1) WHERE id=1;
  RAISE EXCEPTION 'Expected wrong-domain rejection';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM NOT LIKE 'BR-031%' THEN RAISE; END IF;
 END;
END $$;
SELECT 'Native smoke checks completed; concurrency and NFR cases require the stated separate runs' AS result;
'''

def build(out):
 out=Path(out);cat=json.loads((out/'evidence'/'catalogue_v2.json').read_text(encoding='utf-8'))
 sample=json.loads((out/'evidence'/'sample_data_v2.json').read_text(encoding='utf-8'))
 # Normalize SQL token spacing from compact static templates before writing.
 controls=CONTROLS.replace('SELECT1','SELECT 1').replace('PERFORM1','PERFORM 1').replace('LIMIT1','LIMIT 1')
 tables=sorted({a['table'] for a in cat['attributes'] if a['column'].endswith('_reference_value_id') and a['table']!='transition_rule'})
 extra=[]
 for table in tables:extra.append(f'CREATE TRIGGER trg_domain_{table} BEFORE INSERT OR UPDATE ON "{table}" FOR EACH ROW EXECUTE FUNCTION enforce_reference_domain();')
 life_tables=sorted({r['entity_table'] for r in sample['transition_rule']})
 for table in life_tables:extra.append(f'CREATE TRIGGER trg_state_{table} BEFORE UPDATE OF status_reference_value_id ON "{table}" FOR EACH ROW EXECUTE FUNCTION enforce_state_edge();')
 for e in cat['entities']:
  if e['deletion'].startswith('Append-only'):
   extra.append(f'CREATE TRIGGER trg_immutable_{e["table"]} BEFORE UPDATE OR DELETE ON "{e["table"]}" FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();')
 # Triggers are created after functions but before grants/commit.
 controls=controls.replace('-- RLS principal is supplied', '\n'.join(extra)+'\n\n-- RLS principal is supplied')
 (out/'database'/'002_controls.sql').write_bytes(controls.encode('utf-8'))
 (out/'database'/'004_verify.sql').write_bytes(VERIFY.replace('SELECT1','SELECT 1').replace('LIMIT1','LIMIT 1').encode('utf-8'))
 (out/'database'/'900_rollback.sql').write_text('-- DESTRUCTIVE: dedicated disposable proof database only. Review the target before execution.\n-- No automatic production rollback is supplied.\nBEGIN;\nDROP SCHEMA talentra CASCADE;\nCOMMIT;\n',encoding='utf-8')
 (out/'database'/'RUN_ORDER.md').write_text('''# Native PostgreSQL checkpoint

Use an empty, dedicated PostgreSQL18 database and an owner allowed to create the btree_gist extension and a NOLOGIN runtime role. No existing database is targeted automatically.

    psql -v ON_ERROR_STOP=1 -d talentra_proof -f database/001_baseline.sql
    psql -v ON_ERROR_STOP=1 -d talentra_proof -f database/003_seed.sql
    psql -v ON_ERROR_STOP=1 -d talentra_proof -f database/002_controls.sql
    psql -v ON_ERROR_STOP=1 -d talentra_proof -f database/004_verify.sql

The seed precedes enforcement triggers so historical snapshots can load with deferred foreign keys. It is not a mechanism for the application to bypass controls. Only the database owner performs this bootstrap. Native smoke tests do not replace two-connection race tests, detailed service guard tests or target-volume NFR tests.

Runtime identity is a trusted-middleware contract. End users do not receive database credentials or permission to choose the authenticated principal. Current direct runtime grants expose scoped job requirements only. Candidate PII, credentials, ledger and audit tables are not directly granted to that role. Full purpose-gated API implementation is later lifecycle work.

000/001 naming represents the initial baseline rather than an ALTER of a pre-existing production database. Migration checksums are recorded in the Excel baseline register. 900_rollback.sql is explicitly destructive and is never executed by the generator.

Concurrency recipes:

- Seats: session A holds the licence row lock and allocates the final seat. Session B attempts another seat; after A commits, B must reject.
- Login: use two connections for one user/active licence at the final device allowance. Only one new active session may commit.
- Wallet: two debits individually within balance but jointly exceeding it. Only one may commit; no negative balance.
- Refund: concurrent pending refunds jointly exceeding captured value. One must reject while the original payment lock serializes the checks.
- Gig/subscription: intersecting same-owner windows must conflict. Adjacent half-open windows must both commit.

Target-volume test IDs and unresolved owner decisions are in the step20 NFR register. Until native execution, concurrency and required NFR evidence pass, G3 stays open.
''',encoding='utf-8')
 introspection=r'''"""Compare dictionary_v2.json with a psql --csv information_schema export."""
import csv,json,sys
from pathlib import Path
if len(sys.argv)!=3:raise SystemExit('Usage: python check_dictionary.py dictionary_v2.json metadata.csv')
dictionary=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
rows=list(csv.DictReader(Path(sys.argv[2]).read_text(encoding='utf-8-sig').splitlines()))
actual={(r['table_name'],r['column_name']):r for r in rows}
expected={(a['table'],a['column']):a for a in dictionary};issues=[]
for key,a in expected.items():
 r=actual.get(key)
 if r is None:issues.append([*key,'Missing physical column']);continue
 kind=a['type'].split('(')[0]
 types={'varchar':'character varying','char':'character','timestamptz':'timestamp with time zone','integer':'integer','bigint':'bigint','smallint':'smallint','boolean':'boolean','date':'date','text':'text','numeric':'numeric'}
 if r['data_type']!=types[kind]:issues.append([*key,'Type differs'])
 if (r['is_nullable']=='YES')!=a['nullable']:issues.append([*key,'Nullability differs'])
 if kind in ['varchar','char'] and r.get('character_maximum_length')!=a['type'].split('(')[1][:-1]:issues.append([*key,'Length differs'])
 if kind=='numeric':
  precision,scale=a['type'].split('(')[1][:-1].split(',')
  if r.get('numeric_precision')!=precision or r.get('numeric_scale')!=scale:issues.append([*key,'Precision or scale differs'])
for key in actual.keys()-expected.keys():issues.append([*key,'Unexpected physical column'])
print(json.dumps({'mismatches':issues,'expected_columns':len(expected),'actual_columns':len(actual)},indent=2))
raise SystemExit(bool(issues))
'''
 (out/'database'/'check_dictionary.py').write_text(introspection,encoding='utf-8')
 (out/'database'/'export_metadata.sql').write_text("SELECT table_name,column_name,data_type,is_nullable,character_maximum_length,numeric_precision,numeric_scale FROM information_schema.columns WHERE table_schema='talentra' ORDER BY table_name,ordinal_position;\n",encoding='utf-8')
 # Detailed ER source retains every non-audit FK, including newly refined entities.
 lines=['erDiagram']
 for e in cat['entities']:
  lines.append('  '+e['table']+' {')
  for a in [a for a in cat['attributes'] if a['table']==e['table'] and a['column'] not in ['created_at','updated_at','created_by','updated_by','deleted_at']]:
   kind=re.sub(r'[^a-zA-Z0-9_]','_',a['type']);lines.append('    '+kind+' '+a['column']+(' PK' if a['column']=='id' else ''))
  lines.append('  }')
 for r in cat['relationships']:
  if r['column'] in ['created_by','updated_by']:continue
  left='|o' if r['optional'] else '||'
  right='o|' if r['parent_to_child']=='0..1' else 'o{'
  lines.append('  '+r['parent']+' '+left+'--'+right+' '+r['child']+' : "'+r['column']+'"')
 (out/'diagrams'/'er_model.mmd').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 modules=defaultdict(list)
 for e in cat['entities']:modules[e['module']].append(e)
 colors=['#e9eff7','#e8f2ee','#f9eedf'];width=1500;boxw=440;gap=40;rowh=310
 height=((len(modules)+2)//3)*rowh+140
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#f4f6f9"/><style>text{{font-family:Arial,sans-serif;fill:#172b47}}.title{{font-size:30px;font-weight:700}}.module{{font-size:20px;font-weight:700}}.table{{font-size:15px}}.note{{font-size:15px;fill:#5c6d84}}</style><text class="title" x="40" y="48">Talentra baseline ER v2</text><text class="note" x="40" y="80">110 entities. Module overview; exact cardinalities and field-level links are in the detailed ER source and step21 workbook.</text>']
 for i,(module,es) in enumerate(modules.items()):
  x=40+(i%3)*(boxw+gap);y=110+(i//3)*rowh;svg.append(f'<rect x="{x}" y="{y}" width="{boxw}" height="280" rx="10" fill="{colors[i%3]}" stroke="#ccd6e4"/><text class="module" x="{x+18}" y="{y+32}">{html.escape(module.title())} ({len(es)})</text>')
  for j,e in enumerate(es):
   xx=x+18+(j//12)*210;yy=y+58+(j%12)*17
   label=e['table'];svg.append(f'<text class="table" x="{xx}" y="{yy}">{html.escape(label[:27])}</text>')
 svg.append('</svg>');(out/'diagrams'/'er_overview.svg').write_text(''.join(svg),encoding='utf-8')
 # Logical link diagram for the core workflow, with explicit cardinalities.
 core=r'''<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="660" viewBox="0 0 1440 660"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="none" stroke="#5475a1"/></marker></defs><rect width="100%" height="100%" fill="#f4f6f9"/><style>text{font-family:Arial;fill:#14243b;font-size:17px}.n{fill:#fff;stroke:#9eb2cd;stroke-width:1.5;rx:8}.edge{fill:none;stroke:#5475a1;stroke-width:2;marker-end:url(#arrow)}.title{font-size:28px;font-weight:bold}.label{font-size:14px;fill:#58708c}</style><text class="title" x="40" y="45">Talentra core relationships</text><rect class="n" x="40" y="110" width="220" height="70"/><text x="68" y="151">app_user</text><rect class="n" x="360" y="110" width="230" height="70"/><text x="381" y="151">candidate_profile</text><rect class="n" x="720" y="110" width="230" height="70"/><text x="743" y="151">job_application</text><rect class="n" x="1100" y="110" width="260" height="70"/><text x="1127" y="151">job_requirement</text><path class="edge" d="M260 145 H360"/><text class="label" x="280" y="130">1 : 0..1</text><path class="edge" d="M590 145 H720"/><text class="label" x="620" y="130">1 : N</text><path class="edge" d="M1100 145 H950"/><text class="label" x="995" y="130">1 : N</text><rect class="n" x="1100" y="310" width="260" height="70"/><text x="1145" y="350">organisation</text><path class="edge" d="M1230 310 V180"/><text class="label" x="1242" y="255">1 : N</text><rect class="n" x="40" y="310" width="220" height="70"/><text x="65" y="350">gig_worker_profile</text><path class="edge" d="M150 180 V310"/><text class="label" x="165" y="255">1 : 0..1</text><rect class="n" x="360" y="310" width="230" height="70"/><text x="390" y="350">gig_application</text><path class="edge" d="M260 345 H360"/><text class="label" x="280" y="330">1 : N</text><rect class="n" x="720" y="310" width="230" height="70"/><text x="761" y="350">gig_request</text><path class="edge" d="M720 345 H590"/><text class="label" x="620" y="330">1 : N</text><rect class="n" x="360" y="510" width="230" height="70"/><text x="388" y="551">gig_assignment</text><path class="edge" d="M475 380 V510"/><text class="label" x="490" y="458">1 : 0..1</text><rect class="n" x="720" y="510" width="230" height="70"/><text x="760" y="551">outbox_event</text><path class="edge" d="M590 545 H720"/><text class="label" x="610" y="530">1 : N intent</text><text class="label" x="40" y="630">Gig fulfilment and earnings remain external. Audit actor FKs are omitted here; every FK appears in the detailed model.</text></svg>'''
 (out/'diagrams'/'er_core.svg').write_text(core,encoding='utf-8')

if __name__=='__main__':
 import sys
 build(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'outputs'/'talentra_steps_01_21')
