# Cognee single-process memory and agentic graph for OMP plan

Run one Cognee REST server as the only memory and graph process. Add a `cognee` memory backend and a trace extension to OMP in TypeScript. The agent sees the existing `retain`, `recall`, `reflect` tools plus a code-graph and correlate surface. Hindsight stays installed for rollback. The program enforces one rule. Every memory and graph operation goes through the single Cognee process so there is exactly one Python runtime.

PR ids in order. `ag-cognee-server`, `ag-omp-backend`, `ag-trace`, `ag-migrate-bench`.

## How to read this

One box is one unit of work. Every box names the evidence that checks it. A nested box is a sub-step of the box above it. Check a box only when its evidence exists, a file, a log line, a screenshot, a test run, or a SHA. The body is a how-to. The appendices explain and record.

The program runs `skill://poteto-mode/playbooks/autopilot-stack.md`. The operator merges. `ag-omp-backend` and `ag-trace` are the operator's items that stop at merge-ready.

Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

## Program checklist

### Arm the program

- [ ] State the protocol and this plan to the operator, then stop. Start execution only on her explicit go.
- [ ] On her go, pin the program objective at the top of the plan file. "docs/plans/cognee-omp-integration.md, PR ids ag-cognee-server, ag-omp-backend, ag-trace, ag-migrate-bench, the verification rule, the operator merges, done when all four merge."
- [ ] Read these at program start. Re-read them at every tick.
  - [ ] `skill://poteto-mode/playbooks/autopilot-stack.md`
  - [ ] `skill://swarm`
  - [ ] The installed terminal control capability for the CLI surface.
  - [ ] `skill://poteto-mode/playbooks/opening-a-pr.md`
  - [ ] `skill://typescript-best-practices`
- [ ] Arm the 30-minute audit tick through the active adapter's watcher protocol, with a long root-controlled heartbeat fallback. Never leave the cadence to memory or lossy completion notifications.
- [ ] Use this tick prompt, verbatim. "Re-read the execution playbook and the plan's pinned objective. Audit the operation against both and fix drift in this tick. Probe every active lane and judge progress by side effects only. Stand down a stuck lane and dispatch its replacement now. Then send the operator a status message, whether or not anything changed, with the queue table of PR, owner, state, and head SHA, the verdicts since the last tick, what merged, open operator gates, and blockers."
- [ ] On the operator's hold or stand-down, send every owner a zero-writes order at once.

### Spawn owners

- [ ] Spawn one owner per PR with the full lifecycle the execution playbook names.
- [ ] Follow this dependency graph. Start dependent work only after its parent merges, or base it on the parent branch when the execution playbook stacks.
  - [ ] `ag-cognee-server` is independent and first. It stands up the single Cognee process.
  - [ ] `ag-omp-backend` after `ag-cognee-server`. It needs the server's memory endpoints.
  - [ ] `ag-trace` after `ag-cognee-server`. It needs the server's trace and correlate surface.
  - [ ] `ag-migrate-bench` after `ag-omp-backend`. It needs a working `memory.backend: cognee` to compare against.
- [ ] Hold the file boundaries. `ag-cognee-server` touches only `agentic-graph/**`. `ag-omp-backend` touches only `oh-my-pi/packages/coding-agent/src/cognee/**`, `oh-my-pi/packages/coding-agent/src/memory-backend/**`, `oh-my-pi/packages/coding-agent/src/config/settings-schema.ts`, and `oh-my-pi/packages/coding-agent/src/tools/memory-*.ts`. `ag-trace` touches only `oh-my-pi/packages/coding-agent/src/cognee/**` and `agentic-graph/**`. `ag-migrate-bench` touches only `agentic-graph/scripts/**`.
- [ ] Hold the review gate. No PR changes an interaction. All four skip the review gate with a `None.` line.

### PR mechanics, for every PR

