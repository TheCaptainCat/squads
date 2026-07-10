"""The pure ``GraphNode`` -> DOT / Mermaid serializers: a valid digraph/flowchart, the
"required by" label for an inbound dependency edge, and de-duplication of a node that
appears twice in the tree (once expanded, once re-emitted as ``seen``) into one node
declaration.
"""

from squads._services._refs import graph_to_dot, graph_to_mermaid
from squads._services._results import GraphNode


def _node(
    id: str = "X",
    type: str = "task",
    edge_kind: str | None = None,
    direction: str | None = None,
    seen: bool = False,
    children: list[GraphNode] | None = None,
) -> GraphNode:
    return GraphNode(
        id=id,
        type=type,
        status="Draft",
        priority=None,
        assignee=None,
        edge_kind=edge_kind,
        direction=direction,
        seen=seen,
        badges={},
        children=children or [],
    )


def test_graph_to_dot_produces_a_valid_digraph_with_a_depends_on_label() -> None:
    root = _node(
        id="FEAT-000002",
        type="feature",
        children=[_node(id="TASK-000003", edge_kind="depends-on", direction="out")],
    )
    dot = graph_to_dot(root)
    assert dot.startswith("digraph {") and dot.endswith("}")
    assert '"FEAT-000002"' in dot and '"TASK-000003"' in dot
    assert '[label="depends on"]' in dot


def test_graph_to_dot_uses_required_by_for_an_inbound_dependency_edge() -> None:
    root = _node(
        id="TASK-000003",
        children=[_node(id="FEAT-000002", type="feature", edge_kind="depends-on", direction="in")],
    )
    dot = graph_to_dot(root)
    assert '[label="required by"]' in dot


def test_graph_to_mermaid_produces_a_flowchart_with_underscored_node_ids() -> None:
    root = _node(
        id="FEAT-000002",
        type="feature",
        children=[_node(id="TASK-000003", edge_kind="related", direction="out")],
    )
    mermaid = graph_to_mermaid(root)
    assert mermaid.startswith("flowchart LR")
    assert "FEAT_000002" in mermaid and "TASK_000003" in mermaid
    assert "-->|related|" in mermaid


def test_graph_to_dot_deduplicates_a_node_seen_twice_into_one_declaration() -> None:
    root = _node(
        id="FEAT-000002",
        type="feature",
        children=[
            _node(
                id="TASK-000003",
                edge_kind="related",
                direction="out",
                children=[
                    _node(
                        id="FEAT-000002",
                        type="feature",
                        edge_kind="related",
                        direction="in",
                        seen=True,
                    )
                ],
            )
        ],
    )
    dot = graph_to_dot(root)
    assert dot.count('"FEAT-000002";') == 1
