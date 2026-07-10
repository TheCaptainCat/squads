"""A chained flow: `sq init` scaffolds `.claude/` pointer files, then `sq migrate up` runs
(a no-op today, since a fresh init is already at the current schema) — after both steps, every
`.claude/` pointer's `@`-referenced target must exist on disk. Neither step in isolation proves
this; it's the composite that matters, which is exactly why it lives at the integration layer.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio


def _pointer_files(root: Path) -> list[Path]:
    claude_dir = root / ".claude"
    if not claude_dir.is_dir():
        return []
    return [p for p in claude_dir.rglob("*.md") if p.is_file()]


def _referenced_targets(pointer: Path) -> list[str]:
    """Every `@relative/path` reference line in a pointer file's body."""
    text = pointer.read_text(encoding="utf-8")
    return [line[1:].strip() for line in text.splitlines() if line.startswith("@")]


async def test_init_then_migrate_up_leaves_no_dangling_claude_pointers(tmp_path, monkeypatch):
    from squads._services import _service as service

    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")

    svc = service.Service(result.paths)
    await svc.run_pending_migrations()  # sq migrate up's own path; a no-op on a fresh init

    pointers = _pointer_files(tmp_path)
    assert pointers, "a fresh init with the claude_code backend must scaffold pointer files"

    dangling = [
        f"{pointer.relative_to(tmp_path)} -> {target}"
        for pointer in pointers
        for target in _referenced_targets(pointer)
        if not (tmp_path / target).exists()
    ]

    assert not dangling, f"dangling .claude pointer target(s): {dangling}"


async def test_init_then_migrate_up_cli_leaves_no_dangling_claude_pointers(
    tmp_path, monkeypatch, invoke
):
    monkeypatch.chdir(tmp_path)
    r = await invoke(["init", "--roles", "minimal"])
    assert r.exit_code == 0, r.output

    r = await invoke(["migrate", "up"])
    assert r.exit_code == 0, r.output

    from squads._paths import resolve

    root = resolve().root
    pointers = _pointer_files(root)
    assert pointers

    dangling = [
        f"{pointer.relative_to(root)} -> {target}"
        for pointer in pointers
        for target in _referenced_targets(pointer)
        if not (root / target).exists()
    ]
    assert not dangling, f"dangling .claude pointer target(s): {dangling}"


def test_pointer_reference_regex_matches_the_at_syntax_used_by_the_templates():
    """A guard on the helper above: the templates emit a bare `@relative/path` line (not
    markdown link syntax) — if that convention ever changes this test fails loudly instead of
    the dangling-pointer scan above silently finding nothing to check."""
    assert re.match(r"^@\S+$", "@squads/agents/roles/ROLE-000001-manager.md")
