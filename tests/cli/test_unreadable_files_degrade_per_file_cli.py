"""CLI-level smoke coverage for the per-file degradation contract: exit codes asserted on a
bare process invocation, never through a shell pipe that would mask them (a pipeline reports
the pipe's own exit code, not the command's -- see the project's exit-code contract notes).
"""

import os
import subprocess
import sys

import pytest

from _helpers import create_item, make_unreadable_by_the_os
from squads._services import _service as service

pytestmark = pytest.mark.anyio


def _run(tmp_path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "squads", *args],
        cwd=tmp_path,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


async def test_check_exits_3_bare_on_a_corrupt_item_file(tmp_path):
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init.paths)
    task = (await create_item(svc, "task", "corrupt target")).item
    make_unreadable_by_the_os(svc.paths.abspath(task.path))

    result = _run(tmp_path, "check")

    assert result.returncode == 3, result.stderr.decode("utf-8", "replace")


async def test_repair_exits_1_bare_on_a_corrupt_item_file(tmp_path):
    """Exit code decision (a `sq check`-style error signal, not the old bare 0): `repair` did
    rebuild, but it carried a stale entry forward rather than refreshing it, and its own
    printed message tells the operator to fix the file and repair again -- a caller gating on
    `$?` must be able to tell that apart from a clean rebuild."""
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init.paths)
    task = (await create_item(svc, "task", "corrupt target")).item
    make_unreadable_by_the_os(svc.paths.abspath(task.path))

    result = _run(tmp_path, "repair")

    assert result.returncode == 1, result.stderr.decode("utf-8", "replace")

    listed = _run(tmp_path, "list", "-a")
    assert listed.returncode == 0, listed.stderr.decode("utf-8", "replace")
    assert task.id in listed.stdout.decode("utf-8", "replace")


async def test_board_list_exits_1_bare_on_a_corrupt_notice(tmp_path):
    """Same exit-code decision as `repair` above, for the same reason: a listing that printed
    `error:` and silently kept exit 0 is indistinguishable from a clean one to a script."""
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init.paths)
    notice = await svc.board_post("op-alice", "a fine notice")
    notice_path = svc.paths.squad_dir / "board" / f"{notice.id}.md"
    make_unreadable_by_the_os(notice_path)

    result = _run(tmp_path, "board", "list")

    assert result.returncode == 1, result.stderr.decode("utf-8", "replace")
    # Rich hard-wraps a long unbroken path at the console width with a bare newline -- flatten
    # before searching so a wrap point isn't mistaken for a miss.
    flattened = result.stdout.decode("utf-8", "replace").replace("\n", "")
    assert notice_path.name in flattened


async def test_board_list_json_stays_a_bare_array_and_reports_on_stderr(tmp_path):
    """`--json`'s array shape is a frozen contract, so a degraded read cannot add a key to it
    -- the unreadable notice is instead named on stderr, and the exit code (not the JSON body)
    is what tells an automated caller the listing was incomplete."""
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init.paths)
    await svc.board_post("op-alice", "a fine notice")
    notice2 = await svc.board_post("op-alice", "a corrupt notice")
    notice_path = svc.paths.squad_dir / "board" / f"{notice2.id}.md"
    make_unreadable_by_the_os(notice_path)

    result = _run(tmp_path, "board", "list", "--json")

    assert result.returncode == 1, result.stderr.decode("utf-8", "replace")
    stdout = result.stdout.decode("utf-8", "replace")
    assert stdout.strip().startswith("["), stdout
    assert notice_path.name not in stdout, "the JSON body itself must stay untouched"
    # Rich hard-wraps a long unbroken path at the console width with a bare newline -- flatten
    # before searching so a wrap point isn't mistaken for a miss.
    stderr_flattened = result.stderr.decode("utf-8", "replace").replace("\n", "")
    assert notice_path.name in stderr_flattened


async def test_check_reports_a_type_invalid_field_without_a_traceback(tmp_path):
    """The fourth failure shape (valid YAML, type-invalid field), at the CLI edge: `check` must
    report it cleanly rather than print `no issues` (the bug) or a raw pydantic traceback."""
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init.paths)
    task = (await create_item(svc, "task", "type-invalid target")).item
    path = svc.paths.abspath(task.path)
    path.write_text(
        path.read_text(encoding="utf-8").replace("title: type-invalid target", "title:\n- a\n- b"),
        encoding="utf-8",
    )

    result = _run(tmp_path, "check")
    assert result.returncode == 3, result.stderr.decode("utf-8", "replace")
    stdout = result.stdout.decode("utf-8", "replace")
    assert "Traceback" not in stdout
    assert task.path.split("/")[-1] in stdout.replace("\n", "")

    result = _run(tmp_path, "repair")
    assert result.returncode == 1, result.stderr.decode("utf-8", "replace")
    stdout = result.stdout.decode("utf-8", "replace")
    assert "Traceback" not in stdout


async def test_repair_recovers_from_a_broken_symlink_without_a_traceback(tmp_path):
    """The fifth failure shape (a present dirent, absent target) at the CLI edge, across both
    commands the finding drove."""
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init.paths)
    await create_item(svc, "task", "an ordinary task")
    ghost = svc.paths.squad_dir / "tasks" / "TASK-999998-ghost.md"
    ghost.symlink_to("/nonexistent/target")

    for args, code in (("check", 3), ("repair", 1)):
        result = _run(tmp_path, args)
        assert result.returncode == code, (args, result.stderr.decode("utf-8", "replace"))
        stdout = result.stdout.decode("utf-8", "replace")
        assert "Traceback" not in stdout
        assert "ghost.md" in stdout.replace("\n", "")


@pytest.mark.parametrize("args", [["check"], ["repair"], ["board", "list"]])
async def test_a_clean_board_exits_0_bare_across_touched_commands(tmp_path, args):
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init.paths)
    await create_item(svc, "task", "an ordinary task")
    await svc.board_post("op-alice", "an ordinary notice")

    result = _run(tmp_path, *args)

    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
