from dotenv import load_dotenv

load_dotenv()

from cognee.infrastructure.databases.graph import use_graph_adapter
from agentic_graph.cognee_adapters.agentic_pggraph import AgenticPgGraphAdapter

use_graph_adapter("agentic_pggraph", AgenticPgGraphAdapter)

from agentic_graph.hindsight import HindsightMemory


def test_hindsight_memory():
    m = HindsightMemory(
        hindsight_id="test-1",
        text="hello world",
        context="ctx",
        fact_type="memory",
        date="2026-01-01T00:00:00Z",
        mentioned_at="2026-01-01T00:00:00Z",
        occurred_start=None,
        occurred_end=None,
        entities="",
        document_id=None,
        chunk_id=None,
        proof_count=0,
        tags=["t1"],
        consolidated_at=None,
        state="valid",
    )
    assert m.id
    assert m.text == "hello world"
    assert m.metadata == {"index_fields": ["text"], "identity_fields": ["hindsight_id"]}


if __name__ == "__main__":
    test_hindsight_memory()
