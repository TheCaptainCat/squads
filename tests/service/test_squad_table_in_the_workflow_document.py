"""The ``[squad]`` table of the workflow document: its override shapes, and every refusal of a
``validators`` entry, crossed with spec load and ``sq workflow lint``."""

from dataclasses import dataclass
from typing import Any

import pytest

from squads import __version__
from squads._errors import SquadsError
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import load_workflow_spec
from squads._workflow._loader import lint_workflow_spec

_ENV_ROLES = """
[roles.active]
live = false

[roles.running]
settled = false
hidden = false
color = "positive"
live = true

[statuses.Active]
role = "running"
"""

_NO_DEPENDENCY_KINDS = """
[selected]
ref_kinds = [
  "related", "implements", "fixes", "addresses", "supersedes", "duplicates", "scopes", "targets",
]
"""


def _write(project: Any, body: str) -> None:
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(exist_ok=True)
    (overrides / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(project.squad_dir)


def _squad(entries: list[str]) -> str:
    items = ", ".join(f'"{e}"' for e in entries)
    return f"[squad]\nvalidators = [{items}]\n"


def _lint_errors(project: Any) -> list[str]:
    return [
        m for level, _loc, m, _hint in lint_workflow_spec(project.squad_dir) if level == "error"
    ]


@dataclass(frozen=True)
class Shape:
    id: str
    toml: str | None
    resolved: list[str] | None  # the loaded list, None when the load is refused
    message: str | None = None


SHAPES = [
    Shape("no-override", None, []),
    Shape("no-squad-table", "[items.task]\nvalidators = []\n", []),
    Shape("empty-list", "[squad]\nvalidators = []\n", []),
    Shape("plain-list", _squad(["children_settled_with_parent"]), ["children_settled_with_parent"]),
    Shape(
        "splat-plus-one",
        '[squad]\nvalidators = ["$(*squad.validators)", "dependency_acyclic"]\n',
        ["dependency_acyclic"],
    ),
    Shape("unknown-key", "[squad]\nextra = 1\n", None, "extra"),
    Shape("not-a-table", "squad = 3\n", None, "squad"),
    Shape("not-a-list", '[squad]\nvalidators = "wip_limit:3"\n', None, "validators"),
    Shape("selected-squad", '[selected]\nsquad = ["validators"]\n', None, "no entries to drop"),
]


@pytest.mark.parametrize("shape", SHAPES, ids=lambda s: s.id)
async def test_override_shape_by_resolved_list(project, shape: Shape) -> None:
    if shape.toml is not None:
        _write(project, shape.toml)

    if shape.resolved is not None:
        assert load_workflow_spec(squad_dir=project.squad_dir).squad.validators == shape.resolved
        assert _lint_errors(project) == []
    else:
        with pytest.raises(SquadsError, match=shape.message):
            load_workflow_spec(squad_dir=project.squad_dir)
        assert any(shape.message in m for m in _lint_errors(project))  # pyright: ignore[reportOperatorIssue]


@dataclass(frozen=True)
class Entry:
    entry: str
    message: str | None  # None: the entry loads clean
    extra: str = ""  # further override text the row needs


ENTRIES = [
    # Each of the five members, bare, at warn and at error.
    *[
        Entry(f"{name}{param}{level}", None)
        for name, param in [
            ("children_settled_with_parent", ""),
            ("dependency_acyclic", ""),
            ("wip_limit", ":3"),
            ("unassigned_active", ":0"),
            ("stale_active", ":30"),
        ]
        for level in ("", "@warn", "@error")
    ],
    Entry("foo", "unknown validator"),
    Entry("index_reconciled", "always runs and cannot be selected"),
    Entry("roster_slug_valid", "always runs and cannot be selected"),
    Entry("playbook_guide_role_live", "always runs and cannot be selected"),
    Entry("body_written", "per-item validator"),
    Entry("parent_in", "per-item validator"),
    Entry("children_settled_with_parent:3", "takes no parameter"),
    Entry("dependency_acyclic:3", "takes no parameter"),
    Entry("wip_limit", "needs its parameter"),
    Entry("wip_limit:", "needs its parameter"),
    Entry("wip_limit:0", "positive integer"),
    Entry("wip_limit:-1", "positive integer"),
    Entry("wip_limit:x", "positive integer"),
    Entry("stale_active:1.5", "positive integer"),
    Entry("stale_active:0", "positive integer"),
    Entry("unassigned_active", "needs its parameter"),
    Entry("unassigned_active:-1", "non-negative integer"),
    Entry("dependency_acyclic@info", "unknown level"),
    Entry("wip_limit:3@fatal", "unknown level"),
    Entry("wip_limit:3@error@warn", "unknown level"),
    Entry("wip_limit:@error", "needs its parameter"),
    Entry("wip_limit:3", "needs a work type", _ENV_ROLES),
    Entry("unassigned_active:0", "needs a work type", _ENV_ROLES),
    Entry("stale_active:3", "needs a work type", _ENV_ROLES),
    Entry("dependency_acyclic", "needs a declared ref kind", _NO_DEPENDENCY_KINDS),
    Entry("children_settled_with_parent", None, _ENV_ROLES + _NO_DEPENDENCY_KINDS),
]


@pytest.mark.parametrize("row", ENTRIES, ids=lambda r: f"{r.entry}|{'env' if r.extra else 'std'}")
async def test_selection_entry_by_outcome(project, row: Entry) -> None:
    _write(project, _squad([row.entry]) + row.extra)

    if row.message is None:
        assert load_workflow_spec(squad_dir=project.squad_dir).squad.validators == [row.entry]
        assert _lint_errors(project) == []
        return
    with pytest.raises(SquadsError, match=row.message) as excinfo:
        load_workflow_spec(squad_dir=project.squad_dir)
    assert row.entry in str(excinfo.value)
    assert any(row.message in m and row.entry in m for m in _lint_errors(project))


@pytest.mark.parametrize(
    "entries",
    [
        ["wip_limit:3", "wip_limit:3"],
        ["wip_limit:3", "wip_limit:4"],
        ["stale_active:3@warn", "stale_active:5@error"],
        ["children_settled_with_parent", "children_settled_with_parent@error"],
    ],
    ids=lambda e: "+".join(e),
)
async def test_the_same_member_twice_is_refused_whatever_the_parameters(
    project, entries: list[str]
) -> None:
    _write(project, _squad(entries))

    with pytest.raises(SquadsError, match="already selected"):
        load_workflow_spec(squad_dir=project.squad_dir)
    assert any("already selected" in m for m in _lint_errors(project))


@pytest.mark.parametrize(
    "name", ["wip_limit:3", "children_settled_with_parent", "index_reconciled", "nope"]
)
async def test_a_type_list_naming_a_squad_global_member_gets_the_reciprocal_message(
    project, name: str
) -> None:
    _write(project, f'[items.task]\nvalidators = ["{name}"]\n')

    expected = "unknown validator" if name == "nope" else "squad-global validator"
    with pytest.raises(SquadsError, match=expected):
        load_workflow_spec(squad_dir=project.squad_dir)


async def test_a_selection_the_corpus_cannot_satisfy_still_loads(project) -> None:
    """Whether a selection can fire is decided from the spec alone; the corpus is never read."""
    _write(project, _squad(["wip_limit:1", "dependency_acyclic"]))

    assert load_workflow_spec(squad_dir=project.squad_dir).squad.validators == [
        "wip_limit:1",
        "dependency_acyclic",
    ]


async def test_a_squad_table_that_fails_to_load_is_reported_by_check_like_any_other_declaration(
    project, invoke
) -> None:
    _write(project, _squad(["nope"]))

    result = await invoke(["check"])

    assert result.exit_code == 3
    assert "workflow config invalid" in result.output
