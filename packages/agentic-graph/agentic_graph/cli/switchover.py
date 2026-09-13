"""Switchover runbook: finalize a Hindsight -> Cognee migration."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.console import Console

from agentic_graph.cli.link import _run_link
from agentic_graph.cli.migrate import _check_auth, _checkpoint_path, _default_token, _default_url, _run_import

app = typer.Typer(name="ag-switchover", help="Finalize a Hindsight -> Cognee migration")
console = Console()


@app.command()
def switchover(
    bank: Annotated[str, typer.Option("--bank", help="Hindsight bank to read from")] = "omp",
    dataset: Annotated[str, typer.Option("--dataset", help="Cognee dataset to write to")] = "hindsight",
    api_url: Annotated[str, typer.Option("--api-url", help="Hindsight base URL")] = _default_url(),
    api_token: Annotated[str, typer.Option("--api-token", help="Hindsight bearer token")] = _default_token(),
    limit: Annotated[int, typer.Option("--limit", help="Memories to import (0 = all)")] = 0,
    resume: Annotated[bool, typer.Option("--resume", help="Resume from checkpoint")] = True,
) -> None:
    """Import remaining Hindsight memories, then link memory entities to the code graph."""
    if not api_token:
        raise typer.BadParameter("--api-token or HINDSIGHT_API_TOKEN is required")

    _check_auth(api_url, api_token)
    checkpoint_path = _checkpoint_path()

    console.print("[bold]Step 1:[/bold] import Hindsight memories into Cognee")
    result = asyncio.run(
        _run_import(
            api_url,
            api_token,
            bank,
            dataset,
            limit,
            1000,
            1000,
            None,
            None,
            resume,
            checkpoint_path,
        )
    )
    console.print(f"  imported: {result['imported']} | total: {result['total']} | skipped: {result.get('skipped', 0)}")

    console.print("[bold]Step 2:[/bold] link memory entities to code graph nodes")
    link_result = asyncio.run(_run_link(dry_run=False))
    console.print(
        f"  edges created: {link_result['edges_created']} across {link_result['memories_with_entities']} memory nodes"
    )

    console.print("[bold green]Switchover complete.[/bold green]")


def main() -> None:
    app()
