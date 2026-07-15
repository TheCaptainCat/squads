"""``sq graph`` CLI surface: renders a tree, resolves a bare number, ``--depth``/``--direction``/
``--kind``/``--all`` reach the service, dependency edge labels never leak a raw ref-kind string,
``--format dot``/``--format mermaid`` emit serialized graphs, a badge renders on a node, and
``--json``/``--format dot`` match a pinned golden shape.
"""

import json
import os
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.anyio

GOLDENS_DIR = Path(__file__).parents[1] / "goldens"
_UPDATE = os.getenv("UPDATE_GOLDENS") == "1"


def _check_golden(name: str, actual: Any) -> None:
    path = GOLDENS_DIR / f"{name}.json"
    if _UPDATE:
        GOLDENS_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(actual, indent=2) + "\n", encoding="utf-8")
        return
    assert path.exists(), f"golden file missing: {path}"
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert actual == expected, f"golden mismatch for {name!r}"


async def _seed(invoke) -> None:
    """Seeds a feature, a task that depends-on it, and a bug related to the task."""
    await invoke(["create", "feature", "Feature A", "--author", "manager"])
    await invoke(["create", "task", "Task B", "--author", "manager", "--parent", "FEAT-000002"])
    await invoke(["create", "bug", "Bug C", "--author", "manager"])
    await invoke(["task", "3", "ref", "add", "FEAT-000002", "--kind", "depends-on"])
    await invoke(["bug", "4", "ref", "add", "TASK-000003", "--kind", "related"])


async def test_renders_a_tree_and_resolves_a_bare_number_to_the_full_id(project, invoke):
    await _seed(invoke)
    by_id = await invoke(["graph", "FEAT-000002"])
    assert by_id.exit_code == 0 and "FEAT-2" in by_id.output
    by_number = await invoke(["graph", "2"])
    assert by_number.exit_code == 0 and "FEAT-2" in by_number.output


async def test_depth_zero_shows_only_the_root(project, invoke):
    await _seed(invoke)
    result = await invoke(["graph", "FEAT-000002", "--depth", "0"])
    assert result.exit_code == 0
    assert "FEAT-2" in result.output
    assert "TASK-3" not in result.output


async def test_direction_and_kind_flags_reach_the_service(project, invoke):
    await _seed(invoke)
    out_dir = await invoke(["graph", "TASK-000003", "--direction", "out", "--depth", "1"])
    assert out_dir.exit_code == 0 and "FEAT-2" in out_dir.output

    kind_filtered = await invoke(["graph", "TASK-000003", "--kind", "related", "--depth", "1"])
    assert kind_filtered.exit_code == 0
    assert "BUG-4" in kind_filtered.output  # related backref
    assert "FEAT-2" not in kind_filtered.output  # depends-on filtered out


async def test_dependency_labels_never_leak_a_raw_ref_kind_string(project, invoke):
    await _seed(invoke)
    result = await invoke(["graph", "TASK-000003", "--depth", "2"])
    assert result.exit_code == 0
    for line in result.output.splitlines():
        assert "(depends-on)" not in line
        assert "(blocks)" not in line


async def test_format_dot_and_mermaid_emit_serialized_graphs(project, invoke):
    await _seed(invoke)
    dot = await invoke(
        ["graph", "FEAT-000002", "--format", "dot", "--depth", "1", "--direction", "in"]
    )
    assert dot.exit_code == 0
    assert "digraph {" in dot.output and '"FEAT-2"' in dot.output

    mermaid = await invoke(
        ["graph", "FEAT-000002", "--format", "mermaid", "--depth", "1", "--direction", "in"]
    )
    assert mermaid.exit_code == 0
    assert "flowchart LR" in mermaid.output and "FEAT_2" in mermaid.output


async def test_format_mermaid_md_wraps_the_serialized_body_in_a_fence(project, invoke):
    await _seed(invoke)
    plain = await invoke(
        ["graph", "FEAT-000002", "--format", "mermaid", "--depth", "1", "--direction", "in"]
    )
    fenced = await invoke(
        ["graph", "FEAT-000002", "--format", "mermaid-md", "--depth", "1", "--direction", "in"]
    )
    assert fenced.exit_code == 0
    lines = fenced.output.splitlines()
    assert lines[0] == "```mermaid"
    assert lines[-1] == "```"
    assert plain.output.strip() in fenced.output


async def test_format_rejects_an_unknown_value(project, invoke):
    await _seed(invoke)
    result = await invoke(["graph", "FEAT-000002", "--format", "svg"])
    assert result.exit_code != 0


async def test_a_badge_field_renders_on_a_node_without_crashing(project, invoke):
    await invoke(["create", "feature", "Root", "--author", "manager", "--priority", "high"])
    await invoke(["create", "task", "Dep", "--author", "manager", "--priority", "urgent"])
    await invoke(["task", "3", "ref", "add", "FEAT-000002", "--kind", "depends-on"])

    result = await invoke(["graph", "FEAT-000002", "--depth", "1", "--direction", "in"])
    assert result.exit_code == 0, result.output
    assert "high" in result.output and "urgent" in result.output


async def test_all_flag_includes_closed_items_hidden_by_default(project, invoke):
    await invoke(["create", "feature", "Root", "--author", "manager"])
    await invoke(["create", "task", "Done task", "--author", "manager"])
    await invoke(["task", "3", "status", "InProgress"])
    await invoke(["task", "3", "status", "Done"])
    await invoke(["feature", "2", "ref", "add", "TASK-000003", "--kind", "related"])

    without_all = await invoke(["graph", "FEAT-000002", "--depth", "1"])
    assert "TASK-3" not in without_all.output
    with_all = await invoke(["graph", "FEAT-000002", "--depth", "1", "--all"])
    assert "TASK-3" in with_all.output


async def test_json_output_is_ansi_free_and_shape_matches_the_pinned_golden(project, invoke):
    await _seed(invoke)
    result = await invoke(["graph", "FEAT-000002", "--json", "--depth", "1", "--direction", "in"])
    assert result.exit_code == 0
    assert "\x1b[" not in result.output
    data = json.loads(result.output)
    assert data["id"] == "FEAT-2"
    _check_golden("graph_feat_json", data)


async def test_format_dot_output_matches_the_pinned_golden(project, invoke):
    await _seed(invoke)
    result = await invoke(
        ["graph", "FEAT-000002", "--format", "dot", "--depth", "1", "--direction", "in"]
    )
    assert result.exit_code == 0
    _check_golden("graph_feat_dot", result.output.strip())
