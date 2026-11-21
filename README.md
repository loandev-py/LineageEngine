# Real-Time Data Lineage Engine

[![CI](https://github.com/loandev-py/LineageEngine/actions/workflows/ci.yml/badge.svg)](https://github.com/loandev-py/LineageEngine/actions)
[![Coverage](https://img.shields.io/badge/coverage-79%25-brightgreen)](https://github.com/loandev-py/LineageEngine)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)

> **"Git history, but for your data."**
>
> A system that automatically tracks the origin, transformations, and destination
> of every piece of data in a pipeline. When a report breaks at 3 AM,
> you know in seconds which table, which transformation, and which source caused it.

## The Problem

Imagine you are a data engineer with 50+ pipeline transformations. A dashboard breaks.
Your manager asks: "Where does this number come from?"

Without data lineage, you spend hours reading SQL files and Slack messages tracing
data back to its source. **Mean Time to Detect (MTTD) is measured in hours.**

This engine solves that by automatically capturing the complete data graph at runtime.

## Architecture

```
+------------------------------------------------------------------+
|                     Data Pipeline (your code)                    |
|   @track_lineage          with track_block(...) as block:        |
|   def transform():   -->      ...                                |
+-------------------------------+----------------------------------+
                                | LineageEvent (Pydantic model)
                                v
                   +----------------------+
                   |    Apache Kafka      |
                   |  Topic: lineage-     |
                   |        events        |
                   +-----------+----------+
                               |
             +-----------------+-----------------+
             v                 v                 v
   +---------------+  +--------------+  +--------------+
   |    Neo4j      |  |  Prometheus  |  |  JSONL File  |
   |  Graph DB     |  |   Metrics    |  |   (backup)   |
   +-------+-------+  +------+-------+  +--------------+
           |                 |
           v                 v
   +---------------+  +--------------+
   |   FastAPI     |  |   Grafana    |
   |   REST API    |  |  Dashboard   |
   +---------------+  +--------------+
```

## Stack & Why

| Technology | Role | Why this, not X? |
|------------|------|-----------------|
| **Python 3.11** | Core language | Modern type hints |
| **Pydantic v2** | Data validation | Runtime type safety + auto JSON serialization |
| **NetworkX** | In-memory graph | nx.descendants() for impact analysis |
| **Neo4j** | Graph persistence | Cypher [:PRODUCES*] queries any-depth lineage in one line |
| **FastAPI** | REST API | Pydantic integration, auto /docs |
| **Apache Kafka** | Event streaming | Decouples capture from storage |
| **Prometheus** | Metrics | Counter/Gauge/Histogram primitives |
| **Grafana** | Visualization | Standard in every data platform team |
| **uv** | Package manager | 10-100x faster than pip |

## Quickstart

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 1. Clone & install
```bash
git clone https://github.com/loandev-py/lineage-engine.git
cd lineage-engine
uv sync
```

### 2. Start infrastructure
```bash
docker compose -f docker/docker-compose.yml up -d
```

### 3. Run the demo pipeline
```bash
uv run python scripts/demo_pipeline.py
```

### 4. Explore

| Interface | URL | Credentials |
|-----------|-----|-------------|
| Neo4j Browser | http://localhost:7474 | neo4j / lineage_password |
| API Docs | http://localhost:8000/docs | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin / lineage_password |

```cypher
MATCH (n)-[r]->(m) RETURN n, r, m
```

```bash
curl http://localhost:8000/lineage/impact/orders_raw
```

### 5. Run tests
```bash
uv run pytest -v
```

## Project Structure

```
lineage-engine/
+-- src/lineage_engine/
|   +-- models/lineage.py
|   +-- core/tracker.py
|   +-- core/graph_builder.py
|   +-- core/impact_analyzer.py
|   +-- storage/neo4j_repository.py
|   +-- api/routes.py
|   +-- streaming/kafka_producer.py
|   +-- observability/metrics.py
+-- tests/                     # 37 tests, 79% coverage
+-- docker/docker-compose.yml  # Neo4j, Kafka, Prometheus, Grafana
+-- scripts/demo_pipeline.py
+-- pyproject.toml
```

## Key Engineering Decisions

**Why Neo4j?** Lineage queries are graph traversals. `MATCH (n)-[:PRODUCES*]->(d)` in one line. SQL needs recursive CTEs that grow with each hop.

**Why Kafka?** Decoupling. If Neo4j is slow or down, events queue up and nothing is lost.

**Why decorators?** Zero-instrumentation. Add `@track_lineage` to existing functions without changing their logic.

## What I Learned

- Pydantic v2: runtime validation, field_validator, model_dump_json()
- Graph theory applied to data: DAGs, cycle detection, nx.descendants()
- Decorator and context manager patterns
- Repository pattern for testable database access
- Kafka: topic/producer/consumer model, daemon threads
- Prometheus Counter/Gauge/Histogram, Grafana provisioning
- pytest fixtures with scope="session" and autouse=True

## Author

**Hilker** — Junior Data Engineer @ Electro Perú

## License

MIT