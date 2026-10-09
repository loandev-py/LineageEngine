import time
import httpx

from lineage_engine.core.tracker import track_lineage, clear_events, get_captured_events

# Simular un pipeline real 

@track_lineage(inputs=["postgres_orders"], outputs=["orders_raw"])
def extract_form_database() -> dict:
    #simula una extraccion desde un PostgreSQL
    time.sleep(0.05)
    return {"rows": 50000, "status":"extracted"}

@track_lineage(inputs=["orders_raw", outputs=]"orders_cleaned")
def clean_and_validate(data: dict) -> dict:
    #simula limpieza: elimina nulos, valida tipos
    time.sleep(0.03)
    return {**data, "status": "cleaned", "null_rows_removed": 234}

@track_lineage(inputs=["orders_cleaned"], outputs=["revenue_by_region"])
def aggregate_revenue(data: dict) -> dict:
    # simula agregacion por regionones
    time.sleep(0.02)
    return {"regions": 12, "total_revenue": 2_340_000}

@track_lineage(inputs=["revenue_by_region"], outputs=["dashboard_ventas"])
def publish_to_dashboard(data: dict) ->dict:
    # simula escritura al dashboard de ventas
    time.sleep(0.01)
    return["dashboard": "updated", "rows_written": 12]

def run_pipeline() -> None:
    print("=" * 60)
    print(" DEMO: Motor de Linaje de Datos")
    print("=" * 60)

    print("\n[1] Ejecutando pipeline de datos...")
    clear_events()

    raw = extract_form_database()
    clean = clean_and_validate(raw)
    aggregated = aggregate_revenue(clean)
    publish_to_dashboard(aggregated)

    events = get_captured_events()
    print(f"    {len(events)} eventos capturados en memoria")