- [ ] Open the PR ready, never draft, with `gh pr create` and `draft: false`, or with Graphite `gt` for a stack. If a PR still opens as a draft, run `gh pr ready <number>`.
- [ ] Run the repo's lint and typecheck once before the PR-facing push. Push with hooks on.
- [ ] Apply the **unslop** skill before each commit and the **no-comments** skill before review.
- [ ] Triage every Bugbot and security-reviewer comment per `skill://poteto-mode/references/bugbot-triage.md`.
- [ ] Rebase onto current trunk before babysit and again before the merge-ready report.

### Verdict and merge, for every PR

- [ ] At the merge-ready head SHA, run the swarm per the **swarm** skill. One gates lane. The ten live lanes from the PR's **Verify, live** block. The perf lane from its **Verify, perf** block. One audit lane that reads the diff and the receipts and distrusts the PR body.
- [ ] Clean only when every lane is `PASS`. Findings go back to the owner. A new head gets a fresh swarm and a fresh verdict.
- [ ] The owner squash-merges its own PR after a clean verdict and a rebase with unchanged patch-id, per `skill://poteto-mode/playbooks/shipping.md`.

### Boot recipe, for every live lane

Each live lane runs at the PR head on its own isolated checkout of the PR branch. Drive it through the installed terminal control capability.

- [ ] `git fetch origin <head-branch> && git checkout <head SHA>`.
- [ ] Start the Cognee server. Wait for ready.
- [ ] Deliver input only through the terminal control capability's commands. Name the read-only diagnostics.
- [ ] Save every screenshot to `/tmp/swarm-<pr-id>/worker-<n>/<slug>.png` and return the paths with the report.

## Stand up the single Cognee process (ag-cognee-server)

**Depends on.** None.

**Files.**

- [ ] Edit `agentic-graph/.env`.
- [ ] Create `agentic-graph/agentic_graph/app.py`.
- [ ] Create `agentic-graph/agentic_graph/codegraph.py`.
- [ ] Create `agentic-graph/agentic_graph/steps.py`.
- [ ] Create `agentic-graph/scripts/run_server.sh`.
- [ ] Delete `agentic-graph/agentic_graph/server.py`, `daemon.py`, `client.py`, `tools.py`, `ingest_code.py`, `e2e_test.py`.

**Build.**

- [ ] `.env` sets `LLM_PROVIDER=custom`, `LLM_MODEL=openai/glm-4.5-flash`, `LLM_ENDPOINT=https://api.z.ai/api/coding/paas/v4`, `LLM_API_KEY`, `EMBEDDING_PROVIDER=fastembed`, `EMBEDDING_MODEL`, and `COGNEE_SKIP_CONNECTION_TEST=true`.
- [ ] `app.py` mounts the Cognee FastAPI app and adds the two routes the stock server lacks, so there is still one process.
- [ ] `codegraph.py` adds a `/codegraph/sync` route that runs `get_code_graph_tasks` for a `repo_path` into a dataset, and a `/codegraph/query` route that runs `SearchType.CODE`.
- [ ] `steps.py` adds a `/steps` route that ingests a structured `AgentStep` into a `steps` dataset with a `node_set` for repo and worktree, and a `/correlate` route that joins code facts with steps.
- [ ] `run_server.sh` starts the single process on a configurable port.

**You see.**

- [ ] `bash scripts/run_server.sh` serves `/api/v1/*`, `/codegraph/*`, `/steps`, and `/correlate` on one port.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `agentic-graph/tests/test_app.py` gains a case that posts a step then correlates its file. Run `pytest tests/test_app.py`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten live lanes at the PR head, per the boot recipe.

