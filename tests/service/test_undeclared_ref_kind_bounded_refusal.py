"""An undeclared ref kind on a live edge is bounded to the write and lint boundary — never a
load failure. Nothing pinned this family at the fail-closed boundary before: the three test
files that exercise ``validate_against_index`` never reach the ref-kind axis, so the family
could lock every command in the squad (``sq check``, ``sq graph``, ``refs``, even ``Service``
construction) with nothing here turning red. This file pins the bound from both directions,
over both shapes the collector can see an undeclared kind through:

- **native** — a kind spelled by an ordinary ``ref add`` that the override later drops. No
  legacy map anywhere; the general case.
- **legacy** — a pre-0.2 ``extra.ref_kinds``-mapped edge whose recorded kind stops equalling
  the live default once the override renames it. The fold only spells this edge once ``sq
  repair`` re-derives the index from the still-legacy-shaped file *under the renamed spec* —
  which, since repair now also rewrites the file (see the "repair canonicalises the file"
  tests below), is the very call that manufactures the undeclared-kind state it will go on to
  survive cleanly.

Per shape: what refuses (``sq workflow lint``; writing a *new* ref of the undeclared kind) and
what keeps running (a read command, ``sq check`` — a per-item warn, never the "workflow config
invalid" line, ``sq repair``, ``sq <type> <n> ref rm``, an ordinary mutation of the affected
item, ``sq graph`` with a null semantic). ``test_end_to_end_recovery_needs_no_hand_editing``
drives the whole documented recovery — revert, repair, mutate, re-apply the rename — over both
a legacy-folded and a natively bare edge, confirming every message read along the way is true.
"""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads._errors import SquadsError
from squads._models._item import split_ref
from squads._rendering._engine import invalidate_squad_dir
from squads._sections import join_frontmatter, split_frontmatter
from squads._services._service import Service, open_service
from squads._workflow import load_workflow_spec
from squads._workflow._loader import lint_workflow_spec

pytestmark = pytest.mark.anyio

_DROP_DUPLICATES = (
    '[selected]\nref_kinds = ["related", "blocks", "depends-on", "implements", "fixes", '
    '"addresses", "supersedes", "scopes", "targets"]\n'
)

_RENAME_DEFAULT = (
    '[selected]\nref_kinds = ["blocks", "depends-on", "implements", "fixes", "addresses", '
    '"supersedes", "duplicates", "scopes", "targets", "seealso"]\n\n'
    '[ref_kinds.seealso]\nlabel = "See also"\nrole = "default"\n'
)


def _write_override(squad_dir: Path, body: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)


def _remove_override(squad_dir: Path) -> None:
    (squad_dir / ".overrides" / "workflow.toml").unlink()
    invalidate_squad_dir(squad_dir)


def _plant_legacy_shape(svc: Service, item, target_id: str, *, kind: str) -> None:
    """Rewrite *item*'s file to the pre-0.2 shape (bare ``refs`` plus an ``extra.ref_kinds``
    map naming *kind*) directly — bypassing every normalising writer, so the index still
    holds whatever canonical form ``add_ref`` last wrote (as if this item's index entry
    predates this release's file-canonicalisation and was never touched since) while disk
    carries the legacy map."""
    path = svc.paths.abspath(item.path)
    fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
    fm["refs"] = [target_id]
    fm["extra"] = {"ref_kinds": {target_id: kind}}
    path.write_text(join_frontmatter(fm, body), encoding="utf-8")


def _no_errors(issues) -> bool:
    return not any(i.level == "error" for i in issues)


# ─── shape setup ──────────────────────────────────────────────────────────────────


async def _seed_native_shape(svc: Service) -> tuple[str, str]:
    """A live edge natively spelling a declared, non-default kind — no legacy map anywhere."""
    a = (await create_item(svc, "task", "referrer")).item
    b = (await create_item(svc, "task", "target")).item
    await svc.add_ref(a.id, b.id, kind="duplicates")
    return a.id, b.id


async def _seed_legacy_shape(svc: Service, squad_dir: Path) -> tuple[str, str]:
    """A legacy-mapped edge whose recorded kind ("related") stops equalling the live default
    once the override renames it — manifested by the very ``sq repair`` that re-derives the
    index (and, per this release, the file) from the still-legacy-shaped disk under the
    renamed spec."""
    a = (await create_item(svc, "task", "referrer")).item
    b = (await create_item(svc, "task", "target")).item
    await svc.add_ref(a.id, b.id, kind="related")
    _plant_legacy_shape(svc, a, b.id, kind="related")
    _write_override(squad_dir, _RENAME_DEFAULT)
    svc2 = Service(svc.paths, spec=load_workflow_spec(squad_dir=squad_dir))
    result = await svc2.repair()
    assert result.canonicalized == [a.id]  # the repair that manufactures the locked state
    return a.id, b.id


