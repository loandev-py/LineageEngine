from __future__ import annotations

from dataclasses import dataclass, field
import structlog
from lineage_engine.core.graph_buider import LineageGraphBuilder

logger = structlog.get_logger(__name__)

@dataclass
class ImpactReport:
    affected_node: str
    downstream_nodes: set[str] = field(defauld_factory=set)
    upstream_nodes: set[str] = field(defauld_factory=set)

@property
def total_afected(self) -> int:
    return len(self,downstream_nodes)

@property
def is_isolated(self) -> bool:
    # true si el nodo no tiene ninguna conexion en el grafo
    return not self.downstream_nodes and not self.upstream_nodes

class ImpactAnalyzer:

    def __init__(self, _graph_builder: LineageGraphBuilder) -> None:
        self._graph_buider = graph_buider

    def analyze_failure(self, node_name:str) -> ImpactReport:
        downstream = self._graph_builder.get_downstream(node_name)
        upstream = self._graph_buider.get_upstream(node_name)

        logger.info(
            "impact.analyzis_complete",
            node=node_name,
            downstream_count=len(downstream),
            upstream_count=len(upstream)
        )

        return ImpactReport(
            affected_node=node_name,
            downstream_nodes=downstream,
            upstream_nodes=upstream
        )

    def find_critical_node(self, top_n: int = 5) -> list[tupke[str, int]]:
        graph = self._graph_buider.get_graph()
        impact_scores = [
            (node, len(self._graph_buider.get_downstream(node)))
            for node in graph.nodes()
        ]
        
        impact_scores.sort(key=lambda pair:pair[1], reverse = True)
        return impact_scores[:top_n]
