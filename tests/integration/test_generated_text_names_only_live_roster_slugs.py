"""No generated agent-facing file states a slug pattern or names a role the squad does not
have: examples carry concrete slugs of live roles, computed from the roster.

One table: roster by generated surface. Per cell, every slug printed inside a command or an
example is on the live roster, there is no ``<tech>`` placeholder, and no sentence states how a
developer's slug is spelled.
"""

import re
from pathlib import Path

import pytest

from squads import __version__
from squads._interactions._skills import item_skill_name
from squads._roles._catalog import PREDEFINED
from squads._services import _service as service
from squads._workflow import ROSTER_SKILL

pytestmark = pytest.mark.anyio

PREDEFINED_SLUGS = frozenset(r.slug for r in PREDEFINED)

#: A sentence stating a slug pattern, matched on whitespace-collapsed text so a wrapped
#: sentence cannot hide.
_SLUG_PATTERN_SENTENCE = re.compile(
    r"(slug is `?<[a-z]+>-[a-z]+`?|`<[a-z-]+>-dev`|<tech>|slug (?:ends|ending) (?:in|with))", re.I
)
#: The sentence a previous release generated: the pattern above must hit it.
_KNOWN_POSITIVE = "(a developer's slug is `<tech>-dev`, e.g. `dotnet-dev`)"

#: Slugs printed as the value of ``--assignee``/``--author``.
_COMMAND_SLUG = re.compile(r"(?:--assignee|--author) ([a-z0-9][a-z0-9-]*)")
#: The slugs a generated "delegate" sentence gives as examples of a ``subagent_type``.
_DELEGATE_SENTENCE = re.compile(r"slug below — e\.g\. (.*?)\), and hand it")

_ROLE_FILE = (
    f"# squads:override-base:{__version__}\n"
    'full_name = "Bea Builder"\n'
    'title = "builder"\n'
    'description = "Builds things."\n'
    'mission = "Build things."\n'
)


async def _declared(svc, root: Path) -> None:
    path = root / "squads" / ".overrides" / "roles" / "builder.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_ROLE_FILE + 'capabilities = ["dev"]\n', encoding="utf-8")
    await svc.activate_role("builder")


async def _suffixed(svc, root: Path) -> None:
    path = root / "squads" / ".overrides" / "roles" / "legacy-dev.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_ROLE_FILE, encoding="utf-8")
    await svc.activate_role("legacy-dev")


async def _all_with_templated(svc, root: Path) -> None:
    await svc.add_dev("rust")


async def _architect_with_declared(svc, root: Path) -> None:
    await svc.activate_role("architect")
    await _declared(svc, root)


async def _renamed_squad(svc, root: Path) -> None:
    """Live roles that share no slug with the bundled catalog; the bundled default retired."""
    await _declared(svc, root)
    path = root / "squads" / ".overrides" / "roles" / "lead.toml"
    path.write_text(_ROLE_FILE.replace("Bea Builder", "Lee Lead"), encoding="utf-8")
    await svc.activate_role("lead")
    manager = await svc.roster_item("role", "manager")
    assert manager is not None
    await svc.set_status(manager.id, "Archived")


async def _nothing(svc, root: Path) -> None:
    return None


_ROSTERS = {
    "all-with-templated-developer": ("all", _all_with_templated),
    "minimal": ("minimal", _nothing),
    "architect-with-declared-developer": ("minimal", _architect_with_declared),
    "default-with-suffixed-role": ("minimal", _suffixed),
    "no-slug-shared-with-the-catalog": ("minimal", _renamed_squad),
}


def _squad_texts(root: Path) -> dict[str, str]:
    texts = {"CLAUDE.md": (root / "CLAUDE.md").read_text(encoding="utf-8")}
    agents_md = root / "AGENTS.md"
    if agents_md.exists():
        texts["AGENTS.md"] = agents_md.read_text(encoding="utf-8")
    for pointer in sorted((root / ".claude" / "agents").glob("*.md")):
        texts[f".claude/agents/{pointer.name}"] = pointer.read_text(encoding="utf-8")
    return texts


@pytest.mark.parametrize("roster", list(_ROSTERS))
async def test_generated_text_names_only_live_roster_slugs(
    roster: str, tmp_path, monkeypatch
) -> None:
    roles_spec, populate = _ROSTERS[roster]
    monkeypatch.chdir(tmp_path)
    await service.init(root=tmp_path, roles_spec=roles_spec, backend=["claude_code", "agents_md"])
    svc = service.open_service()
    await populate(svc, tmp_path)
    await svc.seed_bundled_skills()
    await svc.refresh_managed()

    svc = service.open_service()
    live = {r.slug for r in await svc.roster()}
    operators = {o.slug for o in await svc.operators()}
    texts = _squad_texts(tmp_path)
    for skill in await svc.list_items(item_type=ROSTER_SKILL):
        texts[f"skill {skill.slug}"] = await svc.read_body(skill.id)
    assert item_skill_name("task") in {s.slug for s in await svc.list_items(item_type=ROSTER_SKILL)}

    for surface, text in texts.items():
        collapsed = " ".join(text.split())
        assert "<tech>" not in collapsed, surface
        assert not _SLUG_PATTERN_SENTENCE.search(collapsed), surface
        delegate = _DELEGATE_SENTENCE.search(collapsed)
        named = re.findall(r"`([a-z0-9-]+)`", delegate.group(1)) if delegate else []
        commanded = [
            slug
            for line in text.splitlines()
            if "sq " in line and not line.lstrip().startswith("#")
            for slug in _COMMAND_SLUG.findall(line)
        ]
        for slug in PREDEFINED_SLUGS - live:
            assert not re.search(
                rf"(?<![\w-])(--author |--assignee |--as |@){slug}(?![\w-])", text
            ), (
                surface,
                slug,
            )
        for slug in [*commanded, *named]:
            assert slug in live | operators or slug.startswith("op-"), (surface, slug)


def test_the_slug_pattern_check_matches_the_sentence_a_previous_release_generated() -> None:
    assert _SLUG_PATTERN_SENTENCE.search(_KNOWN_POSITIVE)
    assert _COMMAND_SLUG.findall("update --assignee python-dev") == ["python-dev"]
    assert _DELEGATE_SENTENCE.search("slug below — e.g. `a`, `b`), and hand it")
