"""Discussion: comments, author resolution, and the @mention inbox."""

from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._models._enums import ItemType
from squads._models._item import Item
from squads._services._base import ServiceCore, reject_markers
from squads._workflow import is_open


def _strip_frontmatter(text: str) -> str:
    """Drop the leading ``---`` YAML block so a search matches prose, not index plumbing."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1 :])
    return text


class CollabMixin(ServiceCore):
    def comment(
        self,
        item_id: str,
        messages: list[str],
        *,
        as_slug: str = "operator",
        story: str | None = None,
        subtask: str | None = None,
        finding: str | None = None,
    ) -> Item:
        if not messages:
            raise SquadsError("a comment needs at least one -m message")
        for msg in messages:
            reject_markers(msg, "comment message")
        tag = self._discussion_tag(story, subtask, finding)
        entry = discussion.format_comment(clock.iso(clock.now()), self.author(as_slug), messages)

        def mutate(text: str, _item: Item) -> str:
            if not sections.has_section(text, tag):
                raise SquadsError(
                    f"no discussion section {tag!r} in {item_id} (was it scaffolded?)"
                )
            return sections.append_to_section(text, tag, entry)

        return self._locked_section_edit(item_id, mutate)

    @staticmethod
    def _discussion_tag(story: str | None, subtask: str | None, finding: str | None) -> str:
        if sum(bool(t) for t in (story, subtask, finding)) > 1:
            raise SquadsError("target only one of --story / --subtask / --finding")
        if story:
            return markers.discussion_tag(markers.story_tag(story))
        if subtask:
            return markers.discussion_tag(markers.subtask_tag(subtask))
        if finding:
            return markers.discussion_tag(markers.finding_tag(finding))
        return markers.DISCUSSION

    def inbox(self, slug: str) -> list[tuple[Item, list[str]]]:
        """Open items whose body/discussion mentions ``@slug``, with the matching lines."""
        slug = slug.lstrip("@").lower()
        out: list[tuple[Item, list[str]]] = []
        for item in self.list_items():
            if not is_open(item.status):
                continue
            path = item_file(self.paths, item)
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            if slug not in discussion.extract_mentions(text):
                continue
            hits = [ln.strip() for ln in text.splitlines() if f"@{slug}" in ln.lower()]
            out.append((item, hits))
        return out

    def search(
        self, text: str, *, item_type: ItemType | None = None
    ) -> list[tuple[Item, list[str]]]:
        """Items whose title, summary, or body/discussion contains ``text`` (case-insensitive)."""
        needle = text.strip().lower()
        if not needle:
            raise SquadsError("search needs a non-empty query")
        out: list[tuple[Item, list[str]]] = []
        for item in self.list_items(item_type=item_type):
            path = item_file(self.paths, item)
            prose = _strip_frontmatter(path.read_text(encoding="utf-8")) if path.exists() else ""
            candidates = [item.title, item.description, *prose.splitlines()]
            hits = [ln.strip() for ln in candidates if ln and needle in ln.lower()]
            if hits:
                out.append((item, hits))
        return out
