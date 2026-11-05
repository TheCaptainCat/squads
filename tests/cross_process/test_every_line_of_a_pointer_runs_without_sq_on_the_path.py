"""Each shell line of a role skill pointer exits 0 and prints its fallback text when `sq` is not on
the PATH, under bash and zsh. The pointer is written by the real `sq sync` of a scratch squad.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from squads._paths import SquadPaths
from tests.cross_process._sq import env, run, sq_command

ROLE_SKILL = Path(".claude/skills/sq-role-manager/SKILL.md")


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_every_line_of_a_pointer_exits_0_and_names_its_command_when_sq_is_absent(
    seeded_project: SquadPaths, tmp_path: Path, shell: str
) -> None:
    interpreter = shutil.which(shell)
    if interpreter is None:
        pytest.skip(f"{shell} is not installed")
    assert run(sq_command(seeded_project, "sync")).returncode == 0
    lines = [
        line[2:-1]
        for line in (seeded_project.root / ROLE_SKILL).read_text(encoding="utf-8").splitlines()
        if line.startswith("!`")
    ]
    assert len(lines) == 3
    for line in lines:
        ran = subprocess.run(
            [interpreter, "-c", line],
            env={**env(), "PATH": str(tmp_path)},
            capture_output=True,
            text=True,
            check=False,
        )
        assert (ran.returncode, ran.stdout) == (
            0,
            line.split("echo '")[1].removesuffix("'") + "\n",
        )
