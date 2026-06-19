"""Read/write the markdown file backing an item, keeping frontmatter and body in sync.

The ``.md`` frontmatter is the durable source of truth; ``sq`` rewrites only the frontmatter
(and marker sections), never the agent-authored body.
"""

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from squads import _aio
from squads._models._item import Item
from squads._sections import join_frontmatter, replace_frontmatter, split_frontmatter


def read_frontmatter(path: Path | None = None, *, text: str | None = None) -> dict[str, Any]:
    if text is None:
        if path is None:
            raise ValueError("read_frontmatter requires a path or text")
        text = path.read_text(encoding="utf-8")
    return split_frontmatter(text)[0]


async def load_item(path: Path, *, squad_relative: str) -> Item:
    """Read and parse the item file on a worker thread."""
    text = await _aio.read_text(path)
    data = split_frontmatter(text)[0]
    return Item.from_frontmatter(data, path=squad_relative)


async def write_new(path: Path, item: Item, rendered_body: str) -> None:
    """Create a brand-new item file: frontmatter + the rendered (templated) body."""
    text = join_frontmatter(item.to_frontmatter_dict(), rendered_body)
    await _aio.mkdir(path.parent, parents=True, exist_ok=True)
    await _aio.write_text(path, text)


async def update_frontmatter(path: Path, item: Item) -> None:
    """Rewrite the frontmatter from the item; body is preserved verbatim."""
    text = await _aio.read_text(path)
    await _aio.write_text(path, replace_frontmatter(text, item.to_frontmatter_dict()))


async def rewrite_ids(paths: Iterable[Path], remap: dict[str, str]) -> list[Path]:
    """Whole-word substitution of every old ID → new ID across the given files.

    Replaces all occurrences of ``\\bOLD\\b → NEW`` (exact whole-word match so e.g. a longer ID
    sharing a prefix is not touched).  Returns the list of paths that were actually modified.
    """
    touched: list[Path] = []
    for path in paths:
        text = await _aio.read_text(path)
        new_text = text
        for old, new in remap.items():
            new_text = re.sub(rf"\b{re.escape(old)}\b", new, new_text)
        if new_text != text:
            await _aio.write_text(path, new_text)
            touched.append(path)
    return touched
