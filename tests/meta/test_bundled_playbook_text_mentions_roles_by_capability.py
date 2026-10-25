"""The bundled playbook hands off to roles by capability (`@*<name>`), never by a bundled role's
slug or the `@<developer>` placeholder, so its hand-offs follow whoever holds the capability."""

import re

from squads._interactions import get_playbook_spec
from squads._roles._catalog import PREDEFINED

_BUNDLED_SLUG_MENTION = re.compile(
    r"(?<![\w-])@(" + "|".join(re.escape(r.slug) for r in PREDEFINED) + r")(?![\w-])"
)


def _playbook_text() -> list[str]:
    return [
        line
        for entry in get_playbook_spec().types.values()
        for line in (
            *entry.commands,
            *(text for g in entry.roles for text in (*g.enter, *g.do, *g.handoff, *g.watch)),
        )
    ]


def test_no_bundled_line_mentions_a_bundled_role_by_slug() -> None:
    assert [ln for ln in _playbook_text() if _BUNDLED_SLUG_MENTION.search(ln)] == []


def test_no_bundled_line_mentions_the_developer_placeholder() -> None:
    assert [ln for ln in _playbook_text() if "@<developer>" in ln] == []
