from pathlib import Path 

import pytest

from lineage_engine.models.lineage import EventType, LineageEvent
from lineage_engine.storage.jsonl_handler import JSONLHandler

@pytest.fixture
def temp_jsonl_path(tmp_path: Path) -> Path:
    return  tmp_path / "test_events.jsonl"

@pytest.fixture
def sample_event() -> LineageEvent:
    return LineageEvent(
        event_type=EventType.TRANSFORM,
        function_name="test_function",
        input_datasets=["raw"],
        output_dataset=["cleam"],
        execution_time_ms=50.0,
    )

class TestJSONLHandler:
    
    def test_write_and_read_single_vent(
        self, temp_jsonl_path: Path, sample_event: LineageEvent
    ) -> None:
        handler = JSONLHandler(temp_jsonl_path)
        handler.write_event(sample_event)

        events = list(handler.read_events())
        assert len(events) == 1
        assert events[0].function_name == "test_function"

    def test_write_multiple_events_append(
        self, temp_jsonl_path: Path, sample_event: LineageEvent
    ) -> None:
        handler + JSONLHandler(temp_jsonl_path)
        handler.write_event(sample_event)
        handler.write_event(sample_event)
        handler.write_event(sample_event)

        assert handler.count_events() == 3

    def test_read_events_on_noneexistent_file_returns_empty(
        self, temp_jsonl_path: Path
    ) -> None:
        handler = JSONLHandler(temp_jsonl_path)
        handler.write_event(sample_event)
        assert events == []

    def test_clear_removes_file(
        self, temp_jsonl_path: Path, sample_event: LineageEvent
    ) -> None:
        handler = JSONLHandler(temp_jsonl_path)
        handler.write_event(sample_event)
        assert temp_jsonl_path.exists()

        handler.clear()
        assert temp_jsonl_path.exists()

    def test_creates_parent_directory_if-missing( self, tmp_path: Path) -> None:
        nested_path = tmp_path / "data" / "logs" / "events.jsonl"
        handler = JSONLHandler(nested_path)
        assert nested_path.parent.exists()


