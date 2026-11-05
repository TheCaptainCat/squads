"""The multi-line-summary finding for memories: the entries that hold one, and the message
``sq check`` and ``memory add`` both print.
"""

from squads._errors import SquadsError
from squads._memory._model import MemoryEntry
from squads._memory._store import MEMORY_ROOT
from squads._paths import SquadPaths
from squads._sections import split_frontmatter
from squads._util import has_line_break


def multi_line_summary_message(role_slug: str, slug: str) -> str:
    """The warning for one memory, with the commands that file it again under a one-line summary."""
    return (
        f"memory {role_slug}/{slug} has a multi-line summary; file it again with a one-line"
        f" summary: `sq memory {role_slug} forget {slug}`, then `sq memory {role_slug} add"
        f' "<summary>" --file <body> --slug {slug}`'
    )


def multi_line_summary_warnings(paths: SquadPaths) -> list[tuple[str, str]]:
    """One ``(<role>/<slug>, message)`` per memory, in every folder under the memory root, whose
    summary holds a line break. A file that cannot be read is skipped."""
    root = paths.abspath(MEMORY_ROOT)
    found: list[tuple[str, str]] = []
    for path in sorted(root.glob("*/*.md")):
        try:
            frontmatter, body = split_frontmatter(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, SquadsError):  # fmt: skip
            continue
        role_slug = path.parent.name
        entry = MemoryEntry.from_frontmatter(path.stem, frontmatter, body)
        if has_line_break(entry.summary):
            found.append(
                (f"{role_slug}/{entry.slug}", multi_line_summary_message(role_slug, entry.slug))
            )
    return found
