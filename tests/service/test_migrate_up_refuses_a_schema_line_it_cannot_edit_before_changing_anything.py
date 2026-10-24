"""``sq migrate up`` on a config whose schema line it cannot edit safely stops before the first
runner: the error names the file and the line, and no file in the squad has changed."""

import hashlib
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.anyio


def _tree(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.parts
    }


async def test_nothing_is_written_when_the_schema_line_cannot_be_edited(
    svc: Any, invoke: Any
) -> None:
    path = svc.paths.config_path
    current = svc.paths.config.schema_version
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(f'schema_version = "{current}"', 'schema_version = """0.14"""'),
        encoding="utf-8",
    )
    before = _tree(svc.paths.root)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 1, result.output
    assert ".squads.toml" in result.output
    assert "candidate lines: 2" in " ".join(result.output.split())
    assert _tree(svc.paths.root) == before
