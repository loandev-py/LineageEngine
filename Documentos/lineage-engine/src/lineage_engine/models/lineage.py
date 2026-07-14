"""
Modelos de datos del Motor de Linaje.

- LineageNode: un dataset o transformación (un "nodo" en el grafo)
- LineageEdge: la relación entre dos nodos ("A produjo B")
- LineageEvent: un evento capturado en tiempo real
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class NodeType(str, Enum):
    DATASET = "dataset"
    TRANSFORMATION = "transformation"
    SOURCE = "source"
    SINK = "sink"


class EventType(str, Enum):
    READ = "read"
    WRITE = "write"
    TRANSFORM = "transform"
    SCHEMA_CHANGE = "schema_change"


class LineageNode(BaseModel):
    """Un nodo en el grafo: tabla, archivo, función, lo que produzca o consuma datos."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=255)
    node_type: NodeType
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def name_must_be_snake_case(cls, v: str) -> str:
        if " " in v:
            raise ValueError(
                f"El nombre del nodo no puede tener espacios: '{v}'. "
                f"Usa snake_case: '{v.replace(' ', '_')}'"
            )
        return v.lower()


class LineageEdge(BaseModel):
    """Relación entre dos nodos: el flujo de datos de A hacia B."""

    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    transformation_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("transformation_name")
    @classmethod
    def validate_transformation_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre de la transformación no puede estar vacío.")
        return v.strip()


class LineageEvent(BaseModel):
    """Un evento capturado en tiempo real al ejecutar una función decorada."""

    id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    function_name: str
    input_datasets: list[str] = Field(default_factory=list)
    output_datasets: list[str] = Field(default_factory=list)
    execution_time_ms: float = Field(ge=0)
    success: bool = True
    error_message: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("error_message")
    @classmethod
    def error_requires_failure(cls, v: str | None, info: Any) -> str | None:
        if v is not None and info.data.get("success", True):
            raise ValueError(
                "No puedes tener error_message con success=True. "
                "Si hay error, establece success=False."
            )
        return v

    def to_jsonl_line(self) -> str:
        """JSONL: cada línea es un JSON independiente, ideal para hacer append a un log."""
        return self.model_dump_json() + "\n"
