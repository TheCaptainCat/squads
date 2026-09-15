"""``sync()``'s version-drift trigger must fire when ``squads_version`` names a *prerelease* of
the release currently running, not just an older one.

The trigger's comparator strips a package version's suffix on ``ValueError`` and treats that as
drift rather than ordering it — see the comment beside the trigger in
``MaintenanceMixin.sync()``. Before that fallback existed, the tolerant
:func:`~squads._util.version_tuple` comparator this trigger used to share with the CLI's cosmetic
drift notice ordered a prerelease *above* its own release and *equal to* the next patch (it
strips non-digits per segment and concatenates the survivors, so ``"0.15.0rc1"`` becomes
``(0, 15, 1)`` — identical to ``"0.15.1"``). A squad stamped by a prerelease build of the
release currently installed therefore read as never-drifted against it, and the backfill this
trigger exists to run was silently never called.

Driven by patching :meth:`MaintenanceMixin._backfill_roster_body_tags` and asserting whether it
was awaited, rather than only checking the on-disk body — the exact same shape of failure this
guards against (a definition that quietly never renders again) would otherwise leave a false
negative undetected if some other path happened to converge the body anyway.
"""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from squads import __version__
from squads._paths import resolve as resolve_squad_paths
from squads._services import _maintenance as maintenance
from squads._services import _service as service

pytestmark = pytest.mark.anyio


async def _build_corpus_stamped_at(tmp_path: Path, *, squads_version_stamp: str) -> Path:
    result = await service.init(root=tmp_path, roles_spec="minimal")
    (result.paths.root / ".squads.toml").write_text(
        "# squads project configuration\n"
        'schema_version = "0.14"\n'
        'squad_dir = "squads"\n'
        'active_backends = ["claude_code"]\n'
        f'squads_version = "{squads_version_stamp}"\n',
        encoding="utf-8",
    )
    return result.paths.root


async def test_a_prerelease_stamp_of_the_current_release_still_triggers_the_backfill(
    tmp_path, frozen_time, monkeypatch
) -> None:
    """``squads_version`` is a prerelease of the exact release now running (``__version__``
    itself, suffixed) — the sharpest form of the reordering bug, since an ordinary
    lexicographic/string comparison would also get this one right by accident. Only the
    stripped-and-concatenated tuple comparison confuses the two."""
    stamp = f"{__version__}rc1"
    root = await _build_corpus_stamped_at(tmp_path, squads_version_stamp=stamp)
    paths = resolve_squad_paths(client_cwd=root)
    svc = service.Service(paths)

    backfill = AsyncMock(return_value=[])
    monkeypatch.setattr(maintenance.MaintenanceMixin, "_backfill_roster_body_tags", backfill)

    await svc.sync()

    backfill.assert_awaited_once()


async def test_an_ordinary_older_stamp_still_triggers_the_backfill(
    tmp_path, frozen_time, monkeypatch
) -> None:
    """Regression control: a plain, older release stamp must still be seen as drift — the
    fail-safe fallback must not have swallowed the ordinary case."""
    root = await _build_corpus_stamped_at(tmp_path, squads_version_stamp="0.14.0")
    paths = resolve_squad_paths(client_cwd=root)
    svc = service.Service(paths)

    backfill = AsyncMock(return_value=[])
    monkeypatch.setattr(maintenance.MaintenanceMixin, "_backfill_roster_body_tags", backfill)

    await svc.sync()

    backfill.assert_awaited_once()


async def test_an_already_current_stamp_does_not_trigger_the_backfill(
    tmp_path, frozen_time, monkeypatch
) -> None:
    """Regression control: a squad already at the running version must not re-run the backfill
    on every sync — the fail-safe fallback only fires on a genuine parse failure, never on an
    ordinary no-drift comparison."""
    root = await _build_corpus_stamped_at(tmp_path, squads_version_stamp=__version__)
    paths = resolve_squad_paths(client_cwd=root)
    svc = service.Service(paths)

    backfill = AsyncMock(return_value=[])
    monkeypatch.setattr(maintenance.MaintenanceMixin, "_backfill_roster_body_tags", backfill)

    await svc.sync()

    backfill.assert_not_awaited()
