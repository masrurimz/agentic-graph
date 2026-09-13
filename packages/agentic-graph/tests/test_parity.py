"""Parity tests for Hindsight -> Cognee migration."""

from __future__ import annotations

import asyncio
import os
import urllib.parse

import httpx
import sqlalchemy as sa
from dotenv import load_dotenv

load_dotenv()

from cognee.infrastructure.databases.graph import use_graph_adapter
from agentic_graph.cognee_adapters.agentic_pggraph import AgenticPgGraphAdapter

use_graph_adapter("agentic_pggraph", AgenticPgGraphAdapter)

from cognee.infrastructure.databases.unified import get_unified_engine


HINDSIGHT_URL = os.environ.get("HINDSIGHT_API_URL", "http://127.0.0.1:28188")
HINDSIGHT_TOKEN = os.environ.get("HINDSIGHT_API_TOKEN", "")
HINDSIGHT_BANK = "omp"


def _hindsight_total() -> int:
    path = f"/v1/default/banks/{urllib.parse.quote(HINDSIGHT_BANK, safe='')}/memories/list"
    with httpx.Client(base_url=HINDSIGHT_URL, timeout=30.0) as client:
        r = client.get(
            path,
            headers={"Authorization": f"Bearer {HINDSIGHT_TOKEN}"},
            params={"limit": 1, "offset": 0},
        )
        r.raise_for_status()
        return r.json().get("total") or 0


async def _cognee_count() -> int:
    engine = await get_unified_engine()
    async with engine.graph.sessionmaker() as session:
        result = await session.execute(
            sa.text("SELECT COUNT(*) FROM graph_node WHERE type = 'HindsightMemory'")
        )
        return result.scalar() or 0


async def _memory_search(query: str) -> list[dict]:
    engine = await get_unified_engine()
    found = await engine.vector.search(
        "HindsightMemory_text", query, limit=3, include_payload=True
    )
    return [
        {
            "id": str(item.id),
            "score": item.score,
            "text": (item.payload or {}).get("text", "")[:200],
        }
        for item in found
    ]


async def main() -> None:
    total_hind = _hindsight_total()
    total_cog = await _cognee_count()
    print(f"Hindsight total: {total_hind}")
    print(f"Cognee HindsightMemory nodes: {total_cog}")
    print(f"Coverage: {total_cog / total_hind:.2%}" if total_hind else "N/A")

    sample = await _memory_search("LynxJS")
    print(f"Sample memory search results: {len(sample)}")
    assert total_cog > 0, "no HindsightMemory nodes in Cognee"
    assert len(sample) > 0, "memory search returned no results"
    print("Parity checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
