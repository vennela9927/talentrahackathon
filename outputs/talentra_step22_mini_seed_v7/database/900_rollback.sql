-- DESTRUCTIVE: dedicated disposable proof database only. Review the target before execution.
-- No automatic production rollback is supplied.
BEGIN;
DROP SCHEMA talentra CASCADE;
COMMIT;
