"""``sq repair``, ``sq migrate up``, ``sq sync`` and ``sq adopt`` all run the same corpus-rebuild
sweep, and must report an unreadable file with the same wording and exit code."""

from pathlib import Path

import pytest

from _helpers import make_unreadable_by_the_os
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"

#: The sentence `sq repair` prints; every row asserts its own command reuses this wording.
_UNREADABLE_WORDING = "its previous index entry, if any, was carried forward as-is; fix the file"


# ------------------------------------------------------------------------ (repair, unreadable)


async def test_repair_unreadable_row(svc, invoke) -> None:
    from _helpers import create_item

    bad = (await create_item(svc, "task", "a task whose file will be made unreadable")).item
    make_unreadable_by_the_os(svc.paths.abspath(bad.path))

    r = await invoke(["repair"])

    assert bad.path.rsplit("/", 1)[-1] in r.output
    assert _UNREADABLE_WORDING in r.output
    assert r.exit_code == 1, r.output


# ------------------------------------------------------------------- (migrate_up, unreadable)


async def test_migrate_up_unreadable_row(tmp_path, monkeypatch, invoke) -> None:
    import shutil

    dst = tmp_path / "v0_11"
    shutil.copytree(_CORPUS_DIR / "v0_11", dst)
    bad_path = dst / "tasks" / "TASK-000003-implement-auth.md"
    make_unreadable_by_the_os(bad_path)
    monkeypatch.chdir(dst)

    r = await invoke(["migrate", "up"])

    assert bad_path.name in r.output, (
        f"migrate up must report the unreadable file by name, matching sq repair: {r.output!r}"
    )
    assert _UNREADABLE_WORDING in r.output
    assert r.exit_code == 1, r.output


async def test_sync_clean_row_still_claims_success(svc, invoke) -> None:
    """An ordinary sync with nothing to skip must print the green success line."""
    r = await invoke(["sync"])

    assert "synced" in r.output.lower()
    assert r.exit_code == 0, r.output


# --------------------------------------------------------------------------- (adopt, unreadable)


async def test_adopt_unreadable_row(tmp_path, monkeypatch, invoke) -> None:
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init.paths)
    from _helpers import create_item

    bad = (await create_item(svc, "task", "a task whose file will be made unreadable")).item
    make_unreadable_by_the_os(svc.paths.abspath(bad.path))
    (tmp_path / ".squads.toml").unlink()
    (tmp_path / "squads" / ".squads.json").unlink()
    monkeypatch.chdir(tmp_path)

    r = await invoke(["adopt", "--roles", "minimal"])

    assert bad.path.rsplit("/", 1)[-1] in r.output
    assert _UNREADABLE_WORDING in r.output
    assert r.exit_code == 1, r.output


async def test_adopt_clean_row_still_exits_zero(tmp_path, monkeypatch, invoke) -> None:
    """Regression control: an ordinary adopt of a clean folder must keep exiting 0."""
    await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    (tmp_path / ".squads.toml").unlink()
    (tmp_path / "squads" / ".squads.json").unlink()
    monkeypatch.chdir(tmp_path)

    r = await invoke(["adopt", "--roles", "minimal"])

    assert r.exit_code == 0, r.output
