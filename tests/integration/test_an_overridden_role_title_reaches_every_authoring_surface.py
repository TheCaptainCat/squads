"""A project override that retitles a bundled role reaches **every** line of the compiled
managed region, not only the roster list.

The region names a role's title twice from two different code paths: the roster list renders it
off the ``RoleView`` (resolved through the role catalog + overrides), and each authoring bullet
renders it through ``authoring_owner``. When only the first resolves, one compiled file states
two different titles for one role — the roster line carrying the project's answer and the
authoring bullet carrying the bundled one, both inside the same ``squads:start``/``squads:end``
block an agent host reads as authoritative.

So the assertion here is by absence rather than by position: the bundled title occurs **nowhere**
in the region. Checking the two known lines would pass while a third rendering of the same value
kept disagreeing.

The same function feeds the workflow cheatsheet, which is shared by the generated ``squads``
skill body and ``sq workflow`` — both covered, because the cheatsheet half of the defect never
appeared in the compiled region at all.
"""

from pathlib import Path

import pytest

from squads._backends._managed_region import END, START
from squads._paths import SquadPaths
from squads._roles._catalog import PREDEFINED
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_OVERRIDDEN_TITLE = "chief verification officer"
#: The bundled title the override displaces — read from the catalog, never spelled as a literal.
_BUNDLED_TITLE = next(r for r in PREDEFINED if r.slug == "reviewer").title


def _managed_region(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    start, end = text.find(START), text.find(END)
    assert start != -1 and end != -1, f"{path} carries no managed region"
    return text[start : end + len(END)]


def _write_catalog_override(squad_dir: Path, body: str) -> None:
    path = squad_dir / ".overrides" / "roles.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _write_role_override(squad_dir: Path, slug: str, body: str) -> None:
    path = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _write_playbook_override(squad_dir: Path, body: str) -> None:
    path = squad_dir / ".overrides" / "playbook.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _flat(text: str) -> str:
    """Whitespace-collapsed, case-folded text.

    The cheatsheet renders a title with its first character upper-cased, and the console wraps
    long lines — either alone would make a plain substring check answer the wrong question.
    """
    return " ".join(text.split()).casefold()


async def _squads_skill_body(paths: SquadPaths) -> str:
    """The ``squads`` skill definition this squad resolves — rendered on read from the live
    roster and the active catalog, never from a stored region."""
    return await service.Service(paths).skill_definition_text("squads")


async def _initialized_squad(tmp_path: Path) -> SquadPaths:
    """A squad carrying the whole bundled roster and both managed-region backends."""
    result = await service.init(
        root=tmp_path, backend=["claude_code", "agents_md"], roles_spec="all"
    )
    return result.paths


async def test_a_retitled_bundled_role_leaves_no_bundled_title_in_the_compiled_region(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    paths = await _initialized_squad(tmp_path)
    await service.Service(paths).sync()

    # Control: with no override, both renderings agree on the bundled title. This is also the
    # standing proof that the catalog and the live roster carry the *same* kind of value (the
    # role title), so consulting the roster first cannot change a no-override render.
    baseline = _flat(_managed_region(tmp_path / "CLAUDE.md"))
    assert _BUNDLED_TITLE.casefold() in baseline
    assert _OVERRIDDEN_TITLE.casefold() not in baseline

    _write_catalog_override(paths.squad_dir, f'[roles.reviewer]\ntitle = "{_OVERRIDDEN_TITLE}"\n')
    await service.Service(paths).sync()

    for name in ("CLAUDE.md", "AGENTS.md"):
        region = _flat(_managed_region(tmp_path / name))
        assert _OVERRIDDEN_TITLE.casefold() in region, name
        # By absence, not by line number: no rendering anywhere in the region still says it.
        assert _BUNDLED_TITLE.casefold() not in region, name


async def test_the_generated_squads_skill_carries_the_overridden_title(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    paths = await _initialized_squad(tmp_path)
    _write_catalog_override(paths.squad_dir, f'[roles.reviewer]\ntitle = "{_OVERRIDDEN_TITLE}"\n')
    await service.Service(paths).sync()

    body = _flat(await _squads_skill_body(paths))
    assert _OVERRIDDEN_TITLE.casefold() in body
    assert _BUNDLED_TITLE.casefold() not in body


async def test_the_workflow_cheatsheet_command_carries_the_overridden_title(
    tmp_path, monkeypatch, invoke
):
    monkeypatch.chdir(tmp_path)
    paths = await _initialized_squad(tmp_path)
    _write_catalog_override(paths.squad_dir, f'[roles.reviewer]\ntitle = "{_OVERRIDDEN_TITLE}"\n')
    await service.Service(paths).sync()

    res = await invoke(["workflow"])
    assert res.exit_code == 0
    output = _flat(res.output)
    assert _OVERRIDDEN_TITLE.casefold() in output
    assert _BUNDLED_TITLE.casefold() not in output


#: A role that exists only because the project declared it — no bundled catalog entry at all —
#: put in an authoring lane by a playbook override. This is the path that used to be the *only*
#: consumer of the live titles; the reordering must not regress it.
_AUDITOR_AUTHORS_REVIEWS = """
[types.review]
roles = [
    { slug = "auditor", authors = true, do = ["record the audit"] },
]
"""


async def test_a_role_declared_only_by_the_project_still_gets_its_authoring_bullet(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    paths = await _initialized_squad(tmp_path)
    _write_role_override(
        paths.squad_dir,
        "auditor",
        'full_name = "Ann Auditor"\ntitle = "compliance auditor"\n'
        'description = "Audits the record."\nmission = "Audit every change."\n',
    )
    _write_playbook_override(paths.squad_dir, _AUDITOR_AUTHORS_REVIEWS)
    fresh = service.Service(paths)
    await fresh.activate_role("auditor")
    await fresh.sync()

    region = _flat(_managed_region(tmp_path / "CLAUDE.md"))
    assert "compliance auditor" in region
