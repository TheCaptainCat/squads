"""One formatter prints ``Name (pronouns)`` with the parenthesis dimmed: bare when the setting is
off or there are no pronouns, with no empty parentheses and no trailing space, and with the
pronouns taken as content so brackets print as written."""

import pytest

from squads._pronouns import named

# (id, pronouns, enabled, plain text, dim span text)
CASES: list[tuple[str, str | None, bool, str, str | None]] = [
    ("set-and-on", "they/them", True, "Alex Rivera (they/them)", "(they/them)"),
    ("set-and-off", "they/them", False, "Alex Rivera", None),
    ("unset", None, True, "Alex Rivera", None),
    ("unset-and-off", None, False, "Alex Rivera", None),
    ("brackets", "[x]", True, "Alex Rivera ([x])", "([x])"),
    ("markup-looking", "[bold]a[/bold]", True, "Alex Rivera ([bold]a[/bold])", "([bold]a[/bold])"),
]


@pytest.mark.parametrize(
    ("case", "pronouns", "enabled", "plain", "dim"), CASES, ids=[c[0] for c in CASES]
)
def test_the_name_prints_with_a_dimmed_parenthesis_only_when_enabled_and_set(
    case: str, pronouns: str | None, enabled: bool, plain: str, dim: str | None
) -> None:
    text = named("Alex Rivera", pronouns, enabled=enabled)

    assert text.plain == plain
    dimmed = [text.plain[s.start : s.end] for s in text.spans if s.style == "dim"]
    assert dimmed == ([dim] if dim else [])


def test_the_markup_form_round_trips_the_brackets() -> None:
    from rich.text import Text

    text = named("Alex Rivera", "[x]", enabled=True, style="bold")

    assert Text.from_markup(text.markup).plain == "Alex Rivera ([x])"
