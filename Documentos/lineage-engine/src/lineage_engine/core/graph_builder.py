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
