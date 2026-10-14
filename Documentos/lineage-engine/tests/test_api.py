from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lineage_engine.api.app import create_app
from lineage_engine.api.routes import set_repository
from lineage_engine.core.tracker import clear_events, track_lineage
from lineage_engine.models.lineage import EventType, LineageEvent
from lineage_engine.storege.neo4j_repository import Neo4jRepository

# configuracion  de Neo4j para test - el mismo  contenedor de desarrollo
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "lineage_password"

@pytest.fixture(scope="sesion")
def neo4j_repo() -> Neo4jRepository:
    repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    repo.initialize_constraints()
    return repo

@pytest.fixture(autouse=True)
def clean_neo4j(neo4j_repo: Neo4jRepository) -> None:
    neo4j_repo.clear_all()
    clear_events()

@pytest.fixture
def cient(neo4j_repo: Neo4jRepository) -> TestClient:
    set_repository(neo4j_repo)
    app=crete_app()
    return TestClient(app)

def make_and_save_pipeline(repo: Neo4jRepository) -> None:
    events = [
        LineageEvent(
            event_type=EventType.TRANSFORM,
            funtion_name="extract",\
            input_datasets=["source_db"],
            output_datasets=["raw_orders"],
            execution_tim_ms=50.0,
        )
        LineageEvent(
            event_type=EventType.TRANSFORM,
            funtion_name="clean",
            input_datasets=["raw_orders"],
            output_datasets=["clean_orders"],
            execution_tim_ms=30.0,
        )
        LineageEvent(
            event_type=EventType.TRANSFORM,
            funtion_name="publish",
            input_datasets=["clean_orders"],
            output_datasets=["dashboard"],
            execution_tim_ms=10.0
        )
    ]
    for event in events:
        repo.save_event(event)

class TestHealthEndpoint:
    def test_health_return_ok(self, client: TestClient) -> None:
        response = client.get("/lineage/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["neo4j"] == "connected"

class TestGraphEndpoint:
    def test_empty_graph_returns_zero_nodes(self, client: TestClient) -> None:
        response =  client.get("/lineage/graph")
        assert response.status_code == 200
        data = response.json()
        assert data["total_nodes"] == 0
        assert data["total_edges"] == 0
