import pytest

from agentic_graph import client


@pytest.fixture(scope="module")
def trace_step():
    step_id = client.trace(
        tool="edit",
        args={"file": "packages/agentic-graph/agentic_graph/server.py"},
        result="explore uses name filter",
        touched_files=["packages/agentic-graph/agentic_graph/server.py"],
        touched_symbols=["explore"],
    )
    return step_id


def test_health():
    assert client.watcher_status() == {"ok": True}


def test_search():
    r = client.search("client", limit=5)
    assert "results" in r
    facts = [f for entry in r["results"] for f in entry.get("facts", [])]
    assert len(facts) > 0


def test_explore():
    r = client.explore("client.watcher_status", depth=1)
    assert "error" not in r, r.get("error")
    assert "results" in r
    focus = r["results"][0]["focus"]
    assert focus["name"].endswith("client.watcher_status")


def test_trace(trace_step):
    assert len(trace_step) > 0


def test_correlate(trace_step):
    r = client.correlate("explore")
    assert trace_step in [s["step_id"] for s in r["traces"]]


def test_sync_incremental(tmp_path):
    repo = tmp_path / "test-repo"
    repo.mkdir()
    (repo / "main.py").write_text("def hello():\n    return 1\n")
    (repo / "lib.py").write_text("def helper():\n    pass\n")

    status = client.sync(str(repo), force=True)
    assert status == "ok"
