"""End-to-end scenario for testing the agentic-graph server against a target repo."""

from __future__ import annotations

import json
import os
from typing import Annotated

import typer
from rich.console import Console

from agentic_graph.client import (
    correlate,
    explore,
    recall,
    remember,
    search,
    sync,
    trace,
    watcher_status,
)

app = typer.Typer(name="ag-scenario", help="Run an agentic-graph scenario against a repo")
console = Console()


def _pp(value: object) -> None:
    console.print_json(json.dumps(value, default=str))


@app.command()
def scenario(
    repo_path: Annotated[str, typer.Argument(help="Path to the repo to index")],
    query: Annotated[str, typer.Option("--query", help="Search query")] = "main",
    symbol: Annotated[str, typer.Option("--symbol", help="Symbol to explore")] = "",
    file: Annotated[str, typer.Option("--file", help="File to trace/correlate")] = "main.py",
    force: Annotated[bool, typer.Option("--force", help="Wipe the dataset and re-index")] = False,
) -> None:
    """Index a repo, then exercise search, explore, trace, correlate, remember, and recall."""
    repo = os.path.abspath(repo_path)
    target = symbol or query
    file_path = os.path.join(repo, file)

    console.print("health:", watcher_status())

    console.print(f"\n1. sync (force={force}):")
    console.print("  status:", sync(repo, force=force))

    console.print(f"\n2. search {query!r}:")
    _pp(search(query, scope="code", limit=3))

    console.print(f"\n3. explore {target!r}:")
    _pp(explore(target, depth=1))

    console.print(f"\n4. trace a fake edit of {file}:")
    step_id = trace(
        tool="edit",
        args={"file": file_path},
        result="scenario test",
        touched_files=[file_path],
        touched_symbols=[target],
        parent_step_id="",
    )
    console.print("  step_id:", step_id)

    console.print(f"\n5. correlate {file}:")
    _pp(correlate(file_path))

    console.print("\n6. remember a fact:")
    _pp(remember(f"Scenario memory for {repo}", dataset_name="agentic_graph", node_set=[repo]))

    console.print("\n7. recall that fact:")
    _pp(recall("scenario memory", dataset_name="agentic_graph", node_set=[repo], top_k=3))


def main() -> None:
    app()
