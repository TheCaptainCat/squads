"""Message-and-exit parity across the four CLI consumers of the same body-tag-convergence /
corpus-rebuild sweep — ``sq repair`` (the reference implementation: its own docstring states
the exit rule, "0 = a clean rebuild, 1 = ... the same 'reported degradation is not success'
signal `sq check` gives at error level, so a caller gating on `$?` cannot mistake a board that
still needs a file fixed for one that came back clean"), ``sq migrate up`` (which runs the same
rebuild as its own trailing step), ``sq sync`` (which runs the narrower body-tag-only slice of
it on a version drift), and ``sq adopt`` (which runs the same rebuild to import a pre-existing
folder — the only route a folder of squads-native markdown meeting sq for the first time takes,
per its own code comment).

Table-driven over (command, channel): a body-tag convergence the guard declines (``skipped``),
a file that fails to read or parse (``unreadable``), and — ``sync`` only — a run that withheld
its own version stamp because of exactly that first channel. Each row builds the corpus state
that channel needs and asserts the reporting command's own wording against ``sq repair``'s for
the same defect, plus the exit code, checked bare (``CliRunner.exit_code``, never parsed back
out of a shell pipeline).

Before this task's fix: ``migrate up`` printed nothing at all for an ``unreadable`` file (while
still exiting 1 for it — a failure with no stated cause), ``sync`` printed the green
"synced ... to this squads version" line and exited 0 on the run that had just, by its own
docstring, deliberately withheld that exact stamp, and ``adopt`` printed nothing about either
channel and exited 0 regardless — the same "read the notice, drop the rest" shape ``migrate up``
had, reached through a fourth command the original three-command table never covered.
"""

from pathlib import Path

import pytest

from _helpers import make_unreadable_by_the_os
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._paths import resolve as resolve_squad_paths
from squads._sections import replace_section
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"

#: The two sentences `sq repair` prints, pinned once here — every row below asserts the command
#: under test reuses this exact wording rather than reimplementing its own.
_SKIPPED_WORDING = "this region was left untouched; fix the file by hand and repair again"
_UNREADABLE_WORDING = "its previous index entry, if any, was carried forward as-is; fix the file"


def _seed_marker_shaped_body(path: Path) -> None:
    """A well-formed ``sq:body`` region the convergence guard has no model for — the shape
    every ``skipped`` row in this module reproduces."""
    text = replace_section(
        path.read_text(encoding="utf-8"),
        markers.BODY,
        f"stray content {markers.open_marker('something-unexpected')}",
    )
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- (repair, skipped)


async def test_repair_skipped_row(svc, invoke) -> None:
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    _seed_marker_shaped_body(item_file(svc.paths, role))

    r = await invoke(["repair"])

    assert role.id in r.output
    assert _SKIPPED_WORDING in r.output
    assert r.exit_code == 1, r.output


# ------------------------------------------------------------------------ (repair, unreadable)


async def test_repair_unreadable_row(svc, invoke) -> None:
    from _helpers import create_item

    bad = (await create_item(svc, "task", "a task whose file will be made unreadable")).item
    make_unreadable_by_the_os(svc.paths.abspath(bad.path))

    r = await invoke(["repair"])

    assert bad.path.rsplit("/", 1)[-1] in r.output
    assert _UNREADABLE_WORDING in r.output
    assert r.exit_code == 1, r.output


# ---------------------------------------------------------------------- (migrate_up, skipped)


async def test_migrate_up_skipped_row(tmp_path, monkeypatch, invoke) -> None:
    import shutil

    dst = tmp_path / "v0_11"
    shutil.copytree(_CORPUS_DIR / "v0_11", dst)
    _seed_marker_shaped_body(dst / "agents" / "skills" / "SKILL-000008-squads.md")
    monkeypatch.chdir(dst)

    r = await invoke(["migrate", "up"])

    assert "SKILL-8" in r.output
    assert _SKIPPED_WORDING in r.output
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


