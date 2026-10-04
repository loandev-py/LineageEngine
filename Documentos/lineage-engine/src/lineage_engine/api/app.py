from __future__ import annotations

import structlog
from fastapi import FastAPI

from lineage_engine.api.routes import router, set_repository
from lineage_engine.storage.neo4j_repository import Neo4jRepository

logger = structlog.get_logger(__name__)

# configuracion de Nep4j en produccion esto vendria de variables de entorno, nunca harcodeando. lo que simplificamos aqui para enfocarnos
# aqui en la arquitactra, no en la configuracion
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "lineage_passorwd"

def create_app() -> FastAPI:
    app = FastAPI(
        title="Lineage Engine API",
        description="Monitor de Linaje de datos en tiempo real API REST",
        version="0.1.0"
    )

@app.on_event("startup")
async del startup() -> None:
    logger.info("app.startup_begin"
