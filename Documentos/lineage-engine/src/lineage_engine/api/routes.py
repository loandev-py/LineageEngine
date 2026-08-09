"""
Endpoints de la API REST del Motor de Linaje.

Cada función es un endpoint. FastAPI lee las anotaciones de tipo
para validar entradas y generar la documentación automáticamente.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lineage_engine.core.tracker import get_captured_events
from lineage_engine.storage.neo4j_repository import Neo4jRepository

logger = structlog.get_logger(__name__)

# APIRouter agrupa endpoints relacionados. En proyectos grandes
# hay un router por dominio (lineage, users, metrics, etc.).
router = APIRouter(prefix="/lineage", tags=["lineage"])


# ─── Modelos de request/response ─────────────────────────────────────────────
# Pydantic define exactamente qué espera y qué retorna cada endpoint.
# FastAPI los usa para validar entradas y generar la documentación.

class TrackEventRequest(BaseModel):
    """Cuerpo del request para registrar un evento manualmente."""
    function_name: str
    input_datasets: list[str]
    output_datasets: list[str]
    execution_time_ms: float
    success: bool = True


class ImpactResponse(BaseModel):
    """Respuesta del análisis de impacto."""
    node: str
    downstream: list[str]
    upstream: list[str]
    total_downstream_affected: int


class GraphResponse(BaseModel):
    """Representación completa del grafo de linaje."""
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    total_nodes: int
    total_edges: int


# ─── Dependencia compartida ───────────────────────────────────────────────────
# En lugar de crear una nueva conexión a Neo4j en cada endpoint,
# la instancia del repositorio se crea una vez al iniciar la app
# y se inyecta donde se necesita. Esto es inyección de dependencias.
_repository: Neo4jRepository | None = None


def get_repository() -> Neo4jRepository:
    """Retorna el repositorio Neo4j. Falla con error claro si no está inicializado."""
    if _repository is None:
        raise RuntimeError(
            "El repositorio Neo4j no está inicializado. "
            "Llama a set_repository() antes de usar la API."
        )
    return _repository


def set_repository(repo: Neo4jRepository) -> None:
    """Inyecta el repositorio. Se llama al iniciar la aplicación."""
    global _repository
    _repository = repo


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/graph", response_model=GraphResponse)
def get_graph() -> GraphResponse:
    """
    Retorna el grafo de linaje completo.

    Útil para dashboards de visualización que necesitan ver
    todos los nodos y relaciones existentes en el sistema.
    """
    repo = get_repository()
    data = repo.get_lineage_graph()
    return GraphResponse(
        nodes=data["nodes"],
        edges=data["edges"],
        total_nodes=len(data["nodes"]),
        total_edges=len(data["edges"]),
    )


@router.get("/impact/{node_name}", response_model=ImpactResponse)
def get_impact(node_name: str) -> ImpactResponse:
    """
    Analiza el impacto de un fallo en el nodo especificado.

    Responde: "Si node_name tiene un bug o falla, ¿qué otros
    datasets y reportes se verán afectados?"

    Esta es la query de mayor valor de negocio del sistema.
    """
    repo = get_repository()
    downstream = repo.get_downstream(node_name)
    upstream = repo.get_upstream(node_name)

    if not downstream and not upstream:
        # Si no existe el nodo o no tiene conexiones, lo informamos claramente
        logger.warning("api.node_not_found_or_isolated", node=node_name)
        raise HTTPException(
            status_code=404,
            detail=f"Nodo '{node_name}' no encontrado o sin conexiones en el grafo.",
        )

    return ImpactResponse(
        node=node_name,
        downstream=downstream,
        upstream=upstream,
        total_downstream_affected=len(downstream),
    )


@router.post("/sync", status_code=202)
def sync_events_to_neo4j() -> dict[str, Any]:
    """
    Sincroniza todos los eventos capturados en memoria hacia Neo4j.

    En producción esto correría automáticamente (Fase 4 con Kafka).
    Por ahora, es un endpoint manual que toma los eventos del store
    en memoria y los persiste en Neo4j.

    HTTP 202 Accepted: indica que la solicitud fue aceptada pero
    el procesamiento puede no estar completo todavía.
    """
    repo = get_repository()
    events = get_captured_events()

    if not events:
        return {"message": "No hay eventos pendientes de sincronizar.", "synced": 0}

    synced = 0
    errors = 0
    for event in events:
        try:
            repo.save_event(event)
            synced += 1
        except Exception as exc:
            logger.error("api.sync_event_failed", event_id=str(event.id), error=str(exc))
            errors += 1

    logger.info("api.sync_completed", synced=synced, errors=errors)
    return {
        "message": f"Sincronización completada.",
        "synced": synced,
        "errors": errors,
    }


@router.get("/nodes", response_model=list[dict[str, Any]])
def get_all_nodes() -> list[dict[str, Any]]:
    """Lista todos los datasets/nodos registrados en el sistema."""
    repo = get_repository()
    return repo.get_all_nodes()


@router.get("/health")
def health_check() -> dict[str, str]:
    """
    Verifica que la API y Neo4j están operativos.

    Los health checks son estándar en producción: Kubernetes, Docker,
    y los load balancers los usan para saber si el servicio está sano.
    """
    try:
        repo = get_repository()
        repo.get_all_nodes()  # query liviana para confirmar que Neo4j responde
        return {"status": "ok", "neo4j": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Neo4j no disponible: {exc}")
