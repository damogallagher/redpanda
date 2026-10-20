"""Bounded, opt-in model acceptance with a frozen rubric and visible transcripts."""

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Annotated, Literal

import httpx
from pydantic import Field, TypeAdapter

from triage.config import Settings
from triage.enrichment import EnrichmentResult
from triage.reasoning import CallRecord, ReasoningFailure, reason
from triage.schema import Contract


class Case(Contract):
    id: Annotated[str, Field(min_length=1, max_length=80)]
    rubric: Annotated[str, Field(min_length=1, max_length=1000)]
    expected: Literal["routine", "review", "insufficient_evidence"]
    source: EnrichmentResult


CASES = TypeAdapter(Annotated[list[Case], Field(min_length=1, max_length=9)])


def evaluate(cases: list[Case], settings: Settings, client: httpx.Client) -> dict[str, object]:
    results = []
    started = monotonic()
    for case in cases:
        calls: list[CallRecord] = []
        start = monotonic()
        failed = False
        try:
            result = reason(case.source, settings, client, record=calls.append)
            output = result.model_dump(mode="json")
            count_ok = 2 <= len(calls) <= 4 if case.source.status == "ready" else not calls
            passed = (
                result.analysis.decision == case.expected
                and result.analysis.attempts == len(calls)
                and count_ok
            )
        except ReasoningFailure as exc:
            output = {"error": exc.code, "steps": [step.model_dump() for step in exc.steps]}
            passed = False
            failed = True
        results.append(
            {
                "case": case.id,
                "expected": case.expected,
                "rubric": case.rubric,
                "passed": passed,
                "elapsed_seconds": round(monotonic() - start, 3),
                "calls": [call.model_dump() for call in calls],
                "output": output,
            }
        )
        if failed:
            break  # Avoid repeated charges when the provider is unavailable.
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "backend": settings.backend,
        "model": settings.model,
        "max_tokens": settings.max_tokens,
        "elapsed_seconds": round(monotonic() - started, 3),
        "passed": sum(item["passed"] is True for item in results),
        "total": len(cases),
        "completed": len(results),
        "cases": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    args = parser.parse_args(argv)
    try:
        with args.cases.open("rb") as file:
            cases = CASES.validate_json(file.read(262145))
        settings = Settings.from_env(os.environ)
    except (OSError, ValueError):
        print(
            "Invalid evaluation input or model configuration; check the profile.", file=sys.stderr
        )
        return 2
    with httpx.Client() as client:
        report = evaluate(cases, settings, client)
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] == report["total"] else 1