- [ ] Lane 1. Start the server and `curl /api/v1/datasets`. Save `up.png`. Pass when it returns a list.
- [ ] Lane 2. `POST /api/v1/remember` a fact then `POST /api/v1/recall`. Save `recall.png`. Pass when the fact returns.
- [ ] Lane 3. `POST /codegraph/sync` on a sample repo then `/codegraph/query`. Save `code.png`. Pass when a symbol returns.
- [ ] Lane 4. `POST /steps` a step then `POST /correlate` its file. Save `correlate.png`. Pass when both appear.
- [ ] Lane 5. Recall across two datasets. Save `cross.png`. Pass when both return.
- [ ] Lane 6. Sync two worktrees of one repo then correlate. Save `worktree.png`. Pass when both appear.
- [ ] Lane 7. Recall with a `node_set` filter. Save `tag.png`. Pass when only tagged facts return.
- [ ] Lane 8. `POST /api/v1/forget` a dataset. Save `forget.png`. Pass when recall then returns empty.
- [ ] Lane 9. Recall with the LLM key unset. Save `nokey.png`. Pass when it returns a clean error.
- [ ] Lane 10. Restart the server and recall. Save `persist.png`. Pass when prior facts survive.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. `remember` wall time for one fact.
- [ ] Probe. `time curl /api/v1/remember` at trunk and head, interleaved.
- [ ] Baseline. Record the trunk value first.
- [ ] Rule. Head must not exceed trunk by more than 20 percent.

**Review gate.** None.

**Merge.**

- [ ] Root's clean verdict at the exact head SHA.
- [ ] Bugbot triage done.
- [ ] Rebased onto current trunk after the verdict, patch-id unchanged.
- [ ] The owner squash-merges its own PR.

## Add the cognee memory backend to OMP (ag-omp-backend)

**Depends on.** `ag-cognee-server`.

**Files.**

- [ ] Edit `oh-my-pi/packages/coding-agent/src/memory-backend/types.ts`.
- [ ] Edit `oh-my-pi/packages/coding-agent/src/memory-backend/resolve.ts`.
- [ ] Edit `oh-my-pi/packages/coding-agent/src/config/settings-schema.ts`.
- [ ] Create `oh-my-pi/packages/coding-agent/src/cognee/backend.ts`.
- [ ] Create `oh-my-pi/packages/coding-agent/src/cognee/client.ts`.
- [ ] Create `oh-my-pi/packages/coding-agent/src/cognee/config.ts`.
- [ ] Create `oh-my-pi/packages/coding-agent/src/cognee/state.ts`.
- [ ] Create `oh-my-pi/packages/coding-agent/src/cognee/bank.ts`.
- [ ] Create `oh-my-pi/packages/coding-agent/src/cognee/content.ts`.
- [ ] Edit `oh-my-pi/packages/coding-agent/src/tools/memory-recall.ts`, `memory-retain.ts`, `memory-reflect.ts`, `memory-edit.ts`, `learn.ts`.
- [ ] Edit `oh-my-pi/packages/coding-agent/src/modes/components/settings-defs.ts`.
- [ ] Edit `oh-my-pi/packages/coding-agent/src/modes/controllers/selector-controller.ts`.

**Build.**

- [ ] `types.ts` adds `"cognee"` to `MemoryBackendId`.
- [ ] `settings-schema.ts` adds `"cognee"` to the `memory.backend` enum and a `cognee.*` settings block for `apiUrl`, `apiToken`, `dataset`, `scoping`.
- [ ] `cognee/backend.ts` implements `MemoryBackend` against the Cognee REST server, mirroring `hindsight/backend.ts`.
- [ ] `cognee/client.ts` is a thin `fetch` client for `remember`, `recall`, `improve`, `forget`, `datasets`.
- [ ] `cognee/bank.ts` maps `scoping` to `dataset_name` and `node_set` so `global`, `per-project`, and `per-project-tagged` behave like Hindsight.
- [ ] `resolve.ts` returns the cognee backend for `memory.backend === "cognee"`.
- [ ] Each memory tool's `createIf` accepts `"cognee"`.

**You see.**

- [ ] `memory.backend: cognee` in config makes `recall` return a Cognee result.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `oh-my-pi/packages/coding-agent/test/cognee-backend.test.ts` gains a case that resolves the backend and calls `search`. Run `bun test cognee`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten live lanes at the PR head, per the boot recipe.

