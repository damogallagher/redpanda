"""Verify the maintenance upgrade against data created by the previous image."""

import json
import os
import subprocess
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_IMAGE = (
    "postgres:16.14-bookworm@sha256:"
    "64154d0babcb1741988719e703419af0382b19953706149f9872fbd0f438efa8"
)


def test_postgres_16_14_data_survives_16_15_upgrade(tmp_path):
    override = tmp_path / "postgres-version.json"
    base = [
        "docker",
        "compose",
        "--env-file",
        "/dev/null",
        "-f",
        str(ROOT / "compose.infrastructure.yml"),
        "-f",
        str(override),
        "-p",
        "triage-upgrade-test-" + uuid.uuid4().hex[:10],
    ]
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("LLM_") and name != "OPENAI_API_KEY"
    }
    env["POSTGRES_PASSWORD"] = "test-only"

    def compose(*args):
        return subprocess.run(
            [*base, *args],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=True,
            timeout=180,
        ).stdout.strip()

    def sql(query):
        return compose(
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "triage",
            "-d",
            "triage",
            "-v",
            "ON_ERROR_STOP=1",
            "-Atc",
            query,
        )

    # JSON is valid YAML; only the disposable project's image is overridden.
    override.write_text(json.dumps({"services": {"postgres": {"image": PREVIOUS_IMAGE}}}))
    try:
        compose("up", "-d", "--wait", "--wait-timeout", "120", "postgres")
        assert sql("SHOW server_version_num") == "160014"
        sql("CREATE TABLE upgrade_sentinel (id integer PRIMARY KEY, payload text NOT NULL)")
        sql("INSERT INTO upgrade_sentinel VALUES (1, 'preserve this row')")
        before = sql("SELECT version, applied_at FROM schema_migrations ORDER BY version")
        assert before.startswith("1|")

        compose("stop", "postgres")
        # Removing the image override selects the exact new pin from the repository.
        override.write_text(json.dumps({"services": {"postgres": {}}}))
        compose("up", "-d", "--wait", "--wait-timeout", "120", "postgres")
        assert sql("SHOW server_version_num") == "160015"
        assert sql("SELECT id, payload FROM upgrade_sentinel") == "1|preserve this row"
        assert sql("SELECT version, applied_at FROM schema_migrations ORDER BY version") == before
        sql("INSERT INTO upgrade_sentinel VALUES (2, 'new writes work')")
        assert sql("SELECT count(*) FROM upgrade_sentinel") == "2"
    finally:
        # This unique project owns these volumes; never remove the user's demo data.
        compose("down", "--volumes", "--remove-orphans")
