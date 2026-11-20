🔍 Real-Time Data Lineage Engine

CI Coverage Python Mostrar imagen

"Git history, but for your data."

A system that automatically tracks the origin, transformations, and destination of every piece of data in a pipeline — so when a report breaks at 3 AM, you know in seconds which table, which transformation, and which source caused it.

The Problem

Imagine you're a data engineer at a company with 50+ pipeline transformations. A dashboard breaks. Your manager asks: "Where does this number come from?"

Without data lineage, you spend hours reading SQL files, Airflow DAGs, and Slack messages trying to trace the data back to its source. Mean Time to Detect (MTTD) is measured in hours.

This engine solves that by automatically capturing the complete data graph at runtime — no manual documentation required.

Architecture
┌─────────────────────────────────────────────────────────────────┐
│                     Data Pipeline (your code)                    │
│                                                                   │
│   @track_lineage          with track_block(...)                  │
│   def transform():   ──►  as block:                              │
│       ...                     ...                                │
└──────────────────────────────┬──────────────────────────────────┘
                               │ LineageEvent (Pydantic model)
                               ▼
                    ┌─────────────────────┐
                    │   Apache Kafka      │  ← decouples capture
                    │   Topic: lineage-   │    from storage
                    │         events      │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │    Neo4j     │  │  Prometheus  │  │   JSONL File │
    │  Graph DB    │  │   Metrics    │  │   (backup)   │
    │              │  │              │  │              │
    │ MATCH path   │  │ /metrics     │  │ append-only  │
    │ [:PRODUCES*] │  │ scrape 10s   │  │ generator    │
    └──────┬───────┘  └──────┬───────┘  └──────────────┘
           │                 │
           ▼                 ▼
    ┌──────────────┐  ┌──────────────┐
    │  FastAPI     │  │   Grafana    │
    │  REST API    │  │  Dashboard   │
    │              │  │              │
    │ GET /graph   │  │ localhost:   │
    │ GET /impact  │  │    3000      │
    └──────────────┘  └──────────────┘

Data flow in one sentence: your functions emit LineageEvent objects → Kafka distributes them → a consumer persists them in Neo4j → FastAPI exposes the graph → Grafana visualizes the metrics.

Stack & Why
Technology	Role	Why this, not X?
Python 3.11	Core language	X | Y union types, tomllib built-in
Pydantic v2	Data validation	Runtime type safety + auto JSON serialization
NetworkX	In-memory graph	Standard graph library; nx.descendants() for impact analysis
Neo4j	Graph persistence	Cypher [:PRODUCES*] queries any-depth lineage in one line; SQL JOINs can't
FastAPI	REST API	Pydantic integration, auto /docs, async-ready
Apache Kafka	Event streaming	Decouples capture from storage; handles spikes without data loss
Prometheus	Metrics	Pull-based scraping; Counter/Gauge/Histogram primitives
Grafana	Visualization	Standard in every data platform team
uv	Package manager	10-100x faster than pip; uv.lock for reproducible builds
pytest	Testing	Fixtures with scope="session" for expensive Neo4j connections
Quickstart
Prerequisites
Python 3.11+
uv
Docker Desktop
1. Clone & install
bash
git clone https://github.com/TU_USUARIO/lineage-engine.git
cd lineage-engine
uv sync
2. Start infrastructure
bash
docker compose -f docker/docker-compose.yml up -d

Wait ~15 seconds for Neo4j and Kafka to initialize.

3. Run the demo pipeline
bash
uv run python scripts/demo_pipeline.py

Expected output:

[1] Ejecutando pipeline de datos...
    4 eventos capturados en memoria

[2] Enviando eventos a Neo4j via API...
    4 eventos sincronizados

[3] Consultando el grafo completo...
    Nodos: 5, Aristas: 8

[4] Análisis de impacto: ¿qué se rompe si orders_raw falla?
    Downstream afectados (3):
      → orders_cleaned
      → revenue_by_region
      → dashboard_ventas
