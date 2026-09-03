"""With the roster held constant, every managed file resolves a role through the role catalog
rather than through the item's own stored ``extra`` mirror.

A sync-then-diff cannot tell that claim apart from "converges eventually": the reconciler heals
a stale mirror on its next `sq sync`, so a squad that syncs *after* an override lands looks
identical either way. The case that actually proves the claim is the one asserted here — the
compiled regions, the per-entry pointer, and the roster projection itself already carry the
override's answer with **no sync at all** having run since the override appeared, while the
item's own stored mirror is left provably stale throughout.

The disagreement is constructed on purpose: a squad synced *before* its override was added, so
the stored mirror and the resolver genuinely differ.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio

_OVERRIDDEN_TITLE = "Chief Verification Officer"
_OVERRIDDEN_RESPONSIBILITIES = ["Audit every merge", "Own the release gate"]


def _write_role_override(squad_dir: Path, slug: str, body: str) -> None:
    path = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    assert path.is_file()


def _index_role_extra(paths: Any, slug: str) -> dict[str, Any]:
    raw = json.loads(paths.index_path.read_text(encoding="utf-8"))
    for entry in raw["items"].values():
        extra = entry.get("extra", {})
        if extra.get("slug") == slug:
            return extra
    raise AssertionError(f"no role item for {slug!r} in the index")


async def test_a_post_sync_override_reaches_every_managed_file_with_no_sync(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = await service.init(
        root=tmp_path, backend=["claude_code", "agents_md"], roles_spec="all"
    )
    paths = result.paths
    svc = service.Service(paths)
    await svc.sync()  # baseline: mirror and every managed file carry the bundled definition

    baseline_extra = _index_role_extra(paths, "reviewer")
    assert baseline_extra["title"] != _OVERRIDDEN_TITLE  # sanity: nothing overridden yet
    baseline_pointer = (paths.root / ".claude" / "agents" / "reviewer.md").read_text(
        encoding="utf-8"
    )
    assert _OVERRIDDEN_TITLE not in baseline_pointer

    _write_role_override(
        paths.squad_dir,
        "reviewer",
        f'title = "{_OVERRIDDEN_TITLE}"\n'
        f"responsibilities = {json.dumps(_OVERRIDDEN_RESPONSIBILITIES)}\n",
    )

    # No sync, no repair anywhere below — the item's own stored mirror never gets a chance to
    # heal itself. Reconfirmed at the very end, so nothing in between could have quietly synced.
    fresh = service.Service(paths)

    # 1. The roster projection itself — what every backend's write_managed compiles from.
    reviewer_view = next(r for r in await fresh.roster() if r.slug == "reviewer")
    assert reviewer_view.title == _OVERRIDDEN_TITLE
    assert list(reviewer_view.responsibilities) == _OVERRIDDEN_RESPONSIBILITIES
    # roster_all() (the full-vocabulary counterpart) resolves the same way.
    reviewer_view_all = next(r for r in await fresh.roster_all() if r.slug == "reviewer")
    assert reviewer_view_all.title == _OVERRIDDEN_TITLE

    # 2. The compiled regions — CLAUDE.md's role line and AGENTS.md's responsibilities block.
    await fresh.refresh_managed()
    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    agents_md = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert _OVERRIDDEN_TITLE in claude_md
    for line in _OVERRIDDEN_RESPONSIBILITIES:
        assert line in agents_md

    # 3. The per-entry pointer (the `RoleDef.from_extra` site `sq role <slug> regen` used).
    reviewer_item = await fresh.roster_item("role", "reviewer")
    assert reviewer_item is not None
    await fresh.regen(reviewer_item.id)
    pointer_text = (paths.root / ".claude" / "agents" / "reviewer.md").read_text(encoding="utf-8")
    assert _OVERRIDDEN_TITLE in pointer_text

    # The item's own stored mirror is STILL untouched — nothing above ever wrote it.
    assert _index_role_extra(paths, "reviewer")["title"] != _OVERRIDDEN_TITLE
    on_disk_md = (paths.abspath(reviewer_item.path)).read_text(encoding="utf-8")
    assert f"title: {_OVERRIDDEN_TITLE}" not in on_disk_md


async def test_sq_role_set_default_survives_sq_sync(tmp_path, monkeypatch):
    """Behaviour-level proof that the designation survives a reconcile: designate, sync, and it
    holds — no other role holds it, and the compiled default-role line names the designated
    role."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(
        root=tmp_path, backend=["claude_code", "agents_md"], roles_spec="all"
    )
    paths = result.paths
    svc = service.Service(paths)
    qa = await svc.roster_item("role", "qa")
    assert qa is not None

    move = await svc.set_default_role(qa.id)
    assert move.changed

    await svc.sync()

    roles = await svc.list_roles()
    default_holders = sorted(
        it.extra.get("slug", it.slug) for it in roles if it.extra.get("is_default")
    )
    assert default_holders == ["qa"]

    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "default to **Mara Tester** (`qa`)" in claude_md
    assert "default to **Catherine Manager**" not in claude_md


async def test_falsifying_the_is_default_carry_reproduces_the_revert(tmp_path, monkeypatch):
    """Break the fix, watch it fail; restore it, watch it pass — the durability-class check.

    Simulates the pre-fix merge base directly (``full_name`` carried, ``is_default`` not) to
    prove the carry is what closes the gap, without depending on any private resolver state
    that would make this brittle to unrelated refactors.
    """
    from dataclasses import replace

    from squads._roles._catalog import PREDEFINED
    from squads._roles._resolver import resolve_role_with_base

    monkeypatch.chdir(tmp_path)
    result = await service.init(
        root=tmp_path, backend=["claude_code", "agents_md"], roles_spec="all"
    )
    paths = result.paths
    svc = service.Service(paths)
    qa_item = await svc.roster_item("role", "qa")
    assert qa_item is not None
    await svc.set_default_role(qa_item.id)
    qa_item = await svc.roster_item("role", "qa")  # re-fetch: the designation just landed
    assert qa_item is not None

    qa_predefined = next(r for r in PREDEFINED if r.slug == "qa")
    assert qa_predefined.is_default is False  # sanity: qa is not the bundled catalog's default

    # The pre-fix base: only full_name carried, is_default always the catalog's stale answer —
    # reproduces the sync-reverts-set-default defect, at the resolver level rather than the CLI.
    pre_fix_base = replace(qa_predefined, full_name=qa_item.title)
    reverted = resolve_role_with_base("qa", paths.squad_dir, base=pre_fix_base)
    assert reverted.is_default is False  # the operator's designation is lost — the revert

    # The fixed base (what role_base_from_item now builds) carries the operator's designation.
    from squads._roles._resolver import role_base_from_item

    fixed_base = role_base_from_item(qa_item, paths.squad_dir)
    assert fixed_base is not None
    resolved = resolve_role_with_base("qa", paths.squad_dir, base=fixed_base)
    assert resolved.is_default is True  # restored — the carry holds
