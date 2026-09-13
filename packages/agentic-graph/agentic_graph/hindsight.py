"""Cognee DataPoint for a Hindsight memory unit."""

from __future__ import annotations

from cognee.infrastructure.engine import DataPoint
from cognee.infrastructure.engine.models.DataPoint import MetaData


class HindsightMemory(DataPoint):
    """A memory unit migrated from the Hindsight agent memory server."""

    hindsight_id: str
    text: str
    context: str = ""
    fact_type: str = ""
    date: str | None = None
    mentioned_at: str | None = None
    occurred_start: str | None = None
    occurred_end: str | None = None
    entities: str = ""
    document_id: str | None = None
    chunk_id: str | None = None
    proof_count: int = 0
    tags: list[str] = []
    consolidated_at: str | None = None
    state: str = "valid"
    source_node_set: str = "hindsight"
    metadata: MetaData = {
        "index_fields": ["text"],
        "identity_fields": ["hindsight_id"],
    }
