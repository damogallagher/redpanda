-- Idempotent foundation marker. Result persistence is added in Phase 5.
BEGIN;
CREATE TABLE IF NOT EXISTS schema_migrations (
    version integer PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO schema_migrations (version) VALUES (1) ON CONFLICT (version) DO NOTHING;
COMMIT;
