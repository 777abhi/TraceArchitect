"""TraceArchitect: architectural inference from distributed tracing data."""

from tracearchitect.ingest import Span, TraceGraph, ingest_spans

__version__ = "0.1.0"

__all__ = ["Span", "TraceGraph", "ingest_spans", "__version__"]
