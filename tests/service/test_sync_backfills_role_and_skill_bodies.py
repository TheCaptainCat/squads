"""The driven upgrade path: a corpus whose role and permanently-system skill ``sq:body`` regions
are all empty (the shape a release that rendered the definition on read, rather than storing
it, leaves behind), upgraded through the ordinary action (``sq sync``, never a manual
``sq repair``) and shown to render every definition again.
"""

from pathlib import Path

import pytest

from _helpers import make_service
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
    svc = make_service(result.paths)
    await svc.activate_role(None, from_template="dev", tech="python", name="Elias Python")
    await svc.seed_bundled_skills()

    roles = await svc.list_items(item_type="role")
    skills = [
        it
        for it in await svc.list_items(item_type="skill")
        if it.slug in ("squads", "greeting", "sq-memory")
    ]
    assert len(roles) >= 9  # the full bundled roster plus the added developer
    assert len(skills) == 3

    for item in [*roles, *skills]:
        path = item_file(svc.paths, item)
        text = replace_section(path.read_text(encoding="utf-8"), markers.BODY, "")
        path.write_text(text, encoding="utf-8")

    return result.paths.root, [it.id for it in roles], [it.id for it in skills]


async def test_every_role_and_skill_body_is_genuinely_empty_before_the_upgrade(
    tmp_path, frozen_time
) -> None:
    """Precondition, driven: the constructed corpus really is in the pre-tag shape."""
    root, role_ids, skill_ids = await _build_pre_tag_corpus(tmp_path)
    paths = resolve_squad_paths(client_cwd=root)
    svc = make_service(paths)
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
    paths = resolve_squad_paths(client_cwd=root)
    svc = make_service(paths)

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
        svc = make_service(paths)
        item = await svc.get(role_ids[0])
        rendered = await svc.read_body(item.id)
        assert rendered.strip()
    finally:
        os.chdir(cwd)


async def test_a_second_sync_leaves_a_converged_body_byte_identical(tmp_path, frozen_time) -> None:
    root, role_ids, _skill_ids = await _build_pre_tag_corpus(tmp_path)
    paths = resolve_squad_paths(client_cwd=root)
    svc = make_service(paths)
    await svc.sync()

    item = await svc.get(role_ids[0])
    path = item_file(svc.paths, item)
    before = path.read_bytes()

    await make_service(resolve_squad_paths(client_cwd=root)).sync()

    assert path.read_bytes() == before
