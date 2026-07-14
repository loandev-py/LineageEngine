"""
Decorador de tracking de linaje.

@track_lineage es la interfaz principal del sistema: cualquier función
de pipeline decorada con él emite automáticamente un LineageEvent
cada vez que se ejecuta.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

import structlog

from lineage_engine.models.lineage import EventType, LineageEvent

F = TypeVar("F", bound=Callable[..., Any])

logger = structlog.get_logger(__name__)

_event_store: list[LineageEvent] = []


def track_lineage(
    inputs: list[str],
    outputs: list[str],
    *,
    event_type: EventType = EventType.TRANSFORM,
) -> Callable[[F], F]:
    """
    Decorador de fábrica: retorna el decorador real para poder
    pasarle argumentos (inputs, outputs) al envolver la función.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)  # preserva func.__name__ y docstring
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            logger.info(
                "lineage.execution_started",
                function=func.__name__,
                inputs=inputs,
                outputs=outputs,
            )

            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                event = LineageEvent(
                    event_type=event_type,
                    function_name=func.__name__,
                    input_datasets=inputs,
                    output_datasets=outputs,
                    execution_time_ms=round(elapsed_ms, 2),
                    success=True,
                )
                _event_store.append(event)

                logger.info(
                    "lineage.execution_completed",
                    function=func.__name__,
                    duration_ms=event.execution_time_ms,
                    event_id=str(event.id),
                )
                return result

            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                event = LineageEvent(
                    event_type=event_type,
                    function_name=func.__name__,
                    input_datasets=inputs,
                    output_datasets=outputs,
                    execution_time_ms=round(elapsed_ms, 2),
                    success=False,
                    error_message=str(exc),
                )
                _event_store.append(event)

                logger.error(
                    "lineage.execution_failed",
                    function=func.__name__,
                    error=str(exc),
                    event_id=str(event.id),
                )
                raise  # nunca silenciamos el error original

        return wrapper  # type: ignore[return-value]

    return decorator  # type: ignore[return-value]


def get_captured_events() -> list[LineageEvent]:
    """Retorna todos los eventos capturados hasta ahora."""
    return _event_store.copy()


def clear_events() -> None:
    """Limpia el store. Se usa en tests para que no se contaminen entre sí."""
    _event_store.clear()
