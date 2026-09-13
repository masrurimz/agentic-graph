"""Tool-agnostic graph schema for code + agentic step correlation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeType(str, Enum):
    FILE = "file"
    SYMBOL = "symbol"
    DOC = "doc"
    AGENT_STEP = "agent_step"
    TOOL_CALL = "tool_call"
    SEARCH_QUERY = "search_query"


class EdgeType(str, Enum):
    CONTAINS = "contains"
    CALLS = "calls"
    IMPORTS = "imports"
    REFERENCES = "references"
    PRODUCED_BY = "produced_by"
    SEARCHED_FOR = "searched_for"
    TOUCHED = "touched"
    TRIGGERED_BY = "triggered_by"


@dataclass
class Node:
    id: str
    type: NodeType
    name: str
    path: Optional[str] = None
    language: Optional[str] = None
    source: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    id: str
    type: EdgeType
    source: str
    target: str
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentStep:
    step_id: str
    tool: str
    args: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    touched_files: List[str] = field(default_factory=list)
    touched_symbols: List[str] = field(default_factory=list)
    parent_step_id: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchQuery:
    query_id: str
    query: str
    result_refs: List[str] = field(default_factory=list)
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphSchema:
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)

    def add_node(self, node: Node) -> None:
        self.nodes.append(node)

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def node_ids(self) -> List[str]:
        return [n.id for n in self.nodes]

    def edge_ids(self) -> List[str]:
        return [e.id for e in self.edges]
