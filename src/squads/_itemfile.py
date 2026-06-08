"""Read/write the markdown file backing an item, keeping frontmatter and body in sync.

The ``.md`` frontmatter is the durable source of truth; ``sq`` rewrites only the frontmatter
(and marker sections), never the agent-authored body.
"""

from pathlib import Path
from typing import Any

from squads._models._item import Item
from squads._sections import join_frontmatter, replace_frontmatter, split_frontmatter


def read_frontmatter(path: Path | None = None, *, text: str | None = None) -> dict[str, Any]:
    if text is None:
        if path is None:
            raise ValueError("read_frontmatter requires a path or text")
        text = path.read_text(encoding="utf-8")
    return split_frontmatter(text)[0]


def load_item(path: Path, *, squad_relative: str) -> Item:
    data = read_frontmatter(path)
    return Item.from_frontmatter(data, path=squad_relative)


def write_new(path: Path, item: Item, rendered_body: str) -> None:
    """Create a brand-new item file: frontmatter + the rendered (templated) body."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = join_frontmatter(item.to_frontmatter_dict(), rendered_body)
    path.write_text(text, encoding="utf-8")


def update_frontmatter(path: Path, item: Item) -> None:
    """Rewrite the frontmatter from the item; body is preserved verbatim."""
    text = path.read_text(encoding="utf-8")
    path.write_text(replace_frontmatter(text, item.to_frontmatter_dict()), encoding="utf-8")
