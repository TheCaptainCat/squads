"""Read/write the markdown file backing an item, keeping frontmatter and body in sync.

The ``.md`` frontmatter is the durable source of truth; ``sq`` rewrites only the frontmatter
(and marker sections), never the agent-authored body.

**Atomic by construction.** Every writer here (``write_new``, ``update_frontmatter``,
``write_text``, ``rewrite_ids``) goes through :func:`squads._aio.atomic_write_text` — temp file
+ fsync + ``os.replace`` in one thread hop — so a process killed mid-write leaves the file
complete-or-previous, never a truncated prefix. This is the *only* place a mutation core should
reach for; a bare ``_aio.write_text`` on an item ``.md`` reintroduces the truncation hazard.

**Ordering rule this module's callers must keep.** Within a transaction, every write to an
item's markdown — via this module's functions — happens inside the transaction body, before it
returns; the index commit (``IndexStore``'s own atomic replace) is always the transaction's
last write. A markdown write may never run after the commit — a killed process must always
leave the markdown ahead of (or equal to) the index, never behind, so ``sq repair`` can
converge on the file's state.
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


async def write_new(path: Path, item: Item, rendered_body: str) -> None:
    """Create a brand-new item file: frontmatter + the rendered (templated) body."""
    text = join_frontmatter(item.to_frontmatter_dict(), rendered_body)
    await _aio.mkdir(path.parent, parents=True, exist_ok=True)
    await _aio.atomic_write_text(path, text)


async def update_frontmatter(path: Path, item: Item) -> None:
    """Rewrite the frontmatter from the item; body is preserved verbatim."""
    text = await _aio.read_text(path)
    await _aio.atomic_write_text(path, replace_frontmatter(text, item.to_frontmatter_dict()))


async def write_text(path: Path, text: str) -> None:
    """Atomically overwrite an *existing* item file with fully-formed new text.

    The item-file layer's general-purpose exit for callers that have already built the whole
    new file contents themselves (a section edit, a sub-entity block rewrite, a retype's
    frontmatter+body rewrite, …) rather than growing a bespoke ``_aio.atomic_write_text`` import
    at each such call site — so every write of an item ``.md`` funnels through this module and
    "the item-file layer exposes only the atomic primitive" stays structurally true.
    """
    await _aio.atomic_write_text(path, text)


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
            await _aio.atomic_write_text(path, new_text)
            touched.append(path)
    return touched