4. Explore
Interface	URL	Credentials
Neo4j Browser	http://localhost:7474	neo4j / lineage_password
API Docs (Swagger)	http://localhost:8000/docs	—
Prometheus	http://localhost:9090	—
Grafana	http://localhost:3000	admin / lineage_password

Neo4j query to visualize the full graph:

cypher
MATCH (n)-[r]->(m) RETURN n, r, m

API: impact analysis

bash
curl http://localhost:8000/lineage/impact/orders_raw
5. Run tests
bash
uv run pytest -v

Output: 37 passed with 79% coverage.

Project Structure
lineage-engine/
├── src/
│   └── lineage_engine/
│       ├── models/
│       │   └── lineage.py          # Pydantic models: LineageNode, LineageEvent
│       ├── core/
│       │   ├── tracker.py          # @track_lineage decorator factory
│       │   ├── context_tracker.py  # track_block context manager
│       │   ├── graph_builder.py    # NetworkX DAG wrapper
│       │   └── impact_analyzer.py  # Failure impact analysis
│       ├── storage/
│       │   ├── jsonl_handler.py    # Append-only JSONL with generators
│       │   └── neo4j_repository.py # Repository pattern + Cypher queries
│       ├── api/
│       │   ├── app.py              # FastAPI lifespan, Prometheus mount
│       │   └── routes.py           # REST endpoints
│       ├── streaming/
│       │   ├── kafka_producer.py   # Confluent Kafka producer
│       │   └── kafka_consumer.py   # Daemon thread consumer
│       └── observability/
│           └── metrics.py          # Prometheus Counter/Gauge/Histogram
├── tests/
│   ├── test_models.py
│   ├── test_tracker.py
│   ├── test_graph_builder.py
│   ├── test_impact_analyzer.py
│   ├── test_jsonl_handler.py
│   └── test_api.py                 # Integration tests with real Neo4j
├── docker/
│   ├── docker-compose.yml          # Neo4j, Kafka, Prometheus, Grafana
│   └── prometheus.yml
├── scripts/
│   └── demo_pipeline.py            # End-to-end demo
└── pyproject.toml                  # uv config, deps, pytest, ruff, mypy
Key Engineering Decisions

Why Neo4j instead of PostgreSQL?
Lineage queries are fundamentally graph traversals: "find all nodes reachable from X". In Cypher: MATCH (n {name: 'X'})-[:PRODUCES*]->(downstream). In SQL: recursive CTEs that grow in complexity with each hop. Neo4j is the right tool for the right problem.

Why Kafka instead of direct Neo4j writes?
Decoupling. The pipeline emitting events doesn't need to know about the storage layer. Kafka acts as a buffer — if Neo4j is slow or down, events queue up and nothing is lost. This is the pattern used in production data platforms.

Why the decorator pattern for capture?
Zero-instrumentation adoption. Engineers add @track_lineage(inputs=[...], outputs=[...]) to existing functions without changing their logic. The decorator is transparent — it doesn't modify return values or catch exceptions beyond logging.

Why src/ layout?
Prevents Python from accidentally importing from the project root instead of the installed package. A common source of "works locally, fails in CI" bugs.

What I Learned Building This

This project was built to learn data engineering fundamentals from first principles:

Data modeling with Pydantic v2 — runtime validation, field_validator, model_dump_json()
Graph theory applied to data — DAGs, cycle detection, nx.descendants() for impact analysis
Decorator and context manager patterns — @track_lineage as a decorator factory, __enter__/__exit__ protocol
Repository pattern — encapsulating Neo4j behind an interface, enabling mock-free testing with a real DB
Event streaming with Kafka — topic/producer/consumer model, offset tracking, daemon threads
Observability — Prometheus Counter/Gauge/Histogram primitives, Grafana datasource provisioning
Testing strategy — scope="session" fixtures for expensive connections, autouse=True for cleanup
Author

Hilker — Junior Data Engineer @ Electro Perú
Built as a portfolio project to demonstrate production-grade data engineering patterns.

License

MIT