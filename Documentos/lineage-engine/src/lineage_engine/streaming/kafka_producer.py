"""
Kafka Producer para publicar eventos de linaje al topic.
"""

from __future__ import annotations

import structlog

from lineage_engine.models.lineage import LineageEvent
from lineage_engine.observability.metrics import EVENTS_PUBLISHED_KAFKA

logger = structlog.get_logger(__name__)

TOPIC = "lineage-events"


class LineageKafkaProducer:
    def __init__(self, bootstrap_servers: str = "localhost:9092") -> None:
        from confluent_kafka import Producer

        self._producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "retries": 3,
                "batch.size": 16384,
                "linger.ms": 5,
            }
        )

    def publish_event(self, event: LineageEvent) -> None:
        def on_delivery(err: Exception | None, msg: object) -> None:
            if err:
                logger.error("kafka.delivery_failed", error=str(err))
            else:
                EVENTS_PUBLISHED_KAFKA.inc()
                logger.info("kafka.event_published", function=event.function_name)

        self._producer.produce(
            topic=TOPIC,
            value=event.model_dump_json().encode("utf-8"),
            callback=on_delivery,
        )
        self._producer.poll(0)

    def flush(self) -> None:
        self._producer.flush()

    def close(self) -> None:
        self.flush()
