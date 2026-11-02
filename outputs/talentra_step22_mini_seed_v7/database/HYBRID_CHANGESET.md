# Hybrid changeset plan

The retained baseline has120 tables and1250 physical-design columns. The157 additional fields in ../evidence/proposed_fields.json are proposed and have not been migrated. Do not apply the original baseline SQL to an existing production database.

1. Owner approves credit versus currency units, account scoping, privacy, retention and canonical ID mappings.
2. Database owner writes an additive migration for each approved new table/column, with nullable/backfill/constraint stages.
3. Translate source IDs to canonical keys. Currency minor_units is not display sort order; label IDs are not translation IDs; language metadata uses its own extension.
4. Backfill in bounded resumable batches with checksums, parent-before-child ordering, a retry key and quarantine for conflicts.
5. Run positive/negative FK, uniqueness, account-scope, credit/money and concurrent debit tests in the native engine. Collect logs and measured plans.
6. Validate counts and reconciliations, then enable constraints and deploy compatible readers/writers. Test rollback/forward recovery before release.
7. Re-run authorization, target workload, signed provider callbacks, recovery and interview gates. Only then change implementation status and full rubric scores with the evidence.

The typed synthetic examples are illustrations and must not be loaded as production business records. Source B native PASS claims are not hybrid execution evidence.
