"""``sq workflow --raw`` (and ``sq workflow show --raw``) print the cheatsheet as clean
markdown — zero Rich chrome (no box-drawing table borders, no ANSI) — mirroring the
``sq show --raw`` precedent: opt out of ``rich.Markdown`` rendering, print the
``workflow.md.j2`` source verbatim (markdown tables + fenced ```mermaid``` blocks). Pinned
against a golden text file so a future template change is a deliberate, reviewed diff.

Regenerating the golden: set ``UPDATE_GOLDENS=1`` and run this module; commit the diff.
"""

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

GOLDENS_DIR = Path(__file__).parents[1] / "goldens"
_UPDATE = os.getenv("UPDATE_GOLDENS") == "1"


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


async def test_workflow_raw_emits_fenced_mermaid_and_markdown_tables(project, invoke):
    result = await invoke(["workflow", "--raw"])
    assert result.exit_code == 0
    assert "```mermaid" in result.output
    assert "flowchart TD" in result.output
    assert "stateDiagram-v2" in result.output
    assert "| Canonical | Aliases | Example |" in result.output
