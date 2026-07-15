"""The board-notice model — deliberately NOT the ``Item`` model.

A notice is a short, prescriptive team broadcast: light frontmatter (author, posted-at, an
optional ``until`` expiry) over a freeform, author-owned body — the notice text itself. There
is no schema-version, status/workflow machinery, sub-entities, or refs, and no global-counter
id is ever allocated for one; it is identified by a stable short-hash id derived from its
content (see :mod:`squads._board._store`).

Content files are marker-free: nothing inside a notice body is regenerated (only the
frontmatter feeds the generated ``.index.jsonl`` roll-up), so it carries no ``<!-- sq:... -->``
markers.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BoardNotice:
    """One notice: identified by its stable short-hash *id* (the filename stem), not a
    counter id."""

    id: str
    author: str
    posted_at: str  # ISO-8601 (via squads._clock.iso), the frontmatter's posted_at
    body: str
    until: str | None = None  # ISO-8601 expiry (via squads._clock.iso), or None if it never expires

    def to_frontmatter_dict(self) -> dict[str, Any]:
        """The light frontmatter block written over the freeform body.

        Omits ``id`` — it is fully derivable from the filename stem (see
        :func:`from_frontmatter`, called with ``path.stem``) and nothing reads it back from
        the frontmatter, so storing it would be redundant (mirrors the memory store, which
        likewise omits its slug from frontmatter for the same reason).
        """
        data: dict[str, Any] = {"author": self.author, "posted_at": self.posted_at}
        if self.until:
            data["until"] = self.until
        return data

    @classmethod
    def from_frontmatter(
        cls, notice_id: str, frontmatter: dict[str, Any], body: str
    ) -> BoardNotice:
        """Rebuild a ``BoardNotice`` from a parsed frontmatter dict + body (round-trips
        :meth:`to_frontmatter_dict`)."""
        until = frontmatter.get("until")
        return cls(
            id=notice_id,
            author=str(frontmatter.get("author", "")),
            posted_at=str(frontmatter.get("posted_at", "")),
            body=body,
            until=str(until) if until else None,
        )
