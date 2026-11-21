"""
Aplicación FastAPI con Kafka consumer y métricas de Prometheus.
Usa el patrón 'lifespan' moderno en lugar del deprecado on_event.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_client import make_asgi_app

from lineage_engine.api.routes import router, set_repository
from lineage_engine.observability.metrics import GRAPH_EDGES_TOTAL, GRAPH_NODES_TOTAL
from lineage_engine.storage.neo4j_repository import Neo4jRepository
from lineage_engine.streaming.kafka_consumer import LineageKafkaConsumer

logger = structlog.get_logger(__name__)

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "lineage_password"
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Todo lo que está ANTES del yield → se ejecuta al arrancar.
    Todo lo que está DESPUÉS del yield → se ejecuta al apagar.
    El yield es el momento en que el servidor atiende requests.
    """
    logger.info("app.startup_begin")

    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    repo.initialize_constraints()
    set_repository(repo)

    consumer = LineageKafkaConsumer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="lineage-engine-group",
    )
    consumer.start(repo)

    graph_data = repo.get_lineage_graph()
    GRAPH_NODES_TOTAL.set(len(graph_data["nodes"]))
    GRAPH_EDGES_TOTAL.set(len(graph_data["edges"]))

    logger.info("app.startup_complete")
    yield

    consumer.stop()
    repo.close()
    logger.info("app.shutdown_complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Lineage Engine API",
        description="Motor de Linaje de Datos en Tiempo Real — API REST",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    return app


app = create_app()
