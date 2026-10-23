"""
Aplicación FastAPI principal.

Este archivo crea la instancia de la app, registra los routers,
y define los eventos de startup/shutdown (inicialización y limpieza).
"""

from __future__ import annotations

import structlog
from fastapi import FastAPI

from lineage_engine.api.routes import router, set_repository
from lineage_engine.storage.neo4j_repository import Neo4jRepository

logger = structlog.get_logger(__name__)

# Configuración de Neo4j — en producción esto vendría de variables
# de entorno, nunca hardcodeado. Lo simplificamos aquí para enfocarnos
# en la arquitectura, no en la configuración.
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "lineage_password"


def create_app() -> FastAPI:
    """
    Factory function que crea y configura la aplicación FastAPI.

    Usar una factory en vez de una variable global permite crear
    instancias separadas en tests (con configuración diferente)
    sin afectar la app de producción.
    """
    app = FastAPI(
        title="Lineage Engine API",
        description="Motor de Linaje de Datos en Tiempo Real — API REST",
        version="0.1.0",
    )

    @app.on_event("startup")
    async def startup() -> None:
        """
        Se ejecuta una vez cuando el servidor arranca.
        Aquí inicializamos recursos que deben existir durante toda
        la vida del servidor: el driver de Neo4j, los índices, etc.
        """
        logger.info("app.startup_begin")
        repo = Neo4jRepository(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        repo.initialize_constraints()
        set_repository(repo)
        logger.info("app.startup_complete")

    @app.on_event("shutdown")
    async def shutdown() -> None:
        """
        Se ejecuta cuando el servidor se apaga (Ctrl+C o señal SIGTERM).
        Cerramos el pool de conexiones limpiamente para no dejar
        conexiones huérfanas en Neo4j.
        """
        from lineage_engine.api.routes import get_repository
        try:
            repo = get_repository()
            repo.close()
            logger.info("app.shutdown_complete")
        except RuntimeError:
            pass  # el repositorio nunca se inicializó, no hay nada que cerrar

    app.include_router(router)
    return app


# Instancia que uvicorn levanta cuando corres el servidor
app = create_app()