# ─── the bound, table-driven over both shapes ──────────────────────────────────────


@pytest.mark.parametrize(
    ("shape", "override_body", "dropped_kind"),
    [
        pytest.param("native", _DROP_DUPLICATES, "duplicates", id="native-spelled-dropped-kind"),
        pytest.param("legacy", _RENAME_DEFAULT, "related", id="legacy-mapped-default-renamed"),
    ],
)
async def test_undeclared_kind_refuses_at_write_and_lint_only(
    project, invoke, shape, override_body, dropped_kind
) -> None:
    svc = Service(project)
    if shape == "native":
        referrer_id, target_id = await _seed_native_shape(svc)
        _write_override(project.squad_dir, override_body)
    else:
        referrer_id, target_id = await _seed_legacy_shape(svc, project.squad_dir)

    merged = load_workflow_spec(squad_dir=project.squad_dir)
    assert dropped_kind not in merged.ref_kinds
    svc2 = Service(project, spec=merged)

    # The load boundary is bounded: neither the low-level constructor above nor the real
    # per-invocation resolution `open_service` uses raises.
    assert open_service(str(project.squad_dir)).spec is not None

    # A read command still sees the edge, under its stale, undeclared spelling.
    assert (target_id, dropped_kind) in await svc2.refs_out(referrer_id)

    # sq check: a per-item warn, never the "workflow config invalid" fallback line.
    check_result = await invoke(["check", "--json"])
    assert check_result.exit_code == 0
    assert "workflow config invalid" not in check_result.output
    assert dropped_kind in check_result.output
    assert f"unknown ref kind {dropped_kind!r}" in check_result.output

    # sq graph traverses the stale edge and reports a null semantic rather than dropping it.
    node = await svc2.graph(referrer_id)
    child = next(c for c in node.children if c.id == target_id)
    assert child.edge_kind == dropped_kind
    assert child.edge_semantic is None

    # sq repair keeps running (and, on this now-canonical corpus, has nothing left to do).
    repair_result = await svc2.repair()
    assert repair_result.canonicalized == []

    # An ordinary mutation of the item carrying the stale edge succeeds — PERSISTING an
    # undeclared-kind edge is not what the write gate catches, only INTRODUCING one is.
    await svc2.update(referrer_id, description="touched")
    updated_path = svc2.paths.abspath((await svc2.get(referrer_id)).path)
    still_there, _ = split_frontmatter(updated_path.read_text(encoding="utf-8"))
    assert any(split_ref(r) == (target_id, dropped_kind) for r in still_there.get("refs", []))

    # sq workflow lint refuses, naming the offending kind and IDs — and states a sequence
    # rather than a remedy no command performs: the removal verb it names is not itself
    # locked, and (for the legacy shape) it may name `sq repair` as what canonicalises the
    # edge, since a command now performs that too.
    findings = lint_workflow_spec(project.squad_dir)
    ref_kind_findings = [f for f in findings if f[0] == "error" and dropped_kind in f[2]]
    assert ref_kind_findings
    for _level, _loc, message, fix_hint in ref_kind_findings:
        assert "no command rewrites a corpus's ref kinds" not in message
        assert "no command rewrites" not in fix_hint
        assert "ref rm" in message or "ref rm" in fix_hint
    lint_result = await invoke(["workflow", "lint"])
    assert lint_result.exit_code != 0
    assert dropped_kind in lint_result.output

    # Writing a NEW ref of the undeclared kind refuses by name — introducing, not persisting.
    c = (await create_item(svc2, "task", "fresh-referrer")).item
    d = (await create_item(svc2, "task", "fresh-target")).item
    with pytest.raises(SquadsError, match="unknown ref kind"):
        await svc2.add_ref(c.id, d.id, kind=dropped_kind)

    # sq <type> <n> ref rm runs — the remedy the refusal names is performable end to end.
    await svc2.rm_ref(referrer_id, target_id)
    assert (target_id, dropped_kind) not in await svc2.refs_out(referrer_id)
    assert _no_errors(await svc2.check())


