"""Sequential processing and safe acknowledgement order, with bounded metadata logs."""

import hashlib
import json
import signal
from collections.abc import Callable, Mapping
from threading import Event
from time import monotonic
from types import FrameType
from typing import Annotated, Literal

import httpx
from pydantic import Field

from triage.broker import Broker, DeliveryError, Record, WorkerSettings
from triage.config import Settings
from triage.enrichment import enrich
from triage.limits import MAX_EVENT_BYTES
from triage.prompts import ANALYSIS_VERSION
from triage.reasoning import ReasonedEdit, ReasoningFailure, Step, reason
from triage.schema import Contract, EditEvent


class Position(Contract):
    topic: str
    partition: Annotated[int, Field(ge=0)]
    offset: Annotated[int, Field(ge=0)]


ErrorCode = Literal["invalid_event", "model_failed", "deadline_exceeded", "enrichment_failed"]


class ProcessingError(Contract):
    schema_version: Literal[1] = 1
    source: Position
    event: EditEvent | None
    code: ErrorCode
    detail: str
    payload_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    steps: Annotated[tuple[Step, ...], Field(max_length=4)] = ()


def worker_settings(env: Mapping[str, str]) -> WorkerSettings:
    return WorkerSettings.model_validate(
        {
            "brokers": env.get("KAFKA_BROKERS", "redpanda:9092"),
            "group_id": env.get("KAFKA_GROUP_ID", "triage-v1"),
            "max_items": env.get("WORKER_MAX_ITEMS", "10"),
        }
    )


def process(
    record: Record,
    settings: Settings,
    client: httpx.Client,
    *,
    deadline: float,
    clock: Callable[[], float] = monotonic,
) -> ReasonedEdit | ProcessingError:
    event: EditEvent | None = None

    def failure(code: ErrorCode, detail: str, steps: tuple[Step, ...] = ()) -> ProcessingError:
        return ProcessingError(
            source=Position(topic=record.topic, partition=record.partition, offset=record.offset),
            event=event,
            code=code,
            detail=detail,
            payload_sha256=hashlib.sha256(record.value or b"").hexdigest(),
            steps=steps,
        )

    try:
        if record.value is None or len(record.value) > MAX_EVENT_BYTES:
            raise ValueError("missing or oversized event")
        event = EditEvent.model_validate_json(record.value)
        if record.key != event.event_id.encode():
            raise ValueError("event key mismatch")
    except ValueError:
        return failure("invalid_event", "Event schema, size, or Kafka key is invalid.")
    source = enrich(event, client, clock=clock)
    if source.status not in {
        "ready",
        "no_text_change",
        "revision_unavailable",
        "evidence_limit",
        "response_too_large",
    }:
        return failure("enrichment_failed", source.status)
    try:
        return reason(source, settings, client, deadline=deadline, clock=clock)
    except ReasoningFailure as exc:
        return failure(exc.code, "Reasoning could not complete within its budget.", exc.steps)


def emit(event: str, **fields: object) -> None:
    print(json.dumps({"event": event, **fields}), flush=True)


def run_worker(
    broker: Broker,
    settings: Settings,
    client: httpx.Client,
    stop: Event,
    *,
    clock: Callable[[], float] = monotonic,
) -> int:
    processed = 0
    emit(
        "worker_started",
        group_id=broker.settings.group_id,
        max_items=broker.settings.max_items,
        backend=settings.backend,
        model=settings.model,
    )
    try:
        while not stop.is_set() and (
            broker.settings.max_items == 0 or processed < broker.settings.max_items
        ):
            record = broker.poll()
            if stop.is_set():
                break
            if record is None:
                continue
            outcome = process(
                record,
                settings,
                client,
                deadline=clock() + broker.settings.item_timeout_seconds,
                clock=clock,
            )
            if isinstance(outcome, ReasonedEdit):
                topic = broker.settings.results_topic
                key = f"{outcome.analysis.event.event_id}:{ANALYSIS_VERSION}"
                decision: str = outcome.analysis.decision
                attempts = outcome.analysis.attempts
            else:
                topic = broker.settings.errors_topic
                key = f"{record.topic}:{record.partition}:{record.offset}:{ANALYSIS_VERSION}"
                decision = outcome.code
                attempts = len(outcome.steps)
            broker.publish(topic, key.encode(), outcome.model_dump_json().encode())
            broker.commit(record)
            processed += 1
            emit(
                "record_committed",
                topic=record.topic,
                partition=record.partition,
                offset=record.offset,
                output_topic=topic,
                output_key=key,
                decision=decision,
                attempts=attempts,
            )
    finally:
        broker.close()
    emit("worker_stopped", processed=processed)
    return processed


def serve(config: WorkerSettings, settings: Settings) -> int:
    stop = Event()

    def request_stop(signum: int, frame: FrameType | None) -> None:
        stop.set()

    previous = {
        signum: signal.signal(signum, request_stop) for signum in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        with httpx.Client() as client:
            broker = Broker(config)
            run_worker(broker, settings, client, stop)
        return 0
    except DeliveryError as exc:
        emit("worker_failed", reason=str(exc), recovery="restart to replay uncommitted input")
        return 1
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
