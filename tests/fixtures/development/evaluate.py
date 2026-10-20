"""Explicit live development probe, outside unit/CI gates; records every visible model I/O."""

import json
import os
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from time import monotonic

import httpx

from triage.config import Settings
from triage.enrichment import decode_comparison
from triage.reasoning import ReasoningFailure, reason
from triage.schema import EditEvent

root = Path(__file__).resolve().parents[1]
settings = Settings.from_env(os.environ)
results = []
started = monotonic()
with httpx.Client() as client:
    for case in json.loads((root / "development/cases.json").read_text()):
        event = EditEvent.model_validate_json(
            (root / "enrichment/synthetic-event.json").read_bytes()
        )
        if case.get("saved_fixture"):
            event = EditEvent.model_validate_json(
                (root / "enrichment/belle-event.json").read_bytes()
            )
            payload = (root / "enrichment/belle-response.json").read_bytes()
        elif case.get("missing"):
            payload = b'{"error":{"code":"nosuchrevid"}}'
        else:
            body = (
                '<tr><td class="diff-lineno">Line 1:</td>'
                '<td class="diff-lineno">Line 1:</td></tr>'
                '<tr><td class="diff-marker"></td><td class="diff-deletedline"><div>'
                + escape(case["before"])
                + '</div></td><td class="diff-marker"></td><td class="diff-addedline"><div>'
                + escape(case["after"])
                + "</div></td></tr>"
            )
            payload = json.dumps(
                {
                    "compare": {
                        "fromid": 42,
                        "toid": 42,
                        "fromrevid": event.old_revision_id,
                        "torevid": event.revision_id,
                        "fromns": 0,
                        "tons": 0,
                        "fromtitle": event.title,
                        "totitle": event.title,
                        "body": body,
                    }
                }
            ).encode()
        calls = []
        source = decode_comparison(event, payload)
        start = monotonic()
        try:
            result = reason(source, settings, client, record=calls.append)
            output = result.model_dump(mode="json")
            passed = result.analysis.decision in case["expected"]
            passed = passed and result.analysis.attempts == (
                0 if case.get("missing") else len(calls)
            )
            passed = passed and (not calls if case.get("missing") else 2 <= len(calls) <= 4)
        except ReasoningFailure as exc:
            output = {"error": exc.code, "steps": [step.model_dump() for step in exc.steps]}
            passed = False
        results.append(
            {
                "case": case["id"],
                "expected": case["expected"],
                "rubric": case["rubric"],
                "passed": passed,
                "elapsed_seconds": round(monotonic() - start, 3),
                "calls": [call.model_dump() for call in calls],
                "output": output,
            }
        )
print(
    json.dumps(
        {
            "checked_at": datetime.now(UTC).isoformat(),
            "backend": settings.backend,
            "model": settings.model,
            "max_tokens": settings.max_tokens,
            "timeout_seconds": settings.timeout_seconds,
            "elapsed_seconds": round(monotonic() - started, 3),
            "passed": sum(item["passed"] for item in results),
            "total": len(results),
            "cases": results,
        },
        indent=2,
    )
)
raise SystemExit(0 if all(item["passed"] for item in results) else 1)
