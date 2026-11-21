"""
Kafka Consumer que corre en un thread separado y persiste
cada evento recibido en Neo4j.
"""

from __future__ import annotations

import json
import threading
from typing import TYPE_CHECKING

import structlog

from lineage_engine.models.lineage import LineageEvent
from lineage_engine.observability.metrics import EVENTS_CONSUMED_KAFKA

if TYPE_CHECKING:
    from lineage_engine.storage.neo4j_repository import Neo4jRepository

logger = structlog.get_logger(__name__)

TOPIC = "lineage-events"


class LineageKafkaConsumer:
    """
    Consume eventos del topic de Kafka y los persiste en Neo4j.

    Corre en un daemon thread para no bloquear el servidor FastAPI.
    Un daemon thread muere automáticamente cuando el proceso principal termina.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "lineage-engine-group",
    ) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self, repository: Neo4jRepository) -> None:
        """Arranca el consumer en un thread separado."""
        self._running = True
        self._thread = threading.Thread(
            target=self._consume_loop,
            args=(repository,),
            daemon=True,
            name="kafka-consumer",
        )
        self._thread.start()
        logger.info("kafka.consumer_started", topic=TOPIC, group_id=self.group_id)

    def _consume_loop(self, repository: Neo4jRepository) -> None:
        """
        Loop principal del consumer.

        Intenta importar confluent_kafka; si no está disponible
        (entorno de test sin Kafka), sale silenciosamente.
        """
        try:
            from confluent_kafka import Consumer, KafkaError
        except ImportError:
            logger.warning(
                "kafka.consumer_unavailable", reason="confluent_kafka not installed"
            )
            return

        consumer = Consumer(
            {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": self.group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": True,
            }
        )
        consumer.subscribe([TOPIC])

        try:
            while self._running:
                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error("kafka.consumer_error", error=str(msg.error()))
                    continue

                try:
                    data = json.loads(msg.value().decode("utf-8"))
                    event = LineageEvent(**data)
                    repository.save_event(event)
                    EVENTS_CONSUMED_KAFKA.inc()
                    logger.info("kafka.event_consumed", function=event.function_name)
                except Exception as e:
                    logger.error("kafka.event_processing_error", error=str(e))
        finally:
            consumer.close()

    def stop(self) -> None:
        """Detiene el consumer limpiamente."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("kafka.consumer_stopped")
