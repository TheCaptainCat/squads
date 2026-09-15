"""``sync()``'s version-drift trigger must not stamp ``squads_version`` past a body-tag skip.

Before this fix, ``sync()`` stamped the config to the running version unconditionally at the
end of the run, whether or not the backfill it had just called actually converged every body.
A role/skill whose ``sq:body`` held marker-shaped content the guard has no model for was
therefore never revisited: the very next ``sync`` reads the config already at the current
version, the drift comparison goes false, and the backfill call is never reached again — the
skip reported once, in passing, alongside a run that otherwise says "synced", and then silence
forever. This module drives the fix: withholding the stamp is what keeps the drift trigger true
until the skip is actually resolved, so every later ``sync`` retries (and re-reports) it.
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


async def _build_corpus_with_one_marker_shaped_role(tmp_path: Path):
    """A full roster, one role's ``sq:body`` left genuinely empty (the ordinary pre-tag shape,
    which converges cleanly) and a second role's ``sq:body`` holding marker-shaped content the
    convergence guard has no model for (which does not) — both stamped as needing the
    version-drift backfill."""
    result = await service.init(root=tmp_path, roles_spec="all")
    svc = service.Service(result.paths)
    await svc.seed_bundled_skills()

    roles = await svc.list_items(item_type="role")
    assert len(roles) >= 2

    good_role, bad_role = roles[0], roles[1]
    good_path = item_file(svc.paths, good_role)
    good_text = replace_section(good_path.read_text(encoding="utf-8"), markers.BODY, "")
    good_path.write_text(good_text, encoding="utf-8")

    bad_path = item_file(svc.paths, bad_role)
    bad_text = replace_section(
        bad_path.read_text(encoding="utf-8"),
        markers.BODY,
        f"stray content {markers.open_marker('something-unexpected')}",
    )
    bad_path.write_text(bad_text, encoding="utf-8")

    (result.paths.root / ".squads.toml").write_text(
        "# squads project configuration\n"
        'schema_version = "0.14"\n'
        'squad_dir = "squads"\n'
        'active_backends = ["claude_code"]\n'
        'squads_version = "0.14.0"\n',
        encoding="utf-8",
    )
    return result.paths.root, good_role.id, bad_role.id


async def test_a_sync_that_reports_a_skip_does_not_stamp_the_config(tmp_path, frozen_time) -> None:
    root, _good_id, bad_id = await _build_corpus_with_one_marker_shaped_role(tmp_path)
    paths = resolve_squad_paths(client_cwd=root)
    svc = service.Service(paths)

    skipped = await svc.sync()

    assert any(bad_id in msg for msg in skipped)
    refreshed = resolve_squad_paths(client_cwd=root)
    assert refreshed.config.squads_version == "0.14.0", (
        "the stamp must be withheld when this run's own backfill reported a skip"
    )


async def test_the_skip_is_still_retried_and_reported_on_a_second_sync(
    tmp_path, frozen_time
) -> None:
    """The reachability half of the fix: since the stamp was withheld, a second, later ``sync``
    (nothing else changed) must retry the backfill and report the same skip again — not read
    the config as already-current and go silent."""
    root, _good_id, bad_id = await _build_corpus_with_one_marker_shaped_role(tmp_path)
    paths = resolve_squad_paths(client_cwd=root)
    await service.Service(paths).sync()

    fresh_paths = resolve_squad_paths(client_cwd=root)
    second_skipped = await service.Service(fresh_paths).sync()

    assert any(bad_id in msg for msg in second_skipped), (
        "a second sync must retry and re-report the still-unresolved skip, not go silent"
    )
    still_unstamped = resolve_squad_paths(client_cwd=root)
    assert still_unstamped.config.squads_version == "0.14.0"


async def test_the_other_roles_own_convergence_still_completes_despite_the_withheld_stamp(
    tmp_path, frozen_time
) -> None:
    """Withholding the stamp must not regress the sweep's own per-file isolation: the one bad
    body is reported and left alone, while every other role in the same run still converges
    onto its tag."""
    root, good_id, bad_id = await _build_corpus_with_one_marker_shaped_role(tmp_path)
    paths = resolve_squad_paths(client_cwd=root)
    svc = service.Service(paths)

    await svc.sync()

    good_item = await svc.get(good_id)
    good_path = item_file(svc.paths, good_item)
    good_region = (get_section(good_path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
    assert good_region.startswith("<!-- sq:view:")

    bad_item = await svc.get(bad_id)
    bad_path = item_file(svc.paths, bad_item)
    bad_region = (get_section(bad_path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
    assert "something-unexpected" in bad_region


async def test_a_clean_run_with_no_skips_still_stamps_the_config(tmp_path, frozen_time) -> None:
    """Control: the withholding is conditional on an actual skip, not a general regression —
    a corpus with nothing marker-shaped still gets stamped on the very first sync, exactly as
    before this fix."""
    result = await service.init(root=tmp_path, roles_spec="minimal")
    svc = service.Service(result.paths)
    roles = await svc.list_items(item_type="role")
    path = item_file(svc.paths, roles[0])
    text = replace_section(path.read_text(encoding="utf-8"), markers.BODY, "")
    path.write_text(text, encoding="utf-8")
    (result.paths.root / ".squads.toml").write_text(
        "# squads project configuration\n"
        'schema_version = "0.14"\n'
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
