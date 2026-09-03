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
    edge_semantic: str | None = None,
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
        edge_semantic=edge_semantic,
        direction=direction,
        seen=seen,
        badges={},
        children=children or [],
    )


def test_graph_to_dot_produces_a_valid_digraph_with_a_depends_on_label() -> None:
    root = _node(
        id="FEAT-000002",
        type="feature",
        children=[
            _node(
                id="TASK-000003",
                edge_kind="depends-on",
                edge_semantic="dependency",
                direction="out",
            )
        ],
    )
    dot = graph_to_dot(root)
    assert dot.startswith("digraph {") and dot.endswith("}")
    assert '"FEAT-000002"' in dot and '"TASK-000003"' in dot
    assert '[label="depends on"]' in dot


def test_graph_to_dot_uses_required_by_for_an_inbound_dependency_edge() -> None:
    root = _node(
        id="TASK-000003",
        children=[
            _node(
                id="FEAT-000002",
                type="feature",
                edge_kind="depends-on",
                edge_semantic="dependency",
                direction="in",
            )
        ],
    )
    dot = graph_to_dot(root)
    assert '[label="required by"]' in dot


def test_graph_to_mermaid_produces_a_flowchart_labelled_with_the_real_ids() -> None:
    root = _node(
        id="FEAT-000002",
        type="feature",
        children=[_node(id="TASK-000003", edge_kind="related", direction="out")],
    )
    mermaid = graph_to_mermaid(root)
    assert mermaid.startswith("flowchart LR")
    assert 'FEAT_002d000002["FEAT-000002"]' in mermaid
    assert 'TASK_002d000003["TASK-000003"]' in mermaid
    assert "-->|related|" in mermaid


def test_graph_to_mermaid_keeps_two_ids_differing_only_by_separator_apart() -> None:
    """The defect the fold caused. `MY-WIDGET-1` and `MY_WIDGET-1` are two distinct items an
    adopter can declare (nothing validates a prefix's character set), and a fold is many-to-one,
    so the diagram drew them as one node — wrong output, before anyone clicked anything."""
    root = _node(
        id="MY-WIDGET-1",
        children=[_node(id="MY_WIDGET-1", edge_kind="related", direction="out")],
    )
    mermaid = graph_to_mermaid(root)

    from squads._services._refs import _mermaid_node_id

    assert _mermaid_node_id("MY-WIDGET-1") != _mermaid_node_id("MY_WIDGET-1")
    assert 'MY_002dWIDGET_002d1["MY-WIDGET-1"]' in mermaid
    assert 'MY_005fWIDGET_002d1["MY_WIDGET-1"]' in mermaid


def test_the_mermaid_node_id_escape_is_injective_across_separator_shapes() -> None:
    """One test per encountered pair proves the pair; this asserts the property. Every id in a
    family whose members differ only in where the separators fall must get its own node id —
    that is what "injective" buys over "handles the reported case"."""
    from squads._services._refs import _mermaid_node_id

    family = [
        "A-B",
        "A_B",
        "A__B",
        "A-_B",
        "A_-B",
        "A--B",
        "AB",
        "A.B",
        "A B",
        "A-0b-B",  # an alphanumeric run that looks like the tail of a shorter escape
        "A_002dB",  # …and text that spells an escape literally
    ]
    encoded = [_mermaid_node_id(nid) for nid in family]
    assert len(set(encoded)) == len(family), sorted(zip(family, encoded, strict=True))
    assert all(c.isascii() and (c.isalnum() or c == "_") for e in encoded for c in e)


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
