"""
Repositorio Neo4j para el grafo de linaje.

Encapsula toda la comunicación con Neo4j. El resto del sistema
(la API, el motor de linaje) solo conoce esta interfaz — nunca
habla directamente con el driver de Neo4j.

Patrón Repository: separa "qué quiero hacer con los datos" (lógica
de negocio) de "cómo se almacenan esos datos" (detalles de Neo4j).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import structlog
from neo4j import GraphDatabase, Session

from lineage_engine.models.lineage import LineageEvent

logger = structlog.get_logger(__name__)


class Neo4jRepository:
    """
    Maneja todas las operaciones de lectura y escritura en Neo4j.

    Ciclo de vida:
        repo = Neo4jRepository("bolt://localhost:7687", "neo4j", "lineage_password")
        repo.initialize_constraints()   # una sola vez al arrancar
        repo.save_event(event)
        nodes = repo.get_all_nodes()
        repo.close()                    # al apagar el sistema
    """

    def __init__(self, uri: str, user: str, password: str) -> None:
        # GraphDatabase.driver() crea un pool de conexiones reutilizables.
        # No es una conexión por operación — es un pool que Neo4j gestiona
        # eficientemente. Por eso solo creamos el driver una vez.
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info("neo4j.driver_created", uri=uri)

    @contextmanager
    def _session(self) -> Iterator[Session]:
        """
        Context manager que abre una sesión, la retorna, y la cierra
        automáticamente al salir del bloque 'with', incluso si hay error.

        Una sesión Neo4j es la unidad de trabajo: cada sesión puede
        contener múltiples transacciones. Siempre hay que cerrarla.
        """
        session = self._driver.session()
        try:
            yield session
        finally:
            session.close()

    def initialize_constraints(self) -> None:
        """
        Crea constraints e índices en Neo4j.

        Los constraints garantizan integridad: no pueden existir dos nodos
        con el mismo 'name'. Los índices aceleran las búsquedas por 'name'.
        Se deben crear una sola vez al iniciar el sistema.
        """
        with self._session() as session:
            session.run("""
                CREATE CONSTRAINT dataset_name_unique IF NOT EXISTS
                FOR (n:Dataset) REQUIRE n.name IS UNIQUE
            """)
        logger.info("neo4j.constraints_initialized")

    def save_event(self, event: LineageEvent) -> None:
        """
        Persiste un LineageEvent en Neo4j como nodos y relaciones.

        Usamos MERGE en lugar de CREATE porque MERGE es idempotente:
        si el nodo ya existe (mismo nombre), lo reutiliza en vez de
        crear un duplicado. Si no existe, lo crea. Esto es esencial
        porque el mismo dataset puede aparecer en múltiples eventos
        (como input de una función y output de otra).

        La relación PRODUCES conecta cada input con cada output,
        igual que hace el GraphBuilder de NetworkX en memoria.
        """
        with self._session() as session:
            for input_name in event.input_datasets:
                for output_name in event.output_datasets:
                    session.run(
                        """
                        MERGE (source:Dataset {name: $source_name})
                        MERGE (target:Dataset {name: $target_name})
                        CREATE (source)-[:PRODUCES {
                            function_name: $function_name,
                            event_id:      $event_id,
                            success:       $success,
                            timestamp:     $timestamp,
                            duration_ms:   $duration_ms
                        }]->(target)
                        """,
                        source_name=input_name,
                        target_name=output_name,
                        function_name=event.function_name,
                        event_id=str(event.id),
                        success=event.success,
                        timestamp=event.timestamp.isoformat(),
                        duration_ms=event.execution_time_ms,
                    )

        logger.info(
            "neo4j.event_saved",
            function=event.function_name,
            event_id=str(event.id),
        )

    def get_all_nodes(self) -> list[dict[str, Any]]:
        """Retorna todos los nodos del grafo de linaje."""
        with self._session() as session:
            result = session.run("MATCH (n:Dataset) RETURN n.name AS name")
            return [{"name": record["name"]} for record in result]

    def get_downstream(self, node_name: str) -> list[str]:
        """
        Retorna todos los nodos descendientes (downstream) de node_name.

        La query Cypher [*] significa "recorre cualquier cantidad de
        saltos siguiendo relaciones PRODUCES hacia adelante".
        Es el equivalente de nx.descendants() pero en Neo4j.
        """
        with self._session() as session:
            result = session.run(
                """
                MATCH (n:Dataset {name: $name})-[:PRODUCES*]->(descendant:Dataset)
                RETURN DISTINCT descendant.name AS name
                """,
                name=node_name,
            )
            return [record["name"] for record in result]

    def get_upstream(self, node_name: str) -> list[str]:
        """
        Retorna todos los nodos ancestros (upstream) de node_name.

        La flecha va al revés: <-[:PRODUCES*]- significa "recorre
        relaciones PRODUCES hacia atrás".
        """
        with self._session() as session:
            result = session.run(
                """
                MATCH (n:Dataset {name: $name})<-[:PRODUCES*]-(ancestor:Dataset)
                RETURN DISTINCT ancestor.name AS name
                """,
                name=node_name,
            )
            return [record["name"] for record in result]

    def get_lineage_graph(self) -> dict[str, Any]:
        """
        Retorna el grafo completo como un diccionario serializable a JSON.
        Este es el formato que consumirá la API REST.
        """
        with self._session() as session:
            result = session.run(
                """
                MATCH (source:Dataset)-[r:PRODUCES]->(target:Dataset)
                RETURN
                    source.name AS source,
                    target.name AS target,
                    r.function_name AS function_name,
                    r.success AS success,
                    r.timestamp AS timestamp
                """
            )
            edges = [
                {
                    "source": record["source"],
                    "target": record["target"],
                    "function_name": record["function_name"],
                    "success": record["success"],
                    "timestamp": record["timestamp"],
                }
                for record in result
            ]

        nodes_result = self.get_all_nodes()
        return {"nodes": nodes_result, "edges": edges}

    def clear_all(self) -> None:
        """
        Elimina todos los nodos y relaciones.
        DETACH DELETE borra el nodo y todas sus relaciones adjuntas.
        Usado en tests de integración para empezar desde cero.
        """
        with self._session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.warning("neo4j.all_data_cleared")

    def close(self) -> None:
        """Cierra el pool de conexiones. Llamar al apagar el sistema."""
        self._driver.close()
        logger.info("neo4j.driver_closed")