- [ ] Lane 1. Set `memory.backend: cognee`, start `omp`, run `recall`. Save `recall.png`. Pass when a Cognee result returns.
- [ ] Lane 2. Run `retain` then `recall` the same fact. Save `retain.png`. Pass when the fact returns.
- [ ] Lane 3. Run `reflect` on a seeded topic. Save `reflect.png`. Pass when a synthesized answer returns.
- [ ] Lane 4. Set `cognee.scoping: per-project`, retain in repo A, recall in repo B. Save `scope.png`. Pass when repo B does not see it.
- [ ] Lane 5. Set `cognee.scoping: global`, retain in repo A, recall in repo B. Save `global.png`. Pass when repo B sees it.
- [ ] Lane 6. Spawn a subagent and recall. Save `subagent.png`. Pass when the subagent reads the parent dataset.
- [ ] Lane 7. Run `/memory view`. Save `view.png`. Pass when the cognee instructions render.
- [ ] Lane 8. Stop the server and run `recall`. Save `down.png`. Pass when the tool returns a clean unavailable message.
- [ ] Lane 9. Switch `memory.backend` back to `hindsight`. Save `rollback.png`. Pass when Hindsight recall works.
- [ ] Lane 10. Run `learn` with `autolearn.enabled`. Save `learn.png`. Pass when the lesson lands in Cognee.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. `recall` round-trip latency.
- [ ] Probe. Time `recall` at trunk (hindsight) and head (cognee), interleaved.
- [ ] Baseline. Record the trunk value first.
- [ ] Rule. Head must not exceed trunk by more than 3x.

**Review gate.** None.

**Merge.**

- [ ] Root's clean verdict at the exact head SHA.
- [ ] Bugbot triage done.
- [ ] Rebased onto current trunk after the verdict, patch-id unchanged.
- [ ] The owner squash-merges its own PR.

## Wire agentic step capture and correlation (ag-trace)

**Depends on.** `ag-cognee-server`.

**Files.**

- [ ] Edit `oh-my-pi/packages/coding-agent/src/cognee/backend.ts`.
- [ ] Create `oh-my-pi/packages/coding-agent/src/cognee/trace.ts`.
- [ ] Edit `agentic-graph/agentic_graph/steps.py`.
- [ ] Edit `agentic-graph/agentic_graph/app.py`.

**Build.**

- [ ] `cognee/backend.ts` `start()` subscribes to the session's tool-call events and POSTs each step to the server `/steps`.
- [ ] `trace.ts` shapes an `AgentStep` from a tool call, its args, its result, and the files and symbols it touched.
- [ ] `steps.py` stores each step with a `node_set` for repo and worktree so `correlate` can join across them.
- [ ] `app.py` `/correlate` joins code-graph facts for a target with the steps that touched it.

**You see.**

- [ ] After an `edit` tool call, `correlate <file>` lists that step.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `agentic-graph/tests/test_correlate.py` gains a case that writes a step then correlates its file. Run `pytest tests/test_correlate.py`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten live lanes at the PR head, per the boot recipe.

- [ ] Lane 1. Run an `omp` session that edits a file, then `correlate` it. Save `edit.png`. Pass when the edit step appears.
- [ ] Lane 2. Correlate a symbol. Save `symbol.png`. Pass when steps touching it appear.
- [ ] Lane 3. Correlate across two repos in one dataset. Save `cross.png`. Pass when both repos' steps appear.
- [ ] Lane 4. Correlate across two worktrees of one repo. Save `worktree.png`. Pass when both worktrees' steps appear.
- [ ] Lane 5. Run `codegraph/query` on a symbol then `correlate` it. Save `explore.png`. Pass when code and steps both return.
- [ ] Lane 6. Run a `search` tool call then `correlate` the query. Save `search.png`. Pass when the search step appears.
- [ ] Lane 7. Correlate a file with no steps. Save `empty.png`. Pass when it returns `count: 0`.
- [ ] Lane 8. Run 100 steps then correlate. Save `scale.png`. Pass when it returns under the latency rule.
- [ ] Lane 9. Restart the server and correlate. Save `restart.png`. Pass when steps persist.
- [ ] Lane 10. Correlate with the code graph empty. Save `nocode.png`. Pass when only steps return.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. `correlate` latency at 1000 stored steps.
- [ ] Probe. `time curl /correlate` at trunk and head, interleaved.
- [ ] Baseline. Record the trunk value first.
- [ ] Rule. Head must return in under 500ms.

