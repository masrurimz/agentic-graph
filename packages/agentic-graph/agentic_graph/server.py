import json
import os
import uuid
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

from cognee.infrastructure.databases.graph import use_graph_adapter
from agentic_graph.cognee_adapters.agentic_pggraph import AgenticPgGraphAdapter

use_graph_adapter("agentic_pggraph", AgenticPgGraphAdapter)

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
import cognee
from cognee import SearchType
from cognee.modules.engine.operations.setup import setup as cognee_setup
from cognee.shared.logging_utils import setup_logging, ERROR
from cognee.infrastructure.databases.vector.exceptions import CollectionNotFoundError
from cognee.tasks.code_graph import get_code_graph_tasks

setup_logging(log_level=ERROR)

DATASET = os.environ.get("COGNEE_DATASET", "agentic_graph")
STEPS_FILE = os.environ.get(
    "COGNEE_STEPS_FILE",
    "/home/zahid/work/labs/agentic-graph/.cognee_data/agentic_steps.jsonl",
)
class SyncRequest(BaseModel):
    repo_path: str
    force: bool = False

app = FastAPI(title="agentic-graph", default_response_class=ORJSONResponse)

@app.on_event("startup")
async def _startup():
    from cognee.run_migrations import run_migrations

    await run_migrations()
    await cognee_setup()


@app.post("/sync")
async def sync(req: SyncRequest):
    if req.force:
        await cognee.prune.prune_data()
        await cognee.prune.prune_system(graph=True, vector=True, metadata=True, cache=False)
        await cognee_setup()
    await cognee.run_custom_pipeline(
        tasks=get_code_graph_tasks(req.repo_path),
        data=req.repo_path,
        dataset=DATASET,
        pipeline_name="code_graph_pipeline",
        skip_connection_test=True,
    )
    return {"status": "ok"}

class SearchRequest(BaseModel):
    query: str
    scope: str = "code"  # "code" | "memory" | "all"
    limit: int = 10


async def _search_code(query: str, limit: int):
    return await cognee.search(
        query_type=SearchType.CODE,
        query_text=query,
        datasets=[DATASET],
        code_query={
            "operation": "query_facts",
            "kinds": ["module", "symbol"],
            "limit": limit,
        },
    )


async def _search_memory(query: str, limit: int):
	from cognee.infrastructure.databases.unified import get_unified_engine

	try:
		engine = await get_unified_engine()
		found = await engine.vector.search(
			"HindsightMemory_text",
			query,
			limit=limit,
			include_payload=True,
		)
	except CollectionNotFoundError:
		return []

	results = []
	for item in found:
		payload = item.payload or {}
		results.append(
			{
				"id": str(item.id),
				"score": item.score,
				"text": payload.get("text", "")[:500],
				"fact_type": payload.get("fact_type"),
				"tags": payload.get("tags", []),
				"entities": payload.get("entities", ""),
			},
		)
	return results


@app.post("/search")
async def search(req: SearchRequest):
    if req.scope == "code":
        return {"results": await _search_code(req.query, req.limit)}
    if req.scope == "memory":
        return {"results": await _search_memory(req.query, req.limit)}
    if req.scope == "all":
        code_results = await _search_code(req.query, req.limit)
        memory_results = await _search_memory(req.query, req.limit)
        return {"results": {"code": code_results, "memory": memory_results}}
    return {"error": f"unknown scope: {req.scope}"}


class ExploreRequest(BaseModel):
    target: str
    direction: str = "callers"
    depth: int = 2


@app.post("/explore")
async def explore(req: ExploreRequest):
    facts = await cognee.search(
        query_type=SearchType.CODE,
        query_text="",
        datasets=[DATASET],
        code_query={
            "operation": "query_facts",
            "kinds": ["symbol"],
            "name": req.target,
            "limit": 10,
        },
    )
    fact_id = _first_fact_id(facts, req.target)
    if not fact_id:
        return {"error": f"no symbol matching {req.target}"}
    results = await cognee.search(
        query_type=SearchType.CODE,
        query_text="",
        datasets=[DATASET],
        code_query={
            "operation": "explore",
            "id": fact_id,
            "max_depth": req.depth,
        },
    )
    return {"results": results}