@pytest.mark.parametrize(
    ("shape", "override_body"),
    [
        pytest.param("native", _DROP_DUPLICATES, id="native-spelled-dropped-kind"),
        pytest.param("legacy", _RENAME_DEFAULT, id="legacy-mapped-default-renamed"),
    ],
)
async def test_retype_remap_ignores_declared_vocabulary(project, shape, override_body) -> None:
    """The retype ref remap rewrites an EXISTING edge wholesale across the whole corpus and
    must not validate its kind — the write gate's write/persist line, exercised through the
    one other production path (besides an ordinary mutation) that rewrites a live ref."""
    svc = Service(project)
    if shape == "native":
        referrer_id, target_id = await _seed_native_shape(svc)
        dropped_kind = "duplicates"
        _write_override(project.squad_dir, override_body)
    else:
        referrer_id, target_id = await _seed_legacy_shape(svc, project.squad_dir)
        dropped_kind = "related"

    svc2 = Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))
    result = await svc2.retype(target_id, "bug")

    updated = await svc2.get(referrer_id)
    remapped = [split_ref(r) for r in updated.refs]
    assert (result.item.id, dropped_kind) in remapped


# ─── repair canonicalises the file ────────────────────────────────────────────────


async def test_repair_writes_no_file_over_an_already_canonical_corpus(project) -> None:
    svc = Service(project)
    a = (await create_item(svc, "task", "a")).item
    b = (await create_item(svc, "task", "b")).item
    await svc.add_ref(a.id, b.id, kind="related")  # ordinary bare edge, already canonical

    before = svc.paths.abspath(a.path).read_text(encoding="utf-8")
    result = await svc.repair()
    after = svc.paths.abspath(a.path).read_text(encoding="utf-8")

    assert result.canonicalized == []
    assert before == after


async def test_repair_converges_byte_identically_on_a_second_run(project) -> None:
    svc = Service(project)
    referrer_id, target_id = await _seed_legacy_shape(svc, project.squad_dir)
    svc2 = Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))

    after_first = svc2.paths.abspath((await svc2.get(referrer_id)).path).read_text(encoding="utf-8")
    second = await svc2.repair()
    after_second = svc2.paths.abspath((await svc2.get(referrer_id)).path).read_text(
        encoding="utf-8"
    )

    assert second.canonicalized == []
    assert after_first == after_second
    assert (target_id, "related") in await svc2.refs_out(referrer_id)


# ─── the full recovery, driven end to end ──────────────────────────────────────────


async def test_end_to_end_recovery_needs_no_hand_editing(project) -> None:
    """The recovery A5 promises: revert the override edit, ``sq repair``, mutate the affected
    item once, re-apply the rename — lint clean, check clean, both a legacy-folded and a
    natively bare edge reading as the new default, with no item ``.md`` touched by hand at any
    point in the *recovery* itself (the legacy-plant below represents pre-existing arriving
    data, not a recovery step)."""
    svc = Service(project)
    a = (await create_item(svc, "task", "legacy-referrer")).item
    b = (await create_item(svc, "task", "target")).item
    c = (await create_item(svc, "task", "native-referrer")).item
    await svc.add_ref(a.id, b.id, kind="related")
    await svc.add_ref(c.id, b.id, kind="related")
    _plant_legacy_shape(svc, a, b.id, kind="related")

    _write_override(project.squad_dir, _RENAME_DEFAULT)
    svc_renamed = Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))
    locking = await svc_renamed.repair()
    assert locking.canonicalized == [a.id]  # the repair that manufactures the locked state

    # Bounded: nothing about this state stops an ordinary command running.
    assert _no_errors(await svc_renamed.check())  # warn-only, never an error
    assert open_service(str(project.squad_dir)).spec is not None

    # Recovery, shipped verbs only, no item file ever opened by hand:
    _remove_override(project.squad_dir)  # 1. revert the override edit
    svc_reverted = Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))
    await svc_reverted.repair()  # 2. sq repair
    await svc_reverted.update(a.id, description="touch")  # 3. mutate the affected item once
    _write_override(project.squad_dir, _RENAME_DEFAULT)  # 4. re-apply the rename

    findings = lint_workflow_spec(project.squad_dir)
    assert not [f for f in findings if f[0] == "error"]  # lint clean

    svc_final = Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))
    assert _no_errors(await svc_final.check())  # check clean

    # Both edges — the once-legacy-mapped one and the always-native one — read as the new
    # default.
    assert (b.id, "seealso") in await svc_final.refs_out(a.id)
    assert (b.id, "seealso") in await svc_final.refs_out(c.id)
