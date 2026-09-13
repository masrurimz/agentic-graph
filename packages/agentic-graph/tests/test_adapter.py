from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agentic_graph.cognee_adapters.agentic_pggraph import (
    AgenticPgGraphAdapter,
    _graph_name,
    _node_data_from_pggraph,
    _table_ref,
    _valid_identifier,
)


def test_valid_identifier():
    assert _valid_identifier("public") == "public"
    assert _valid_identifier("my_schema_2") == "my_schema_2"
    assert _valid_identifier("_private") == "_private"

    with pytest.raises(ValueError):
        _valid_identifier("has-dash")
    with pytest.raises(ValueError):
        _valid_identifier("2starts_with_digit")
    with pytest.raises(ValueError):
        _valid_identifier("has space")


def test_graph_name_and_table_ref():
    assert _graph_name("") == "agentic"
    assert _graph_name("public") == "agentic_public"
    assert _table_ref("", "graph_node") == "graph_node"
    assert _table_ref("public", "graph_node") == "public.graph_node"


def test_node_data_from_pggraph():
    node = {"_id": 1, "_labels": ["CodeSymbol"], "name": "foo", "type": "function"}
    data = _node_data_from_pggraph(node)
    assert data == {"name": "foo", "type": "function"}


def make_relational_config():
    return SimpleNamespace(
        db_username="cognee",
        db_password="cognee",
        db_host="127.0.0.1",
        db_port="28196",
        db_name="cognee_db",
    )


@patch(
    "agentic_graph.cognee_adapters.agentic_pggraph.get_relational_config",
    return_value=make_relational_config(),
)
def test_adapter_uses_relational_config_when_no_graph_env(_mock):
    adapter = AgenticPgGraphAdapter()
    assert "postgresql+asyncpg://cognee:cognee@127.0.0.1:28196/cognee_db" in adapter.db_uri


@patch(
    "agentic_graph.cognee_adapters.agentic_pggraph.get_relational_config",
    return_value=make_relational_config(),
)
def test_adapter_prefers_explicit_graph_env(_mock, monkeypatch):
    monkeypatch.setenv("GRAPH_DATABASE_HOST", "graph.example.com")
    adapter = AgenticPgGraphAdapter(
        graph_database_username="guser",
        graph_database_password="gpass",
        graph_database_port="5433",
        database_name="gdb",
    )
    assert "postgresql+asyncpg://guser:gpass@graph.example.com:5433/gdb" in adapter.db_uri
