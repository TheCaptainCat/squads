"""Bundled guidance teaches ``comment <hash> show|edit|remove``, tells a reader to read again when
a hash stops resolving, and no longer calls the discussion append-only."""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

GOLDENS = Path(__file__).parents[1] / "goldens"
VERBS = "comment <hash> show|edit|remove"
PERMISSION = re.compile(r"author[^.\n]*permission|permission[^.\n]*author", re.I)


@pytest.fixture
async def squad(project, svc, invoke):
    await svc.add_operator("Pierre Chat")
    await svc.seed_bundled_skills()


SURFACES = {
    "squads skill": ["skill", "squads", "show"],
    "workflow cheatsheet": ["workflow"],
    "role definition": ["role", "manager", "show"],
    "operator": ["operator", "op-pierre", "show"],
}


@pytest.mark.parametrize("surface", list(SURFACES))
async def test_each_rendered_surface_teaches_the_address_verbs(squad, invoke, surface) -> None:
    r = await invoke(SURFACES[surface])

    out = " ".join(r.output.split())
    assert r.exit_code == 0, r.output
    assert ("comment <hash>" in out) and ("show|edit|remove" in out or "edit|remove" in out), out
    assert not PERMISSION.search(out)


async def test_the_squads_skill_says_a_quoted_hash_pins_the_text_and_to_read_again(
    squad, invoke
) -> None:
    out = " ".join((await invoke(["skill", "squads", "show"])).output.split())

    assert "A hash quoted in prose pins the text its author read" in out
    assert "read the discussion again" in out


@pytest.mark.parametrize(
    "golden", ["claude_md_section", "agents_md_section", "workflow_cheatsheet"]
)
def test_each_pinned_managed_text_teaches_the_verbs(golden: str) -> None:
    text = " ".join((GOLDENS / f"{golden}.txt").read_text(encoding="utf-8").split())

    assert "comment <hash>" in text and "show|edit|remove" in text
    assert not PERMISSION.search(text)


def test_the_managed_claude_section_no_longer_calls_the_discussion_append_only() -> None:
    text = (GOLDENS / "claude_md_section.txt").read_text(encoding="utf-8")

    assert "append-only" not in text
    assert "only each comment's author can correct" in " ".join(text.split())


@pytest.mark.parametrize(
    "golden",
    ["claude_md_section", "agents_md_section", "workflow_cheatsheet", "skill_body_sq-task"],
)
def test_no_guidance_line_gives_show_an_as_flag(golden: str) -> None:
    text = (GOLDENS / f"{golden}.txt").read_text(encoding="utf-8")

    bad = [ln for ln in text.splitlines() if re.search(r"<hash> show[^`\n]*\s--as", ln)]
    assert not bad
    assert not [ln for ln in text.splitlines() if "show|edit|remove --as" in ln]
