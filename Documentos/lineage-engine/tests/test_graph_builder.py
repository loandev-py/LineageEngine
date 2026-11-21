"""Tests del LineageGraphBuilder."""

import pytest

from lineage_engine.core.graph_builder import LineageGraphBuilder
from lineage_engine.models.lineage import EventType, LineageEvent


def make_event(
    function_name: str, inputs: list[str], outputs: list[str]
) -> LineageEvent:
    """Helper para no repetir boilerplate en cada test."""
    return LineageEvent(
        event_type=EventType.TRANSFORM,
        function_name=function_name,
        input_datasets=inputs,
        output_datasets=outputs,
        execution_time_ms=10.0,
    )


class TestLineageGraphBuilder:
    def test_add_event_creates_nodes(self) -> None:
        builder = LineageGraphBuilder()
        event = make_event("clean_data", ["raw"], ["clean"])
        builder.add_event(event)

        assert builder.get_node_count() == 2
        assert builder.get_edge_count() == 1

    def test_chain_of_transformations(self) -> None:
        """
        Simula un pipeline real: raw -> clean -> aggregated -> dashboard
        """
        builder = LineageGraphBuilder()
        builder.add_event(make_event("clean", ["raw"], ["clean_data"]))
        builder.add_event(make_event("aggregate", ["clean_data"], ["aggregated"]))
        builder.add_event(make_event("publish", ["aggregated"], ["dashboard"]))

        assert builder.get_node_count() == 4
        assert builder.get_edge_count() == 3

    def test_get_downstream_returns_all_affected_nodes(self) -> None:
        """Este es el test que valida la pregunta de negocio central del proyecto."""
        builder = LineageGraphBuilder()
        builder.add_event(make_event("clean", ["raw"], ["clean_data"]))
        builder.add_event(make_event("aggregate", ["clean_data"], ["aggregated"]))
        builder.add_event(make_event("publish", ["aggregated"], ["dashboard"]))

        downstream = builder.get_downstream("raw")

        # Si "raw" falla, TODO lo que viene después está en riesgo
        assert downstream == {"clean_data", "aggregated", "dashboard"}

    def test_get_upstream_returns_all_sources(self) -> None:
        builder = LineageGraphBuilder()
        builder.add_event(make_event("clean", ["raw"], ["clean_data"]))
        builder.add_event(make_event("aggregate", ["clean_data"], ["aggregated"]))

        upstream = builder.get_upstream("aggregated")

        assert upstream == {"raw", "clean_data"}

    def test_get_downstream_of_unknown_node_returns_empty_set(self) -> None:
        builder = LineageGraphBuilder()
        result = builder.get_downstream("nodo_que_no_existe")
        assert result == set()

    def test_no_cycles_in_valid_pipeline(self) -> None:
        builder = LineageGraphBuilder()
        builder.add_event(make_event("clean", ["raw"], ["clean_data"]))
        builder.add_event(make_event("aggregate", ["clean_data"], ["aggregated"]))

        assert builder.has_cycles() is False

    def test_detects_cycle(self) -> None:
        """
        Construimos deliberadamente un ciclo: a -> b -> c -> a
        Esto NUNCA debería pasar en un pipeline real, pero el sistema
        debe poder detectarlo si ocurre por error de configuración.
        """
        builder = LineageGraphBuilder()
        builder.add_event(make_event("step1", ["a"], ["b"]))
        builder.add_event(make_event("step2", ["b"], ["c"]))
        builder.add_event(make_event("step3", ["c"], ["a"]))  # cierra el ciclo

        assert builder.has_cycles() is True

    def test_to_dict_export_format(self) -> None:
        builder = LineageGraphBuilder()
        builder.add_event(make_event("clean", ["raw"], ["clean_data"]))

        exported = builder.to_dict()

        assert "nodes" in exported
        assert "edges" in exported
        assert "raw" in exported["nodes"]
        assert exported["edges"][0]["function_name"] == "clean"
