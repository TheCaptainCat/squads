"""A type's Team workflow line names every live, titled authoring role in the type's
declared order, however many there are; the generated text reads correctly for one, two and
three."""

import pytest

from _helpers import role_of
from squads._interactions import authoring_owners, get_playbook_spec
from squads._interactions._models import ItemPlaybookSpec, PlaybookSpec, RoleGuideSpec
from squads._language import WorkingLanguage
from squads._rendering._engine import render
from squads._workflow import bundled_spec

_BASE = get_playbook_spec()
_ARCHITECT = ("architect", "architect")
_WRITER = ("tech-writer", "technical writer")
_QA = ("qa", "QA engineer")
_ROSTER = [
    {"slug": "architect", "title": "architect", "full_name": "Robert Architect"},
    {"slug": "tech-writer", "title": "technical writer", "full_name": "Theo Writer"},
    {"slug": "qa", "title": "QA engineer", "full_name": "Mara Tester"},
]


def _guide_authors(*slugs: str) -> PlaybookSpec:
    """The bundled playbook with *slugs* as the authors of ``guide``, in that order."""
    entry = _BASE.types["guide"]
    guides = [RoleGuideSpec(slug=slug, authors=True) for slug in slugs]
    return _BASE.model_copy(
        update={
            "types": {
                **_BASE.types,
                "guide": ItemPlaybookSpec(
                    overview=entry.overview,
                    lifecycle=entry.lifecycle,
                    commands=entry.commands,
                    roles=guides,
                ),
            }
        }
    )


# (case, authoring slugs declared, roster, role_titles, expected owners)
OWNERS = {
    "no author": ((), _ROSTER, None, []),
    "one author": (("architect",), _ROSTER, None, [_ARCHITECT]),
    "two authors, in the type's declared order": (
        ("tech-writer", "architect"),
        _ROSTER,
        None,
        [_WRITER, _ARCHITECT],
    ),
    "three authors": (
        ("tech-writer", "qa", "architect"),
        _ROSTER,
        None,
        [_WRITER, _QA, _ARCHITECT],
    ),
    "an author off the roster": (("architect", "tech-writer"), _ROSTER[:1], None, [_ARCHITECT]),
    "an author with no title": (
        ("architect", "ghost"),
        [*_ROSTER, {"slug": "ghost", "full_name": "Ghost"}],
        None,
        [_ARCHITECT],
    ),
}


@pytest.mark.parametrize("case", list(OWNERS))
def test_authoring_owners_lists_every_live_titled_author_in_declared_order(case) -> None:
    slugs, roster, titles, expected = OWNERS[case]

    assert authoring_owners("guide", roster, _guide_authors(*slugs), titles) == expected


def _claude_md(playbook: PlaybookSpec, roles: list[dict[str, str]]) -> str:
    return render(
        "claude/claude_section.md.j2",
        squad_dir="squads",
        working_language=WorkingLanguage("en", "English"),
        roles=roles,
        delegate_examples=[],
        operators=[],
        default_role_full_name="Catherine Manager",
        default_role_slug="manager",
        spec=bundled_spec(),
        playbook=playbook,
    )


# (case, authoring slugs, expected CLAUDE.md line start; None when the line is absent)
CLAUDE_LINES = {
    "one": (("architect",), "- The **architect** authors **guides** (`sq create guide`)"),
    "two": (
        ("architect", "tech-writer"),
        "- The **architect** and the **technical writer** author **guides** (`sq create guide`)",
    ),
    "three": (
        ("tech-writer", "qa", "architect"),
        "- The **technical writer**, the **QA engineer** and the **architect** author **guides**",
    ),
    "none": ((), None),
}


@pytest.mark.parametrize("case", list(CLAUDE_LINES))
def test_the_claude_md_line_reads_for_any_number_of_authors(case) -> None:
    slugs, expected = CLAUDE_LINES[case]

    lines = [
        line
        for line in _claude_md(_guide_authors(*slugs), _ROSTER).splitlines()
        if "**guides**" in line
    ]

    if expected is None:
        assert lines == []
    else:
        assert len(lines) == 1
        assert lines[0].startswith(expected)


def test_the_workflow_cheatsheet_line_names_both_authors_and_both_slugs() -> None:
    rendered = render(
        "workflow.md.j2",
        spec=bundled_spec(),
        roles=[role_of("architect"), role_of("tech-writer")],
        playbook=_guide_authors("architect", "tech-writer"),
    )

    line = next(line for line in rendered.splitlines() if 'sq create guide "…"' in line)
    assert "Architect" in line
    assert "or" in line
    assert "--author architect|tech-writer" in line
