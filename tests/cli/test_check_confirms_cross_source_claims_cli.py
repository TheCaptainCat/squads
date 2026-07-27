"""``sq check``'s confirm round, exercised end to end through the CLI (not only the service):
a real, durable cross-source inconsistency still exits 3 and names itself in the output, and a
mutation that genuinely races the scan — a real background thread, a real transaction, real
files, sharing the same squad directory the CLI command reads — no longer flips a clean board
to exit 3.
"""

import os
import subprocess
import sys
import threading

import anyio
import pytest

from squads import _aio
from squads._services import _maintenance as maintenance
from squads._services import _service as service

pytestmark = pytest.mark.anyio


async def test_a_durable_orphan_file_is_reported_with_exit_code_3_through_the_cli(project, invoke):
    create_result = await invoke(["create", "task", "orphaned", "--author", "manager"])
    assert create_result.exit_code == 0, create_result.output

    svc = service.Service(project)
    db = await svc.store.load()
    task = next(iter(db.items.values()))
    async with svc.store.transaction() as db2:
        del db2.items[task.sequence_id]

    result = await invoke(["check"])
    assert result.exit_code == 3, result.output
    assert "on disk but not in index" in result.output


async def test_a_clean_board_still_exits_0_through_the_cli(project, invoke):
    await invoke(["create", "task", "t"])
    result = await invoke(["check"])
    assert result.exit_code == 0, result.output


async def test_a_mutation_racing_the_scan_no_longer_flips_sq_check_to_exit_3_through_the_cli(
    tmp_path, invoke, monkeypatch
):
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    setup_svc = service.Service(paths)
    task = (await setup_svc.create("task", "t")).item

    started = threading.Event()
    release = threading.Event()
    orig_scan = maintenance.MaintenanceMixin._scan_for_check  # pyright: ignore[reportPrivateUsage]

    async def paused_scan(self):
        started.set()
        await _aio.to_thread(release.wait)
        return await orig_scan(self)

    monkeypatch.setattr(
        maintenance.MaintenanceMixin,
        "_scan_for_check",
        paused_scan,  # pyright: ignore[reportPrivateUsage]
    )

    def mutate() -> None:
        started.wait()

        async def _do() -> None:
            mutator = service.Service(paths)
            await mutator.set_status(task.id, "InProgress")

        anyio.run(_do)
        release.set()

    thread = threading.Thread(target=mutate)
    thread.start()
    try:
        result = await invoke(["--dir", str(paths.squad_dir), "check"])
    finally:
        thread.join()

    assert result.exit_code == 0, result.output
    assert "drift" not in result.output


def test_a_clean_board_exits_0_from_a_bare_subprocess_invocation(tmp_path):
    """The literal contract, checked without a shell pipe masking the code: a bare process
    invocation of the CLI, not `CliRunner`, on a genuinely clean board."""
    init = subprocess.run(
        [
            sys.executable,
            "-m",
            "squads",
            "init",
            "--squad-dir",
            "squads",
            "--roles",
            "minimal",
            "--default-names",
        ],
        cwd=tmp_path,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert init.returncode == 0, init.stderr.decode("utf-8", "replace")

    result = subprocess.run(
        [sys.executable, "-m", "squads", "check"],
        cwd=tmp_path,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