# --------------------------------------------------------------- (sync, backfill_skipped)


async def _build_drifted_corpus_with_one_marker_shaped_role(tmp_path: Path):
    result = await service.init(root=tmp_path, roles_spec="all")
    svc = service.Service(result.paths)
    await svc.seed_bundled_skills()

    roles = await svc.list_items(item_type="role")
    assert len(roles) >= 1
    bad_role = roles[0]
    _seed_marker_shaped_body(item_file(svc.paths, bad_role))

    (result.paths.root / ".squads.toml").write_text(
        "# squads project configuration\n"
        'schema_version = "0.14"\n'
        'squad_dir = "squads"\n'
        'active_backends = ["claude_code"]\n'
        'squads_version = "0.14.0"\n',
        encoding="utf-8",
    )
    return result.paths.root, bad_role.id


async def test_sync_backfill_skipped_row_does_not_claim_success(
    tmp_path, monkeypatch, frozen_time, invoke
) -> None:
    root, bad_id = await _build_drifted_corpus_with_one_marker_shaped_role(tmp_path)
    monkeypatch.chdir(root)

    r = await invoke(["sync"])

    assert bad_id in r.output
    assert "synced" not in r.output.lower(), (
        f"sync must not claim success on a run that withheld its own version stamp: {r.output!r}"
    )
    assert "withheld" in r.output.lower()
    # Exit code is explicitly out of scope for this channel — sq sync already exits 0 for
    # other pre-existing skip channels (roster skew, unindexed bodies); this row does not
    # change that.
    assert r.exit_code == 0, r.output

    paths = resolve_squad_paths(client_cwd=root)
    assert paths.config.squads_version == "0.14.0", "the stamp must still be withheld on disk"


async def test_sync_clean_row_still_claims_success(svc, invoke) -> None:
    """Regression control: an ordinary sync with nothing to skip must still print the green
    success line — this row's fix only *subtracts* the claim, on exactly the withheld-stamp
    case, and must not touch the healthy one."""
    r = await invoke(["sync"])

    assert "synced" in r.output.lower()
    assert r.exit_code == 0, r.output


# --------------------------------------------------------------------------- (adopt, skipped)


async def _legacy_folder_with_one_marker_shaped_role(tmp_path: Path):
    """A folder of squads-native markdown with no ``.squads.toml``/index yet — the shape
    ``sq adopt`` exists to import — carrying one ``sq:body`` region the convergence guard
    declines to overwrite. Built by initialising a squad and then stripping the config/index
    files back off, the same construction :func:`test_adopt_imports_a_legacy_tree...` in
    ``tests/integration`` uses for an ordinary (non-defective) adopt."""
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    role = next(r for r in init.roles if r.extra.get(X.SLUG) == "manager")
    _seed_marker_shaped_body(item_file(init.paths, role))
    (tmp_path / ".squads.toml").unlink()
    (tmp_path / "squads" / ".squads.json").unlink()
    return role


async def test_adopt_skipped_row(tmp_path, monkeypatch, invoke) -> None:
    role = await _legacy_folder_with_one_marker_shaped_role(tmp_path)
    monkeypatch.chdir(tmp_path)

    r = await invoke(["adopt", "--roles", "minimal"])

    assert role.id in r.output
    assert _SKIPPED_WORDING in r.output
    assert r.exit_code == 1, r.output


# ------------------------------------------------------------------------ (adopt, unreadable)


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
    """Regression control: an ordinary adopt of a clean folder must keep exiting 0 — the fix
    only adds a channel, on exactly the skipped/unreadable defect rows, and must not turn a
    healthy import into a reported failure."""
    await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    (tmp_path / ".squads.toml").unlink()
    (tmp_path / "squads" / ".squads.json").unlink()
    monkeypatch.chdir(tmp_path)

    r = await invoke(["adopt", "--roles", "minimal"])

    assert r.exit_code == 0, r.output
