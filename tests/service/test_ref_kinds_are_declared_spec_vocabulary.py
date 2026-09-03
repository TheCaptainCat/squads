"""``[ref_kinds]`` is a declared workflow-spec section: the bundled kinds load
from ``_specs/workflow.toml`` rather than a code-level frozenset, an override may add its own
kind and drop/rename a built-in one (merged leaf-granularly, deselectable via ``[selected]``,
splat-ref addressable against the bundled base — no section-specific code path), and a kind the
merged spec does not declare is refused by name across every consultation site.

Table-driven across the shape families the spec covers: an added kind, a renamed kind, a
dropped kind, and ``[selected]`` — not one example per implemented branch.
"""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads._errors import SquadsError
from squads._models._item import make_ref, split_ref
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import bundled_spec, load_workflow_spec
from squads._workflow._loader import WORKFLOW_TOP_LEVEL_SECTIONS

pytestmark = pytest.mark.anyio


def _write_override(squad_dir: Path, body: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)


# ─── the declared section itself ────────────────────────────────────────────────


def test_ref_kinds_is_a_closed_top_level_section() -> None:
    assert "ref_kinds" in WORKFLOW_TOP_LEVEL_SECTIONS


def test_the_bundled_spec_declares_the_nine_navigational_and_semantic_kinds_plus_targets() -> None:
    spec = bundled_spec()
    expected = {
        "related",
        "blocks",
        "depends-on",
        "implements",
        "fixes",
        "addresses",
        "supersedes",
        "duplicates",
        "scopes",
        "targets",
    }
    assert set(spec.ref_kinds) == expected


def test_exactly_one_bundled_kind_carries_the_default_role() -> None:
    spec = bundled_spec()
    defaults = [k for k, rk in spec.ref_kinds.items() if rk.role == "default"]
    assert defaults == ["related"]
    assert spec.default_ref_kind() == "related"


def test_targets_ships_bundled_with_no_semantic() -> None:
    spec = bundled_spec()
    assert spec.ref_kinds["targets"].role is None


@pytest.mark.parametrize(
    ("kind", "role", "direction"),
    [
        ("blocks", "dependency", "blocker"),
        ("depends-on", "dependency", "dependent"),
        ("scopes", "preload", None),
        ("supersedes", "supersession", None),
        ("implements", None, None),
        ("duplicates", None, None),
    ],
)
def test_each_bundled_kinds_declared_role_and_direction(
    kind: str, role: str | None, direction: str | None
) -> None:
    rk = bundled_spec().ref_kinds[kind]
    assert rk.role == role
    assert rk.direction == direction


# ─── override: add / rename / drop / [selected] ─────────────────────────────────


def test_an_override_can_add_a_navigational_kind_with_no_engine_change(tmp_path: Path) -> None:
    _write_override(tmp_path, '[ref_kinds.escalates]\nlabel = "Escalates"\n')
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "escalates" in spec.ref_kinds
    assert spec.ref_kinds["escalates"].role is None
    # The bundled kinds are still present (shadowing merge, not a replacement).
    assert set(bundled_spec().ref_kinds) <= set(spec.ref_kinds)


