"""The commands a message names to place, disable or clear a view tag, composed in one place so
no message can spell out a command form that does not exist."""

from typing import Literal

from squads._workflow import ROSTER_ROLE, ROSTER_SKILL


def view_placement_invocation(
    item_type: str, addr: int | str, verb: Literal["add", "disable"], name: str
) -> str:
    """The real ``sq … view add|disable <name>`` invocation for a document of *item_type*
    addressed by *addr* (slug for a role/skill, item number otherwise) — there is no bare
    ``sq view add``/``sq view disable``. The one place a message composes this, so it can
    never spell out a command form that does not exist."""
    if item_type == ROSTER_ROLE:
        return f"sq role {addr} view {verb} {name}"
    if item_type == ROSTER_SKILL:
        return f"sq skill {addr} view {verb} {name}"
    return f"sq {item_type} {addr} view {verb} {name}"


def clear_roster_body_cmd(item_type: str, slug: str) -> str:
    """The real, filled-in command that clears a role's or skill's body text, once its view is
    dropped from ``[selected]`` (what lifts the roster write refusal). The one derivation both
    check remedies that need this compose through, so they never disagree."""
    return f'sq {item_type} {slug} body -m "" --force'
