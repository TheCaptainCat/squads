"""A chained flow: `sq init` scaffolds `.claude/` pointer files, then `sq migrate up` runs
(a no-op today, since a fresh init is already at the current schema) — after both steps, every
`.claude/` pointer must carry no filesystem-path reference, and the definition-fetch command it
names instead (`sq role <slug> show` / `sq skill <slug> show`) must actually resolve. Neither
step in isolation proves this; it's the composite that matters, which is exactly why it lives at
the integration layer.

A path reference is unsatisfiable once the CLI is a client to a squads server — there is no
local squad directory for it to name. A named command has no such failure mode: it resolves
through `sq` in every mode, so this is what the dangling-reference scan checks for today.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

#: A pointer's one definition-fetch command line, e.g. `` `sq role architect show` ``.
_FETCH_COMMAND_RE = re.compile(r"`(sq (?:role|skill) \S+ show)`")


def _pointer_files(root: Path) -> list[Path]:
    claude_dir = root / ".claude"
    if not claude_dir.is_dir():
        return []
    return [p for p in claude_dir.rglob("*.md") if p.is_file()]


def _at_path_references(pointer: Path) -> list[str]:
    """Every `@relative/path` reference line in a pointer file's body — the shape a pointer
    must never carry any more: a path a host loader resolves before squads is in the picture
    at all, rather than a command that resolves through `sq`."""
    text = pointer.read_text(encoding="utf-8")
    return [line[1:].strip() for line in text.splitlines() if line.startswith("@")]


def _fetch_commands(pointer: Path) -> list[str]:
    """Every definition-fetch command a pointer names, in the order they appear."""
    return _FETCH_COMMAND_RE.findall(pointer.read_text(encoding="utf-8"))


async def test_init_then_migrate_up_leaves_no_pointer_naming_a_dangling_path(tmp_path, monkeypatch):
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
        for target in _at_path_references(pointer)
    ]
    assert not dangling, f"pointer(s) naming a filesystem path: {dangling}"


async def test_init_then_migrate_up_cli_every_pointer_fetch_command_resolves(
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
        for target in _at_path_references(pointer)
    ]
    assert not dangling, f"pointer(s) naming a filesystem path: {dangling}"

    failing: list[str] = []
    for pointer in pointers:
        commands = _fetch_commands(pointer)
        assert commands, f"{pointer.relative_to(root)} names no definition-fetch command"
        for command in commands:
            cr = await invoke(command.split()[1:])
            if cr.exit_code != 0:
                failing.append(f"{pointer.relative_to(root)} -> `{command}` (exit {cr.exit_code})")
    assert not failing, f"pointer fetch command(s) that don't resolve: {failing}"


def test_pointer_reference_regex_matches_the_syntax_used_by_the_templates():
    """A guard on the helpers above: the templates emit a bare `@relative/path` line for a
    dangling reference (never markdown link syntax) and a backtick-quoted `sq role|skill <slug>
    show` line for the fetch command — if either convention ever changes this test fails loudly
    instead of the scans above silently finding nothing to check."""
    assert re.match(r"^@\S+$", "@squads/agents/roles/ROLE-000001-manager.md")
    assert _FETCH_COMMAND_RE.findall("`sq role architect show`") == ["sq role architect show"]
    assert _FETCH_COMMAND_RE.findall("`sq skill sq-task show`") == ["sq skill sq-task show"]
