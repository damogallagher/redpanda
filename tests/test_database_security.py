"""Real PostgreSQL rejects writes even if the reader disables transaction read-only."""

import subprocess

import pytest

pytestmark = pytest.mark.integration


def test_service_roles_enforce_least_privilege_and_password_rotation(compose):
    # Quoted punctuation proves psql parameters are escaped, not SQL concatenation.
    credentials = {
        "TRIAGE_READER_PASSWORD": "reader:'p@ss/word",
        "TRIAGE_WRITER_PASSWORD": "writer:'p@ss/word",
    }
    compose("run", "--rm", "db-migrate", env_overrides=credentials)

    def query(role, statement, password=None):
        key = "TRIAGE_READER_PASSWORD" if role == "triage_reader" else "TRIAGE_WRITER_PASSWORD"
        return compose(
            "exec",
            "-T",
            "-e",
            "PGPASSWORD=" + (password or credentials[key]),
            "postgres",
            "psql",
            "-h",
            "postgres",
            "-U",
            role,
            "-d",
            "triage",
            "-v",
            "ON_ERROR_STOP=1",
            "-Atc",
            statement,
        ).strip()

    for role in ["triage_reader", "triage_writer"]:
        assert query(role, "SELECT current_user") == role
        assert query(role, "SELECT count(*) FROM triage_results") == "0"
        assert (
            query(
                role,
                "SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication "
                "OR rolbypassrls FROM pg_roles WHERE rolname = current_user",
            )
            == "f"
        )
        for statement in [
            "DELETE FROM triage_results",
            "DROP TABLE triage_results",
            "CREATE TABLE should_not_exist (id int)",
            "CREATE ROLE should_not_exist",
            "CREATE TEMP TABLE should_not_exist (id int)",
            "SET ROLE triage",
            "SELECT * FROM pg_authid",
        ]:
            with pytest.raises(subprocess.CalledProcessError):
                query(role, statement)
    for statement in [
        "SET default_transaction_read_only=off; UPDATE triage_results SET decision='review'",
        "INSERT INTO triage_results DEFAULT VALUES",
        "UPDATE schema_migrations SET version=99",
        "SELECT nextval('triage_results_id_seq')",
    ]:
        with pytest.raises(subprocess.CalledProcessError):
            query("triage_reader", statement)
    assert query("triage_writer", "UPDATE triage_results SET decision='review'") == "UPDATE 0"
    with pytest.raises(subprocess.CalledProcessError):
        query("triage_writer", "UPDATE schema_migrations SET version=99")
    with pytest.raises(subprocess.CalledProcessError):
        query("triage_reader", "SELECT 1", password=credentials["TRIAGE_WRITER_PASSWORD"])

    # Reconciliation is repeatable and rotates credentials on existing volumes.
    compose("run", "--rm", "db-migrate", env_overrides=credentials)
    old = credentials["TRIAGE_READER_PASSWORD"]
    credentials["TRIAGE_READER_PASSWORD"] = "rotated:'reader"
    compose("run", "--rm", "db-migrate", env_overrides=credentials)
    with pytest.raises(subprocess.CalledProcessError):
        query("triage_reader", "SELECT 1", password=old)
    assert (
        query("triage_reader", "SELECT version FROM schema_migrations ORDER BY version") == "1\n2"
    )
