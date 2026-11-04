"""How a comment is shown: the fields derived at read time for a comment a tracker wrote (its
composed author, author URL, matching operator and trust) and its tracker references translated
to item IDs."""

import unicodedata
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from squads import _discussion as discussion
from squads._api._dto._items import Comment
from squads._errors import SquadsError
from squads._models._attributes import AttributeKey, map_attribute
from squads._models._item import Item
from squads._models._participants import source_of
from squads._models._source import SourceRecord
from squads._services._fetch import connector_for
from squads._sources._spec import SourceSpec, SourcesSpec

#: The comment attributes a pull stores for the tracker user who wrote the comment.
AUTHOR_ID = "author_id"
AUTHOR_HANDLE = "author_handle"
AUTHOR_NAME = "author_name"


def comment_dtos(comments: Sequence[discussion.Comment]) -> list[Comment]:
    """A discussion's entries, each with its hash shown at the scope's length. A comment a tracker
    wrote carries its source and is untrusted: nothing here declares otherwise."""
    return [
        Comment.model_validate(
            {**entry, **({} if (name := source_of(c.author_slug)) is None else _unknown(name))}
        )
        for c, entry in zip(comments, discussion.comments_json(comments), strict=True)
    ]


def _unknown(name: str) -> dict[str, Any]:
    return {"source": name, "trusted": False}


def translate_references(
    text: str,
    record: SourceRecord | None,
    declared: SourceSpec | None,
    items: Sequence[Item] | Iterable[Item],
) -> str:
    """*text* with each tracker reference to a pulled item replaced by that item's ID, when the
    host holds a *record* of a *declared* source and exactly one item holds the key named."""
    if record is None or declared is None:
        return text
    held_items = list(items)
    connector = connector_for(declared, {})
    out = text
    for ref in sorted(connector.references(text, record.key), key=lambda r: -r.start):
        held = [
            it.id
            for it in held_items
            if it.source is not None and (it.source.name, it.source.key) == (record.name, ref.key)
        ]
        if len(held) == 1:
            out = out[: ref.start] + held[0] + out[ref.end :]
    return out


def _quoted(text: str) -> str:
    """*text* in double quotes, with the quote, the backslash and control or format characters
    escaped, so a tracker name can never pass for the slug or the roster name before it."""
    out: list[str] = []
    for ch in text:
        if ch in '"\\':
            out.append("\\" + ch)
        elif unicodedata.category(ch) in ("Cc", "Cf", "Zl", "Zp"):
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


class CommentView:
    """Reads the sources document, the operators' identities and the references between sourced
    items once, for the comments of one host item."""

    def __init__(
        self, sources: Callable[[], SourcesSpec], items: Sequence[Item], host: Item | None
    ) -> None:
        self._sources = sources
        self._items = items
        self._host = host

    def _declared(self, name: str) -> SourceSpec | None:
        try:
            return self._sources().sources.get(name)
        except SquadsError:
            return None

    def _operator(self, source: str, user_id: str) -> Item | None:
        for item in self._items:
            ids = map_attribute(item, AttributeKey.IDENTITIES)
            if ids is not None and ids.get(source) == user_id and user_id:
                return item
        return None

    def _translated(self, text: str, declared: SourceSpec | None) -> str:
        record = self._host.source if self._host is not None else None
        return translate_references(text, record, declared, self._items)

    def _derived(self, cmt: discussion.Comment, name: str) -> dict[str, Any]:
        declared = self._declared(name)
        attrs = cmt.attributes
        handle = attrs.get(AUTHOR_HANDLE, "")
        operator = self._operator(name, attrs.get(AUTHOR_ID, ""))
        tracker_name = attrs.get(AUTHOR_NAME, "")
        parts = [f"{operator.slug} {operator.title}"] if operator else []
        if not operator and tracker_name:
            parts.append(_quoted(tracker_name))
        parts.append(f"via {name} @{handle}" if handle else f"via {name}")
        record = self._host.source if self._host is not None else None
        host_declared = self._declared(record.name) if record is not None else None
        url = connector_for(declared, {}).user_url(handle) if declared and handle else None
        return {
            "author": " ".join(parts),
            "source": name,
            "author_url": url,
            "identity": operator.slug if operator else None,
            "trusted": declared.trusted if declared else False,
            "body": self._translated(cmt.body, host_declared),
        }

    def dtos(self, comments: Sequence[discussion.Comment]) -> list[Comment]:
        """*comments* as DTOs, the ones a tracker wrote with their derived fields."""
        out: list[Comment] = []
        for cmt, entry in zip(comments, discussion.comments_json(comments), strict=True):
            name = source_of(cmt.author_slug)
            derived = self._derived(cmt, name) if name is not None else {}
            out.append(Comment.model_validate({**entry, **derived}))
        return out
