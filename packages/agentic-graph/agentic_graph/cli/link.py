"""Link Hindsight memory entities to code graph nodes."""

from __future__ import annotations

import asyncio
from typing import Annotated

import sqlalchemy as sa
import typer
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

from cognee.infrastructure.databases.graph import use_graph_adapter  # noqa: E402
from agentic_graph.cognee_adapters.agentic_pggraph import AgenticPgGraphAdapter  # noqa: E402

use_graph_adapter("agentic_pggraph", AgenticPgGraphAdapter)

from cognee.infrastructure.databases.unified import get_unified_engine  # noqa: E402

app = typer.Typer(name="ag-link", help="Link memory entities to code graph nodes")
console = Console()


def _split_entities(value: str | None) -> list[str]:
    if not value:
        return []
    return [e.strip() for e in value.split(",") if e.strip()]


async def _run_link(dry_run: bool) -> dict:
    engine = await get_unified_engine()
    graph = engine.graph

    async with graph.sessionmaker() as session:
        memory_rows = await session.execute(
            sa.text(
                "SELECT id, properties FROM graph_node "
                "WHERE type = 'HindsightMemory' AND properties->>'entities' <> ''"
            )
        )
        memories = [
            (str(row["id"]), _split_entities(row["properties"].get("entities")))
            for row in memory_rows.mappings()
        ]

    edges: list[tuple[str, str, str, dict]] = []
    for memory_id, entities in memories:
        for entity in entities:
            entity = entity.lower()
            async with graph.sessionmaker() as session:
                result = await session.execute(
                    sa.text(
                        "SELECT id, type, name FROM graph_node "
                        "WHERE type IN ('CodeSymbol', 'CodeModule', 'CodeFile') "
                        "  AND (LOWER(name) = :entity OR LOWER(name) LIKE :pattern) "
                        "ORDER BY CASE type "
                        "  WHEN 'CodeSymbol' THEN 1 "
                        "  WHEN 'CodeModule' THEN 2 "
                        "  WHEN 'CodeFile' THEN 3 "
                        "END "
                        "LIMIT 1"
                    ),
                    {"entity": entity, "pattern": f"%{entity}%"},
                )
                row = result.mappings().first()
                if row:
                    edges.append(
                        (memory_id, str(row["id"]), "mentions", {"entity": entity})
                    )

    if not dry_run:
        async with graph.sessionmaker() as session:
            await session.execute(
                sa.text("DELETE FROM graph_edge WHERE relationship_name = 'mentions'")
            )
            await session.commit()
        if edges:
            await graph.add_edges(edges)

    return {"memories_with_entities": len(memories), "edges_created": len(edges)}


@app.command()
def link(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Count, do not write")] = False,
) -> None:
    """Create mentions edges from HindsightMemory nodes to code graph nodes."""
    result = asyncio.run(_run_link(dry_run))
    console.print(
        f"[bold green]{result['edges_created']} edges created[/bold green] "
        f"across {result['memories_with_entities']} memory nodes"
    )


def main() -> None:
    app()
