"""Opt-in public API check; kept outside the deterministic/coverage gates."""

import json
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

import httpx
import pytest

from triage.enrichment import decode_comparison, enrich
from triage.schema import EditEvent


@pytest.mark.integration
@pytest.mark.live
def test_public_revision_comparison():
    fixtures = Path("tests/fixtures/enrichment")
    event = EditEvent.model_validate_json((fixtures / "belle-event.json").read_bytes())
    expected = decode_comparison(event, (fixtures / "belle-response.json").read_bytes())
    start = monotonic()
    with httpx.Client() as client:
        result = enrich(event, client)
    record = {
        "checked_at": datetime.now(UTC).isoformat(),
        "elapsed_seconds": round(monotonic() - start, 3),
        "result": result.model_dump(mode="json"),
    }
    Path("reports").mkdir(exist_ok=True)
    Path("reports/live-enrichment.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    assert result.status == "ready", "Public content may be unavailable; inspect the saved outcome."
    assert result.evidence == expected.evidence
    assert result.provenance == expected.provenance
