"""
Script de demo: simula un pipeline de datos real y consulta el linaje.

Ejecutar con el servidor corriendo en otra terminal:
    uv run uvicorn lineage_engine.api.app:app --reload --port 8000
    uv run python scripts/demo_pipeline.py
"""

import time
import httpx

from lineage_engine.core.tracker import track_lineage, clear_events, get_captured_events
from lineage_engine.models.lineage import EventType


# ─── Simular un pipeline real ─────────────────────────────────────────────────

@track_lineage(inputs=["postgres_orders"], outputs=["orders_raw"])
def extract_from_database() -> dict:
    time.sleep(0.05)
    return {"rows": 50000, "status": "extracted"}


@track_lineage(inputs=["orders_raw"], outputs=["orders_cleaned"])
def clean_and_validate(data: dict) -> dict:
    time.sleep(0.03)
    return {**data, "status": "cleaned", "null_rows_removed": 234}


@track_lineage(inputs=["orders_cleaned"], outputs=["revenue_by_region"])
def aggregate_revenue(data: dict) -> dict:
    time.sleep(0.02)
    return {"regions": 12, "total_revenue": 2_340_000}


@track_lineage(inputs=["revenue_by_region"], outputs=["dashboard_ventas"])
def publish_to_dashboard(data: dict) -> dict:
    time.sleep(0.01)
    return {"dashboard": "updated", "rows_written": 12}


def run_pipeline() -> None:
    print("=" * 60)
    print("  DEMO: Motor de Linaje de Datos")
    print("=" * 60)

    print("\n[1] Ejecutando pipeline de datos...")
    clear_events()

    raw = extract_from_database()
    clean = clean_and_validate(raw)
    aggregated = aggregate_revenue(clean)
    publish_to_dashboard(aggregated)

    events = get_captured_events()
    print(f"    {len(events)} eventos capturados en memoria")

    # ── Solución: enviamos los eventos directamente via API ──────────────────
    # En lugar de depender de memoria compartida (imposible entre procesos),
    # serializamos cada evento a JSON y lo enviamos al endpoint de registro.
    print("\n[2] Enviando eventos a Neo4j via API...")
    with httpx.Client(base_url="http://localhost:8000") as client:
        synced = 0
        for event in events:
            response = client.post(
                "/lineage/event",
                content=event.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 201:
                synced += 1
        print(f"    {synced} eventos sincronizados")

        print("\n[3] Consultando el grafo completo...")
        graph = client.get("/lineage/graph").json()
        print(f"    Nodos: {graph['total_nodes']}, Aristas: {graph['total_edges']}")

        print("\n[4] Análisis de impacto: ¿qué se rompe si orders_raw falla?")
        response = client.get("/lineage/impact/orders_raw")
        if response.status_code == 200:
            impact = response.json()
            print(f"    Downstream afectados ({impact['total_downstream_affected']}):")
            for node in impact["downstream"]:
                print(f"      → {node}")
        else:
            print(f"    Error {response.status_code}: {response.json()}")

        print("\n[5] ¿De dónde vienen los datos de dashboard_ventas?")
        response = client.get("/lineage/impact/dashboard_ventas")
        if response.status_code == 200:
            impact_dash = response.json()
            print(f"    Upstream (fuentes):")
            for node in impact_dash["upstream"]:
                print(f"      ← {node}")

    print("\n✓ Demo completado.")
    print("  Abre http://localhost:7474 y corre:")
    print("  MATCH (n)-[r]->(m) RETURN n, r, m")


if __name__ == "__main__":
    run_pipeline()
