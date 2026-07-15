"""Byte-identical goldens for the three rendered surfaces the generic spec-engine rewire
touches: the raw ``sq workflow`` cheatsheet markdown, the managed CLAUDE.md workflow-section
body, and the managed AGENTS.md workflow-section body — each pinned against the SAME fixed
roster/operator list so a change to any of the three (or a roster-derived template) is caught
immediately.

Closes a reviewer forward-flag from an earlier chunk: the CLAUDE.md section golden and the
AGENTS.md section golden are BOTH pinned here — not just the AGENTS.md one — so the AGENTS.md
render doesn't accidentally end up the only one with an exact-byte pin.

ALL inputs are frozen: the roster includes one python-dev so ``has_dev``-driven templates are
exercised consistently with every other pinned-roster golden in this suite; ``squad_dir`` is
the literal string ``"squads"`` so path references are stable across machines.
"""

import os
from pathlib import Path

from squads._backends._base import OperatorView, RoleView
from squads._rendering._engine import render
from squads._workflow import bundled_spec

GOLDENS_DIR = Path(__file__).parents[1] / "goldens"
_UPDATE = os.getenv("UPDATE_GOLDENS") == "1"

#: Same fixed roster (all 8 bundled roles + one python-dev) the pre-existing skill-body and
#: rendered-output goldens were pinned against — reused read-only.
_PINNED_ROSTER: list[RoleView] = [
    RoleView(slug="manager", full_name="Catherine Manager", title="Manager", is_default=True),
    RoleView(slug="architect", full_name="Robert Architect", title="Architect", is_default=False),
    RoleView(slug="tech-lead", full_name="Olivia Lead", title="Tech lead", is_default=False),
    RoleView(slug="reviewer", full_name="Paul Reviewer", title="Code reviewer", is_default=False),
    RoleView(slug="qa", full_name="Mara Tester", title="QA engineer", is_default=False),
    RoleView(slug="devops", full_name="Hugo Ops", title="DevOps engineer", is_default=False),
    RoleView(
        slug="product-owner", full_name="Nina Product", title="Product owner", is_default=False
    ),
    RoleView(
        slug="tech-writer", full_name="Theo Writer", title="Technical writer", is_default=False
    ),
    RoleView(
        slug="python-dev", full_name="Elias Python", title="Python developer", is_default=False
    ),
]
_PINNED_OPERATORS: list[OperatorView] = [OperatorView(slug="op-pierre", full_name="Pierre Chat")]
_DEFAULT_ROLE = next(r for r in _PINNED_ROSTER if r.is_default)


def _check_golden(name: str, actual: str) -> None:
    path = GOLDENS_DIR / f"{name}.txt"
    if _UPDATE:
        GOLDENS_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        return
    assert path.exists(), f"golden file missing: {path}"
    expected = path.read_text(encoding="utf-8")
    assert actual == expected, f"golden mismatch for {name!r}"


def test_the_workflow_cheatsheet_matches_its_pinned_golden() -> None:
    actual = render("workflow.md.j2", spec=bundled_spec())
    assert "\x1b[" not in actual
    _check_golden("workflow_cheatsheet", actual)


def test_the_claude_md_managed_section_body_matches_its_pinned_golden() -> None:
    actual = render(
        "claude/claude_section.md.j2",
        squad_dir="squads",
        roles=[
            {"full_name": r.full_name, "title": r.title, "slug": r.slug} for r in _PINNED_ROSTER
        ],
        operators=[{"full_name": o.full_name, "slug": o.slug} for o in _PINNED_OPERATORS],
        default_role_full_name=_DEFAULT_ROLE.full_name,
        default_role_slug=_DEFAULT_ROLE.slug,
        spec=bundled_spec(),
    )
    assert "Elias Python" in actual  # sanity: the pinned dev is in the roster
    assert "\x1b[" not in actual
    _check_golden("claude_md_section", actual)


def test_the_agents_md_managed_section_body_matches_its_pinned_golden() -> None:
    actual = render(
        "agents_md/agents_section.md.j2",
        squad_dir="squads",
        roles=[
            {
                "full_name": r.full_name,
                "title": r.title,
                "slug": r.slug,
                "mission": "",
                "responsibilities": [],
                "memory_lines": [],
            }
            for r in _PINNED_ROSTER
        ],
        operators=[{"full_name": o.full_name, "slug": o.slug} for o in _PINNED_OPERATORS],
        spec=bundled_spec(),
    )
    assert "Elias Python" in actual
    assert "\x1b[" not in actual
    _check_golden("agents_md_section", actual)
