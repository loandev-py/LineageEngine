from __future__ import annotations

import structlog 
from fastapi import FastAPI

from lineage_engine.api.routes import router, set_repository
from lineage_engine.storage.neo4j_repository import Neo4jRepository

logger = structlog.get_logger(__name__)

