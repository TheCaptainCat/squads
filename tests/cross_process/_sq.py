"""Running the real `sq` console script of the test environment against a scratch squad."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from squads._paths import SquadPaths


def env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("FORCE_COLOR", None)
    return env


def sq_command(project: SquadPaths, *args: str) -> list[str]:
    """The `sq` console script of the running environment, on the project."""
    script = shutil.which("sq", path=str(Path(sys.executable).parent))
    assert script is not None, "the sq console script is not installed next to the interpreter"
    return [script, "-C", str(project.root), *args]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, env=env(), check=False)
