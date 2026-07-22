# TraceArchitect

TraceArchitect ingests distributed tracing / telemetry data (OpenTelemetry-style
spans) and performs **architectural inference** — reconstructing system
structure, service topology, and data schemas directly from traces. Instead of
maintaining architecture diagrams by hand, TraceArchitect derives them from what
your system actually does at runtime.

> Status: early scaffold. The ingestion layer is a working stub; inference and
> visualization stages are on the roadmap below.

## Getting Started

Requires Python 3.9+.

```bash
# Clone
git clone https://github.com/777abhi/TraceArchitect.git
cd TraceArchitect

# (optional) create a virtual environment
python -m venv .venv && source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run the test suite
pytest
```

Quick example:

```python
from tracearchitect import ingest_spans

spans = [
    {"span_id": "a", "trace_id": "t1", "name": "GET /orders", "service_name": "gateway"},
    {"span_id": "b", "trace_id": "t1", "name": "query", "parent_span_id": "a",
     "resource": {"service.name": "orders-db"}},
]

graph = ingest_spans(spans)
print(len(graph))            # 2
print(graph.services)        # {'gateway', 'orders-db'}
print(graph.root_spans())    # [Span(span_id='a', ...)]
```

## Project Structure

```
TraceArchitect/
├── src/tracearchitect/     # Package source
│   ├── __init__.py         # Public API exports
│   └── ingest.py           # Span model + trace-graph ingestion stub
├── tests/                  # pytest test suite
│   └── test_ingest.py
├── .github/workflows/ci.yml  # CI: install deps + run tests
├── pyproject.toml          # Project metadata & dependencies
├── .gitignore
├── LICENSE                 # MIT
└── README.md
```

## Learning

- [Agentic AI & Generative AI Test Orchestration — Learning Roadmap](./LEARNING_ROADMAP.md): a 30-minute daily path to master Agentic AI & Generative AI Test Orchestration.

## Roadmap

- [x] Project scaffold (packaging, tests, CI)
- [x] Span model + in-memory trace-graph ingestion stub
- [ ] OTLP (gRPC/HTTP) and JSON trace source adapters
- [ ] Service topology inference (call graph, dependencies)
- [ ] Schema inference from span attributes and payloads
- [ ] Architecture diagram / export (e.g. Mermaid, C4)
- [ ] Drift detection against a declared architecture

## License

[MIT](LICENSE) © Abhinav Sharma
