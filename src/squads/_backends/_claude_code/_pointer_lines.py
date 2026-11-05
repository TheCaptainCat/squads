"""The ``!`` lines and grants of a Claude Code skill pointer.

Each line runs one ``sq`` command and falls back to an ``echo`` naming the command to run by
hand, so the host always gets a line that exits 0.
"""

import re
from dataclasses import dataclass

from squads._errors import SquadsError
from squads._models import is_valid_slug

#: The characters an ``echo`` text may hold: bash and zsh read none of them specially inside
#: single quotes, and none can close the quote.
_ECHO_SAFE = re.compile(r"[A-Za-z0-9 ;:.,-]+")


@dataclass(frozen=True)
class PointerLine:
    """One command a pointer runs and the text it falls back to naming."""

    command: str
    failure: str

    def render(self) -> str:
        """The ``!`` line: the command, then ``||`` and an ``echo`` of the failure text."""
        if _ECHO_SAFE.fullmatch(self.failure) is None:
            raise SquadsError(f"cannot render a pointer line: unsafe echo text {self.failure!r}")
        return f"!`{self.command} || echo '{self.failure}'`"

    @property
    def grant(self) -> str:
        """The ``allowed-tools`` entry that lets the host run the command."""
        return f"Bash({self.command})"


def _require_slug(slug: str) -> None:
    """Refuse a *slug* outside the slug grammar, so no command or echo text holds a character a
    shell reads specially."""
    if not is_valid_slug(slug):
        raise SquadsError(
            f"cannot render a skill pointer for {slug!r}: a slug is lowercase letters, "
            "digits and hyphens"
        )


def skill_lines(slug: str) -> list[PointerLine]:
    """The one line a skill's pointer renders."""
    _require_slug(slug)
    return [
        PointerLine(
            f"sq skill {slug} show --raw --no-header",
            f"squads could not render the {slug} skill; run: sq skill {slug} show",
        )
    ]


def role_skill_lines(slug: str) -> list[PointerLine]:
    """The three lines a role skill's pointer renders: the role, its memory index, the board."""
    _require_slug(slug)
    return [
        PointerLine(
            f"sq role {slug} show --raw --no-header",
            f"squads could not render the {slug} role; run: sq role {slug} show",
        ),
        PointerLine(
            f"sq memory {slug} list --raw",
            f"squads could not read the {slug} memory; run: sq memory {slug} list",
        ),
        PointerLine(
            "sq board list --raw",
            "squads could not read the board; run: sq board list",
        ),
    ]
