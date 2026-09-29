"""The generated sq-<type> skill body's ``*dev`` role-guide sentinel: present only when a
``*-dev`` role is in the roster (rendered as "## For developers"), absent — not crashing —
otherwise, and byte-identical (modulo the golden's own trailing newline — see below) to a
pinned golden on the pinned, has-dev roster.

Pure-function tests: render() with no active squad dir uses the bundled-only template
loader, so no project/svc fixture is needed (CLAUDE.md invariant: the has_dev gate is
roster-dependent, so every test here pins its own roster explicitly rather than trusting
whatever `sq init` happens to default to — see the "pin roster when diffing generated
skills" hazard).
"""

from datetime import UTC, datetime
from pathlib import Path

from squads._backends._base import RoleView
from squads._interactions import PLAYBOOK, get_playbook_spec, is_dev_slug
from squads._models._item import Item
from squads._rendering._engine import render
from squads._views import PlaybookSource
from squads._workflow import bundled_spec
from squads._workflow._models import ROSTER_SKILL

GOLDENS_DIR = Path(__file__).parents[1] / "goldens"

#: The four bundled types whose playbook declares a ``*dev`` role guide.
_DEV_GUIDE_TYPES: frozenset[str] = frozenset({"task", "bug", "review", "contract"})

#: Same fixed roster the existing skill-body goldens were pinned against (all 8 bundled
#: roles + one python-dev) — reused read-only so this test's byte-identity check targets
#: the same reviewed reference render, not a second copy of it.
_ROSTER_WITH_DEV: list[RoleView] = [
    RoleView(slug="manager", full_name="Catherine Manager", title="manager", is_default=True),
    RoleView(slug="architect", full_name="Robert Architect", title="architect", is_default=False),
    RoleView(slug="tech-lead", full_name="Olivia Lead", title="tech lead", is_default=False),
    RoleView(slug="reviewer", full_name="Paul Reviewer", title="code reviewer", is_default=False),
    RoleView(slug="qa", full_name="Mara Tester", title="QA engineer", is_default=False),
    RoleView(slug="devops", full_name="Hugo Ops", title="DevOps engineer", is_default=False),
    RoleView(
        slug="product-owner", full_name="Nina Product", title="product owner", is_default=False
    ),
    RoleView(
        slug="tech-writer", full_name="Theo Writer", title="technical writer", is_default=False
    ),
    RoleView(
        slug="python-dev", full_name="Elias Python", title="Python developer", is_default=False
    ),
]

_ROSTER_NO_DEV: list[RoleView] = [r for r in _ROSTER_WITH_DEV if not is_dev_slug(r.slug)]


def _probe_skill_item(item_type: str) -> Item:
    now = datetime.now(UTC)
    slug = f"sq-{item_type}"
    return Item(
        sequence_id=0,
        type=ROSTER_SKILL,
        title=slug,
        slug=slug,
        status="Active",
        path=f"agents/skills/{slug}.md",
        created_at=now,
        updated_at=now,
    )


def _render_item_skill(item_type: str, roster: list[RoleView]) -> str:
    """Mirror the real read-time expansion (``resolve_source``/``render_source_view`` over the
    ``item_skill`` view) without going through it, so this test is an independent reproduction
    rather than a call to the code under test."""
    spec = bundled_spec()
    playbook = get_playbook_spec()
    source = PlaybookSource(
        item_type=item_type, lane=playbook.types[item_type], roster=roster, playbook=playbook
    )
    return render(
        "views/item_skill.md.j2",
        source=source,
        item=_probe_skill_item(item_type),
        spec=spec,
        squad_dir=None,
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
    """One golden per bundled type, reusing the existing reviewed reference renders.

    The golden files were captured with a single trailing newline (the plain file
    convention); the live mechanism's own template wraps its content in a ``trim`` filter so a
    resolved definition splices cleanly into a placement tag's exact span with no stray
    newline either side — so the comparison strips the golden's own trailing newline rather
    than the other way around.
    """
    for item_type in PLAYBOOK:
        golden_path = GOLDENS_DIR / f"skill_body_sq-{item_type}.txt"
        if not golden_path.exists():
            continue  # not every bundled type ships a pre-existing golden (e.g. epic/feature)
        actual = _render_item_skill(item_type, _ROSTER_WITH_DEV)
        expected = golden_path.read_text(encoding="utf-8").strip("\n")
        assert actual == expected, f"{item_type}: rendered skill body drifted from the golden"
