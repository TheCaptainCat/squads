"""``sync()``'s version-drift trigger must tolerate a non-numeric ``squads_version`` segment —
the shape a pre-release/dev/local package build stamps (``"0.14.0rc1"``) and the exact shape
the CLI's own drift notice (``_cli/_common.py::version_notice``) already tolerates when it tells
an operator to run this very command.

Before this fix the trigger compared with ``schema_tuple`` (``_models/_schema.py``), which parses
each dot-segment as a plain integer and raises a bare ``ValueError`` the moment one carries a
non-digit suffix — a real regression: a v0.14.0-built squad synced cleanly under the pre-collapse
code, and the same stamp shape only started crashing once this trigger was added on top of it.
"""

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


async def _build_pre_tag_role_corpus(tmp_path: Path, *, squads_version_stamp: str):
    """One role with a genuinely empty ``sq:body`` (the pre-tag-mechanism shape), stamped at
    *squads_version_stamp* — a value below the running package's own version, by the tolerant
    comparator, whatever its exact digit shape."""
    result = await service.init(root=tmp_path, roles_spec="minimal")
    svc = service.Service(result.paths)
    roles = await svc.list_items(item_type="role")
    role = roles[0]
    path = item_file(svc.paths, role)
    text = replace_section(path.read_text(encoding="utf-8"), markers.BODY, "")
    path.write_text(text, encoding="utf-8")

    (result.paths.root / ".squads.toml").write_text(
        "# squads project configuration\n"
        f'schema_version = "{SCHEMA_VERSION}"\n'
        'squad_dir = "squads"\n'
        'active_backends = ["claude_code"]\n'
        f'squads_version = "{squads_version_stamp}"\n',
        encoding="utf-8",
    )
    return result.paths.root, role.id


async def test_sync_does_not_raise_on_a_prerelease_squads_version_stamp(
    tmp_path, frozen_time
) -> None:
    """Driven with the exact reproduction shape from the review: a squad whose config reads
    ``squads_version = "0.14.0rc1"``. Before the fix this raised a bare ``ValueError`` out of
    ``schema_tuple``; ``sync()`` must complete without raising anything at all here (the trigger
    tolerates the shape cleanly — there is nothing malformed about it for this call's purposes)."""
    root, _role_id = await _build_pre_tag_role_corpus(tmp_path, squads_version_stamp="0.14.0rc1")
    paths = resolve_squad_paths(client_cwd=root)
    svc = service.Service(paths)

    await svc.sync()  # must not raise ValueError (or anything else)


async def test_sync_still_detects_drift_and_backfills_under_a_prerelease_stamp(
    tmp_path, frozen_time
) -> None:
    """Not just "doesn't crash" — the comparison must still correctly see 0.14.0rc1 as older
    than the running build and run the backfill, rather than silently treating the unfamiliar
    shape as "no drift" and leaving the empty body exactly as it was."""
    root, role_id = await _build_pre_tag_role_corpus(tmp_path, squads_version_stamp="0.14.0rc1")
    paths = resolve_squad_paths(client_cwd=root)
    svc = service.Service(paths)

    await svc.sync()

    item = await svc.get(role_id)
    path = item_file(svc.paths, item)
    region = (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
    assert region.startswith("<!-- sq:view:"), (
        f"drift was not detected under a prerelease stamp: {region!r}"
    )
    refreshed = resolve_squad_paths(client_cwd=root)
    assert refreshed.config.squads_version == __version__


async def test_sync_reports_no_manual_repair_was_needed_under_a_prerelease_stamp_through_the_cli(
    tmp_path, frozen_time, invoke
) -> None:
    """The same proof through the actual CLI surface — confirms the fix reaches ``sq sync`` as
    an operator would run it, not only the service call directly."""
    import os

    root, role_id = await _build_pre_tag_role_corpus(tmp_path, squads_version_stamp="0.14.0rc1")
    cwd = Path.cwd()
    os.chdir(root)
    try:
        r = await invoke(["sync"])
        assert r.exit_code == 0, r.output
        assert "Traceback" not in r.output
    finally:
        os.chdir(cwd)

    paths = resolve_squad_paths(client_cwd=root)
    svc = service.Service(paths)
    rendered = await svc.read_body(role_id)
    assert rendered.strip()
