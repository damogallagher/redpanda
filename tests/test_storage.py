"""Read-only database boundary, pagination, and corrupt-data handling."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import psycopg
import pytest

from triage.storage import DatabaseSettings, ResultQuery, StorageUnavailable, Store

FIXTURE = Path("tests/fixtures/serving/review.jsonl")
NOW = datetime(2026, 10, 20, tzinfo=UTC)


def row(id=1):
    return {
        "id": id,
        "payload": json.loads(FIXTURE.read_text()),
        "created_at": NOW,
        "updated_at": NOW,
    }


def test_settings_defaults_and_password_redaction():
    assert DatabaseSettings.from_env({}) == DatabaseSettings()
    settings = DatabaseSettings.from_env(
        {"PGHOST": "db.example", "PGPORT": "5433", "PGPASSWORD": "test:p@ss/word"}
    )
    assert settings.host == "db.example"
    assert settings.port == 5433
    assert settings.password.get_secret_value() == "test:p@ss/word"
    assert "test:p@ss/word" not in repr(settings)
    with pytest.raises(ValueError):
        DatabaseSettings.from_env({"PGPORT": "0"})


def test_query_uses_bound_parameters_read_only_transaction_and_timeouts(monkeypatch):
    connect = MagicMock()
    connection = connect.return_value.__enter__.return_value
    connection.execute.return_value.fetchall.return_value = [{"version": 2}]
    monkeypatch.setattr("triage.storage.psycopg.connect", connect)
    store = Store(DatabaseSettings(password="test:p@ss/word"))
    assert store.query("SELECT %s", ("'; DROP TABLE triage_results; --",)) == [{"version": 2}]
    connection.execute.assert_called_once_with("SELECT %s", ("'; DROP TABLE triage_results; --",))
    config = connect.call_args.kwargs
    assert config["password"] == "test:p@ss/word"
    assert config["user"] == "triage_reader"
    assert config["connect_timeout"] == 3
    assert config["autocommit"] is True
    assert config["options"] == (
        "-c default_transaction_read_only=on -c statement_timeout=3000 -c lock_timeout=1000"
    )
    connect.return_value.__exit__.assert_called_once()


@pytest.mark.parametrize("stage", ["connect", "execute"])
def test_database_errors_are_sanitized(monkeypatch, stage):
    connect = MagicMock()
    failing = connect if stage == "connect" else connect.return_value.__enter__.return_value.execute
    failing.side_effect = psycopg.OperationalError("secret database address/password")
    monkeypatch.setattr("triage.storage.psycopg.connect", connect)
    with pytest.raises(StorageUnavailable, match=r"^storage unavailable$"):
        Store(DatabaseSettings()).query("SELECT 1")


@pytest.mark.parametrize("marker,expected", [([], False), ([{"version": 2}], True)])
def test_readiness_requires_schema_marker_and_table(monkeypatch, marker, expected):
    store = Store(DatabaseSettings())
    query = MagicMock(side_effect=[[], marker])
    monkeypatch.setattr(store, "query", query)
    assert store.ready() is expected
    assert "triage_results" in query.call_args_list[0].args[0]
    assert "version = 2" in query.call_args_list[1].args[0]


def test_detail_not_found_and_bound_identity(monkeypatch):
    store = Store(DatabaseSettings())
    query = MagicMock(side_effect=[[], [row()]])
    monkeypatch.setattr(store, "query", query)
    version = "'; DROP TABLE triage_results; --"
    assert store.get("enwiki", 101, version) is None
    result = store.get("enwiki", 101, version)
    assert result.result.analysis.decision == "review"
    assert result.source_url == "https://en.wikipedia.org/w/index.php?diff=101&oldid=100"
    assert query.call_args.args[1] == ("enwiki", 101, version)
    assert version not in query.call_args.args[0]


@pytest.mark.parametrize("bad", [{}, {"payload": {}}, {"payload": object()}, {**row(), "id": -1}])
def test_corrupt_records_are_not_returned(bad):
    with pytest.raises(StorageUnavailable, match="stored result is invalid"):
        Store.stored(bad)


def test_excessive_stored_nesting_is_sanitized():
    deep = []
    deep.append(deep)
    with pytest.raises(StorageUnavailable):
        Store.stored({**row(), "payload": deep})


@pytest.mark.parametrize("count,cursor", [(0, None), (1, None), (2, 3)])
def test_keyset_page_uses_extra_row_without_returning_it(monkeypatch, count, cursor):
    store = Store(DatabaseSettings())
    query = MagicMock(return_value=[row(3), row(2)][:count])
    monkeypatch.setattr(store, "query", query)
    page = store.list(ResultQuery(limit=1, decision="review", before_id=10, analysis_version="v'1"))
    assert len(page.items) == min(count, 1)
    assert page.next_before_id == cursor
    if count:
        assert page.items[0].revision_id == 101
        assert page.items[0].decision == "review"
    sql, params = query.call_args.args
    assert "id < %s" in sql and "ORDER BY id DESC LIMIT %s" in sql
    assert params == ("review", "review", 10, 10, "v'1", "v'1", 2)
    assert "v'1" not in sql
