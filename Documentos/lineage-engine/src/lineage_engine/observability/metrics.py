"""
Métricas de Prometheus para el Motor de Linaje.

Counter   → solo sube, nunca baja (eventos capturados, errores)
Gauge     → sube y baja (nodos actuales en el grafo)
Histogram → distribución de valores (tiempos de ejecución)
"""

from prometheus_client import Counter, Gauge, Histogram

# Cuántos eventos de linaje se han capturado
EVENTS_CAPTURED = Counter(
    "lineage_events_captured_total",
    "Total de eventos de linaje capturados",
    ["function_name", "success"],
)

# Cuántos eventos se publicaron a Kafka
EVENTS_PUBLISHED_KAFKA = Counter(
    "lineage_events_published_kafka_total",
    "Total de eventos publicados a Kafka",
)

# Cuántos eventos consumió el consumer de Kafka
EVENTS_CONSUMED_KAFKA = Counter(
    "lineage_events_consumed_kafka_total",
    "Total de eventos consumidos desde Kafka",
)

# Distribución de tiempos de ejecución (en milisegundos)
EXECUTION_DURATION = Histogram(
    "lineage_execution_duration_ms",
    "Duración de ejecución de funciones tracked (ms)",
    buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000, 10000],
)

# Estado actual del grafo
GRAPH_NODES_TOTAL = Gauge(
    "lineage_graph_nodes_total",
    "Número actual de nodos en el grafo de linaje",
)

GRAPH_EDGES_TOTAL = Gauge(
    "lineage_graph_edges_total",
    "Número actual de aristas en el grafo de linaje",
)
