"""Migrate Hindsight memory into Cognee with a dry-run first."""

from __future__ import annotations

import asyncio
import json
import os
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

import httpx
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich import box

# Load env before any Cognee import that reads env.
load_dotenv()

# Register the custom Postgres-backed graph adapter before Cognee is used.  # noqa: E402
from cognee.infrastructure.databases.graph import use_graph_adapter  # noqa: E402
from agentic_graph.cognee_adapters.agentic_pggraph import AgenticPgGraphAdapter  # noqa: E402

use_graph_adapter("agentic_pggraph", AgenticPgGraphAdapter)

from cognee.modules.data.methods.create_authorized_dataset import (  # noqa: E402
    create_authorized_dataset,
)
from cognee.modules.engine.operations.setup import setup as cognee_setup  # noqa: E402
from cognee.modules.pipelines.models import PipelineContext  # noqa: E402
from cognee.modules.users.methods import get_default_user  # noqa: E402
from cognee.run_migrations import run_migrations  # noqa: E402
from cognee.tasks.storage import add_data_points  # noqa: E402

from agentic_graph.hindsight import HindsightMemory  # noqa: E402
app = typer.Typer(name="ag-migrate", help="Hindsight -> Cognee memory migration")
console = Console()


def _default_url() -> str:
    return os.environ.get("HINDSIGHT_API_URL", "http://127.0.0.1:28188")


def _default_token() -> str:
    return os.environ.get("HINDSIGHT_API_TOKEN", "")


def _hindsight_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _checkpoint_path(data_root: str | None = None) -> Path:
    root = Path(data_root or os.environ.get("DATA_ROOT_DIRECTORY", ".cognee_data"))
    return root / "hindsight_migration_checkpoint.json"


def _load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _save_checkpoint(path: Path, checkpoint: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(checkpoint, indent=2, default=str))


def _list_memories(
    url: str,
    token: str,
    bank: str,
    limit: int = 100,
    offset: int = 0,
    timeout: float = 30.0,
) -> dict[str, Any]:
    path = f"/v1/default/banks/{urllib.parse.quote(bank, safe='')}/memories/list"
    params = {"limit": limit, "offset": offset}
    with httpx.Client(base_url=url, timeout=timeout) as client:
        r = client.get(path, headers=_hindsight_headers(token), params=params)
        r.raise_for_status()
        return r.json()


def _check_auth(url: str, token: str) -> None:
    with httpx.Client(base_url=url, timeout=10.0) as client:
        r = client.get("/health")
        if r.status_code != 200:
            raise typer.BadParameter(f"Hindsight health failed: {r.status_code}")


def _to_datapoint(item: dict[str, Any]) -> HindsightMemory | None:
    text = (item.get("text") or "").strip()
    if not text:
        return None

    if item.get("state") == "invalidated":
        return None

    return HindsightMemory(
        hindsight_id=str(item.get("id", "")),
        text=text,
        context=item.get("context") or "",
        fact_type=item.get("fact_type") or "",
        date=item.get("date"),
        mentioned_at=item.get("mentioned_at"),
        occurred_start=item.get("occurred_start"),
        occurred_end=item.get("occurred_end"),
        entities=item.get("entities") or "",
        document_id=item.get("document_id"),
        chunk_id=item.get("chunk_id"),
        proof_count=item.get("proof_count") or 0,
        tags=item.get("tags") or [],
        consolidated_at=item.get("consolidated_at"),
        state=item.get("state") or "valid",
    )


def _matches_filters(
    item: dict[str, Any],
    fact_type: str | None,
    since: str | None,
) -> bool:
    if fact_type and item.get("fact_type") != fact_type:
        return False
    if since:
        mentioned = item.get("mentioned_at") or item.get("date") or ""
        if mentioned and mentioned < since:
            return False
    return True


async def _import_batch(
    points: list[HindsightMemory],
    dataset: Any,
    user: Any,
) -> int:
    if not points:
        return 0
    ctx = PipelineContext(
        user=user,
        dataset=dataset,
        data_item=None,
        pipeline_name="hindsight_migration",
    )
    await add_data_points(points, ctx=ctx)
    return len(points)


