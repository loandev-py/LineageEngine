"""Tests del decorador @track_lineage."""

import time

import pytest

from lineage_engine.core.tracker import (
    clear_events,
    get_captured_events,
    track_lineage,
)


@pytest.fixture(autouse=True)
def reset_event_store() -> None:
    """Se ejecuta antes de cada test para que no se contaminen entre sí."""
    clear_events()


class TestTrackLineageDecorator:
    def test_captures_successful_execution(self) -> None:
        @track_lineage(inputs=["raw"], outputs=["clean"])
        def my_transform(x: int) -> int:
            return x * 2

        result = my_transform(5)

        assert result == 10
        events = get_captured_events()
        assert len(events) == 1
        assert events[0].function_name == "my_transform"
        assert events[0].success is True
        assert events[0].input_datasets == ["raw"]
        assert events[0].output_datasets == ["clean"]

    def test_captures_failed_execution(self) -> None:
        @track_lineage(inputs=["raw"], outputs=["clean"])
        def failing_transform() -> None:
            raise ValueError("Dataset corrupto")

        with pytest.raises(ValueError):
            failing_transform()

        events = get_captured_events()
        assert len(events) == 1
        assert events[0].success is False
        assert "Dataset corrupto" in events[0].error_message  # type: ignore

    def test_preserves_function_name(self) -> None:
        @track_lineage(inputs=[], outputs=["result"])
        def compute_revenue() -> float:
            return 42.0

        assert compute_revenue.__name__ == "compute_revenue"

    def test_captures_execution_time(self) -> None:
        @track_lineage(inputs=[], outputs=["out"])
        def slow_function() -> None:
            time.sleep(0.01)

        slow_function()
        events = get_captured_events()
        assert events[0].execution_time_ms >= 10.0

    def test_multiple_executions_captured(self) -> None:
        @track_lineage(inputs=["source"], outputs=["dest"])
        def pipeline_step() -> str:
            return "ok"

        pipeline_step()
        pipeline_step()
        pipeline_step()

        assert len(get_captured_events()) == 3
