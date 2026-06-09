"""Discussion: comments, author resolution, and the @mention inbox."""

from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._roles._catalog import role_by_slug
from squads._services._base import ServiceCore
from squads._workflow import is_open


class CollabMixin(ServiceCore):
    def comment(
        self,
        item_id: str,
        messages: list[str],
        *,
        as_slug: str = "operator",
        story: str | None = None,
        subtask: str | None = None,
    ) -> Item:
        if not messages:
            raise SquadsError("a comment needs at least one -m message")
        item = self.get(item_id)
        path = item_file(self.paths, item)
        tag = self._discussion_tag(story, subtask)
        text = path.read_text(encoding="utf-8")
        if not sections.has_section(text, tag):
            raise SquadsError(f"no discussion section {tag!r} in {item_id} (was it scaffolded?)")
        entry = discussion.format_comment(clock.iso(clock.now()), self.author(as_slug), messages)
        path.write_text(sections.append_to_section(text, tag, entry), encoding="utf-8")
        self._bump(item_id)
        return item

    @staticmethod
    def _discussion_tag(story: str | None, subtask: str | None) -> str:
        if story and subtask:
            raise SquadsError("use either --story or --subtask, not both")
        if story:
            return markers.discussion_tag(markers.story_tag(story))
        if subtask:
            return markers.discussion_tag(markers.subtask_tag(subtask))
        return markers.DISCUSSION

    def author(self, slug: str) -> str:
        if slug == "operator":
            return "Operator"
        role_item = self._role_item(slug)
        if role_item is not None:
            return role_item.extra.get(X.FULL_NAME, slug)
        try:
            return role_by_slug(slug).full_name
        except SquadsError:
            return slug

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
