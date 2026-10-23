"""
Tests de integración de la API REST.

Estos tests necesitan Neo4j corriendo (docker compose up neo4j -d).
Usan httpx.TestClient para hacer requests a la API sin levantar
un servidor real — FastAPI provee esta capacidad de forma nativa.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lineage_engine.api.app import create_app
from lineage_engine.api.routes import set_repository
from lineage_engine.core.tracker import clear_events, track_lineage
from lineage_engine.models.lineage import EventType, LineageEvent
from lineage_engine.storage.neo4j_repository import Neo4jRepository

# Configuración de Neo4j para tests — el mismo contenedor de desarrollo
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "lineage_password"


@pytest.fixture(scope="session")
def neo4j_repo() -> Neo4jRepository:
    """
    Crea el repositorio Neo4j una sola vez para toda la sesión de tests.
    scope="session" significa que esta fixture se crea una vez y se
    reutiliza en todos los tests del archivo — más eficiente que
    reconectar en cada test.
    """
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    repo.initialize_constraints()
    return repo


@pytest.fixture(autouse=True)
def clean_neo4j(neo4j_repo: Neo4jRepository) -> None:
    """
    Limpia Neo4j antes de cada test.
    autouse=True: se ejecuta automáticamente antes de cada test
    sin necesidad de declararlo como parámetro.
    """
    neo4j_repo.clear_all()
    clear_events()


@pytest.fixture
def client(neo4j_repo: Neo4jRepository) -> TestClient:
    """
    Crea el cliente de test con el repositorio real de Neo4j inyectado.
    TestClient de FastAPI no necesita un servidor real — llama la app directamente.
    """
    set_repository(neo4j_repo)
    app = create_app()
    return TestClient(app)


def make_and_save_pipeline(repo: Neo4jRepository) -> None:
    """Helper: guarda un pipeline de ejemplo directamente en Neo4j."""
    events = [
        LineageEvent(
            event_type=EventType.TRANSFORM,
            function_name="extract",
            input_datasets=["source_db"],
            output_datasets=["raw_orders"],
            execution_time_ms=50.0,
        ),
        LineageEvent(
            event_type=EventType.TRANSFORM,
            function_name="clean",
            input_datasets=["raw_orders"],
            output_datasets=["clean_orders"],
            execution_time_ms=30.0,
        ),
        LineageEvent(
            event_type=EventType.TRANSFORM,
            function_name="publish",
            input_datasets=["clean_orders"],
            output_datasets=["dashboard"],
            execution_time_ms=10.0,
        ),
    ]
    for event in events:
        repo.save_event(event)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/lineage/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["neo4j"] == "connected"


class TestGraphEndpoint:
    def test_empty_graph_returns_zero_nodes(self, client: TestClient) -> None:
        response = client.get("/lineage/graph")
        assert response.status_code == 200
        data = response.json()
        assert data["total_nodes"] == 0
        assert data["total_edges"] == 0

    def test_graph_returns_correct_counts(
        self, client: TestClient, neo4j_repo: Neo4jRepository
    ) -> None:
        make_and_save_pipeline(neo4j_repo)

        response = client.get("/lineage/graph")
        assert response.status_code == 200
        data = response.json()
        assert data["total_nodes"] == 4   # source_db, raw_orders, clean_orders, dashboard
        assert data["total_edges"] == 3


class TestImpactEndpoint:
    def test_impact_returns_correct_downstream(
        self, client: TestClient, neo4j_repo: Neo4jRepository
    ) -> None:
        make_and_save_pipeline(neo4j_repo)

        response = client.get("/lineage/impact/raw_orders")
        assert response.status_code == 200
        data = response.json()
        assert set(data["downstream"]) == {"clean_orders", "dashboard"}
        assert data["total_downstream_affected"] == 2

    def test_impact_returns_correct_upstream(
        self, client: TestClient, neo4j_repo: Neo4jRepository
    ) -> None:
        make_and_save_pipeline(neo4j_repo)

        response = client.get("/lineage/impact/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert set(data["upstream"]) == {"source_db", "raw_orders", "clean_orders"}

    def test_impact_unknown_node_returns_404(self, client: TestClient) -> None:
        response = client.get("/lineage/impact/nodo_inexistente")
        assert response.status_code == 404


class TestSyncEndpoint:
    def test_sync_with_no_events_returns_zero(self, client: TestClient) -> None:
        response = client.post("/lineage/sync")
        assert response.status_code == 202
        assert response.json()["synced"] == 0

    def test_sync_persists_captured_events(
        self, client: TestClient, neo4j_repo: Neo4jRepository
    ) -> None:
        # Capturamos eventos con el decorador
        @track_lineage(inputs=["source"], outputs=["dest"])
        def my_transform() -> str:
            return "ok"

        my_transform()
        my_transform()

        response = client.post("/lineage/sync")
        assert response.status_code == 202
        assert response.json()["synced"] == 2

        # Verificamos que realmente llegaron a Neo4j
        nodes = neo4j_repo.get_all_nodes()
        names = {n["name"] for n in nodes}
        assert "source" in names
        assert "dest" in names
