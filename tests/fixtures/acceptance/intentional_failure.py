"""Deliberately wrong expectation, run only by make demo-test-failure."""

from pathlib import Path

from triage.evaluation import CASES
from triage.reasoning import Change, Extraction, validate_grounding


def test_invented_quote_is_wrongly_expected_to_be_accepted():
    source = CASES.validate_json(Path(__file__).with_name("cases.json").read_bytes())[0].source
    invented = Extraction(
        changes=(
            Change(
                hunk=0,
                kind="meaning",
                summary="Deliberately invalid test",
                before="This quotation does not appear in the source.",
                after=source.evidence[0].after,
            ),
        )
    )
    # This intentionally fails: production validation must reject an invented quotation.
    validate_grounding(invented, source)
