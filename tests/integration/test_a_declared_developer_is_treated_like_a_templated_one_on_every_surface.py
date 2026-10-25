"""A role is a developer because it holds a capability the ``[dev]`` table declares, however it
came to exist: a templated developer (``sq dev add``) and a declared one (a role file with the
capability) get identical answers on every surface, and a role merely named ``...-dev`` gets
the answers of any ordinary role.

One table: role shape by roster. Surfaces per role: the pointer's skill list, the per-type
skill's capability section, the create lane, ``sq dev list``. Surfaces per roster: the example
assignee in the squads skill and the delegate examples in ``CLAUDE.md``.
"""

import json
import re
from pathlib import Path

import pytest

from squads import __version__
from squads._interactions._skills import item_skill_name
from squads._workflow import ROSTER_SKILL

pytestmark = pytest.mark.anyio

_ROLE_FILE = (
    f"# squads:override-base:{__version__}\n"
    'full_name = "Bea Builder"\n'
    'title = "builder"\n'
    'description = "Builds things."\n'
    'mission = "Build things."\n'
)

#: shape -> slug
_SLUGS = {
    "templated": "rust-dev",
    "declared": "builder",
    "suffixed": "legacy-dev",
    "bundled": "architect",
}
_DEVELOPER_SHAPES = {"templated", "declared"}

_ROSTERS = {
    "all-four": ["bundled", "suffixed", "declared", "templated"],
    "only-declared": ["declared"],
    "only-suffixed": ["suffixed"],
    "no-developer": ["bundled"],
}


async def _add(svc, project, shape: str) -> None:
    slug = _SLUGS[shape]
    if shape == "templated":
        await svc.add_dev("rust")
        return
    if shape in ("declared", "suffixed"):
        path = project.squad_dir / ".overrides" / "roles" / f"{slug}.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        capabilities = 'capabilities = ["dev"]\n' if shape == "declared" else ""
        path.write_text(_ROLE_FILE + capabilities, encoding="utf-8")
    await svc.activate_role(slug)


def _pointer_skills(root: Path, slug: str) -> set[str]:
    text = (root / ".claude" / "agents" / f"{slug}.md").read_text(encoding="utf-8")
    return set(re.findall(r"^\s*- (sq-[a-z-]+)$", text, re.M))


async def _skill_body(svc, name: str) -> str:
    item = await svc.roster_item(ROSTER_SKILL, name)
    assert item is not None, name
    return await svc.read_body(item.id)


@pytest.mark.parametrize("roster", list(_ROSTERS))
async def test_every_surface_treats_a_developer_alike_however_it_was_made(
    roster: str, project, svc, invoke
) -> None:
    shapes = _ROSTERS[roster]
    for shape in shapes:
        await _add(svc, project, shape)
    await svc.seed_bundled_skills()
    synced = await invoke(["sync"])
    assert synced.exit_code == 0, synced.output

    from squads._services._service import open_service

    reader = open_service()
    task_skill = await _skill_body(reader, item_skill_name("task"))
    dev_listing = await invoke(["dev", "list"])
    assert dev_listing.exit_code == 0, dev_listing.output
    developer_slugs = [_SLUGS[s] for s in shapes if s in _DEVELOPER_SHAPES]

    answers: dict[str, tuple[bool, bool, tuple[str, ...], bool]] = {}
    for shape in shapes:
        slug = _SLUGS[shape]
        preloads_task = "sq-task" in _pointer_skills(Path(project.root), slug)
        in_section = f"(`{slug}`)" in "".join(
            ln for ln in task_skill.splitlines() if ln.startswith("## For `*dev`")
        )
        shown = await invoke(["role", slug, "show", "--json"])
        assert shown.exit_code == 0, shown.output
        lane = tuple(json.loads(shown.output)["create_lane"])
        listed = slug in dev_listing.output.split()
        answers[shape] = (preloads_task, in_section, lane, listed)
        is_developer = shape in _DEVELOPER_SHAPES
        assert (preloads_task, in_section, listed) == (is_developer,) * 3, (shape, answers[shape])

    # the invariants: developers alike on every surface, ordinary roles alike on the
    # developer surfaces
    assert len({a for s, a in answers.items() if s in _DEVELOPER_SHAPES}) <= 1
    assert len({(a[0], a[1], a[3]) for s, a in answers.items() if s not in _DEVELOPER_SHAPES}) <= 1

    # roster-level: the example assignee prefers a live developer, else the first role
    squads_skill = await _skill_body(reader, "squads")
    assignee = re.search(r"\d update --assignee (\S+)", squads_skill)
    assert assignee is not None
    all_slugs = ["manager", *(_SLUGS[s] for s in shapes)]
    expected = developer_slugs[0] if developer_slugs else "manager"
    assert assignee.group(1) == expected, (all_slugs, assignee.group(1))

    # roster-level: the delegate examples in CLAUDE.md are live non-default roles
    claude_md = " ".join((Path(project.root) / "CLAUDE.md").read_text(encoding="utf-8").split())
    sentence = re.search(r"slug below — e\.g\. (.*?)\), and hand it", claude_md)
    named = re.findall(r"`([a-z0-9-]+)`", sentence.group(1)) if sentence else []
    assert "manager" not in named
    assert set(named) <= {_SLUGS[s] for s in shapes}
    assert len(named) == min(4, len(shapes))
    if developer_slugs:
        assert set(named) & set(developer_slugs)


async def test_a_role_named_dev_gains_and_loses_the_developer_guidance_with_its_capability(
    project, svc, invoke
) -> None:
    """Declaring the capability and syncing turns an ordinary role named ``-dev`` into a
    developer; dropping it turns it back, with nothing else changed."""
    await _add(svc, project, "suffixed")
    role_file = project.squad_dir / ".overrides" / "roles" / "legacy-dev.toml"
    plain = role_file.read_text(encoding="utf-8")

    async def preloads_task() -> bool:
        assert (await invoke(["sync"])).exit_code == 0
        return "sq-task" in _pointer_skills(Path(project.root), "legacy-dev")

    assert await preloads_task() is False
    role_file.write_text(plain + 'capabilities = ["dev"]\n', encoding="utf-8")
    assert await preloads_task() is True
    role_file.write_text(plain, encoding="utf-8")
    assert await preloads_task() is False
