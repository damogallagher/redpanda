from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from confluent_kafka import KafkaException

from triage import broker as module
from triage.broker import Broker, DeliveryError, Record, WorkerSettings


@pytest.fixture
def clients(monkeypatch):
    consumer = Mock()
    producer = Mock()
    producer.flush.return_value = 0
    producer.produce.side_effect = lambda *a, **kw: kw["on_delivery"](None, object())
    consumer.commit.return_value = [SimpleNamespace(error=None)]
    factories = (Mock(return_value=consumer), Mock(return_value=producer))
    monkeypatch.setattr(module, "Consumer", factories[0])
    monkeypatch.setattr(module, "Producer", factories[1])
    return consumer, producer, factories


def test_configuration_disables_automatic_offsets_and_requires_producer_acks(clients):
    consumer, _, factories = clients
    broker = Broker(WorkerSettings())
    c = factories[0].call_args.args[0]
    p = factories[1].call_args.args[0]
    assert c["enable.auto.commit"] is c["enable.auto.offset.store"] is False
    assert c["auto.offset.reset"] == "earliest"
    assert c["max.poll.interval.ms"] == 600000
    assert c["allow.auto.create.topics"] is False
    assert p["enable.idempotence"] is True and p["acks"] == "all"
    assert p["queue.buffering.max.messages"] == 1
    assert p["message.timeout.ms"] == 10000
    consumer.subscribe.assert_called_once_with(["edits"])
    broker.close()
    consumer.close.assert_called_once()


@pytest.mark.parametrize(
    "values",
    [
        {"brokers": "host:0"},
        {"brokers": "host:65536"},
        {"brokers": "host"},
        {"brokers": "user:secret@host:9092"},
        {"input_topic": "."},
        {"results_topic": ".."},
        {"input_topic": "results"},
        {"errors_topic": "results"},
        {"max_items": -1},
    ],
)
def test_invalid_worker_config_is_rejected(values):
    with pytest.raises(ValueError):
        WorkerSettings(**values)


@pytest.mark.parametrize("failure", ["consumer", "producer", "subscribe"])
def test_initialization_failure_is_sanitized_and_closes_created_consumer(clients, failure):
    consumer, _, factories = clients
    target = {"consumer": factories[0], "producer": factories[1], "subscribe": consumer.subscribe}[
        failure
    ]
    target.side_effect = KafkaException("PRIVATE")
    with pytest.raises(DeliveryError, match="initialization failed"):
        Broker(WorkerSettings())
    assert consumer.close.call_count == (0 if failure == "consumer" else 1)


def test_poll_projects_record_position_and_bytes(clients):
    consumer, _, _ = clients
    message = Mock()
    for name, value in {
        "error": None,
        "topic": "edits",
        "partition": 2,
        "offset": 7,
        "key": b"key",
        "value": b"value",
    }.items():
        getattr(message, name).return_value = value
    consumer.poll.return_value = message
    assert Broker(WorkerSettings()).poll() == Record("edits", 2, 7, b"key", b"value")
    consumer.poll.assert_called_once_with(0.5)


@pytest.mark.parametrize("failure", ["empty", "exception", "message-error"])
def test_poll_handles_idle_and_errors_without_exposing_details(clients, failure):
    consumer, _, _ = clients
    consumer.poll.return_value = None
    if failure == "exception":
        consumer.poll.side_effect = KafkaException("PRIVATE")
    if failure == "message-error":
        consumer.poll.return_value = Mock(error=Mock(return_value="PRIVATE"))
    broker = Broker(WorkerSettings())
    if failure == "empty":
        assert broker.poll() is None
    else:
        with pytest.raises(DeliveryError) as exc:
            broker.poll()
        assert "PRIVATE" not in str(exc.value)


def test_publish_requires_exactly_one_successful_delivery_callback(clients):
    _, producer, _ = clients
    Broker(WorkerSettings()).publish("results", b"key", b"value")
    assert producer.produce.call_args.args == ("results",)
    assert producer.produce.call_args.kwargs["key"] == b"key"
    assert producer.produce.call_args.kwargs["value"] == b"value"
    producer.flush.assert_called_once_with(11)


@pytest.mark.parametrize(
    "failure", ["queue", "produce", "flush", "pending", "missing-ack", "error-ack"]
)
def test_unacknowledged_publication_fails(clients, failure):
    _, producer, _ = clients
    if failure in {"queue", "produce"}:
        producer.produce.side_effect = (
            BufferError("PRIVATE") if failure == "queue" else KafkaException("PRIVATE")
        )
    elif failure == "flush":
        producer.flush.side_effect = KafkaException("PRIVATE")
    elif failure == "pending":
        producer.flush.return_value = 1
    elif failure == "missing-ack":
        producer.produce.side_effect = None
    else:
        producer.produce.side_effect = lambda *a, **kw: kw["on_delivery"]("PRIVATE", object())
    with pytest.raises(DeliveryError) as exc:
        Broker(WorkerSettings()).publish("results", b"key", b"value")
    assert "PRIVATE" not in str(exc.value)


def test_commit_uses_only_the_acknowledged_record_offset_plus_one(clients):
    consumer, _, _ = clients
    Broker(WorkerSettings()).commit(Record("edits", 2, 7, None, None))
    kwargs = consumer.commit.call_args.kwargs
    position = kwargs["offsets"][0]
    assert (position.topic, position.partition, position.offset) == ("edits", 2, 8)
    assert kwargs["asynchronous"] is False


@pytest.mark.parametrize("failure", ["exception", "empty", "partition-error"])
def test_commit_failure_is_explicit(clients, failure):
    consumer, _, _ = clients
    if failure == "exception":
        consumer.commit.side_effect = KafkaException("PRIVATE")
    elif failure == "empty":
        consumer.commit.return_value = None
    else:
        consumer.commit.return_value = [SimpleNamespace(error="PRIVATE")]
    with pytest.raises(DeliveryError, match="offset commit"):
        Broker(WorkerSettings()).commit(Record("edits", 0, 1, None, None))


def test_failed_shutdown_still_closes_consumer(clients):
    consumer, producer, _ = clients
    producer.flush.side_effect = KafkaException("PRIVATE")
    with pytest.raises(DeliveryError, match="shutdown failed"):
        Broker(WorkerSettings()).close()
    consumer.close.assert_called_once()
