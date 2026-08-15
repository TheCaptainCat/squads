"""A squad with no live designated role omits the default-role line from the generated
``CLAUDE.md`` region — but the surrounding ``{% if default_role_full_name %}`` block tags were
not whitespace-trimmed, so the omission left a double blank line where the line and the
following paragraph used to be. Present-default rendering (the pinned golden in
``test_managed_section_and_cheatsheet_goldens.py``) must stay byte-identical.
"""

from squads._rendering._engine import render
from squads._workflow import bundled_spec

_ROLES = [{"full_name": "A", "title": "T", "slug": "a"}]


def _render(default_role_full_name: str | None) -> str:
    return render(
        "claude/claude_section.md.j2",
        squad_dir="squads",
        roles=_ROLES,
        operators=[],
        default_role_full_name=default_role_full_name,
        default_role_slug="a" if default_role_full_name else None,
        spec=bundled_spec(),
    )


def test_no_default_role_leaves_a_single_blank_line_not_a_double_one() -> None:
    rendered = _render(None)
    assert "to yourself by full name.\n\nA human introducing" in rendered
    assert "to yourself by full name.\n\n\n" not in rendered


def test_a_designated_default_role_still_renders_the_line_with_normal_spacing() -> None:
    rendered = _render("Catherine Manager")
    assert (
        "to yourself by full name.\n\n"
        "If no agent is named, default to **Catherine Manager** (`a`),\n"
        "who triages the request and routes it to the right specialist.\n\n"
        "A human introducing" in rendered
    )
