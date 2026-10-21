"""Shared boundary policies. Bytes and Unicode character counts are deliberately distinct."""

MAX_EVENT_BYTES = 8_192  # Same event budget at CLI and Kafka entry points.
MAX_TEXT_CHARS = 4_096  # One before/after side and general v1 text fields.
MAX_WIRE_HUNKS = 20  # Historical v1 records remain readable.
MAX_REASONING_HUNKS = 8  # New processing must fit extraction and token budgets.
MAX_MODEL_CALLS = 4  # Extraction, assessment, optional repair/review share this cap.
MIN_ASSESSMENT_CALLS = 2  # Extraction and assessment are separate steps.
MAX_STAGE_ATTEMPTS = 2  # Initial response plus one repair/retry.
ITEM_DEADLINE_SECONDS = 240
MAX_EVALUATION_CASES = 9
MAX_EVALUATION_READY_CASES = 7
MAX_EVALUATION_CALLS = MAX_EVALUATION_READY_CASES * MAX_MODEL_CALLS
MAX_EVALUATION_BYTES = 262_144
MAX_TCP_PORT = 65_535
