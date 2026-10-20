-- Applied on every startup by db-migrate, including existing Phase 1 volumes.
BEGIN;
SELECT pg_advisory_xact_lock(20261020, 2);
CREATE TABLE IF NOT EXISTS triage_results (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    wiki text NOT NULL CHECK (wiki = 'enwiki'),
    revision_id bigint NOT NULL CHECK (revision_id > 0 AND revision_id < 9007199254740992),
    analysis_version text NOT NULL,
    decision text NOT NULL CHECK (decision IN ('routine', 'review', 'insufficient_evidence')),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    source_offset bigint NOT NULL CHECK (source_offset >= 0),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (wiki, revision_id, analysis_version)
);
CREATE INDEX IF NOT EXISTS triage_results_decision_id ON triage_results (decision, id DESC);
CREATE INDEX IF NOT EXISTS triage_results_version_id ON triage_results (analysis_version, id DESC);
INSERT INTO schema_migrations (version) VALUES (2) ON CONFLICT (version) DO NOTHING;
COMMIT;
