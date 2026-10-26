"""``sq workflow --raw`` (and ``sq workflow show --raw``) print the cheatsheet as clean
markdown — zero Rich chrome (no box-drawing table borders, no ANSI) — mirroring the
``sq show --raw`` precedent: opt out of ``rich.Markdown`` rendering, print the
``workflow.md.j2`` source verbatim (markdown tables, no diagram markup). Pinned
against a golden text file so a future template change is a deliberate, reviewed diff.

Regenerating the golden: set ``UPDATE_GOLDENS=1`` and run this module; commit the diff.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

GOLDENS_DIR = Path(__file__).parents[1] / "goldens"
_UPDATE = os.getenv("UPDATE_GOLDENS") == "1"
#: The installed `sq` console script, so forced colour reaches a fresh process.
_SQ_BIN = Path(sys.executable).parent / "sq"


def _check_golden(name: str, actual: str) -> None:
    path = GOLDENS_DIR / f"{name}.txt"
    if _UPDATE:
        GOLDENS_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        return
    assert path.exists(), f"golden file missing: {path}"
    assert actual == path.read_text(encoding="utf-8"), f"golden mismatch for {name!r}"


async def test_workflow_raw_matches_the_clean_markdown_golden(project, invoke):
    result = await invoke(["workflow", "--raw"])
    assert result.exit_code == 0
    _check_golden("workflow_cheatsheet_raw", result.output)


async def test_workflow_show_raw_matches_the_same_golden(project, invoke):
    """``show --raw`` reaches the identical render path as the bare ``--raw`` callback."""
    result = await invoke(["workflow", "show", "--raw"])
    assert result.exit_code == 0
    _check_golden("workflow_cheatsheet_raw", result.output)


async def test_workflow_raw_has_zero_rich_chrome(project, invoke):
    result = await invoke(["workflow", "--raw"])
    assert result.exit_code == 0
    for box_char in "╭╮╰╯│─":
        assert box_char not in result.output
    assert "\x1b[" not in result.output


async def test_workflow_raw_emits_markdown_tables_and_no_diagram_markup(project, invoke):
    result = await invoke(["workflow", "--raw"])
    assert result.exit_code == 0
    assert "| Canonical | Aliases | Example |" in result.output
    assert "| Prefix | Type | Lifecycle |" in result.output
    assert "```mermaid" not in result.output


@pytest.mark.skipif(sys.platform == "win32", reason="rich writes no ANSI to a pipe on Windows")
async def test_workflow_raw_has_no_escape_codes_even_when_colour_is_forced(project):
    """Run as a subprocess: the console is built once at import, so only a fresh process reads
    forced colour (the autouse fixture strips it from the in-process environment)."""
    env = {k: v for k, v in os.environ.items() if k != "TTY_COMPATIBLE"}
    env["FORCE_COLOR"] = "3"
    env["TERM"] = "xterm-256color"  # a dumb terminal is colourless even when forced

    def run(*args: str) -> str:
        proc = subprocess.run(
            [str(_SQ_BIN), *args], cwd=project.root, env=env, capture_output=True, text=True
        )
        assert proc.returncode == 0, proc.stderr
        return proc.stdout

    assert "\x1b[" in run("workflow"), "precondition: forced colour styles the rendered form"
    raw = run("workflow", "--raw")
    assert "\x1b[" not in raw
    for box_char in "╭╮╰╯│─":
        assert box_char not in raw
