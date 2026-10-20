"""HTTP contracts: bounded inputs, read-only routes, sanitized failures, and JSON evidence."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from test_storage import row

from triage.api import create_app
from triage.storage import ResultPage, ResultQuery, StorageUnavailable, Store


@pytest.fixture
def api():
    store = Mock(spec=Store)
    store.ready.return_value = True
    store.list.return_value = ResultPage(items=(), next_before_id=None)
    store.get.return_value = Store.stored(row())
    with TestClient(create_app(store)) as client:
        yield client, store


def test_default_factory_only_connects_when_database_is_requested():
    with TestClient(create_app()) as client:
        assert client.get("/health/live").json() == {"status": "alive"}
        assert client.get("/openapi.json").status_code == 200


def test_health_readiness_and_outages(api):
    client, store = api
    assert client.get("/health/ready").json() == {"status": "ready"}
    store.ready.return_value = False
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"error": "storage_not_ready"}
    store.ready.side_effect = StorageUnavailable("secret")
    assert client.get("/health/ready").json() == {"error": "storage_unavailable"}
    assert client.get("/health/live").status_code == 200


def test_listing_passes_validated_filters(api):
    client, store = api
    response = client.get("/results?limit=1&before_id=9&decision=review&analysis_version=demo-v1")
    assert response.status_code == 200
    assert response.json() == {"items": [], "next_before_id": None}
    store.list.assert_called_once_with(
        ResultQuery(limit=1, before_id=9, decision="review", analysis_version="demo-v1")
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    client.get("/results")
    assert store.list.call_args.args[0] == ResultQuery()


@pytest.mark.parametrize(
    "path",
    [
        "/results?limit=0",
        "/results?limit=101",
        "/results?limit=invalid",
        "/results?before_id=-1",
        "/results?before_id=9223372036854775808",
        "/results?decision=ignore",
        "/results?analysis_version=",
        "/results?unknown=secret",
        "/results?analysis_version=" + "x" * 513,
        "/results/dewiki/101?analysis_version=v1",
        "/results/enwiki/0?analysis_version=v1",
        "/results/enwiki/9007199254740992?analysis_version=v1",
        "/results/enwiki/101?analysis_version=%20",
    ],
)
def test_invalid_requests_never_reach_storage_or_reflect_input(api, path):
    client, store = api
    response = client.get(path)
    assert response.status_code == 422
    assert response.json() == {"error": "invalid_request"}
    store.list.assert_not_called()
    store.get.assert_not_called()


def test_detail_contains_auditable_evidence_as_json_and_safe_source_url(api):
    client, store = api
    record = row()
    record["payload"]["analysis"]["explanation"] = "<script>alert('example')</script>"
    store.get.return_value = Store.stored(record)
    response = client.get("/results/enwiki/101?analysis_version=demo-v1")
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["analysis"]["explanation"] == "<script>alert('example')</script>"
    assert body["result"]["enrichment"]["provenance"]
    assert body["result"]["extraction"]["changes"]
    assert body["result"]["steps"]
    assert body["source_url"].startswith("https://en.wikipedia.org/")
    assert response.headers["content-type"] == "application/json"
    store.get.assert_called_once_with("enwiki", 101, "demo-v1")
    store.get.return_value = None
    response = client.get("/results/enwiki/102?analysis_version=demo-v1")
    assert response.status_code == 404 and response.json() == {"error": "not_found"}


@pytest.mark.parametrize(
    "path,method", [("/results", "list"), ("/results/enwiki/101?analysis_version=v1", "get")]
)
def test_storage_failure_and_writes_are_rejected(api, path, method):
    client, store = api
    getattr(store, method).side_effect = StorageUnavailable("secret")
    response = client.get(path)
    assert response.status_code == 503
    assert response.json() == {"error": "storage_unavailable"}
    for verb in ["post", "put", "delete", "patch"]:
        assert getattr(client, verb)(path).status_code == 405


def test_detail_version_is_a_query_value_so_slashes_and_quotes_remain_literal(api):
    client, store = api
    version = "v1/'; --"
    assert (
        client.get("/results/enwiki/101", params={"analysis_version": version}).status_code == 200
    )
    store.get.assert_called_once_with("enwiki", 101, version)
    assert client.get("/results/enwiki/101").status_code == 422
