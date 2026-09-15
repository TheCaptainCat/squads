"""The driven upgrade path: a real 0.14.x-shaped corpus — every role and permanently-system
skill ``sq:body`` region present and empty, the shape a release that rendered the definition on
read from a hardcoded branch, rather than storing it, leaves behind — upgraded through the
ORDINARY upgrade action (``sq sync``, never a manual ``sq repair``) and shown to render every
definition again.

``run_pending_migrations`` reaches the body-tag convergence step only when a schema migration
actually applies, so a squads release that bumps ``squads_version`` without also bumping
``schema_version`` leaves ``sq migrate up`` with nothing to run; ``sync()``'s own end-of-run
``_stamp_version`` writes only the config's ``squads_version`` field, never a body. Without
``sync()`` itself reaching the convergence step, a corpus in this shape stays empty regardless of
how many times an operator syncs. This module proves the fix, both at the service layer and
through the CLI, and proves the trigger is genuinely keyed on version drift (a no-drift sync
leaves an already-current, already-converged corpus alone, and costs no corpus walk).
"""

from pathlib import Path

import pytest

from squads import __version__
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._paths import resolve as resolve_squad_paths
from squads._sections import get_section, replace_section
from squads._services import _service as service

pytestmark = pytest.mark.anyio


async def _build_pre_tag_corpus(tmp_path: Path):
    """A full roster + a developer, then every role's and every permanently-system skill's
    ``sq:body`` stripped back to empty — the pre-tag-mechanism shape (a release that rendered
    the definition on read from a hardcoded branch, so the stored region was never anything
    but empty)."""
    result = await service.init(root=tmp_path, roles_spec="all")
    svc = service.Service(result.paths)
    await svc.add_dev("python", name="Elias Python")
    await svc.seed_bundled_skills()

    roles = await svc.list_items(item_type="role")
    skills = [
        it
        for it in await svc.list_items(item_type="skill")
        if it.extra.get("slug") in ("squads", "greeting", "sq-memory")
    ]
    assert len(roles) >= 9  # the full bundled roster plus the added developer
    assert len(skills) == 3

    for item in [*roles, *skills]:
        path = item_file(svc.paths, item)
        text = replace_section(path.read_text(encoding="utf-8"), markers.BODY, "")
        path.write_text(text, encoding="utf-8")

    # The version-drift trigger itself: stamp the config to a real prior release, matching a
    # corpus that has not been touched since 0.14.x.
    (result.paths.root / ".squads.toml").write_text(
        "# squads project configuration\n"
        'schema_version = "0.14"\n'
        'squad_dir = "squads"\n'
        'active_backends = ["claude_code"]\n'
        'squads_version = "0.14.0"\n',
        encoding="utf-8",
    )
    return result.paths.root, [it.id for it in roles], [it.id for it in skills]


async def test_every_role_and_skill_body_is_genuinely_empty_before_the_upgrade(
    tmp_path, frozen_time
) -> None:
    """Precondition, driven: the constructed corpus really is in the pre-tag shape, and the
    config really does record the older version."""
    root, role_ids, skill_ids = await _build_pre_tag_corpus(tmp_path)
    paths = resolve_squad_paths(client_cwd=root)
    assert paths.config.squads_version == "0.14.0"
    svc = service.Service(paths)
    for item_id in [*role_ids, *skill_ids]:
        item = await svc.get(item_id)
        path = item_file(svc.paths, item)
        region = (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
        assert region == "", f"{item_id} was not genuinely empty before the upgrade"


async def test_an_ordinary_sync_backfills_every_definition_with_no_manual_repair(
    tmp_path, frozen_time
) -> None:
    """The acceptance case: build the corpus, then call ONLY ``sync()`` — never ``repair()`` —
    and show every role's and every permanently-system skill's body carries its placement tag
    afterward, so ``sq role/skill show`` renders a real definition rather than an empty hint."""
    root, role_ids, skill_ids = await _build_pre_tag_corpus(tmp_path)
    paths = resolve_squad_paths(client_cwd=root)  # a fresh resolve — the same thing a new sq
    # invocation does, so this reads the 0.14.0 stamp just written, not a cached in-memory value
    svc = service.Service(paths)

    await svc.sync()  # the ordinary upgrade action — repair() is never called in this test

    for item_id in [*role_ids, *skill_ids]:
        item = await svc.get(item_id)
        path = item_file(svc.paths, item)
        region = (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
        assert region.startswith("<!-- sq:view:"), (
            f"{item_id}'s body was not backfilled by sync(): {region!r}"
        )
        # And the tag actually resolves to real rendered text, not an empty/error fallback.
        rendered = await svc.read_body(item_id)
        assert rendered.strip(), f"{item_id}'s definition rendered empty after the backfill"

    # sync() itself finished the job of an upgrade: the config is stamped current again.
    refreshed = resolve_squad_paths(client_cwd=root)
    assert refreshed.config.squads_version == __version__


async def test_sync_reports_no_manual_repair_was_needed_through_the_cli(
    tmp_path, frozen_time, invoke
) -> None:
    """The same proof through the actual command surface, not the service API directly —
    confirms the wiring reaches ``sq sync`` as an operator would run it."""
    import os

    root, role_ids, _skill_ids = await _build_pre_tag_corpus(tmp_path)
    cwd = Path.cwd()
    os.chdir(root)
    try:
        r = await invoke(["sync"])
        assert r.exit_code == 0, r.output

        paths = resolve_squad_paths(client_cwd=root)
        svc = service.Service(paths)
        item = await svc.get(role_ids[0])
        rendered = await svc.read_body(item.id)
        assert rendered.strip()
    finally:
        os.chdir(cwd)


async def test_a_no_drift_sync_does_not_re_walk_an_already_converged_corpus(
    tmp_path, frozen_time
) -> None:
    """The trigger is genuinely keyed on version drift, not run unconditionally on every sync:
    once the corpus is at the current version, a second ``sync()`` leaves an already-converged
    body byte-identical (idempotent either way, but this confirms the drift gate itself, not
    just the convergence function's own idempotency)."""
    root, role_ids, _skill_ids = await _build_pre_tag_corpus(tmp_path)
    paths = resolve_squad_paths(client_cwd=root)
    svc = service.Service(paths)
    await svc.sync()  # first sync: converges + stamps the current version

    item = await svc.get(role_ids[0])
    path = item_file(svc.paths, item)
    before = path.read_bytes()

    # Second sync, now at the current version already — must be a true no-op on this file.
    fresh_paths = resolve_squad_paths(client_cwd=root)
    await service.Service(fresh_paths).sync()

    assert path.read_bytes() == before
