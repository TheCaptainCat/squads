"""Atlassian Document Format to markdown: a pure walk over the JSON document."""

import json
from typing import Any, cast

from squads._sources._markdown import fenced

type Node = dict[str, Any]

#: The deepest nesting of blocks the walk follows; a deeper document is refused.
MAX_DEPTH = 120
_MARKS = (("strong", "**"), ("em", "*"), ("strike", "~~"), ("code", "`"))


def _children(node: Node) -> list[Node]:
    content = node.get("content")
    if not isinstance(content, list):
        return []
    return [cast("Node", c) for c in cast("list[Any]", content) if isinstance(c, dict)]


def _attrs(node: Node) -> Node:
    attrs = node.get("attrs")
    return cast("Node", attrs) if isinstance(attrs, dict) else {}


def _integer(node: Node, key: str, default: int, low: int, high: int) -> int:
    """The integer attribute *key* of *node* held within ``low`` to ``high``, else *default*."""
    value = _attrs(node).get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return min(max(value, low), high)


def _deeper(depth: int) -> int:
    if depth >= MAX_DEPTH:
        raise ValueError("the document nests too deeply")
    return depth + 1


def _marked(text: str, node: Node) -> str:
    """*text* wrapped in the markdown of each mark on *node*."""
    marks = node.get("marks")
    for mark in cast("list[Any]", marks) if isinstance(marks, list) else []:
        if not isinstance(mark, dict):
            continue
        kind = cast("Node", mark).get("type")
        fence = dict(_MARKS).get(str(kind))
        if fence and text.strip():
            text = f"{fence}{text}{fence}"
        elif kind == "link":
            text = f"[{text}]({_attrs(cast('Node', mark)).get('href', '')})"
    return text


def _inline(node: Node, depth: int) -> str:
    kind = node.get("type")
    if kind == "text":
        return _marked(str(node.get("text", "")), node)
    if kind == "hardBreak":
        return "  \n"
    if kind == "mention":
        return str(_attrs(node).get("text") or "@" + str(_attrs(node).get("id", "")))
    if kind in ("inlineCard", "emoji"):
        attrs = _attrs(node)
        return str(attrs.get("url") or attrs.get("text") or attrs.get("shortName") or "")
    below = _deeper(depth)
    return "".join(_inline(c, below) for c in _children(node))


def _prefixed(block: str, first: str, rest: str) -> str:
    lines = block.split("\n")
    return "\n".join([first + lines[0], *(rest + line if line else "" for line in lines[1:])])


def _list(node: Node, depth: int, *, ordered: bool) -> str:
    start = _integer(node, "order", 1, 0, 999_999_999) if ordered else 0
    below = _deeper(depth)
    items: list[str] = []
    for index, item in enumerate(_children(node)):
        body = "\n".join(
            part for part in (_block(child, below) for child in _children(item)) if part
        ).replace("\n\n", "\n")
        marker = f"{start + index}. " if ordered else "- "
        items.append(_prefixed(body, marker, " " * len(marker)))
    return "\n".join(items)


def _cell(node: Node, depth: int) -> str:
    below = _deeper(depth)
    text = " ".join(_block(c, below) for c in _children(node)).replace("\n", " ")
    return text.replace("|", "\\|")


def _table(node: Node, depth: int) -> str:
    below = _deeper(depth)
    rows = [[_cell(c, below) for c in _children(row)] for row in _children(node)]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    padded = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(r) + " |" for r in padded]
    lines.insert(1, "|" + " --- |" * width)
    return "\n".join(lines)


def _code(node: Node) -> str:
    text = "".join(str(c.get("text", "")) for c in _children(node))
    return fenced(text, str(_attrs(node).get("language", "")))


def _block(node: Node, depth: int) -> str:
    kind = node.get("type")
    below = _deeper(depth)
    rendered = {
        "paragraph": lambda: _inline(node, below),
        "heading": lambda: "#" * _integer(node, "level", 1, 1, 6) + " " + _inline(node, below),
        "bulletList": lambda: _list(node, below, ordered=False),
        "orderedList": lambda: _list(node, below, ordered=True),
        "codeBlock": lambda: _code(node),
        "blockquote": lambda: _prefixed(_blocks(node, below), "> ", "> "),
        "rule": lambda: "---",
        "table": lambda: _table(node, below),
    }
    if kind in rendered:
        return rendered[kind]()
    return _blocks(node, below) if _children(node) else _inline(node, below)


def _blocks(node: Node, depth: int) -> str:
    below = _deeper(depth)
    return "\n\n".join(part for part in (_block(c, below) for c in _children(node)) if part)


def adf(text: str, base_url: str, issue_url: str) -> str:
    """Markdown for an ADF document given as JSON text; text that is not one is kept as it is."""
    del base_url, issue_url
    try:
        document = json.loads(text)
    except ValueError, RecursionError:
        return text
    if not isinstance(document, dict) or cast("Node", document).get("type") != "doc":
        return text
    return _blocks(cast("Node", document), 0)
