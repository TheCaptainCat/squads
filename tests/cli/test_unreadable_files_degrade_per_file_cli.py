"""CLI-level smoke coverage for the per-file degradation contract: exit codes asserted on a
bare process invocation, never through a shell pipe that would mask them (a pipeline reports
the pipe's own exit code, not the command's -- see the project's exit-code contract notes).
"""

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from _helpers import create_item, make_unreadable_by_the_os
from squads._index._resolver import item_file
from squads._memory._store import role_folder
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
    `error:` and silently kept exit 0 is indistinguishable from a clean one to a script.

    The per-file error itself belongs on stderr, exactly as the human and ``--json`` branches
    both promise -- asserted here on the two streams captured separately (a real OS pipe per
    stream, not a combined capture), with explicit absence from stdout so a script splitting
    the streams never finds a degraded read mixed into its results."""
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init.paths)
    notice = await svc.board_post("op-alice", "a fine notice")
    notice_path = svc.paths.squad_dir / "board" / f"{notice.id}.md"
    make_unreadable_by_the_os(notice_path)

    result = _run(tmp_path, "board", "list")

    stdout = result.stdout.decode("utf-8", "replace")
    stderr = result.stderr.decode("utf-8", "replace")
    assert result.returncode == 1, stderr
    assert notice_path.name in stderr
    assert notice_path.name not in stdout


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
    assert notice_path.name in result.stderr.decode("utf-8", "replace")


async def test_memory_list_names_the_unreadable_entry_on_stderr_only(tmp_path):
    """`sq memory <role> list`'s docstring promises the per-file error is "named on stderr
    in both output modes" -- checked here on the human branch, with the two streams captured
    separately (a real OS pipe per stream) so a script that splits them never finds the
    degraded-read notice mixed into its results."""
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init.paths)
    await svc.memory_add("manager", "a remembered fact")
    memory_path = next(iter(role_folder(init.paths, "manager").glob("*.md")))
    make_unreadable_by_the_os(memory_path)

    result = _run(tmp_path, "memory", "manager", "list")

    stdout = result.stdout.decode("utf-8", "replace")
    stderr = result.stderr.decode("utf-8", "replace")
    assert memory_path.name in stderr
    assert memory_path.name not in stdout


async def test_memory_search_names_the_unreadable_entry_on_stderr_only(tmp_path):
    """Same stream contract as `memory list` above, for `memory search`'s identical per-file
    loop."""
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init.paths)
    await svc.memory_add("manager", "a remembered fact")
    memory_path = next(iter(role_folder(init.paths, "manager").glob("*.md")))
    make_unreadable_by_the_os(memory_path)

    result = _run(tmp_path, "memory", "manager", "search", "fact")

    stdout = result.stdout.decode("utf-8", "replace")
    stderr = result.stderr.decode("utf-8", "replace")
    assert memory_path.name in stderr
    assert memory_path.name not in stdout


async def _inbox_and_search_setup(tmp_path):
    """One readable item carrying a mention and the needle text, and one to break."""
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init.paths)
    good = (await create_item(svc, "task", "readable")).item
    await svc.set_body(good.id, "the quinoa line, and @manager is called out")
    bad = (await create_item(svc, "task", "unreadable")).item
    await svc.set_body(bad.id, "also quinoa, also @manager")
    bad_path = item_file(svc.paths, bad)
    make_unreadable_by_the_os(bad_path)
    return good, bad_path


@pytest.mark.parametrize("args", [["inbox", "manager"], ["search", "quinoa"]])
async def test_inbox_and_search_name_the_unreadable_file_on_stderr_only(tmp_path, args):
    """`sq inbox` and `sq search` share `_report_unreadable` (unlike `board list`/`memory
    list`, which have their own inline loop) -- checked here with the two streams captured
    as real, separate OS pipes (``subprocess.run``'s default), because a combined-output
    grep passes on the defect this guards against and is exactly how it survived the
    earlier stream-contract sweep."""
    good, bad_path = await _inbox_and_search_setup(tmp_path)

    result = _run(tmp_path, *args)

    stdout = result.stdout.decode("utf-8", "replace")
    stderr = result.stderr.decode("utf-8", "replace")
    assert result.returncode == 1, stderr
    assert good.id in stdout  # the answer is still delivered
    assert bad_path.name in stderr
    assert bad_path.name not in stdout


@pytest.mark.parametrize("command", ["inbox", "search"])
async def test_inbox_and_search_json_stays_a_bare_array_and_reports_on_stderr(tmp_path, command):
    """`--json`'s stream split was already correct before this fix and must stay
    byte-for-byte the same: a bare JSON array on stdout, the per-file error on stderr, and
    nothing of the error leaking into either the JSON body or stdout generally."""
    good, bad_path = await _inbox_and_search_setup(tmp_path)
    args = ["inbox", "manager", "--json"] if command == "inbox" else ["search", "quinoa", "--json"]

    result = _run(tmp_path, *args)

    stdout = result.stdout.decode("utf-8", "replace")
    stderr = result.stderr.decode("utf-8", "replace")
    assert result.returncode == 1, stderr
    payload = json.loads(stdout)
    assert [row["id"] for row in payload] == [good.id]
    assert bad_path.name not in stdout
    assert bad_path.name in stderr


@pytest.mark.parametrize("args", [["inbox", "manager"], ["search", "quinoa"]])
async def test_inbox_and_search_clean_read_has_no_stderr_and_exits_zero(tmp_path, args):
    """The counterpart to the degraded-read tests above: nothing unreadable means nothing on
    stderr, the answer on stdout, and exit 0 -- unchanged by this fix."""
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init.paths)
    good = (await create_item(svc, "task", "readable")).item
    await svc.set_body(good.id, "the quinoa line, and @manager is called out")

    result = _run(tmp_path, *args)

    stdout = result.stdout.decode("utf-8", "replace")
    stderr = result.stderr.decode("utf-8", "replace")
    assert result.returncode == 0, stderr
    assert stderr == ""
    assert good.id in stdout


def _soft_wrap_true_at(rel_path: str, func_name: str) -> bool:
    """Whether *func_name* in *rel_path* has at least one ``.print(..., soft_wrap=True)``
    call -- an explicit, site-named pin (independent of the general marker-matching scan in
    ``tests/meta``) so switching the stream on these three sites cannot silently drop the
    wrapping fix that already landed for them."""
    repo_root = Path(__file__).resolve().parents[2]
    tree = ast.parse((repo_root / rel_path).read_text(encoding="utf-8"))
    func = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.AsyncFunctionDef | ast.FunctionDef) and n.name == func_name
    )
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "print"
        and any(
            kw.arg == "soft_wrap" and isinstance(kw.value, ast.Constant) and kw.value.value is True
            for kw in node.keywords
        )
        for node in ast.walk(func)
    )


@pytest.mark.parametrize(
    ("rel_path", "func_name"),
    [
        ("src/squads/_cli/_board.py", "list_notices"),
        ("src/squads/_cli/_memory.py", "list_memories"),
        ("src/squads/_cli/_memory.py", "search_memories"),
        ("src/squads/_cli/_main.py", "_report_unreadable"),
    ],
)
def test_the_human_mode_unreadable_error_still_carries_soft_wrap(rel_path, func_name):
    """The stream fix above (`console` -> `err_console`) must not quietly drop
    ``soft_wrap=True`` at these sites -- the earlier wrapping fix stays intact. The last entry
    is the single shared site for both `inbox` and `search` (`_report_unreadable`, called from
    each rather than inlined in either)."""
    assert _soft_wrap_true_at(rel_path, func_name)


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
