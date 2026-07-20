# constructor del grafo de lineage
# convierte una secuencia de LineageEvent en un grafo dirigido (DAG) de NetworkX

from __future__ import annotations

from typing import Any

import networkx as nx
import structlog 

from lineage_engine.models.lineage import LineageEvent

logger = structlog.get_logger(__name__)

class LineageGraphBuilder:
    # construye y mantien el grafo de lineage en memoria
    def __init__(self) -> None:
        # nx.DiGraph = grafo dirigido "Di" de "Directed"
        self._graph: nx.DiGraph = nx.DiGraph()

    def add_event(self, event: LineageEvent) -> None:
        # incorpora un evento al grafo, por cada imput y cada output del evento, garrantizamos que el nodo 
        # exista en el grafo (add_node es idempotente: si ya existe, no pasa nada raro). luego conectamos cada input
        # con cada output mediante una arista que representa "esta funcion transformo A en B"
        
        # registramos los nodos de entrada
        for dataset_name in event.input_datasets:
            self._add_or_update_node(dataset_name)

        # registramos los nodos de salida
        for dataset_name in event.output_datasets:
            self._add_or_update_node(dataset_name)

        # conectamos cada input con cada output
        for source in event.input_datasets:
            for target in event.out input_datasets:
                self._graph.add_edge(
                    source,
                    target,
                    function_name=event.function_name,
                    last_execution=event.timestamp.isoformat(),
                    success=event.success,
                )

        logger.debut(
            "graph.event_added",
            function=event.function_name,
            nodes_total=self._graph.number_of_nodes(),
            edges_total=self._graph.number_of_edges(),
        )

    def _add_or_update_node(self, name: str) -> None:
        # agrega un nodo si no existe
        if name not in self._graph:
            self._graph.add_node(name)

    def get_graph(self) -> nx.DiGraph:
        # retorna el grafo de NetworkX para consultas avanzadas
        return self._graph
    
    def get_downstream(self, node_name: str) -> set[str]:
        # retorna todos los nodos que dependen, directamente o inderectamente
        if node_name not in self._graph:
            logger.warning("graph.node_not_found", node=node_name)
            return set()
        return nx.descendants(self._graph, node_name)

    def get_upstream(self, node_name: str) -> set[str]:
        # retorna todos los nodos de los que depende el nodo dado 
        if node_name not in self._graph:
            logger.warning("graph.node_not_found", node=node_name)
            return set()
        return nx.ancestors(self._graph, node_name)

    def has_cycles(self) -> bool:
        # verifica si el grafo tiene ciclos
        return not nx.is_directed_acyclic_graph(self._graph)

    def get_node_count(self) -> int:
        return self._graph.number_of_nodes()

    def get_edge_count(self) -> int:
        return self._graph.number_of_edges()
    
    def to_dict(self) -> dict[str, Any]:
        # exporta el grafo a un diccionario serializable, util para enviarlo despues por la API REST
        return {
            "nodes": list(self._graph.nodes()),
            "edges": [
                {
                    "source": source,
                    "target": target,
                    "function_name": data.get("function_name"),
                    "success": data.get("success")
                }
                for source, target, data in self._graph.edges(data=True)
            ],
        }
