"""Inbound contracts used by the Step 25 pipeline.

legacy.job_requirement.v1 is the released Step 22 contract (CON-018), used unchanged.
The other three are added by Phase 4 change CHG-22-01: Step 22 maps no inbound source to app_user,
job_application or application_status_event, so candidate_profile.app_user_id and every application
had no way in. Each field states its native target and transform, completing the Step 22 mapping.
"""
import hashlib
import json
from pathlib import Path

from common import BASELINE

ENVELOPE = [
    ("event_id", "string", True, "TRANSPORT_ONLY", "Producer delivery id; inbox event key when quarantined"),
    ("correlation_id", "string", True, "TRANSPORT_ONLY", "Trace key"),
    ("schema_version", "integer", True, "integration_contract.schema_version", "Must equal 1 (UNSUPPORTED_VERSION)"),
    ("occurred_at", "date-time", True, "created_at of a new row", "UTC ISO-8601; not in the future"),
    ("source_version", "integer", True, "ingest.key_map.source_version", "Monotonic per external_key; lower = STALE_VERSION"),
    ("external_key", "string", True, "ingest.key_map.external_key", "Source business key; translated to a native id"),
]

CONTRACTS = {
    "legacy.candidate_account.v1": {
        "id": "CON-033", "entity": "candidate", "file": "candidates.csv.gz", "source_code": "legacy_ats.candidates",
        "owner": "Migration data owner", "fields": ENVELOPE + [
            ("email", "string", True, "app_user.email", "Lower-cased; valid address; unique across users"),
            ("person_name", "string", True, "app_user.person_name", "As supplied; synthetic in test data"),
            ("preferred_language", "string", True, "app_user.preferred_language", "en | hi | ta (NFR-013)"),
            ("city_id", "integer|null", False, "candidate_profile.city_id", "Must exist in city"),
            ("headline", "string|null", False, "candidate_profile.headline", "As supplied"),
            ("birth_date", "date|null", False, "candidate_profile.birth_date",
             "Valid date; at least 14 years before occurred_at (proposed rule ING-BR-01)"),
            ("profile_status", "string", True, "candidate_profile.status_reference_value_id",
             "Code in candidate_profile status vocabulary; 'erased' is never accepted inbound"),
            ("content_language", "string", True, "candidate_profile.content_language", "en | hi | ta"),
        ]},
    "legacy.job_requirement.v1": {
        "id": "CON-018", "entity": "job", "file": "jobs.csv.gz", "source_code": "legacy_ats.jobs",
        "owner": "Migration data owner", "released": True},
    "legacy.job_application.v1": {
        "id": "CON-034", "entity": "application", "file": "applications.csv.gz", "source_code": "legacy_ats.applications",
        "owner": "Migration data owner", "fields": ENVELOPE + [
            ("candidate_key", "string", True, "job_application.candidate_profile_id", "Translated via key_map; else UNKNOWN_PARENT"),
            ("job_key", "string", True, "job_application.job_requirement_id", "Translated via key_map; else UNKNOWN_PARENT"),
            ("organisation_key", "integer", True, "TENANT_GUARD", "Must equal the job's organisation; else CROSS_ACCOUNT"),
            ("applied_at", "date-time", True, "job_application.applied_at", "Not before the job was created; not in the future"),
            ("source_channel", "string", True, "TRANSPORT_ONLY", "No native column (MGAP-01); kept in the source file only"),
        ]},
    "legacy.application_status_event.v1": {
        "id": "CON-035", "entity": "status_event", "file": "status_events.csv.gz",
        "source_code": "legacy_ats.status_events", "owner": "Migration data owner", "fields": ENVELOPE + [
            ("application_key", "string", True, "application_status_event.job_application_id", "Translated via key_map"),
            ("organisation_key", "integer", True, "TENANT_GUARD", "Must equal the application's job organisation"),
            ("from_status", "string|null", False, "application_status_event.from_reference_value_id",
             "Must equal the application's status at that point (CHAIN_BREAK); null only for the first event"),
            ("to_status", "string", True, "application_status_event.to_reference_value_id",
             "Edge must exist in transition_rule (ILLEGAL_TRANSITION) for the actor's role (ACTOR_NOT_PERMITTED)"),
            ("actor_type", "string", True, "transition_rule.actor_role_code", "candidate | recruiter"),
            ("actor_key", "string", True, "application_status_event.actor_app_user_id",
             "The application's own candidate, or the organisation's recruiter"),
        ]},
}

LOAD_ORDER = ["legacy.candidate_account.v1", "legacy.job_requirement.v1",
              "legacy.job_application.v1", "legacy.application_status_event.v1"]


def _json_type(kind):
    base = {"string": {"type": "string", "maxLength": 255}, "integer": {"type": "integer", "minimum": 0},
            "date-time": {"type": "string", "format": "date-time"}, "date": {"type": "string", "format": "date"}}
    if kind.endswith("|null"):
        t = dict(base[kind[:-5]])
        t["type"] = [t["type"], "null"]
        return t
    return dict(base[kind])


def schema(key):
    c = CONTRACTS[key]
    if c.get("released"):
        return json.loads((BASELINE / "contracts" / f"{key}.schema.json").read_text(encoding="utf-8"))
    props = {}
    for name, kind, _, target, rule in c["fields"]:
        props[name] = {**_json_type(kind), "description": f"{target}: {rule}"}
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"urn:talentra:{key}",
            "title": key, "type": "object", "properties": props,
            "required": [f[0] for f in c["fields"] if f[2]], "additionalProperties": False}


def write_schemas(folder):
    """Write the JSON Schema of every inbound contract; return {contract: sha256 of the file}."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    out = {}
    for key in LOAD_ORDER:
        if CONTRACTS[key].get("released"):          # byte-for-byte copy keeps the released SHA256
            data = (BASELINE / "contracts" / f"{key}.schema.json").read_bytes()
        else:
            data = (json.dumps(schema(key), indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        (folder / f"{key}.schema.json").write_bytes(data)
        out[key] = hashlib.sha256(data).hexdigest()
    return out
