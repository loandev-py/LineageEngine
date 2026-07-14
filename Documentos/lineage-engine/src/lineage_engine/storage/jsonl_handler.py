"""
Manejador de persistencia en formato JSONL.

JSONL (JSON Lines) almacena un objeto JSON por línea. Esto permite:
- Hacer append eficiente sin reescribir el archivo completo.
- Leer el archivo línea por línea sin cargarlo entero en memoria
  (importante cuando el log crece a millones de eventos).
- Recuperarse de una escritura interrumpida: las líneas completas
  anteriores siguen siendo válidas aunque la última esté corrupta.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import structlog

from lineage_engine.models.lineage import LineageEvent

logger = structlog.get_logger(__name__)


class JSONLHandler:
    """
    Lee y escribe eventos de linaje en un archivo JSONL.

    Ejemplo de uso:
        handler = JSONLHandler(Path("events.jsonl"))
        handler.write_event(event)

        for event in handler.read_events():
            print(event.function_name)
    """

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        # Garantiza que el directorio padre exista antes de escribir.
        # Si alguien pasa "data/logs/events.jsonl" y "data/logs/" no existe,
        # esto evita un FileNotFoundError sorpresa.
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def write_event(self, event: LineageEvent) -> None:
        """
        Agrega un evento al final del archivo.

        El modo "a" (append) abre el archivo sin truncarlo y posiciona
        el cursor al final. Es la operación O(1) que justifica usar JSONL.
        """
        with self.file_path.open("a", encoding="utf-8") as f:
            f.write(event.to_jsonl_line())

        logger.debug(
            "jsonl.event_written",
            file=str(self.file_path),
            event_id=str(event.id),
        )

    def read_events(self) -> Iterator[LineageEvent]:
        """
        Lee todos los eventos del archivo, uno a la vez (lazy).

        Usamos un generador (yield) en lugar de retornar una lista completa
        porque si el archivo tiene millones de líneas, cargarlas todas en
        memoria de golpe puede tumbar el proceso. El caller decide cuánto
        consumir.
        """
        if not self.file_path.exists():
            logger.warning("jsonl.file_not_found", file=str(self.file_path))
            return

        with self.file_path.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue  # ignora líneas vacías (ej. al final del archivo)

                try:
                    data = json.loads(line)
                    yield LineageEvent.model_validate(data)
                except (json.JSONDecodeError, Exception) as exc:
                    # Una línea corrupta no debe tumbar la lectura de todo
                    # el archivo. La registramos y seguimos con la siguiente.
                    logger.error(
                        "jsonl.corrupted_line",
                        file=str(self.file_path),
                        line_number=line_number,
                        error=str(exc),
                    )
                    continue

    def count_events(self) -> int:
        """Cuenta cuántos eventos hay sin cargar todos en memoria a la vez."""
        return sum(1 for _ in self.read_events())

    def clear(self) -> None:
        """Elimina el archivo. Útil para tests y para reiniciar el log."""
        if self.file_path.exists():
            self.file_path.unlink()
