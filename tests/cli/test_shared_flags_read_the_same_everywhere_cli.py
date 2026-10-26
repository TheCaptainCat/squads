"""A flag that several commands take is described in the same words on every one of them:
each flag below reads one of its wordings wherever it appears, and appears on more than one
command.
"""

import pytest

from _help_tree import command_nodes, documented_params

pytestmark = pytest.mark.anyio

#: Flag -> every wording it may read, one per meaning it carries.
WORDINGS: dict[str, set[str]] = {
    "--file": {
        "Read the text from a file instead of `-m`; `-` reads stdin.",
        "Read the memory's body from a file; `-` reads stdin.",
        "A role definition in the `.overrides/roles/<slug>.toml` grammar; flags win over it.",
        "A definition delta in the `.overrides/roles/<slug>.toml` grammar, merged field by field.",
    },
    "--message": {
        "A paragraph of text; repeat for several.",
        "One point of the comment; repeat for several.",
    },
    "--append": {"Append to the body instead of replacing it."},
    "--raw": {"Print plain text instead of rendered markdown."},
    "--desc": {"Short summary shown in listings; not the body."},
    "--author": {"Author: a registered role slug or `op-<slug>`."},
    "--as": {
        "Author: a role slug or `op-<slug>` (required).",
        "The comment's author (required).",
        "Slug to attribute events with no `as` of their own and none to inherit; "
        "without it such an event is refused.",
    },
    "--yes": {"Skip the confirmation prompt."},
    "--tech": {"Technology, such as `python` or `react`."},
    "--depth": {"How many levels below the root to show; 0 shows only the root."},
    "--assignee": {
        "Role or operator slug to assign.",
        "Show only items assigned to this role or operator slug.",
    },
    "--label": {"Label to add (repeatable).", "Show only items carrying this label."},
    "--type": {"Show only items of this type (see `sq workflow types`)."},
    "--all": {"Include closed items.", "Show both directions."},
    "--status": {
        "Show only items in this status, closed or not (see `sq workflow statuses`).",
        "Status to move to (see `sq workflow lifecycles`).",
        "Status to start in instead of the first one.",
    },
    "--parent": {
        "Parent item ID or number.",
        "Show only the direct children of this item ID or number.",
        "New parent item ID or number.",
    },
    "--pronouns": {
        "Pronouns, such as they/them; one line, up to 40 characters.",
        "The role's pronouns; a blank value clears them.",
        "The operator's pronouns; a blank value clears them.",
    },
    "--force": {
        "Make a transition the lifecycle does not allow.",
        "Make a transition the lifecycle does not allow; a change that would leave "
        "the config invalid is still refused.",
        "Replace a body already written; what it held is lost.",
        "Overwrite an override that exists.",
        "Overwrite existing .squads.toml.",
        "Cut the refs other items carry to this one instead of refusing.",
    },
}

#: Flags whose wording is declared once, so they read the same on every command taking them.
SINGLE_MEANING = {"--append", "--raw", "--desc", "--author", "--yes", "--tech", "--depth"}


async def _occurrences(project) -> dict[str, list[tuple[str, str]]]:
    found: dict[str, list[tuple[str, str]]] = {flag: [] for flag in WORDINGS}
    for node in command_nodes():
        for param in documented_params(node):
            for opt in getattr(param, "opts", []):
                if opt in found:
                    found[opt].append((node.label, (param.help or "").strip()))
    return found


async def test_every_shared_flag_reads_one_of_its_wordings_wherever_it_appears(project) -> None:
    found = await _occurrences(project)
    off = [
        f"{label} {flag}: {text!r}"
        for flag, sites in found.items()
        for label, text in sites
        if text not in WORDINGS[flag]
    ]
    assert not off, "\n".join(off[:30])


async def test_a_single_meaning_flag_reads_identically_on_every_command(project) -> None:
    found = await _occurrences(project)
    for flag in SINGLE_MEANING:
        texts = {text for _, text in found[flag]}
        assert len(texts) == 1, f"{flag} reads {sorted(texts)}"
        assert len(found[flag]) > 1, f"{flag} appears on one command only"


async def test_the_message_flag_reads_the_same_on_the_body_commands(project) -> None:
    found = await _occurrences(project)
    by_command = dict(found["--message"])
    assert by_command["sq task body"] == "A paragraph of text; repeat for several."
    assert by_command["sq board post"] == "A paragraph of text; repeat for several."
    assert by_command["sq task comment"] == "One point of the comment; repeat for several."
