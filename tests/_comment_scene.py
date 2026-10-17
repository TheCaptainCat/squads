"""A task with a known set of comments, for the tests of comments addressed by hash.

Comments are written through the service one second apart, then the item file can be given a
preamble ahead of the first comment, so tests read what the verbs did to real files."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from _helpers import create_item
from squads import _discussion as discussion
from squads import _sections as sections
from squads._context import bind_context, get_context
from squads._models import _markers as markers

BASE = datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC)

SHAPES: dict[str, str] = {
    "single": "one line",
    "multi-line": "first line\nsecond line",
    "fenced": "Fix:\n```py\na = 1\n\nb = 2\n```",
}


def at(seconds: int) -> None:
    """Move the frozen clock to *seconds* after the base time."""
    bind_context(replace(get_context(), clock_override=BASE + timedelta(seconds=seconds)))


@dataclass
class Scene:
    svc: Any
    item_id: str
    sub: tuple[str, str] | None
    path: Path
    tag: str

    @property
    def scope(self) -> str:
        return "" if self.sub is None else f"{self.sub[0]}:{self.sub[1]}"

    def text(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def region(self) -> str:
        found = sections.get_section(self.text(), self.tag)
        assert found is not None
        return found

    async def comments(self) -> list[discussion.Comment]:
        item = await self.svc.get(self.item_id)
        return discussion.split_discussion(
            self.region(), sequence_id=item.sequence_id, scope=self.scope
        )

    def set_region(self, region: str) -> None:
        self.path.write_text(sections.replace_section(self.text(), self.tag, region), "utf-8")

    def body(self) -> str:
        return sections.split_frontmatter(self.text())[1]


async def scene(
    svc: Any,
    texts: list[str],
    *,
    sub: bool = False,
    authors: list[str] | None = None,
    preamble: str = "",
) -> Scene:
    """A task (and a subtask, when *sub*) whose discussion holds one comment per text, written
    by the matching author (default ``manager``)."""
    item = (await create_item(svc, "task", "task")).item
    target: tuple[str, str] | None = None
    if sub:
        block = await svc.add_block(item.id, "subtask", "child")
        target = ("subtask", block.local_id)
    for n, msg in enumerate(texts):
        at(n)
        who = authors[n] if authors else "manager"
        await svc.comment(item.id, [msg], as_slug=who, sub=target)
    at(len(texts) + 60)
    tag = (
        markers.DISCUSSION if target is None else markers.discussion_tag(f"{target[0]}:{target[1]}")
    )
    from squads._index._resolver import item_file

    out = Scene(svc, item.id, target, item_file(svc.paths, await svc.get(item.id)), tag)
    if preamble:
        out.set_region("\n" + preamble + "\n\n" + out.region().removeprefix("\n"))
    return out
