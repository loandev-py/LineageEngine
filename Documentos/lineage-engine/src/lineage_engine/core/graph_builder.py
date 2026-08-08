"""
Constructor del grafo de linaje.

Convierte una secuencia de LineageEvent en un grafo dirigido (DAG)
de NetworkX, donde:
  - Cada dataset/función es un NODO.
  - Cada relación "X produjo Y" es una ARISTA dirigida de X hacia Y.

Este es el componente que transforma "una lista de cosas que pasaron"
en "una estructura que entiende cómo se relacionan las cosas que pasaron".
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import structlog

from lineage_engine.models.lineage import LineageEvent

logger = structlog.get_logger(__name__)


class LineageGraphBuilder:
    """
    Construye y mantiene el grafo de linaje en memoria.

    Ejemplo de uso:
        builder = LineageGraphBuilder()
        builder.add_event(event)  # por cada evento capturado

        graph = builder.get_graph()
        print(graph.number_of_nodes())
    """

    def __init__(self) -> None:
        # nx.DiGraph = grafo dirigido. "Di" de "Directed".
        self._graph: nx.DiGraph = nx.DiGraph()

    def add_event(self, event: LineageEvent) -> None:
        """
        Incorpora un evento al grafo.

        Por cada input y cada output del evento, garantizamos que el nodo
        exista en el grafo (add_node es idempotente: si ya existe, no pasa
        nada raro). Luego conectamos cada input con cada output mediante
        una arista que representa "esta función transformó A en B".
        """
        # Registramos (o actualizamos) los nodos de entrada
        for dataset_name in event.input_datasets:
            self._add_or_update_node(dataset_name)

        # Registramos (o actualizamos) los nodos de salida
        for dataset_name in event.output_datasets:
            self._add_or_update_node(dataset_name)

        # Conectamos cada input con cada output: si la función leyó
        # ["raw_a", "raw_b"] y produjo ["clean"], se crean dos aristas:
        # raw_a -> clean y raw_b -> clean
        for source in event.input_datasets:
            for target in event.output_datasets:
                self._graph.add_edge(
                    source,
                    target,
                    function_name=event.function_name,
                    last_execution=event.timestamp.isoformat(),
                    success=event.success,
                )

        logger.debug(
            "graph.event_added",
            function=event.function_name,
            nodes_total=self._graph.number_of_nodes(),
            edges_total=self._graph.number_of_edges(),
        )

    def _add_or_update_node(self, name: str) -> None:
        """Agrega un nodo si no existe. add_node es seguro de llamar repetidamente."""
        if name not in self._graph:
            self._graph.add_node(name)

    def get_graph(self) -> nx.DiGraph:
        """Retorna el grafo de NetworkX para consultas avanzadas."""
        return self._graph

    def get_downstream(self, node_name: str) -> set[str]:
        """
        Retorna todos los nodos que dependen, directa o indirectamente,
        del nodo dado. Es decir: "si node_name falla, ¿qué se ve afectado?"

        nx.descendants() recorre el grafo hacia adelante (siguiendo la
        dirección de las flechas) y devuelve todos los nodos alcanzables.
        """
        if node_name not in self._graph:
            logger.warning("graph.node_not_found", node=node_name)
            return set()
        return nx.descendants(self._graph, node_name)

    def get_upstream(self, node_name: str) -> set[str]:
        """
        Retorna todos los nodos de los que depende el nodo dado.
        Es decir: "¿de dónde vienen los datos de este nodo?"

        nx.ancestors() recorre el grafo hacia atrás (contra la dirección
        de las flechas).
        """
        if node_name not in self._graph:
            logger.warning("graph.node_not_found", node=node_name)
            return set()
        return nx.ancestors(self._graph, node_name)

    def has_cycles(self) -> bool:
        """
        Verifica si el grafo tiene ciclos (lo cual sería un bug grave
        en un pipeline real: significaría una dependencia circular).
        """
        return not nx.is_directed_acyclic_graph(self._graph)

    def get_node_count(self) -> int:
        return self._graph.number_of_nodes()

    def get_edge_count(self) -> int:
        return self._graph.number_of_edges()

    def to_dict(self) -> dict[str, Any]:
        """
        Exporta el grafo a un diccionario serializable, útil para
        enviarlo después por la API REST (Fase 3) o guardarlo como JSON.
        """
        return {
            "nodes": list(self._graph.nodes()),
            "edges": [
                {
                    "source": source,
                    "target": target,
                    "function_name": data.get("function_name"),
                    "success": data.get("success"),
                }
                for source, target, data in self._graph.edges(data=True)
            ],
        }
