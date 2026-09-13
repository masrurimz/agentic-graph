# agentic-graph

agentic-graph indexes a repository into a code knowledge graph and records what your agent did to it. It serves both over a small HTTP API, so any tool can ask where a symbol lives, who calls it, and which agent steps touched it. Cognee drives the indexing. Postgres with pgvector and pgGraph stores everything. One process per concern, no Neo4j.

Agents re-read the same files every session. With a graph behind an API, they ask instead of grep, and the trace log tells you what happened last run.

For how the pieces fit together, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- Docker, for Postgres
- An API key for an OpenAI-compatible LLM endpoint
- The enola code extractor, referenced by `ENOLA_PATH` in `.env`

## Install

```bash
git clone https://github.com/masrurimz/agentic-graph.git
cd agentic-graph
cp .env.example .env
```

Edit `.env` before the first run. Set `LLM_ENDPOINT`, `LLM_MODEL`, and `LLM_API_KEY` to your provider. Point `DATA_ROOT_DIRECTORY`, `SYSTEM_ROOT_DIRECTORY`, and `ENOLA_PATH` at absolute paths on your machine.

```bash
uv sync
```

## Start Postgres

```bash
docker compose up -d postgres
```

This builds a Postgres 17 image with pgvector and pgGraph, then listens on `127.0.0.1:28196`. The credentials in `.env.example` match the compose file.

## Run the server

```bash
uv run ag-server
```

The server runs Cognee migrations at startup and listens on `127.0.0.1:28195`. Set `COGNEE_HOST` and `COGNEE_PORT` in `.env` to change that.

Check it:

```bash
curl -s http://127.0.0.1:28195/health
# {"ok":true}
```

## Index a repository

One-shot:

```bash
curl -s -X POST http://127.0.0.1:28195/sync \
  -H 'Content-Type: application/json' \
  -d '{"repo_path": "/abs/path/to/repo"}'
```

Add `"force": true` to wipe the dataset and index from scratch.

Or keep it fresh while you work:

```bash
uv run ag-watch /abs/path/to/repo
```

`ag-watch` runs one full index at startup, then re-syncs about 2 seconds after each file change. Pass `--debounce 5` to wait longer. It skips `.git`, `.venv`, `node_modules`, caches, and files without a source suffix.

## Query the graph

Search for modules and symbols, or search Hindsight memories, or both at once:

```bash
curl -s -X POST http://127.0.0.1:28195/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "graph adapter", "scope": "code", "limit": 5}'

curl -s -X POST http://127.0.0.1:28195/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "LynxJS", "scope": "memory", "limit": 5}'

curl -s -X POST http://127.0.0.1:28195/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "agentic", "scope": "all", "limit": 5}'
```

Traverse callers of a symbol:

```bash
curl -s -X POST http://127.0.0.1:28195/explore \
  -H 'Content-Type: application/json' \
  -d '{"target": "AgenticPgGraphAdapter", "direction": "callers", "depth": 2}'
```

Or use the Python client, which the daemon also uses:

```python
from agentic_graph.client import sync, search, explore

sync("/abs/path/to/repo")
search("graph adapter", limit=5)
explore("AgenticPgGraphAdapter", direction="callers", depth=2)
```
Then ask for code, memory, and traces together:

```bash
curl -s -X POST http://127.0.0.1:28195/correlate \
  -H 'Content-Type: application/json' \
  -d '{"target": "src/app.py", "scope": "all", "limit": 5}'
```

The response has `code_results` from the graph, `memory_results` from the Hindsight memory dataset, and `traces` from the step log.

## Store and recall memories

```bash
curl -s -X POST http://127.0.0.1:28195/api/v1/remember \
  -H 'Content-Type: application/json' \
  -d '{"data": "Deploys go through the blue pipeline on Fridays"}'

curl -s -X POST http://127.0.0.1:28195/api/v1/recall \
  -H 'Content-Type: application/json' \
  -d '{"query": "how do we deploy?", "top_k": 5}'
```

## Migrate Hindsight memories

`ag-migrate` copies memories from a Hindsight server into a Cognee dataset. It defaults to a dry run, so start there.

```bash
export HINDSIGHT_API_TOKEN=your-hindsight-token
uv run ag-migrate --bank omp --dry-run --limit 10
```

Import for real once the preview looks right:

```bash
uv run ag-migrate --bank omp --no-dry-run
```

Useful options:

- `--limit 100` for a partial run
- `--fact-type preference` or `--since 2026-01-01` to filter what imports
- `--resume` to continue from the last checkpoint

Checkpoints go to `.cognee_data/hindsight_migration_checkpoint.json` after every batch. Imported memories land in the `hindsight` dataset, so query them through `POST /search` with `"scope": "memory"`.

After a migration, link memory entities to code graph nodes:

```bash
uv run ag-link
```

After `ag-migrate` finishes, run the switchover runbook to link entities and verify parity:

```bash
uv run ag-switchover
```


## Run the tests

```bash
uv run pytest
```

## Run everything in Docker

```bash
docker compose up -d --build
```

This starts Postgres and the agentic-graph container. The API stays on `127.0.0.1:28195`.

## License

MIT. See [LICENSE](LICENSE).
