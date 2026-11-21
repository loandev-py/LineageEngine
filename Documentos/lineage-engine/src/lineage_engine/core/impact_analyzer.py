"""
Analizador de impacto sobre el grafo de linaje.

Este es el componente de mayor valor de negocio del sistema: convierte
el grafo construido en respuestas accionables para preguntas como
"¿qué reportes se ven afectados si esta tabla tiene un bug?"
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from lineage_engine.core.graph_builder import LineageGraphBuilder

logger = structlog.get_logger(__name__)


@dataclass
class ImpactReport:
    """
    Resultado de un análisis de impacto.

    Usamos una dataclass simple (no Pydantic) aquí porque este objeto
    nunca se serializa a JSON externamente ni necesita validación de
    entrada — es puramente un resultado de cálculo interno.
    """

    affected_node: str
    downstream_nodes: set[str] = field(default_factory=set)
    upstream_nodes: set[str] = field(default_factory=set)

    @property
    def total_affected(self) -> int:
        return len(self.downstream_nodes)

    @property
    def is_isolated(self) -> bool:
        """True si el nodo no tiene ninguna conexión en el grafo."""
        return not self.downstream_nodes and not self.upstream_nodes


class ImpactAnalyzer:
    """
    Analiza el impacto de fallos sobre un grafo de linaje ya construido.

    Ejemplo de uso:
        analyzer = ImpactAnalyzer(graph_builder)
        report = analyzer.analyze_failure("orders_raw")

        print(f"Si orders_raw falla, se afectan: {report.downstream_nodes}")
    """

    def __init__(self, graph_builder: LineageGraphBuilder) -> None:
        self._graph_builder = graph_builder

    def analyze_failure(self, node_name: str) -> ImpactReport:
        """
        Calcula el radio de impacto de un fallo en node_name.

        downstream_nodes: todo lo que deja de ser confiable si node_name falla.
        upstream_nodes: de dónde viene la información de node_name (para
        investigar la causa raíz del problema).
        """
        downstream = self._graph_builder.get_downstream(node_name)
        upstream = self._graph_builder.get_upstream(node_name)

        logger.info(
            "impact.analysis_completed",
            node=node_name,
            downstream_count=len(downstream),
            upstream_count=len(upstream),
        )

        return ImpactReport(
            affected_node=node_name,
            downstream_nodes=downstream,
            upstream_nodes=upstream,
        )

    def find_critical_nodes(self, top_n: int = 5) -> list[tuple[str, int]]:
        """
        Identifica los nodos "críticos" del sistema: aquellos cuyo fallo
        afectaría a más nodos downstream. Útil para priorizar qué tablas
        merecen más monitoreo y tests de calidad.

        Retorna una lista de tuplas (nombre_nodo, cantidad_afectados),
        ordenada de mayor a menor impacto.
        """
        graph = self._graph_builder.get_graph()
        impact_scores = [
            (node, len(self._graph_builder.get_downstream(node)))
            for node in graph.nodes()
        ]
        # Ordenamos por impacto descendente y tomamos los top_n
        impact_scores.sort(key=lambda pair: pair[1], reverse=True)
        return impact_scores[:top_n]