async def _run_import(
    url: str,
    token: str,
    bank: str,
    dataset_name: str,
    limit: int,
    page_size: int,
    batch_size: int,
    fact_type: str | None,
    since: str | None,
    resume: bool,
    checkpoint_path: Path,
) -> dict[str, Any]:
    await run_migrations()
    await cognee_setup()

    user = await get_default_user()
    dataset = await create_authorized_dataset(dataset_name, user)

    checkpoint: dict[str, Any] = {}
    start_offset = 0
    imported = 0
    if resume and checkpoint_path.exists():
        checkpoint = _load_checkpoint(checkpoint_path)
        start_offset = checkpoint.get("offset", 0)
        imported = checkpoint.get("imported", 0)
        console.print(
            f"[cyan]Resuming from checkpoint {checkpoint_path}: offset={start_offset}, imported={imported}[/cyan]"
        )

    total_page = _list_memories(url, token, bank, limit=1, offset=start_offset)
    total = total_page.get("total") or 0
    if total == 0:
        return {"imported": 0, "total": 0, "skipped": 0}

    to_import = limit if limit > 0 else total
    if to_import > total - start_offset:
        to_import = total - start_offset

    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    )
    task = progress.add_task("Migrating memories...", total=to_import)

    offset = start_offset
    skipped = 0
    started_at = datetime.now(timezone.utc).isoformat()

    with progress:
        while offset < start_offset + to_import:
            remaining = (start_offset + to_import) - offset
            effective_page_size = min(page_size, remaining)
            page = _list_memories(
                url, token, bank, limit=effective_page_size, offset=offset
            )
            page_items = page.get("items") or page.get("data") or []
            if not page_items:
                break

            points: list[HindsightMemory] = []
            for item in page_items:
                if not _matches_filters(item, fact_type, since):
                    skipped += 1
                    continue
                point = _to_datapoint(item)
                if point is None:
                    skipped += 1
                    continue
                points.append(point)

            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                await _import_batch(batch, dataset, user)
                imported += len(batch)
                _save_checkpoint(
                    checkpoint_path,
                    {
                        "bank": bank,
                        "dataset": dataset_name,
                        "offset": offset + len(page_items),
                        "imported": imported,
                        "skipped": skipped,
                        "started_at": started_at,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                progress.update(task, completed=min(imported, to_import))

            offset += len(page_items)
            if offset >= start_offset + to_import:
                break

    _save_checkpoint(
        checkpoint_path,
        {
            "bank": bank,
            "dataset": dataset_name,
            "offset": offset,
            "imported": imported,
            "skipped": skipped,
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {"imported": imported, "total": total, "skipped": skipped}


def _dry_run_preview(
    url: str,
    token: str,
    bank: str,
    limit: int,
    fact_type: str | None,
    since: str | None,
) -> dict[str, Any]:
    _check_auth(url, token)
    data = _list_memories(url, token, bank, limit=limit, offset=0)

    memories = data.get("items") or data.get("data") or []
    total = data.get("total") or len(memories)
    tags: set[str] = set()
    fact_type_counts: dict[str, int] = {}
    skipped = 0

    for m in memories:
        for t in m.get("tags") or []:
            tags.add(t)
        ft = m.get("fact_type") or "unknown"
        fact_type_counts[ft] = fact_type_counts.get(ft, 0) + 1
        if not _matches_filters(m, fact_type, since) or not m.get("text"):
            skipped += 1

    console.print(f"[bold green]Dry-run[/bold green] for Hindsight bank [bold]{bank}[/bold]")
    console.print(f"Total reported: {total} | Fetched: {len(memories)} | Unique tags: {len(tags)}")
    console.print(f"Fact types in sample: {fact_type_counts}")
    if fact_type or since:
        console.print(f"Skipped by filters: {skipped}")

    if not memories:
        console.print("[yellow]No memories returned.[/yellow]")
        raise typer.Exit(0)

    table = Table(title=f"Sample of {bank}", box=box.SIMPLE)
    table.add_column("id", no_wrap=True)
    table.add_column("fact_type")
    table.add_column("tags")
    table.add_column("preview")

    for m in memories[:limit]:
        content = m.get("text", "") or ""
        preview = (content[:80] + "...") if len(content) > 80 else content
        table.add_row(
            str(m.get("id", "-")),
            m.get("fact_type") or "-",
            ", ".join(m.get("tags") or []) or "-",
            preview,
        )
    console.print(table)
    console.print("[cyan]No data was written to Cognee. Run again without --dry-run to import.[/cyan]")

    return {
        "total": total,
        "fetched": len(memories),
        "tags": len(tags),
        "fact_type_counts": fact_type_counts,
        "skipped": skipped,
    }


@app.command()
def migrate(
    bank: Annotated[str, typer.Option("--bank", help="Hindsight bank to read from")] = "omp",
    dataset: Annotated[str, typer.Option("--dataset", help="Cognee dataset to write to")] = "hindsight",
    api_url: Annotated[str, typer.Option("--api-url", help="Hindsight base URL")] = _default_url(),
    api_token: Annotated[str, typer.Option("--api-token", help="Hindsight bearer token")] = _default_token(),
    dry_run: Annotated[bool, typer.Option("--dry-run/--no-dry-run", help="Fetch and report, do not write to Cognee")] = True,
    limit: Annotated[int, typer.Option("--limit", help="Memories to import (0 = all)")] = 0,
    page_size: Annotated[int, typer.Option("--page-size", help="Hindsight list page size")] = 1000,
    fact_type: Annotated[str | None, typer.Option("--fact-type", help="Only import this fact type")] = None,
    batch_size: Annotated[int, typer.Option("--batch-size", help="Cognee add_data_points batch size")] = 1000,
    since: Annotated[str | None, typer.Option("--since", help="Only import memories mentioned on or after this ISO timestamp")] = None,
    resume: Annotated[bool, typer.Option("--resume", help="Resume from checkpoint")] = False,
    data_root: Annotated[str | None, typer.Option("--data-root", help="Cognee data root for checkpoint file")] = None,
) -> None:
    """Read Hindsight memories and (optionally) import them into Cognee."""
    if not api_token:
        raise typer.BadParameter("--api-token or HINDSIGHT_API_TOKEN is required")

    if dry_run:
        _dry_run_preview(api_url, api_token, bank, limit or 10, fact_type, since)
        return

    _check_auth(api_url, api_token)
    checkpoint_path = _checkpoint_path(data_root)

    result = asyncio.run(
        _run_import(
            api_url,
            api_token,
            bank,
            dataset,
            limit,
            page_size,
            batch_size,
            fact_type,
            since,
            resume,
            checkpoint_path,
        )
    )

    console.print(
        f"[bold green]Imported {result['imported']} Hindsight memories into Cognee dataset {dataset}[/bold green]"
    )
    console.print(f"Total in Hindsight bank: {result['total']} | Skipped: {result.get('skipped', 0)}")
    console.print(f"Checkpoint saved to: {checkpoint_path}")


def main() -> None:
    app()
