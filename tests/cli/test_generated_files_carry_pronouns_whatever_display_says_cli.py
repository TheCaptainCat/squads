"""The roster section of ``CLAUDE.md`` and ``AGENTS.md`` and an agent's identity pointer carry the
resolved pronouns after the name, whatever ``[display]`` says; a name without pronouns renders as
it always did, and ``sq check`` is clean after ``sq sync`` for every row."""

from typing import Any

import pytest

from squads import __version__
from squads._rendering._engine import invalidate_squad_dir
from squads._services._service import Service

pytestmark = pytest.mark.anyio

# (shape, own role value, default declared, operator value, display on)
SHAPES: list[tuple[str, str | None, bool, str | None, bool]] = [
    ("nothing-anywhere", None, False, None, True),
    ("own-value", "she/her", False, None, True),
    ("default-declared", None, True, None, True),
    ("operator-with-value", None, False, "he/him", True),
    ("display-off", "she/her", False, "he/him", False),
]
_IDS = [s[0] for s in SHAPES]


async def _build(
    svc: Service, invoke: Any, own: str | None, default: bool, operator: str | None, display: bool
) -> None:
    config = svc.paths.config_path
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            'active_backends = ["claude_code"]', 'active_backends = ["claude_code", "agents_md"]'
        )
        + ("" if display else "\n[display]\npronouns = false\n"),
        encoding="utf-8",
    )
    if default:
        target = svc.paths.squad_dir / ".overrides" / "roles.toml"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f'# squads:override-base:{__version__}\n[defaults]\npronouns = "they/them"\n',
            encoding="utf-8",
        )
        invalidate_squad_dir(svc.paths.squad_dir)
    await svc.activate_role("architect", pronouns=own)
    await svc.add_operator("Alex Rivera", pronouns=operator)
    assert (await invoke(["sync"])).exit_code == 0


@pytest.mark.parametrize(("shape", "own", "default", "operator", "display"), SHAPES, ids=_IDS)
async def test_the_roster_lines_and_pointer_carry_the_resolved_pronouns(
    svc: Service,
    invoke: Any,
    shape: str,
    own: str | None,
    default: bool,
    operator: str | None,
    display: bool,
) -> None:
    await _build(svc, invoke, own, default, operator, display)
    root = svc.paths.root
    role = own or ("they/them" if default else None)
    name = "**Robert Architect**" + (f" ({role})" if role else "")
    person = "**Alex Rivera**" + (f" ({operator})" if operator else "")

    claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    pointer = (root / ".claude" / "agents" / "architect.md").read_text(encoding="utf-8")

    for text in (claude, agents):
        assert f"- {name} — architect (`architect`)" in text
        assert f"- {person} (`op-alex`)" in text
    assert f"You are {name}, the architect on this project." in pointer


@pytest.mark.parametrize(("shape", "own", "default", "operator", "display"), SHAPES, ids=_IDS)
async def test_check_is_clean_after_sync_and_a_second_sync_changes_nothing(
    svc: Service,
    invoke: Any,
    shape: str,
    own: str | None,
    default: bool,
    operator: str | None,
    display: bool,
) -> None:
    await _build(svc, invoke, own, default, operator, display)
    root = svc.paths.root
    files = [root / "CLAUDE.md", root / "AGENTS.md", root / ".claude" / "agents" / "architect.md"]
    once = [f.read_bytes() for f in files]

    await invoke(["sync"])
    checked = await invoke(["check"])

    assert checked.exit_code == 0, checked.output
    assert [f.read_bytes() for f in files] == once


async def test_a_changed_value_and_a_removed_default_reach_the_files_on_sync(
    svc: Service, invoke: Any
) -> None:
    await _build(svc, invoke, None, True, None, True)
    root = svc.paths.root
    assert "(they/them)" in (root / "CLAUDE.md").read_text(encoding="utf-8")

    await invoke(["role", "architect", "update", "--pronouns", "she/her"])
    changed = (root / "CLAUDE.md").read_text(encoding="utf-8")
    (svc.paths.squad_dir / ".overrides" / "roles.toml").unlink()
    invalidate_squad_dir(svc.paths.squad_dir)
    await invoke(["sync"])
    removed = (root / "CLAUDE.md").read_text(encoding="utf-8")

    assert "**Robert Architect** (she/her)" in changed
    assert "**Robert Architect** (she/her)" in removed
    assert "they/them" not in removed
