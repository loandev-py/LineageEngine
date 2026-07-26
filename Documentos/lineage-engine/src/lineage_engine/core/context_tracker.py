from  __future__ import annotations

import time
from types import TracebackType
from typing import Any

import structlog

from lineage_engine.core.tracker import _event_store
from lineage_engine.models.lineage import EventType, LineageEvent 

logger = structlog.get_logger(__name__)

class track_block:
    # contex manager para capturar linaje de un bloque de codigo
    
    def __init__(
        self,
        block_name: str,
        inputs: list[str],
        outputs: list[str],
    ) -> None:
        self.block_name = block_name
        self.inputs = inputs
        self.outputs = outputs
        self._start_time = float = 0.0
        self._metadata: dict[str, Any] = {}

    def add_metadata(self, **kwargs: Any) -> None:
        self._metadata.update(kwargs)

    def __enter__(self) -> track_block:
        self._start_time = time.perf_counter()
        logger.info("lineage.block_started", block = self.block_name)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        elapsed_ms = (time.perf_counter() - self._start_time) * 1000
        success = exc_type is None

        event = LineageEvent(
            event_type=EventType.TRANSFORM,
            function_name=se;f.block_name,
            input_datasets=self.inputs,
            output_datasets=self.outputs,
            execution_time_ms=round(elapsed_ms, 2),
            success=success,
            error_messageg=str(exc_value)if exc_value else None,
            metadata=self._metadata,
        )
        _event_store.append(event)

        if success:
            logger.info(
                "lineage.block_completed",
                block+self.block_name,
                duration_ms=event.execution_time_ms,
            )
        else:
            logger.error(
                "lineage.block_failed",
                block=self.block_name,
                srror=str(exc_value),
            )
        return False
