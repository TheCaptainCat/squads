"""`@*<name>` in playbook text renders as the `@<slug>` of every live role holding `<name>`, in
roster order and `/`-joined, or as `*<name>` — a mention of nobody — when none does."""

import pytest

from squads._discussion import extract_mentions
from squads._interactions._playbook import get_playbook_spec
from squads._interactions._role_guidance import live_roster_text
from squads._roles._projection import RoleView


def _role(slug: str, *capabilities: str) -> RoleView:
    return RoleView(
        slug=slug, full_name=slug, title=slug, is_default=False, capabilities=capabilities
    )


_NONE = [_role("manager"), _role("tech-lead", "plan")]
_ONE = [_role("manager"), _role("reviewer", "review")]
_TWO = [_role("rust-dev", "review"), _role("manager"), _role("go-dev", "review")]
_BOTH = [_role("tech-lead", "plan", "review")]
_LITERAL = [_role("qa", "verify"), _role("reviewer", "review")]

_ROWS = [
    pytest.param(_NONE, "ask `@*review` now", "ask `*review` now", set(), id="no-live-holder"),
    pytest.param(_ONE, "ask `@*review` now", "ask `@reviewer` now", {"reviewer"}, id="one-holder"),
    pytest.param(
        _TWO,
        "ask `@*review` now",
        "ask `@rust-dev/@go-dev` now",
        {"rust-dev", "go-dev"},
        id="two-holders-in-roster-order",
    ),
    pytest.param(
        _BOTH,
        "`@*plan` then `@*review`",
        "`@tech-lead` then `@tech-lead`",
        {"tech-lead"},
        id="one-role-holding-two-named-capabilities-appears-per-token",
    ),
    pytest.param(
        _LITERAL,
        "`@qa` then `@*review`",
        "`@qa` then `@reviewer`",
        {"qa", "reviewer"},
        id="a-literal-slug-beside-a-token-is-unchanged",
    ),
]


@pytest.mark.parametrize(("roster", "line", "expected", "mentioned"), _ROWS)
def test_a_token_renders_as_the_live_holders(roster, line: str, expected: str, mentioned) -> None:
    (rendered,) = live_roster_text([line], roster, get_playbook_spec())
    assert rendered == expected
    assert extract_mentions(rendered) == mentioned
