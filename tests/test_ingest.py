from tracearchitect import Span, TraceGraph, ingest_spans


SAMPLE_SPANS = [
    {
        "span_id": "a",
        "trace_id": "t1",
        "name": "GET /orders",
        "service_name": "gateway",
    },
    {
        "span_id": "b",
        "trace_id": "t1",
        "name": "query orders",
        "parent_span_id": "a",
        "resource": {"service.name": "orders-db"},
    },
]


def test_ingest_returns_trace_graph():
    graph = ingest_spans(SAMPLE_SPANS)
    assert isinstance(graph, TraceGraph)
    assert len(graph) == 2


def test_parent_child_and_services():
    graph = ingest_spans(SAMPLE_SPANS)
    assert graph.services == {"gateway", "orders-db"}
    assert graph.children["a"] == ["b"]
    roots = graph.root_spans()
    assert len(roots) == 1
    assert roots[0].span_id == "a"


def test_span_from_dict_nested_service_name():
    span = Span.from_dict(SAMPLE_SPANS[1])
    assert span.service_name == "orders-db"
    assert span.parent_span_id == "a"


def test_missing_required_field_raises():
    import pytest

    with pytest.raises(ValueError):
        Span.from_dict({"trace_id": "t1"})
