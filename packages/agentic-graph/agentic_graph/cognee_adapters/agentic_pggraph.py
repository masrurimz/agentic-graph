"""Cognee graph adapter backed by Postgres + pgGraph.

Inherits the table-based storage from Cognee's PostgresDemoAdapter and adds
pgGraph graph index registration so graph traversal can use pgGraph functions.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from sqlalchemy import text
from cognee.infrastructure.databases.graph.graph_db_interface import EdgeData, Node, NodeData
from cognee.infrastructure.databases.graph.postgres_demo.adapter import PostgresDemoAdapter
from cognee.infrastructure.databases.relational import get_relational_config


def _valid_identifier(name: str) -> str:
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise ValueError(f"Invalid Postgres identifier: {name!r}")
    return name


def _graph_name(schema: str) -> str:
    return _valid_identifier(f"agentic_{schema}" if schema else "agentic")


def _table_ref(schema: str, table: str) -> str:
    if schema:
        return f'{_valid_identifier(schema)}.{_valid_identifier(table)}'
    return _valid_identifier(table)


def _node_data_from_pggraph(node: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a pgGraph hydrated node JSONB object into Cognee NodeData."""
    data = dict(node)
    data.pop("_id", None)
    data.pop("_labels", None)
    return data


class AgenticPgGraphAdapter(PostgresDemoAdapter):
    """GraphDBInterface adapter that stores nodes/edges in Postgres tables and
    mirrors them to a pgGraph in-memory graph projection for fast traversal.
    """

    supports_cypher_queries = False

    def __init__(
        self,
        graph_database_url: str = "",
        graph_database_username: str = "",
        graph_database_password: str = "",
        graph_database_port: str = "",
        graph_database_key: str = "",
        database_name: str = "",
        **kwargs: Any,
    ) -> None:
        """Accept the kwargs Cognee passes to registered adapters and build a
        SQLAlchemy connection string. When no explicit graph_* credentials are
        provided, fall back to the relational DB config, matching the built-in
        Postgres branch.
        """
        if graph_database_url:
            connection_string = graph_database_url
        elif all(
            [
                graph_database_username,
                graph_database_password,
                os.environ.get("GRAPH_DATABASE_HOST"),
                graph_database_port,
                database_name,
            ]
        ):
            db_host = os.environ.get("GRAPH_DATABASE_HOST")
            db_port = graph_database_port
            connection_string = (
                f"postgresql+asyncpg://{graph_database_username}:{graph_database_password}"
                f"@{db_host}:{db_port}/{database_name}"
            )
        else:
            r = get_relational_config()
            if not all([r.db_username, r.db_password, r.db_host, r.db_port, r.db_name]):
                raise EnvironmentError("Missing Postgres graph credentials")
            connection_string = (
                f"postgresql+asyncpg://{r.db_username}:{r.db_password}"
                f"@{r.db_host}:{r.db_port}/{r.db_name}"
            )

        schema = database_name if database_name else ""
        super().__init__(connection_string=connection_string, schema=schema)

    async def initialize(self) -> None:
        """Create tables and register them with pgGraph."""
        await super().initialize()
        if getattr(self, "_pggraph_initialized", False):
            return

        graph_name = _graph_name(self.schema)
        node_table = _table_ref(self.schema, "graph_node")
        edge_table = _table_ref(self.schema, "graph_edge")

        # Register the graph and tables in one transaction.
        async with self.engine.begin() as conn:
            result = await conn.execute(
                text(
                    f"SELECT COUNT(*) FROM graph.list_graphs() WHERE graph_name = '{graph_name}'"
                )
            )
            exists = result.scalar() or 0
            if exists == 0:
                await conn.execute(text(f"SELECT graph.create_graph('{graph_name}')"))
            await conn.execute(text(f"SELECT graph.set_current_graph('{graph_name}')"))

            result = await conn.execute(
                text(
                    f"SELECT COUNT(*) FROM graph.registered_tables_for_graph('{graph_name}') "
                    f"WHERE table_name = '{node_table}'"
                )
            )
            if (result.scalar() or 0) == 0:
                await conn.execute(
                    text(
                        f"SELECT graph.add_table_to_graph(\n"
                        f"  '{graph_name}',\n"
                        f"  '{node_table}'::regclass,\n"
                        f"  id_column := 'id',\n"
                        f"  columns := ARRAY['name', 'type']\n"
                        f")"
                    )
                )

            result = await conn.execute(
                text(
                    f"SELECT COUNT(*) FROM graph.registered_edges_for_graph('{graph_name}') "
                    f"WHERE from_table = 'graph_edge'"
                )
            )
            if (result.scalar() or 0) == 0:
                await conn.execute(
                    text(
                        f"SELECT graph.add_edge_to_graph(\n"
                        f"  '{graph_name}',\n"
                        f"  '{edge_table}'::regclass,\n"
                        f"  'source_id',\n"
                        f"  '{node_table}'::regclass,\n"
                        f"  'target_id',\n"
                        f"  label := 'rel',\n"
                        f"  label_column := 'relationship_name',\n"
                        f"  bidirectional := false\n"
                        f")"
                    )
                )

        # Build and load must run in a separate transaction after registration.
        async with self.engine.begin() as conn:
            await conn.execute(text(f"SELECT graph.set_current_graph('{graph_name}')"))
            await conn.execute(text(f"SELECT graph.build_graph('{graph_name}')"))

        self._pggraph_initialized = True

    async def _ensure_pggraph_loaded(self) -> None:
        """Load the current pgGraph projection into this session."""
        graph_name = _graph_name(self.schema)
        async with self.engine.begin() as conn:
            await conn.execute(text(f"SELECT graph.set_current_graph('{graph_name}')"))
            await conn.execute(text(f"SELECT graph.load_graph('{graph_name}')"))

    async def _pggraph_refresh(self) -> None:
        """Rebuild and load the pgGraph projection."""
        graph_name = _graph_name(self.schema)
        async with self.engine.begin() as conn:
            await conn.execute(text(f"SELECT graph.set_current_graph('{graph_name}')"))
            await conn.execute(text(f"SELECT graph.build_graph('{graph_name}')"))
            await conn.execute(text(f"SELECT graph.load_graph('{graph_name}')"))

    async def _refresh_if_stale(self) -> None:
        if getattr(self, "_pggraph_stale", False):
            await self._pggraph_refresh()
            self._pggraph_stale = False
        else:
            await self._ensure_pggraph_loaded()

    async def add_nodes(
        self,
        nodes: Union[List[Node], List[Any]],
        source_ref_key: Optional[str] = None,
        pipeline_run_id: Optional[str] = None,
    ) -> None:
        await super().add_nodes(nodes, source_ref_key, pipeline_run_id)
        self._pggraph_stale = True

    async def add_edges(
        self,
        edges: Union[List[EdgeData], List[Tuple[str, str, str, Optional[Dict[str, Any]]]]],
        source_ref_key: Optional[str] = None,
        pipeline_run_id: Optional[str] = None,
    ) -> None:
        await super().add_edges(edges, source_ref_key, pipeline_run_id)
        self._pggraph_stale = True

    async def delete_nodes(self, node_ids: List[str]) -> None:
        await super().delete_nodes(node_ids)
        self._pggraph_stale = True

    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship_name: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        await super().add_edge(source_id, target_id, relationship_name, properties)
        self._pggraph_stale = True

    async def delete_graph(self) -> None:
        await super().delete_graph()
        self._pggraph_stale = True

    async def get_connections(
        self, node_id: Union[str, UUID]
    ) -> List[Tuple[NodeData, Dict[str, Any], NodeData]]:
        """Return (source, edge_props, target) tuples for a node."""
        try:
            await self._refresh_if_stale()
            return await self._pggraph_connections(str(node_id))
        except Exception:
            return await super().get_connections(node_id)

    async def get_neighborhood(
        self,
        node_ids: List[str],
        depth: int = 1,
        edge_types: Optional[List[str]] = None,
    ) -> Tuple[List[Node], List[EdgeData]]:
        """Return the k-hop neighborhood using pgGraph traversal."""
        try:
            await self._refresh_if_stale()
            return await self._pggraph_neighborhood(node_ids, depth, edge_types)
        except Exception:
            return await super().get_neighborhood(node_ids, depth, edge_types)

    async def _pggraph_connections(
        self, node_id: str
    ) -> List[Tuple[NodeData, Dict[str, Any], NodeData]]:
        """Use graph.traverse for outbound and inbound 1-hop connections."""
        await self._ensure_pggraph_loaded()
        results: List[Tuple[NodeData, Dict[str, Any], NodeData]] = []

        node_table = _table_ref(self.schema, "graph_node")
        for direction in ("out", "in"):
            async with self.sessionmaker() as session:
                rows = await session.execute(
                    text(
                        f"SELECT * FROM graph.traverse(\n"
                        f"  '{node_table}'::regclass,\n"
                        f"  :node_id,\n"
                        f"  max_depth := 1,\n"
                        f"  direction := :direction,\n"
                        f"  include_start := false,\n"
                        f"  hydrate := true\n"
                        f")"
                    ),
                    {"node_id": node_id, "direction": direction},
                )
                for row in rows.mappings():
                    if not row["node"]:
                        continue
                    node_data = _node_data_from_pggraph(dict(row["node"]))
                    edge_data = {}
                    if row["edge_path"] and len(row["edge_path"]) > 0:
                        edge_data = dict(row["edge_path"][0])
                    neighbor = (node_id, node_data)
                    if direction == "out":
                        results.append(({}, edge_data, neighbor))
                    else:
                        results.append((neighbor, edge_data, {}))
        return results

    async def _pggraph_neighborhood(
        self,
        node_ids: List[str],
        depth: int = 1,
        edge_types: Optional[List[str]] = None,
    ) -> Tuple[List[Node], List[EdgeData]]:
        """Use graph.traverse for multi-start neighborhood."""
        if not node_ids:
            return [], []

        await self._ensure_pggraph_loaded()
        node_table = _table_ref(self.schema, "graph_node")
        async with self.sessionmaker() as session:
            rows = await session.execute(
                text(
                    f"SELECT * FROM graph.traverse(\n"
                    f"  :node_tables,\n"
                    f"  :node_ids,\n"
                    f"  max_depth := :depth,\n"
                    f"  include_start := true,\n"
                    f"  hydrate := true\n"
                    f")"
                ),
                {
                    "node_tables": [f"{node_table}"] * len(node_ids),
                    "node_ids": [str(n) for n in node_ids],
                    "depth": depth,
                },
            )

        nodes: Dict[str, Node] = {}
        edges: List[EdgeData] = []
        for row in rows.mappings():
            if not row["node"]:
                continue
            data = _node_data_from_pggraph(dict(row["node"]))
            nid = row["node_id"]
            nodes[nid] = (nid, data)
            if row["edge_path"] and len(row["edge_path"]) > 0:
                ep = row["edge_path"][0]
                source_id = ep.get("_start", {}).get("id", row["root_id"])
                target_id = ep.get("_end", {}).get("id", nid)
                rel = ep.get("_type", "rel")
                edges.append((source_id, target_id, rel, {}))

        return list(nodes.values()), edges

    async def pggraph_gql(self, query: str, **params: Any) -> List[Dict[str, Any]]:
        """Run a pgGraph GQL query and return JSONB rows."""
        await self._ensure_pggraph_loaded()
        async with self.sessionmaker() as session:
            result = await session.execute(
                text("SELECT row FROM graph.gql(:q, params := :p::jsonb, hydrate := true)"),
                {"q": query, "p": json.dumps(params) if params else "{}"},
            )
            return [dict(r) for r in result.scalars()]
