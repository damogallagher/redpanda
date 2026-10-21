"""Count boundaries and historical envelopes survive the real sink and API."""

import json
from pathlib import Path

import pytest
from test_evidence_limits import hunks
from test_ingestion import consume
from test_serving_integration import FIXTURES, committed, eventually, publish
from test_serving_integration import serving as serving

from triage.prompts import ANALYSIS_VERSION
from triage.reasoning import ReasonedEdit

pytestmark = pytest.mark.integration


def test_evidence_count_delivery_and_legacy_read_compatibility(compose, serving):
    output = compose(
        "run",
        "--rm",
        "--no-deps",
        "-v",
        f"{FIXTURES.resolve()}:/fixtures:ro",
        "model-check",
        "python",
        "/fixtures/evidence_limits.py",
        timeout=90,
    )
    observation = json.loads(output.splitlines()[-1])
    assert observation["committed_offset"] == 4
    assert observation["model_calls"] == ["Synthetic 8-hunk edit"] * 2
    results = []
    for count in observation["counts"]:
        path = f"/results/enwiki/{1000 + count}?analysis_version={ANALYSIS_VERSION}"
        eventually(lambda path=path: serving.get(path).status_code == 200)
        result = serving.get(path).json()["result"]
        assert len(result["enrichment"]["evidence"]) == 8
        assert result["analysis"]["attempts"] == (2 if count == 8 else 0)
        assert result["analysis"]["decision"] == (
            "review" if count == 8 else "insufficient_evidence"
        )
        assert result["analysis"]["content_truncated"] == (count > 8)
        assert result["enrichment"]["status"] == ("ready" if count == 8 else "evidence_limit")
        assert result["outcome"] == ("assessed" if count == 8 else "incomplete_source")
        if count > 8:
            assert result["extraction"] is None and result["steps"] == []
        results.append(result)

    # Historical v1 results can have 20 source hunks and two failed extractions.
    # They must remain queryable after the processing limit changes to eight.
    legacy = json.loads((FIXTURES / "insufficient_evidence.jsonl").read_text())
    legacy["analysis"].update(analysis_version="legacy-count-v1", evidence=[])
    legacy["enrichment"]["evidence"] = [item.model_dump() for item in hunks(20)]
    legacy.update(
        extraction=None,
        outcome="invalid_output",
        steps=[{"stage": "extract", "outcome": "invalid_output"}] * 2,
    )
    ReasonedEdit.model_validate_json(json.dumps(legacy))
    publish(compose, legacy)
    path = "/results/enwiki/103?analysis_version=legacy-count-v1"
    eventually(lambda: serving.get(path).status_code == 200)
    assert serving.get(path).json()["result"] == legacy
    assert len(serving.get("/results").json()["items"]) == 5
    eventually(lambda: committed(compose) == 5)
    assert consume(compose, "processing-errors") == []
    assert consume(compose, "sink-errors") == []
    observation.update(results=results, legacy_result=legacy, sink_offset=5, stored_rows=5)
    Path("reports").mkdir(exist_ok=True)
    Path("reports/evidence-limits-delivery.json").write_text(
        json.dumps(observation, indent=2) + "\n"
    )
    print(json.dumps({"evidence_boundaries": "passed", "rows": 5, "real_model_calls": 0}))
