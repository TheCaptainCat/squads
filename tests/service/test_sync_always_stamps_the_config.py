"""``sync()`` stamps ``squads_version`` unconditionally on every run, whether or not a roster
body was left untouched by the version-drift backfill — there is no stamp-withholding channel."""

from pathlib import Path

import pytest

from squads import __version__
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._models._schema import SCHEMA_VERSION
from squads._paths import resolve as resolve_squad_paths
from squads._sections import get_section, replace_section
from squads._services import _service as service

pytestmark = pytest.mark.anyio


async def _build_corpus_needing_the_version_drift_backfill(tmp_path: Path):
    """A full roster with one role's ``sq:body`` left genuinely empty, stamped as needing
    the version-drift backfill."""
    result = await service.init(root=tmp_path, roles_spec="all")
    svc = service.Service(result.paths)
    await svc.seed_bundled_skills()

    roles = await svc.list_items(item_type="role")
    assert roles

    role = roles[0]
    path = item_file(svc.paths, role)
    text = replace_section(path.read_text(encoding="utf-8"), markers.BODY, "")
    path.write_text(text, encoding="utf-8")

    (result.paths.root / ".squads.toml").write_text(
        "# squads project configuration\n"
        f'schema_version = "{SCHEMA_VERSION}"\n'
        'squad_dir = "squads"\n'
        'active_backends = ["claude_code"]\n'
        'squads_version = "0.14.0"\n',
        encoding="utf-8",
    )
    return result.paths.root, role.id


async def test_a_marker_shaped_body_is_left_untouched_and_the_stamp_still_lands(
    tmp_path, frozen_time
) -> None:
    """A marker-shaped body is left untouched, silently, and the stamp still lands."""
    root, role_id = await _build_corpus_needing_the_version_drift_backfill(tmp_path)
    paths = resolve_squad_paths(client_cwd=root)
    svc = service.Service(paths)
    path = item_file(svc.paths, await svc.get(role_id))
    text = replace_section(
        path.read_text(encoding="utf-8"),
        markers.BODY,
        f"stray content {markers.open_marker('something-unexpected')}",
    )
    path.write_text(text, encoding="utf-8")

    skipped = await svc.sync()

    assert not skipped
    region = (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
    assert "something-unexpected" in region, "the region was rewritten, not left alone"
    refreshed = resolve_squad_paths(client_cwd=root)
    assert refreshed.config.squads_version == __version__


async def test_a_clean_run_with_nothing_marker_shaped_stamps_the_config(
    tmp_path, frozen_time
) -> None:
    """A clean run with nothing marker-shaped still stamps the config on the first sync."""
    result = await service.init(root=tmp_path, roles_spec="minimal")
    svc = service.Service(result.paths)
    roles = await svc.list_items(item_type="role")
    path = item_file(svc.paths, roles[0])
    text = replace_section(path.read_text(encoding="utf-8"), markers.BODY, "")
    path.write_text(text, encoding="utf-8")
    (result.paths.root / ".squads.toml").write_text(
        "# squads project configuration\n"
        f'schema_version = "{SCHEMA_VERSION}"\n'
        'squad_dir = "squads"\n'
        'active_backends = ["claude_code"]\n'
        'squads_version = "0.14.0"\n',
        encoding="utf-8",
    )

    fresh_paths = resolve_squad_paths(client_cwd=result.paths.root)
    skipped = await service.Service(fresh_paths).sync()

    assert not skipped
    refreshed = resolve_squad_paths(client_cwd=result.paths.root)
    assert refreshed.config.squads_version == __version__