**Review gate.** None.

**Merge.**

- [ ] Root's clean verdict at the exact head SHA.
- [ ] Bugbot triage done.
- [ ] Rebased onto current trunk after the verdict, patch-id unchanged.
- [ ] The owner squash-merges its own PR.

## Migrate Hindsight and benchmark both backends (ag-migrate-bench)

**Depends on.** `ag-omp-backend`.

**Files.**

- [ ] Create `agentic-graph/scripts/migrate_hindsight.py`.
- [ ] Create `agentic-graph/scripts/bench_memory.py`.
- [ ] Create `agentic-graph/scripts/bench_inputs.json`.

**Build.**

- [ ] `migrate_hindsight.py` reads every memory from the Hindsight `omp` bank and calls `cognee.remember` into the `omp` dataset, preserving tags as `node_set`.
- [ ] `bench_memory.py` seeds the same corpus into `memory.backend: hindsight` and `memory.backend: cognee`, runs the same query set, and reports retain and recall latency plus top-1 correctness.
- [ ] `bench_inputs.json` holds the shared corpus and query set.

**You see.**

- [ ] `python scripts/migrate_hindsight.py` prints `migrated: <n>` and `python scripts/bench_memory.py` prints a comparison table.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `agentic-graph/tests/test_migrate.py` gains a case that migrates a fixture bank and asserts the count. Run `pytest tests/test_migrate.py`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten live lanes at the PR head, per the boot recipe.

- [ ] Lane 1. Migrate the real `omp` bank. Save `migrate.png`. Pass when the count matches the source.
- [ ] Lane 2. Recall a migrated fact in Cognee. Save `recall.png`. Pass when it returns.
- [ ] Lane 3. Run the bench. Save `bench.png`. Pass when it prints both backends' numbers.
- [ ] Lane 4. Recall a migrated fact by its project tag. Save `tag.png`. Pass when it returns.
- [ ] Lane 5. Recall across two migrated projects. Save `cross.png`. Pass when both return.
- [ ] Lane 6. Re-run the migration. Save `idempotent.png`. Pass when it does not duplicate.
- [ ] Lane 7. Migrate with the server down. Save `down.png`. Pass when it fails cleanly.
- [ ] Lane 8. Bench recall latency. Save `latency.png`. Pass when both backends report a number.
- [ ] Lane 9. Bench top-1 correctness. Save `correct.png`. Pass when both backends report a number.
- [ ] Lane 10. Roll back to `memory.backend: hindsight`. Save `rollback.png`. Pass when Hindsight still works.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Migration throughput in memories per second.
- [ ] Probe. `time python scripts/migrate_hindsight.py` on a 100-memory fixture.
- [ ] Baseline. Record the trunk value first.
- [ ] Rule. Head must migrate at least 1 memory per second.

**Review gate.** None.

**Merge.**

- [ ] Root's clean verdict at the exact head SHA.
- [ ] Bugbot triage done.
- [ ] Rebased onto current trunk after the verdict, patch-id unchanged.
- [ ] The owner squash-merges its own PR.

## Close the program

- [ ] Every box above is checked with its evidence.
- [ ] Reply to the operator with the report the execution playbook names.

## Appendix A. Prototype evidence

Proven. Cognee `remember` and `recall` work end-to-end on this machine with `LLM_PROVIDER=custom`, `LLM_MODEL=openai/glm-4.5-flash`, `LLM_ENDPOINT=https://api.z.ai/api/coding/paas/v4`, and `EMBEDDING_PROVIDER=fastembed`. One `remember` took 25.3s and one `recall` took 19.8s and returned the correct fact. The Cognee REST server exposes `/api/v1/remember`, `/api/v1/recall`, `/api/v1/search`, `/api/v1/cognify`, `/api/v1/improve`, `/api/v1/forget`, `/api/v1/datasets`, and `/api/v1/agents`, so one process covers memory, scoping, and agent lifecycle.

