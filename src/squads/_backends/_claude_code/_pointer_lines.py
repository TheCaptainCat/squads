"""The ``!`` lines and grants of a Claude Code skill pointer.

Each line runs one ``sq`` command and falls back to an ``echo`` naming the command to run by
hand, so the host always gets a line that exits 0.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from squads._backends._claude_code._frontmatter import oneline
from squads._errors import SquadsError
from squads._models import is_valid_slug
from squads._rendering import render

#: The characters an ``echo`` text may hold: bash and zsh read none of them specially inside
#: single quotes, and none can close the quote.
_ECHO_SAFE = re.compile(r"[A-Za-z0-9 ;:.,-]+")


@dataclass(frozen=True)
class PointerLine:
    """One command a pointer runs and the text it falls back to naming."""

    command: str
    failure: str
    heading: str | None = None

    def render(self) -> str:
        """The ``!`` line: the command, then ``||`` and an ``echo`` of the failure text; under a
        *heading*, a blank line and the heading line come first."""
        if _ECHO_SAFE.fullmatch(self.failure) is None:
            raise SquadsError(f"cannot render a pointer line: unsafe echo text {self.failure!r}")
        line = f"!`{self.command} || echo '{self.failure}'`"
        return line if self.heading is None else f"\n## {self.heading}\n\n{line}"

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
    """The three lines a role skill's pointer renders: the role, then its memory index and the
    board, each of those two under its heading."""
    _require_slug(slug)
    return [
        PointerLine(
            f"sq role {slug} show --raw --no-header",
            f"squads could not render the {slug} role; run: sq role {slug} show",
        ),
        PointerLine(
            f"sq memory {slug} list --raw",
            f"squads could not read the {slug} memory; run: sq memory {slug} list",
            "Memory",
        ),
        PointerLine(
            "sq board list --raw",
            "squads could not read the board; run: sq board list",
            "Board",
        ),
    ]


def render_skill_pointer(squad_dir: Path, slug: str, description: str, *, invocable: bool) -> str:
    """The text of the pointer of skill *slug* as the current release writes it."""
    lines = skill_lines(slug)
    return render(
        "claude/pointer_skill.md.j2",
        from_squad=squad_dir,
        slug=slug,
        description=oneline(description),
        invocable=invocable,
        grants=[line.grant for line in lines],
        lines=[line.render() for line in lines],
    )
