"""`_hoist_global_options` end to end: the real console-script entry point
(`squads._cli.main`, exercised here via `python -m squads`) makes `--at` work after the
subcommand, not just before it. The pure-function unit tests live in
tests/unit/test_hoist_global_options.py.
"""

import subprocess
import sys


def test_at_after_the_subcommand_backdates_the_item_via_a_real_subprocess(tmp_path):
    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "squads", *args], capture_output=True, text=True, cwd=tmp_path
        )

    assert run("init", "--no-seed-skills", "--roles", "minimal").returncode == 0

    result = run("create", "task", "Old work", "--author", "manager", "--at", "2020-05-06")
    assert result.returncode == 0, result.stderr

    md = next((tmp_path / "squads" / "tasks").glob("TASK-*.md")).read_text(encoding="utf-8")
    assert "created_at: '2020-05-06T00:00:00Z'" in md
