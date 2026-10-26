"""A playbook guide's subject is checked for grammar only when the playbook loads; whether a
role holds it is ``sq check``'s finding (``playbook_guide_role_live``). So a guide may name a role
that is defined only in its item, that role preloads the skill, and a typo'd slug loads and is
reported.

One table over the subject shapes.
"""

import json
import re

import pytest

from _helpers import add_role_from_toml
from squads import __version__
from squads._interactions._skills import item_skill_name

pytestmark = pytest.mark.anyio

_ITEM = 'full_name = "Sam Sre"\ntitle = "SRE"\ndescription = "Keeps it up."\nmission = "Run it."\n'


def _playbook(project, *subjects: str) -> None:
    guides = ",\n".join(
        f'    {{ slug = "{s}", enter = ["Read the timeline"], do = ["Roll back"] }}'
        for s in subjects
    )
    path = project.squad_dir / ".overrides" / "playbook.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = f"# squads:override-base:{__version__}\n"
    path.write_text(
        f'{stamp}[types.task]\nroles = [\n    "$(*self)",\n{guides}\n]\n', encoding="utf-8"
    )


def _pointer_skills(project, slug: str) -> set[str]:
    text = (project.root / ".claude" / "agents" / f"{slug}.md").read_text(encoding="utf-8")
    return set(re.findall(r"^\s*- (sq-[a-z-]+)$", text, re.M))


async def test_a_guide_for_a_role_defined_only_in_its_item_loads_and_preloads_the_skill(
    project, invoke
) -> None:
    _playbook(project, "sre")
    from squads._services import _service as service

    svc = service.open_service(client_cwd=project.squad_dir)
    await add_role_from_toml(svc, "sre", _ITEM)
    assert (await invoke(["sync"])).exit_code == 0

    assert item_skill_name("task") in _pointer_skills(project, "sre")
    shown = json.loads((await invoke(["role", "sre", "show", "--json"])).output)
    assert item_skill_name("task") in shown["skills"]
    checked = await invoke(["check"])
    assert "names no live role" not in " ".join(checked.output.split())
    assert not (project.squad_dir / ".overrides" / "roles").exists()  # no per-slug file


async def test_a_typo_in_a_guide_slug_loads_and_is_reported_not_refused(project, invoke) -> None:
    _playbook(project, "srr")

    checked = await invoke(["check", "--json"])

    findings = json.loads(checked.output)
    reported = [f for f in findings if f["rule"] == "playbook_guide_role_live"]
    assert len(reported) == 1 and "'srr'" in reported[0]["message"]
    assert "sq role add srr" in reported[0]["message"]
    assert not [f for f in findings if f["rule"] == "playbook_loads"]


@pytest.mark.parametrize("subject", ["Sre", "s re", "-sre", "*Audit", "op-pierre", "squads", "add"])
async def test_a_subject_outside_the_grammar_is_still_refused_at_load(
    project, invoke, subject: str
) -> None:
    _playbook(project, subject)

    checked = await invoke(["check"])

    assert checked.exit_code != 0
    assert "playbook config invalid" in checked.output


async def test_a_capability_guide_reaches_a_role_that_defines_itself_with_it(
    project, invoke
) -> None:
    _playbook(project, "*audit")
    from squads._services import _service as service

    svc = service.open_service(client_cwd=project.squad_dir)
    await add_role_from_toml(svc, "sre", _ITEM + 'capabilities = ["audit"]\n')
    assert (await invoke(["sync"])).exit_code == 0

    assert item_skill_name("task") in _pointer_skills(project, "sre")
    checked = await invoke(["check", "--json"])
    assert not [f for f in json.loads(checked.output) if f["rule"] == "playbook_guide_role_live"]
