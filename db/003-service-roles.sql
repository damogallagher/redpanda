-- Reconcile service privileges on every startup, including existing volumes.
-- psql reads secrets from the environment; quoted variables escape SQL safely.
\getenv reader_password TRIAGE_READER_PASSWORD
\getenv writer_password TRIAGE_WRITER_PASSWORD
BEGIN;
SELECT pg_advisory_xact_lock(20261020, 3);
SELECT 'CREATE ROLE triage_reader LOGIN'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'triage_reader')
\gexec
SELECT 'CREATE ROLE triage_writer LOGIN'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'triage_writer')
\gexec
ALTER ROLE triage_reader NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS
    PASSWORD :'reader_password';
ALTER ROLE triage_writer NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS
    PASSWORD :'writer_password';
REVOKE ALL ON DATABASE triage FROM PUBLIC;
GRANT CONNECT ON DATABASE triage TO triage_reader, triage_writer;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO triage_reader, triage_writer;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM triage_reader, triage_writer;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM triage_reader, triage_writer;
GRANT SELECT ON triage_results, schema_migrations TO triage_reader;
GRANT SELECT, INSERT, UPDATE ON triage_results TO triage_writer;
GRANT USAGE ON SEQUENCE triage_results_id_seq TO triage_writer;
COMMIT;
