"""The memory-entry model — deliberately NOT the ``Item`` model.

A memory is a small, agent-authored fact: light frontmatter (a one-line summary,
``created_at``, optional tags) over a freeform, agent-owned body. There is no schema-version,
status/workflow machinery, sub-entities, or refs — memory is a lighter tier than an item,
and no global-counter id is ever allocated for one.

Content files are marker-free: a memory's body carries no ``<!-- sq:... -->`` markers, since
nothing inside it is regenerated (only the summary/created_at/tags frontmatter feeds the
generated ``.index.jsonl`` roll-up).
"""

from dataclasses import dataclass, field
from typing import Any, cast


@dataclass(frozen=True)
class MemoryEntry:
    """One memory: identified by its stable *slug* (the filename stem), not a counter id."""

    slug: str
    summary: str
    created_at: str  # ISO-8601 (via squads._clock.iso), the frontmatter's created_at
    body: str
    tags: tuple[str, ...] = field(default_factory=tuple)

    def to_frontmatter_dict(self) -> dict[str, Any]:
        """The light frontmatter block written over the freeform body."""
        data: dict[str, Any] = {"summary": self.summary, "created_at": self.created_at}
        if self.tags:
            data["tags"] = list(self.tags)
        return data

    @classmethod
    def from_frontmatter(cls, slug: str, frontmatter: dict[str, Any], body: str) -> MemoryEntry:
        """Rebuild a ``MemoryEntry`` from a parsed frontmatter dict + body (round-trips
        :meth:`to_frontmatter_dict`)."""
        raw_tags = cast("list[Any]", frontmatter.get("tags") or [])
        return cls(
            slug=slug,
            summary=str(frontmatter.get("summary", "")),
            created_at=str(frontmatter.get("created_at", "")),
            body=body,
            tags=tuple(str(t) for t in raw_tags),
        )
