from __future__ import annotations

from dataclasses import dataclass, field
import structlog
from lineage_engine.core.graph_buider import LineageGraphBuilder

logger = structlog.get_logger(__name__)

@dataclass
class ImpactReport:
    
