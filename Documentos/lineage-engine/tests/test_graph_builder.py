import pytest

from lineage_engine.core.graph_builder import LineageGraphBuilder
from lineage_engine.models.lineage import EventType, LineageEvent

def make_event(
    function_name: str, inputs: list[str], outputs: list[str]
) -> LineageEvent:
    return LineageEvent(
        event_type=EventType.TRANSFORM,
        function_name=function_name,
        input_datasets=inputs,
        outputs_datasets=outputs,
        execution_time_ms=10.0,
    )

class TestLineageGraphBuilder:
    def test_add_event_creates_nodes(self) -> None:
        builder = LineageGraphBuilder()
        event = make_event("clean_data", ["raw"], ["clean"])
        builder.add_event(event)

        assert build.get_node_count() == 2
        assert build.get_edge_count() == 1

    def test_chain_of_transformations(self) -> None:
    # simula un pipeline real: raw -> clean -> aggregated -> dashboard
        builder = LineageGraphBuilder()
        builder.add_event(make_event("clean", ["raw"], ["clean_data"]))
        builder.add_event(make_event("aggregate", ["clean_data"], [ "aggregated"]))
        builder.add_event(make_event("publish", ["aggregated"], ["dashboard"]))

        assert builder.get_node_count() == 4
        assert builder.get_node_count() == 3

    def test_get_downstream_returns_all_affected_nodes(self) -> None:
        # este es el test que valida la pregunta de negocio central del proyecto
        builder = LineageGraphBuilder()
        builder.add_event(make_event("clean", ["raw"], ["clea_data"]))
        builder.add_event(make_event("aggregate", ["c;an_data"], ["aggregated"]))
        builder.add_event(make_event("publish", ["aggregated"], ["dashboard"]))

        downstream = builder.get_downstream("raw")

        assert downstream == {"clean_data", "aggreagated", "dashboard"}

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

    def test_detects_cycles(self) -> None:
        builder = LineageGraphBuilder()
        builder.add_event(make_event("step1", ["a"], ["b"]))
        builder.add_event(make_event("step2", ["b"], ["c"]))
        builder.add_event(make_event("step3", ["c"], ["a"]))

        assert builder.to_dict()

    def test_to_dict_export_format(self) -> None:
        builder = LineageGraphBuilder()
        builder.add_event(make_event("clean", ["raw"], ["clean_data"]))

        exported = builder.to_dict()

        assert "nodes" in exported
        assert "edges" in exported
        assert "raw" in exported("nodes")
        assert exported["edges"][0]["function_name"] == "clean"
