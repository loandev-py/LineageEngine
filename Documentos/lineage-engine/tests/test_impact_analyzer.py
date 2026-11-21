"""Tests del ImpactAnalyzer."""

from lineage_engine.core.graph_builder import LineageGraphBuilder
from lineage_engine.core.impact_analyzer import ImpactAnalyzer
from lineage_engine.models.lineage import EventType, LineageEvent


def make_event(
    function_name: str, inputs: list[str], outputs: list[str]
) -> LineageEvent:
    return LineageEvent(
        event_type=EventType.TRANSFORM,
        function_name=function_name,
        input_datasets=inputs,
        output_datasets=outputs,
        execution_time_ms=10.0,
    )


class TestImpactAnalyzer:
    def test_analyze_failure_returns_downstream_and_upstream(self) -> None:
        builder = LineageGraphBuilder()
        builder.add_event(make_event("clean", ["raw"], ["clean_data"]))
        builder.add_event(make_event("aggregate", ["clean_data"], ["dashboard"]))

        analyzer = ImpactAnalyzer(builder)
        report = analyzer.analyze_failure("clean_data")

        assert report.downstream_nodes == {"dashboard"}
        assert report.upstream_nodes == {"raw"}
        assert report.total_affected == 1

    def test_isolated_node_has_no_impact(self) -> None:
        builder = LineageGraphBuilder()
        builder.add_event(make_event("clean", ["raw"], ["clean_data"]))

        analyzer = ImpactAnalyzer(builder)
        # "raw" no tiene upstream, pero sí downstream — no está aislado
        report = analyzer.analyze_failure("raw")
        assert report.is_isolated is False

    def test_find_critical_nodes_orders_by_impact(self) -> None:
        """
        Construimos un grafo donde "raw" es claramente el nodo más crítico:
        si falla, afecta a 3 nodos downstream.
        """
        builder = LineageGraphBuilder()
        builder.add_event(make_event("clean", ["raw"], ["clean_data"]))
        builder.add_event(make_event("agg1", ["clean_data"], ["report_a"]))
        builder.add_event(make_event("agg2", ["clean_data"], ["report_b"]))

        analyzer = ImpactAnalyzer(builder)
        critical = analyzer.find_critical_nodes(top_n=1)

        assert critical[0][0] == "raw"
        assert critical[0][1] == 3  # afecta a clean_data, report_a, report_b