Proven. `glm-5.3`, `glm-5.3-flash`, and `glm-4.5-flash` all returned 200 in the re-probe, so `glm-5.3-flash` is available for fast extraction.

Unproven. Whether the code-graph pipeline is reachable over REST or needs the one `/codegraph` route added to the same app. Whether `node_set` gives the same isolation as Hindsight's tags. Whether a structured `AgentStep` survives `remember` extraction intact or needs a dedicated store.

## Appendix B. Alternatives rejected
A Rust gateway in front of Cognee. Rejected because it adds a second process and a second language for no footprint gain. The Cognee server is already the single process.

Call Cognee's REST server with no added routes. Rejected because the stock server does not expose the code-graph pipeline or a structured step store, so the agent would lose code and trace correlation.

Reimplement Cognee in Rust. Rejected because Cognee's value is its extraction and retrieval pipeline, which is large and already written.

## Appendix C. Risks and mitigations

**Risk 1. Cognee ingestion is slow.**
A single `remember` took ~25s in the prototype because it runs LLM extraction + graph build in one call. If the agent auto-retains every session, it can stall the turn.
**Mitigations.**
- `ag-cognee-server` sets `run_in_background=true` on all `remember` calls so the agent gets an immediate acknowledgement and the extraction queues on the server.
- `ag-omp-backend` keeps the Hindsight-style debounced retain queue at 16 items or 5s and calls `remember` in a batch per flush.
- Code facts are ingested with `add` + `cognify` in a background task, not `remember`, when we only need vector/graph indexing and not fact extraction.
- The mental-model summaries are stored in a dedicated `mental_models` dataset and refreshed only on consolidation (`improve`/`memify`), not on every prompt rebuild.
- The `.env` pins `LLM_MODEL=glm-5.3-flash` for fast extraction, with a fallback to `glm-4.5-flash` if the 5.x quota is hit again.

**Risk 2. Cognee has no built-in mental-model seed cache.**
Hindsight's `seeds.json` keeps three curated summaries (`user-preferences`, `project-conventions`, `project-decisions`) cached and splices them into every prompt. Cognee does not have this object.
**Mitigations.**
- `ag-omp-backend` creates a `mental_models` dataset with `node_set` named `user-preferences` for global, `project-conventions` for the current `project:<cwd>`, and `project-decisions` for the current `project:<cwd>`.
- On `session_start`, recall the three entries and inject them via the existing `buildDeveloperInstructions` path, exactly like Hindsight.
- Refresh each model with `recall` against the relevant dataset + `node_set`, then `improve` the cached summary. Delta refresh is handled by `improve`/`memify`, not by re-running the full `reflect` prompt every turn.
- Cache the mental-model block for the lifetime of the session; only re-fetch on project switch or compaction.

**Risk 3. A structured `AgentStep` may not survive `remember` extraction.**
`remember` extracts facts from free text. A JSON `AgentStep` might be broken into unstructured nodes.
**Mitigations.**
- `ag-trace` stores the canonical step record in a `steps` dataset as a single `add` with `content_type="text"` and the JSON string as the data, then links it to code facts with `correlate`.
- The code graph is a separate `code` dataset; `correlate` joins `code` nodes to `steps` nodes by `node_set` and file path.
- The `/steps` route accepts a structured step and returns the `data_id` the agent can reference, keeping the schema intact.

## Appendix D. Links and reading list

Read `oh-my-pi/packages/coding-agent/src/hindsight/backend.ts` and `oh-my-pi/packages/coding-agent/src/memory-backend/types.ts` before editing. `ag-omp-backend` gets `skill://how` for the memory-backend contract. The trail per `skill://show-me-your-work`.
