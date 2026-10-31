"""Helpers the squad-wide command tests share: flattening a panel, listing and reading the
agent files a command writes, and the ids and titles the CLI reports."""

import json
import re
from pathlib import Path
from typing import Any

BOX = str.maketrans("", "", "│╭╮╰╯─ \n")


def flat(output: str) -> str:
    """*output* without whitespace and panel borders, so a wrapped panel compares whole."""
    return output.translate(BOX)


def agent_files(root: Path) -> list[str]:
    """The agent files under *root*: the `.claude` pointers and settings (not the skills),
    `CLAUDE.md` and `AGENTS.md`, as sorted relative paths."""
    found = [
        p.relative_to(root).as_posix()
        for p in (*root.glob(".claude/**/*"), root / "CLAUDE.md", root / "AGENTS.md")
        if p.is_file() and not p.relative_to(root).as_posix().startswith(".claude/skills/")
    ]
    return sorted(found)


def region(path: Path) -> list[str]:
    """The lines of the managed region of *path*, between its start and end markers."""
    text = path.read_text(encoding="utf-8")
    match = re.search(r"<!-- squads:start -->\n(.*?)\n<!-- squads:end -->", text, re.DOTALL)
    assert match, f"{path.name} holds no managed region"
    return match.group(1).split("\n")


async def listed(invoke) -> list[tuple[str, str]]:
    """The (id, title) of every item `sq list --json` reports."""
    result = await invoke(["list", "--json"])
    assert result.exit_code == 0, result.output
    items: list[dict[str, Any]] = json.loads(result.output)
    return [(item["id"], item["title"]) for item in items]
