"""One table: an override file of any kind that is non-UTF-8, unreadable, malformed, a directory or
empty, crossed with the commands that touch overrides. No cell ends in a traceback or a codec
dump; a cell that refuses names the file and the cause."""

import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

_CANNOT_CHMOD = sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0)

#: kind -> (path under .overrides, the words that address it in `override diff|update`)
_KINDS = {
    "workflow": ("workflow.toml", ["--workflow"]),
    "playbook": ("playbook.toml", ["--playbook"]),
    "roles": ("roles.toml", ["--roles-catalog"]),
    "role": ("roles/manager.toml", ["--role", "manager"]),
    "template": ("templates/items/task.md.j2", ["items/task.md.j2"]),
}
_DAMAGES = ["not-utf8", "unreadable", "malformed", "directory", "empty"]

#: command label -> argv ({name} is the kind's override name)
_COMMANDS = {
    "list": ["list"],
    "check": ["check"],
    "repair": ["repair"],
    "lint": ["workflow", "lint"],
    "override list": ["override", "list"],
    "override list json": ["override", "list", "--json"],
    "override diff": ["override", "diff"],
    "override diff all": ["override", "diff"],
    "override update": ["override", "update"],
    "override update all": ["override", "update"],
    "sync": ["sync"],
    "role list": ["role", "list"],
    "role show": ["role", "manager", "show"],
    "create task": ["create", "task", "a title", "--author", "manager"],
    "adopt": ["adopt"],
    "help": ["--help"],
}
_DAMAGE_PHRASE = {
    "not-utf8": "not valid utf-8",
    "unreadable": "cannot read",
    "directory": "cannot read",
}
_ALL = frozenset(_KINDS)
_SPEC_DOCUMENTS = frozenset({"workflow", "playbook", "roles", "role"})
#: command label -> the kinds whose damage it must refuse (exit 1, 3 for `check`) by naming the
#: file and the cause; every other cell runs to completion with exit 0.
_REFUSES = {
    "list": frozenset({"workflow", "playbook"}),
    "check": _ALL,
    "lint": frozenset({"workflow"}),
    "override list": _ALL,
    "override list json": _ALL,
    "override diff": _ALL,
    "override diff all": _ALL,
    "override update": _ALL,
    "override update all": _ALL,
    "sync": _SPEC_DOCUMENTS,
    "role list": _SPEC_DOCUMENTS,
    "role show": _SPEC_DOCUMENTS,
    "create task": _ALL,
    "adopt": _SPEC_DOCUMENTS,
}
#: Output that carries no prose to check the cause in: a table or JSON.
_NO_PROSE = frozenset({"lint", "override list json"})


def _damage(path: Path, damage: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if damage == "not-utf8":
        path.write_bytes(b"\xff\xfe")
    elif damage == "unreadable":
        path.write_text("", encoding="utf-8")
        path.chmod(0)
    elif damage == "malformed":
        path.write_text("[[ not toml ===\n{% broken\n", encoding="utf-8")
    elif damage == "directory":
        path.mkdir()
    else:
        path.write_text("", encoding="utf-8")


def _argv(label: str, kind: str) -> list[str]:
    argv = list(_COMMANDS[label])
    if label in ("override diff", "override update"):
        argv += _KINDS[kind][1]
    return argv


@pytest.mark.parametrize("damage", _DAMAGES)
@pytest.mark.parametrize("kind", list(_KINDS))
@pytest.mark.parametrize("label", list(_COMMANDS))
async def test_a_damaged_override_never_ends_in_a_traceback(
    project, invoke, label: str, kind: str, damage: str
) -> None:
    if damage == "unreadable" and _CANNOT_CHMOD:
        pytest.skip("permission bits are not enforced for this user or platform")
    relative = _KINDS[kind][0]
    override = project.squad_dir / ".overrides" / relative
    _damage(override, damage)
    try:
        result = await invoke(_argv(label, kind))
    finally:
        if override.exists() and not override.is_dir():
            override.chmod(0o600)

    out = " ".join(result.output.split())
    assert result.exception is None or isinstance(result.exception, SystemExit), out
    assert "Traceback" not in out
    assert "codec" not in out
    if damage in _DAMAGE_PHRASE:
        _assert_outcome(label, kind, damage, result.exit_code, out)


def _assert_outcome(label: str, kind: str, damage: str, exit_code: int, out: str) -> None:
    if kind not in _REFUSES.get(label, frozenset()):
        assert exit_code == 0, out
        return
    assert exit_code == (3 if label == "check" else 1), out
    if label in _NO_PROSE:
        return
    assert "nothing to update" not in out and "no drifted overrides" not in out, out
    lowered = out.lower()
    assert Path(_KINDS[kind][0]).name.lower() in lowered, out
    assert _DAMAGE_PHRASE[damage] in lowered, out


@pytest.mark.parametrize("label", ["override diff all", "override update all"])
async def test_a_bulk_override_command_handles_the_healthy_ones_and_names_the_damaged(
    project, invoke, label: str
) -> None:
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(exist_ok=True)
    (overrides / "workflow.toml").write_text("[statuses.Triage]\n", encoding="utf-8")
    (overrides / "playbook.toml").write_bytes(b"\xff\xfe")

    result = await invoke(_COMMANDS[label])

    out = " ".join(result.output.split())
    assert result.exit_code == 1, out
    assert "playbook.toml" in out
    assert "not valid UTF-8" in out
    assert ("Override: workflow" in out) if "diff" in label else ("re-stamped workflow" in out)
