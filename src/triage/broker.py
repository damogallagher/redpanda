"""Small Kafka adapter: explicit delivery acknowledgement before synchronous commit."""

from dataclasses import dataclass
from typing import Any, Self

from confluent_kafka import Consumer, KafkaException, Producer, TopicPartition
from pydantic import BaseModel, ConfigDict, Field, model_validator


class WorkerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    brokers: str = Field(
        default="redpanda:9092",
        min_length=1,
        max_length=1024,
        pattern=r"^[A-Za-z0-9_.-]+:[0-9]{1,5}(,[A-Za-z0-9_.-]+:[0-9]{1,5})*$",
    )
    group_id: str = Field(
        default="triage-v1", min_length=1, max_length=200, pattern=r"^[A-Za-z0-9_.-]+$"
    )
    input_topic: str = Field(
        default="edits", min_length=1, max_length=249, pattern=r"^[A-Za-z0-9_.-]+$"
    )
    results_topic: str = Field(
        default="results", min_length=1, max_length=249, pattern=r"^[A-Za-z0-9_.-]+$"
    )
    errors_topic: str = Field(
        default="processing-errors", min_length=1, max_length=249, pattern=r"^[A-Za-z0-9_.-]+$"
    )
    item_timeout_seconds: float = Field(default=240, gt=0, le=240, allow_inf_nan=False)
    delivery_timeout_seconds: float = Field(default=10, ge=1, le=10, allow_inf_nan=False)
    max_items: int = Field(default=10, ge=0, le=10000)

    @model_validator(mode="after")
    def distinct_topics(self) -> Self:
        if any(
            not 1 <= int(address.rsplit(":", 1)[1]) <= 65535 for address in self.brokers.split(",")
        ):
            raise ValueError("broker ports must be between 1 and 65535")
        if {self.input_topic, self.results_topic, self.errors_topic} & {".", ".."}:
            raise ValueError("invalid topic name")
        if len({self.input_topic, self.results_topic, self.errors_topic}) != 3:
            raise ValueError("input, result and error topics must differ")
        return self


@dataclass(frozen=True)
class Record:
    topic: str
    partition: int
    offset: int
    key: bytes | None
    value: bytes | None


class DeliveryError(Exception):
    """Sanitized broker failure. Stop processing; leave the input uncommitted."""


class Broker:
    def __init__(self, settings: WorkerSettings) -> None:
        self.settings = settings
        # The pinned C extension has no typing metadata; Any is confined to this adapter.
        try:
            self.consumer: Any = Consumer(
                {
                    "bootstrap.servers": settings.brokers,
                    "group.id": settings.group_id,
                    "enable.auto.commit": False,
                    "enable.auto.offset.store": False,
                    "auto.offset.reset": "earliest",
                    "allow.auto.create.topics": False,
                    "max.poll.interval.ms": 600_000,
                    "session.timeout.ms": 45_000,
                    "queued.max.messages.kbytes": 1024,
                    "fetch.max.bytes": 1_048_576,
                    "socket.timeout.ms": 10_000,
                }
            )
        except KafkaException:
            raise DeliveryError("broker initialization failed") from None
        try:
            self.producer: Any = Producer(
                {
                    "bootstrap.servers": settings.brokers,
                    "enable.idempotence": True,
                    "acks": "all",
                    "message.timeout.ms": int(settings.delivery_timeout_seconds * 1000),
                    "queue.buffering.max.messages": 1,
                    "message.max.bytes": 262_144,
                }
            )
            self.consumer.subscribe([settings.input_topic])
        except KafkaException:
            self.consumer.close()
            raise DeliveryError("broker initialization failed") from None

    def poll(self) -> Record | None:
        try:
            message = self.consumer.poll(0.5)
        except KafkaException:
            raise DeliveryError("broker poll failed") from None
        if message is None:
            return None
        if message.error():
            raise DeliveryError("broker returned a consumer error")
        return Record(
            message.topic(), message.partition(), message.offset(), message.key(), message.value()
        )

    def publish(self, topic: str, key: bytes, value: bytes) -> None:
        delivered: list[bool] = []

        def acknowledged(error: object, message: object) -> None:
            delivered.append(error is None)

        try:
            self.producer.produce(topic, key=key, value=value, on_delivery=acknowledged)
            pending = self.producer.flush(self.settings.delivery_timeout_seconds + 1)
        except (KafkaException, BufferError):
            raise DeliveryError("broker publication failed") from None
        if pending or delivered != [True]:
            raise DeliveryError("broker publication was not acknowledged")

    def commit(self, record: Record) -> None:
        try:
            partitions = self.consumer.commit(
                offsets=[TopicPartition(record.topic, record.partition, record.offset + 1)],
                asynchronous=False,
            )
        except KafkaException:
            raise DeliveryError("broker offset commit failed") from None
        if not partitions or any(partition.error for partition in partitions):
            raise DeliveryError("broker offset commit was not acknowledged")

    def close(self) -> None:
        try:
            try:
                self.producer.flush(1)
            finally:
                self.consumer.close()  # Auto-commit is disabled, including during close.
        except KafkaException:
            raise DeliveryError("broker shutdown failed") from None