def test_an_override_can_rename_the_kind_carrying_the_default_role(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        '[selected]\nref_kinds = ["blocks", "depends-on", "implements", "fixes", "addresses", '
        '"supersedes", "duplicates", "scopes", "targets", "seealso"]\n\n'
        '[ref_kinds.seealso]\nlabel = "See also"\nrole = "default"\n',
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "related" not in spec.ref_kinds
    assert spec.default_ref_kind() == "seealso"


def test_a_selected_drop_of_an_unused_kind_removes_it_from_the_merged_spec(
    tmp_path: Path,
) -> None:
    _write_override(
        tmp_path,
        '[selected]\nref_kinds = ["related", "blocks", "depends-on", "implements", "fixes", '
        '"addresses", "supersedes", "scopes", "targets"]\n',
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "duplicates" not in spec.ref_kinds
    assert "related" in spec.ref_kinds  # everything else survives the deselect


# ─── retirement at the consultation sites: an undeclared kind is refused by name ─


async def test_add_ref_with_an_undeclared_kind_lists_the_projects_own_accepted_set(svc) -> None:
    a = (await create_item(svc, "task", "a")).item
    b = (await create_item(svc, "task", "b")).item
    with pytest.raises(SquadsError) as excinfo:
        await svc.add_ref(a.id, b.id, kind="banana")
    message = str(excinfo.value)
    assert "banana" in message
    for kind in svc.spec.ref_kinds:
        assert kind in message


async def test_create_with_an_undeclared_kind_ref_is_refused(svc) -> None:
    other = (await create_item(svc, "task", "other")).item
    with pytest.raises(SquadsError, match="unknown ref kind"):
        await create_item(svc, "task", "t", refs=[f"{other.id}:banana"])


async def test_graph_kind_filter_with_an_undeclared_kind_is_refused(svc) -> None:
    a = (await create_item(svc, "task", "a")).item
    b = (await create_item(svc, "task", "b")).item
    await svc.add_ref(a.id, b.id, kind="related")
    with pytest.raises(SquadsError, match="unknown ref kind"):
        await svc.graph(a.id, kinds={"banana"})


async def test_sq_check_flags_an_undeclared_kind_on_a_live_edge(svc) -> None:
    from squads._services._validators import ValidatorContext, _ref_kind_valid

    a = (await create_item(svc, "task", "a")).item
    b = (await create_item(svc, "task", "b")).item
    item = await svc.get(a.id)
    item.refs.append(f"{b.id}:banana")

    issues = _ref_kind_valid(ValidatorContext(item=item, spec=svc.spec))
    assert any("banana" in i.message for i in issues)


async def test_a_project_declared_kind_can_be_added_read_and_graphed(tmp_path: Path) -> None:
    from squads._services._service import Service, init

    result = await init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    _write_override(result.paths.squad_dir, '[ref_kinds.escalates]\nlabel = "Escalates"\n')
    overridden_spec = load_workflow_spec(squad_dir=result.paths.squad_dir)
    svc = Service(result.paths, spec=overridden_spec)
    assert "escalates" in svc.spec.ref_kinds

    a = (await create_item(svc, "task", "a")).item
    b = (await create_item(svc, "task", "b")).item
    await svc.add_ref(a.id, b.id, kind="escalates")

    assert (b.id, "escalates") in await svc.refs_out(a.id)
    node = await svc.graph(a.id, kinds={"escalates"})
    assert any(c.id == b.id and c.edge_kind == "escalates" for c in node.children)


# ─── the bare wire form: structural, not vocabulary ─────────────────────────────


def test_split_ref_decodes_a_bare_id_to_an_unspelled_kind() -> None:
    assert split_ref("TASK-000007") == ("TASK-000007", "")


def test_split_ref_decodes_a_spelled_kind_verbatim() -> None:
    assert split_ref("TASK-000007:blocks") == ("TASK-000007", "blocks")


def test_make_ref_writes_bare_only_for_an_unspelled_kind() -> None:
    assert make_ref("TASK-000007", "") == "TASK-000007"
    assert make_ref("TASK-000007") == "TASK-000007"
    assert make_ref("TASK-000007", "blocks") == "TASK-000007:blocks"
    # make_ref does not itself know which kind is the declared default — a caller who
    # spells it out gets it spelled back, verbatim.
    assert make_ref("TASK-000007", "related") == "TASK-000007:related"


async def test_add_ref_with_no_kind_writes_a_bare_edge(svc) -> None:
    a = (await create_item(svc, "task", "a")).item
    b = (await create_item(svc, "task", "b")).item
    updated = await svc.add_ref(a.id, b.id)
    assert updated.refs == [b.id]  # bare — no ":kind" suffix
    assert (b.id, "related") in await svc.refs_out(a.id)


async def test_add_ref_with_the_default_kind_spelled_out_still_writes_bare(svc) -> None:
    """A rename-safety property: the spelled form of the declared
    default is never emitted on disk, so a hand-written or imported ``:related`` normalises
    to the same bare wire form ``add_ref`` writes when no kind is given at all."""
    a = (await create_item(svc, "task", "a")).item
    b = (await create_item(svc, "task", "b")).item
    updated = await svc.add_ref(a.id, b.id, kind="related")
    assert updated.refs == [b.id]


async def test_add_ref_with_a_non_default_kind_is_spelled_out(svc) -> None:
    a = (await create_item(svc, "task", "a")).item
    b = (await create_item(svc, "task", "b")).item
    updated = await svc.add_ref(a.id, b.id, kind="blocks")
    assert updated.refs == [f"{b.id}:blocks"]
