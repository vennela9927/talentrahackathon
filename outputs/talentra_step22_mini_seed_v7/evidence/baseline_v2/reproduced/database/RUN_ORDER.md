# Native PostgreSQL checkpoint

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
