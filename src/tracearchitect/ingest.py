"""Trace ingestion.

Provides a minimal, dependency-free representation of OpenTelemetry-style
spans and a stub ingestion routine that builds an in-memory trace graph.
This is a placeholder that later architectural-inference stages will build on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional


@dataclass(frozen=True)
class Span:
    """A single OpenTelemetry-style span.

    Only the fields needed for early architectural inference are modeled.
    """

    span_id: str
    trace_id: str
    name: str
    service_name: str
    parent_span_id: Optional[str] = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Span":
        """Build a Span from an OpenTelemetry-style mapping.

        Accepts either flat keys (``span_id``, ``service_name``) or a nested
        ``resource``/``attributes`` shape commonly seen in OTLP exports.
        """

        if "span_id" not in data:
            raise ValueError("span is missing required field 'span_id'")
        if "trace_id" not in data:
            raise ValueError("span is missing required field 'trace_id'")

        resource = data.get("resource", {}) or {}
        service_name = (
            data.get("service_name")
            or resource.get("service.name")
            or data.get("attributes", {}).get("service.name")
            or "unknown"
        )

        return cls(
            span_id=str(data["span_id"]),
            trace_id=str(data["trace_id"]),
            name=str(data.get("name", "")),
            service_name=str(service_name),
            parent_span_id=(
                str(data["parent_span_id"])
                if data.get("parent_span_id") is not None
                else None
            ),
            attributes=dict(data.get("attributes", {})),
        )


@dataclass
class TraceGraph:
    """In-memory representation of ingested spans.

    Indexes spans by id and tracks parent/child relationships plus the set of
    services observed. This is the seed structure for later topology inference.
    """

    spans: Dict[str, Span] = field(default_factory=dict)
    children: Dict[str, List[str]] = field(default_factory=dict)
    services: set = field(default_factory=set)

    def add(self, span: Span) -> None:
        self.spans[span.span_id] = span
        self.services.add(span.service_name)
        if span.parent_span_id is not None:
            self.children.setdefault(span.parent_span_id, []).append(span.span_id)

    def root_spans(self) -> List[Span]:
        """Return spans whose parent is absent from the graph."""

        return [
            s
            for s in self.spans.values()
            if s.parent_span_id is None or s.parent_span_id not in self.spans
        ]

    def __len__(self) -> int:
        return len(self.spans)


def ingest_spans(raw_spans: Iterable[Mapping[str, Any]]) -> TraceGraph:
    """Ingest raw OpenTelemetry-style spans into a :class:`TraceGraph`.

    Args:
        raw_spans: An iterable of span mappings (e.g. decoded OTLP/JSON spans).

    Returns:
        A :class:`TraceGraph` containing the parsed spans, indexed and linked.
    """

    graph = TraceGraph()
    for raw in raw_spans:
        graph.add(Span.from_dict(raw))
    return graph
