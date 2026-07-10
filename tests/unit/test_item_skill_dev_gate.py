"""The generated sq-<type> skill body's ``*dev`` role-guide sentinel: present only when a
``*-dev`` role is in the roster (rendered as "## For developers"), absent — not crashing —
otherwise, and byte-identical to a pinned golden on the pinned, has-dev roster.

Pure-function tests: render() with no active squad dir uses the bundled-only template
loader, so no project/svc fixture is needed (CLAUDE.md invariant: the has_dev gate is
roster-dependent, so every test here pins its own roster explicitly rather than trusting
whatever `sq init` happens to default to — see the "pin roster when diffing generated
skills" hazard).
"""

from pathlib import Path
from typing import Any

from squads._interactions import DEV, PLAYBOOK, is_dev_slug
from squads._rendering._engine import render
from squads._workflow import bundled_spec
from squads._workflow import linearize_lifecycle as _linearize

GOLDENS_DIR = Path(__file__).parents[1] / "goldens"

#: The three bundled types whose playbook declares a ``*dev`` role guide.
_DEV_GUIDE_TYPES: frozenset[str] = frozenset({"task", "bug", "review"})

#: Same fixed roster the existing skill-body goldens were pinned against (all 8 bundled
#: roles + one python-dev) — reused read-only so this test's byte-identity check targets
#: the same reviewed reference render, not a second copy of it.
_ROSTER_WITH_DEV: dict[str, str] = {
    "manager": "Catherine Manager",
    "architect": "Robert Architect",
    "tech-lead": "Olivia Lead",
    "reviewer": "Paul Reviewer",
    "qa": "Mara Tester",
    "devops": "Hugo Ops",
    "product-owner": "Nina Product",
    "tech-writer": "Theo Writer",
    "python-dev": "Elias Python",
}

_ROSTER_NO_DEV: dict[str, str] = {k: v for k, v in _ROSTER_WITH_DEV.items() if not is_dev_slug(k)}


def _render_item_skill(item_type: str, roster: dict[str, str]) -> str:
    """Mirror ClaudeCodeBackend._write_item_skills's section-building + template call."""
    has_dev = any(is_dev_slug(slug) for slug in roster)
    pb = PLAYBOOK[item_type]
    sections: list[dict[str, Any]] = []
    for guide in pb.roles:
        if guide.slug == DEV:
            if not has_dev:
                continue
            title = "developers"
        elif guide.slug in roster:
            title = f"{roster[guide.slug]} (`{guide.slug}`)"
        else:
            continue
        sections.append(
            {
                "title": title,
                "enter": guide.enter,
                "do": guide.do,
                "handoff": guide.handoff,
                "watch": guide.watch,
            }
        )
    spec = bundled_spec()
    subentity_kind = spec.item_subentity_kind(item_type)
    return render(
        "agents/item_skill.md.j2",
        title=item_type.capitalize(),
        type=item_type,
        overview=pb.overview,
        lifecycle=_linearize(spec.machine_for(item_type)),
        commands=list(pb.commands),
        sections=sections,
        subentity_kind=subentity_kind,
        subentity_plural=spec.subentity_plural(subentity_kind) if subentity_kind else None,
    )


def test_dev_section_renders_for_the_three_types_with_a_dev_guide_when_a_dev_is_in_roster() -> None:
    for item_type in PLAYBOOK:
        body = _render_item_skill(item_type, _ROSTER_WITH_DEV)
        has_section = "## For developers" in body
        assert has_section == (item_type in _DEV_GUIDE_TYPES), (
            f"{item_type}: dev-section presence {has_section} unexpected"
        )


def test_dev_section_is_absent_without_crashing_when_no_dev_is_in_roster() -> None:
    for item_type in _DEV_GUIDE_TYPES:
        body = _render_item_skill(item_type, _ROSTER_NO_DEV)
        assert "## For developers" not in body


def test_rendered_skill_body_is_byte_identical_to_the_pinned_golden_on_the_dev_roster() -> None:
    """One golden per bundled type, reusing the existing reviewed reference renders."""
    for item_type in PLAYBOOK:
        golden_path = GOLDENS_DIR / f"skill_body_sq-{item_type}.txt"
        if not golden_path.exists():
            continue  # not every bundled type ships a pre-existing golden (e.g. epic/feature)
        actual = _render_item_skill(item_type, _ROSTER_WITH_DEV)
        expected = golden_path.read_text(encoding="utf-8")
        assert actual == expected, f"{item_type}: rendered skill body drifted from the golden"