class TraceRequest(BaseModel):
    step_id: Optional[str] = None
    tool: str = ""
    args: dict = {}
    result: str = ""
    touched_files: List[str] = []
    touched_symbols: List[str] = []
    parent_step_id: Optional[str] = None


@app.post("/trace")
async def trace(req: TraceRequest):
    sid = req.step_id or str(uuid.uuid4())
    step = {
        "step_id": sid,
        "tool": req.tool,
        "args": req.args,
        "result": req.result,
        "touched_files": req.touched_files,
        "touched_symbols": req.touched_symbols,
        "parent_step_id": req.parent_step_id,
    }
    os.makedirs(os.path.dirname(STEPS_FILE), exist_ok=True)
    with open(STEPS_FILE, "a") as f:
        f.write(json.dumps(step) + "\n")
    return {"step_id": sid}


class CorrelateRequest(BaseModel):
    target: str
    scope: str = "all"  # "code" | "memory" | "all"
    limit: int = 10


@app.post("/correlate")
async def correlate(req: CorrelateRequest):
    code_results = []
    memory_results = []

    if req.scope in ("code", "all"):
        code_results = await cognee.search(
            query_type=SearchType.CODE,
            query_text=req.target,
            datasets=[DATASET],
            code_query={
                "operation": "query_facts",
                "kinds": ["module", "symbol"],
                "limit": req.limit,
            },
        )

    if req.scope in ("memory", "all"):
        memory_results = await _search_memory(req.target, req.limit)

    traces = []
    if os.path.exists(STEPS_FILE):
        with open(STEPS_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                step = json.loads(line)
                fields = (
                    step.get("touched_files", [])
                    + step.get("touched_symbols", [])
                    + [step.get("result", ""), step.get("tool", "")]
                )
                if any(req.target in str(field) for field in fields):
                    traces.append(step)

    return {
        "code_results": code_results,
        "memory_results": memory_results,
        "traces": traces,
    }


@app.get("/health")
async def health():
    return {"ok": True}


def _first_fact_id(results, target):
    for entry in results:
        for f in entry.get("facts", []):
            name = f.get("name", "")
            file_path = f.get("file", "")
            if target in name or target in file_path:
                return f.get("id")
    return None


class RememberRequest(BaseModel):
    data: str
    dataset_name: str = "agentic_graph"
    node_set: Optional[List[str]] = []



class RecallRequest(BaseModel):
	query: str
	dataset_name: str = "agentic_graph"
	node_set: Optional[List[str]] = []
	top_k: int = 5


@app.post("/api/v1/remember")
async def remember(req: RememberRequest):
	result = await cognee.remember(
		data=req.data,
		dataset_name=req.dataset_name,
		node_set=req.node_set,
	)
	return {
		"status": result.status,
		"dataset_id": result.dataset_id,
		"dataset_name": result.dataset_name,
	}


@app.post("/api/v1/recall")
async def recall(req: RecallRequest):
    results = await cognee.recall(
        query_text=req.query,
        datasets=[req.dataset_name],
        query_type=SearchType.SUMMARIES,
        auto_route=True,
        only_context=False,
        top_k=req.top_k,
    )
    return {"results": results}


def main() -> None:
    import granian
    import threading
    from granian.constants import HTTPModes, Interfaces, Loops

    server = granian.Granian(
        target="agentic_graph.server:app",
        address=os.environ.get("COGNEE_HOST", "127.0.0.1"),
        port=int(os.environ.get("COGNEE_PORT", "28195")),
        interface=Interfaces.ASGI,
        loop=Loops.uvloop,
        workers=1,
        websockets=False,
        http=HTTPModes.http1,
        runtime_threads=1,
        blocking_threads=1,
    )
    setup_logging(log_level=ERROR)
    print(f"[agentic-graph] starting on {os.environ.get('COGNEE_HOST', '127.0.0.1')}:{os.environ.get('COGNEE_PORT', '28195')}; threads before serve: {threading.active_count()}")
    server.serve()
