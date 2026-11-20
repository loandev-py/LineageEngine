"""Tests de los modelos Pydantic."""

import pytest
from pydantic import ValidationError

from lineage_engine.models.lineage import (
    EventType,
    LineageEvent,
    LineageNode,
    NodeType,
)


class TestLineageNode:
    def test_creates_node_with_valid_data(self) -> None:
        node = LineageNode(name="orders_raw", node_type=NodeType.DATASET)
        assert node.name == "orders_raw"
        assert node.node_type == NodeType.DATASET
        assert node.id is not None
        assert node.created_at is not None

    def test_name_is_lowercased(self) -> None:
        node = LineageNode(name="Orders_Raw", node_type=NodeType.DATASET)
        assert node.name == "orders_raw"

    def test_name_with_spaces_raises_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            LineageNode(name="orders raw", node_type=NodeType.DATASET)
        assert "snake_case" in str(exc_info.value)

    def test_empty_name_raises_error(self) -> None:
        with pytest.raises(ValidationError):
            LineageNode(name="", node_type=NodeType.DATASET)


class TestLineageEvent:
    def test_creates_event_with_valid_data(self) -> None:
        event = LineageEvent(
            event_type=EventType.TRANSFORM,
            function_name="clean_orders",
            input_datasets=["orders_raw"],
            output_datasets=["orders_clean"],
            execution_time_ms=123.45,
        )
        assert event.success is True
        assert event.error_message is None

    def test_to_jsonl_line_ends_with_newline(self) -> None:
        event = LineageEvent(
            event_type=EventType.READ,
            function_name="read_csv",
            execution_time_ms=10.0,
        )
        assert event.to_jsonl_line().endswith("\n")

    def test_error_message_with_success_true_raises(self) -> None:
        with pytest.raises(ValidationError):
            LineageEvent(
                event_type=EventType.TRANSFORM,
                function_name="broken_func",
                execution_time_ms=5.0,
                success=True,
                error_message="Something went wrong",
            )

    def test_negative_execution_time_raises(self) -> None:
        with pytest.raises(ValidationError):
            LineageEvent(
                event_type=EventType.TRANSFORM,
                function_name="fast_func",
                execution_time_ms=-1.0,
            )
