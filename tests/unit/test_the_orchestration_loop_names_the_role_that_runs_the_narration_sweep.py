"""Step 5 of the generated orchestration loop names the live role holding the `edit` capability
as the one that runs the process-narration sweep, and keeps neutral wording when none is live."""

import pytest

from squads._language import WorkingLanguage
from squads._rendering._engine import render
from squads._workflow import bundled_spec

_MANAGER = {"full_name": "Catherine Manager", "title": "manager", "slug": "manager"}
_WRITER = {
    "full_name": "Theo Writer",
    "title": "technical writer",
    "slug": "tech-writer",
    "capabilities": ["edit"],
}
_EDITOR = {"full_name": "Eve Editor", "title": "editor", "slug": "editor", "capabilities": ["edit"]}

_ROWS = [
    pytest.param(
        [_MANAGER, _WRITER],
        "committed/accepted, have the technical writer (`tech-writer`) run\n   one final",
        id="one-live-editor",
    ),
    pytest.param(
        [_MANAGER, _WRITER, _EDITOR],
        "have the technical writer (`tech-writer`) / editor (`editor`) run\n   one final",
        id="two-live-editors",
    ),
    pytest.param([_MANAGER], "committed/accepted, run\n   one final", id="no-live-editor"),
]


@pytest.mark.parametrize(("roles", "expected"), _ROWS)
def test_step_five_names_the_live_editor_or_stays_neutral(roles, expected: str) -> None:
    rendered = render(
        "claude/claude_section.md.j2",
        squad_dir="squads",
        working_language=WorkingLanguage("en", "English"),
        roles=roles,
        delegate_examples=[],
        operators=[],
        default_role_full_name=None,
        default_role_slug=None,
        spec=bundled_spec(),
    )
    assert expected in rendered
