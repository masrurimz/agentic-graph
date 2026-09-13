---
name: agentic-graph
description: "Use agentic-graph custom tools for code + memory search, correlation, recall, and retention. Replaces Hindsight and graphify in this project."
---

# agentic-graph

This project uses `agentic-graph` (local Cognee server on `http://127.0.0.1:28195`) for code and agentic memory.

When you need context, always prefer these custom tools over the built-in memory tools:

- `agentic_search` — semantic search across code, memory, or both.
- `agentic_correlate` — find related files/symbols/memories for a target.
- `agentic_recall` — vector recall from stored memories.
- `agentic_remember` — persist a fact/lesson into memory.
- `agentic_trace` — record an agentic step with touched files and symbols.
- `agentic_sync` — re-index the worktree code graph.
- `agentic_health` — verify the server is up.

Use `agentic_search` with `scope: "memory"` before answering questions that might rely on prior conversations. Use `agentic_correlate` to follow relationships between code and agentic steps. Use `agentic_remember` to save durable lessons, then `agentic_sync` if the graph needs refreshing.

Hindsight and graphify are disabled for this project (`memory.backend: off`); do not rely on `recall`, `retain`, `reflect`, or `graphify`.
