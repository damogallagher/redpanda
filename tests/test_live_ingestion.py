"""Opt-in live evidence; never runs in the deterministic verification targets."""

import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from test_ingestion import consume

from triage.schema import EditEvent

pytestmark = [pytest.mark.integration, pytest.mark.live]


def test_live_wikimedia_ingestion(compose):
    compose("up", "-d", "connect", env_overrides={"INGEST_SAMPLE_ALL": "true"})
    endpoint = "http://" + compose("port", "connect", "4195").strip()
    deadline = time.monotonic() + 30
    with httpx.Client(timeout=3, trust_env=False) as client:
        while True:
            try:
                if client.get(endpoint + "/ready").status_code == 200:
                    break
            except httpx.TransportError:
                pass
            assert time.monotonic() < deadline, "Connect did not become ready within 30 seconds"
            time.sleep(0.5)
        started = datetime.now(UTC).isoformat()
        time.sleep(30)
        metrics = client.get(endpoint + "/metrics")
        metrics.raise_for_status()
    counts = {name: 0 for name in ("accepted", "filtered", "heartbeat", "invalid", "sampled_out")}
    for line in metrics.text.splitlines():
        if line.startswith("triage_ingest_frames"):
            match = re.search(r'outcome="([^"]+)"', line)
            assert match is not None, line
            counts[match[1]] += int(float(line.rsplit(" ", 1)[1]))
    assert sum(counts.values()) > 0, "No public source frames were processed"
    # Stop ingestion before reading the complete topics. A final frame may be drained
    # after the metrics snapshot, so record snapshot and final topic counts separately.
    compose("stop", "connect")
    edits = consume(compose, "edits")
    errors = consume(compose, "ingest-errors")
    for record in edits:
        event = EditEvent.model_validate_json(record["value"])
        assert record["key"] == event.event_id
        headers = {h["key"]: h["value"] for h in record["headers"]}
        assert headers["source"] == "wikimedia-recentchange"
        assert headers["source_id"]
        assert headers["ingest_version"] == "1"
    evidence = {
        "started_at": started,
        "sample_seconds": 30,
        "sampling": "all eligible edits; intentionally disabled 1% selection for this smoke",
        "source": "https://stream.wikimedia.org/v2/stream/recentchange",
        "metrics_snapshot": counts,
        "final_edits": len(edits),
        "final_errors": len(errors),
        "examples": [{"key": r["key"], "event": json.loads(r["value"])} for r in edits[:3]],
        "live_model_requests": 0,
        "limitations": "No particular live edit is required; gap-free delivery is not established.",
    }
    reports = Path("reports")
    reports.mkdir(exist_ok=True)
    (reports / "phase-2-live.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))
