"""Jira wiki markup to markdown: block by block, then the inline marks of each line."""

import re

from squads._sources._markdown import fenced

_OPEN_RE = re.compile(r"\{(code|noformat)(?::([^}\n]{0,100}))?\}")
_HEADING_RE = re.compile(r"^h([1-6])\.\s+(.*)$")
_LIST_RE = re.compile(r"^([*#]+)\s+(.*)$")
_LINK_RE = re.compile(r"\[(?!~)([^|\]\n]{1,500})\|([^\]\n]{1,2000})\]")
_BARE_LINK_RE = re.compile(r"\[(https?://[^\]\s|]{1,2000})\]")
_MENTION_RE = re.compile(r"\[~(?:accountid:)?([^\]\n]{1,200})\]")
_IMAGE_RE = re.compile(r"!([^!\s|]{1,2000})(?:\|[^!\n]{0,500})?!")
_MONO_RE = re.compile(r"\{\{([^{}\n]{1,500})\}\}")
_BOLD_RE = re.compile(r"(?<![\w*])\*(?!\s)([^*\n]{1,500}?)(?<!\s)\*(?![\w*])")
_ITALIC_RE = re.compile(r"(?<![\w_])_(?!\s)([^_\n]{1,500}?)(?<!\s)_(?![\w_])")
_STRIKE_RE = re.compile(r"(?<![\w-])-(?!\s)([^-\n]{1,500}?)(?<!\s)-(?![\w-])")
_BREAK_RE = re.compile(r"\\\\")


def _inline(line: str) -> str:
    """*line* with its wiki marks as markdown; code spans are set aside so their text stays."""
    spans: list[str] = []

    def keep(match: re.Match[str]) -> str:
        spans.append(f"`{match.group(1)}`")
        return f"\x00{len(spans) - 1}\x00"

    line = _MONO_RE.sub(keep, line)
    line = _LINK_RE.sub(lambda m: f"[{m.group(1)}]({m.group(2)})", line)
    line = _BARE_LINK_RE.sub(lambda m: f"<{m.group(1)}>", line)
    line = _MENTION_RE.sub(lambda m: f"@{m.group(1)}", line)
    line = _IMAGE_RE.sub(lambda m: f"![]({m.group(1)})", line)
    line = _BOLD_RE.sub(lambda m: f"**{m.group(1)}**", line)
    line = _ITALIC_RE.sub(lambda m: f"*{m.group(1)}*", line)
    line = _STRIKE_RE.sub(lambda m: f"~~{m.group(1)}~~", line)
    line = _BREAK_RE.sub("  \n", line)
    return re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], line)


def _row(line: str) -> list[str]:
    header = line.startswith("||")
    cells = re.split(r"\|\|" if header else r"\|", line.strip().strip("|"))
    return [_inline(c.strip()) for c in cells]


def _table(rows: list[str]) -> list[str]:
    parsed = [_row(r) for r in rows]
    width = max(len(r) for r in parsed)
    lines = ["| " + " | ".join(r + [""] * (width - len(r))) + " |" for r in parsed]
    if not rows[0].startswith("||"):
        lines.insert(0, "|" + "  |" * width)
    lines.insert(1, "|" + " --- |" * width)
    return lines


def _lines(text: str) -> list[str]:
    out: list[str] = []
    rows: list[str] = []

    def flush() -> None:
        if rows:
            out.extend(_table(rows))
            rows.clear()

    for line in text.split("\n"):
        if line.startswith("|"):
            rows.append(line)
            continue
        flush()
        heading, item = _HEADING_RE.match(line), _LIST_RE.match(line)
        if heading:
            out.append("#" * int(heading.group(1)) + " " + _inline(heading.group(2)))
        elif item:
            depth = len(item.group(1))
            marker = "1." if item.group(1)[-1] == "#" else "-"
            out.append("  " * (depth - 1) + f"{marker} {_inline(item.group(2))}")
        elif line.startswith("bq. "):
            out.append("> " + _inline(line[4:]))
        elif line.strip() == "----":
            out.append("---")
        else:
            out.append(_inline(line))
    flush()
    return out


def _blocks_set_aside(text: str, blocks: list[str]) -> str:
    """*text* with each ``{code}``/``{noformat}`` block replaced by a placeholder and stored
    converted in *blocks*; an opener with no closer is left as text, and so is every later one."""
    out: list[str] = []
    pos = 0
    exhausted: set[str] = set()
    for opener in _OPEN_RE.finditer(text):
        name = opener.group(1)
        if opener.start() < pos or name in exhausted:
            continue
        close = text.find("{" + name + "}", opener.end())
        if close < 0:
            exhausted.add(name)
            continue
        language = (opener.group(2) or "") if name == "code" else ""
        blocks.append(fenced(text[opener.end() : close].strip("\n"), language))
        out.append(text[pos : opener.start()] + f"\x01{len(blocks) - 1}\x01")
        pos = close + len(name) + 2
    return "".join(out) + text[pos:]


def _quoted(text: str) -> str:
    """*text* with each ``{quote}`` pair turned into quoted lines."""
    parts = text.split("{quote}")
    if len(parts) < 3:
        return text
    out = [parts[0]]
    for index in range(1, len(parts) - 1, 2):
        out.append("\n".join("> " + line for line in parts[index].strip("\n").split("\n")))
        out.append(parts[index + 1])
    if len(parts) % 2 == 0:
        out.append("{quote}" + parts[-1])
    return "".join(out)


def jira_wiki(text: str, base_url: str, issue_url: str) -> str:
    """Markdown for Jira wiki markup: headings, lists, tables, quotes, code, links and marks."""
    del base_url, issue_url
    text = text.replace("\r\n", "\n").replace("\x00", "").replace("\x01", "")
    blocks: list[str] = []
    text = _quoted(_blocks_set_aside(text, blocks))
    converted = "\n".join(_lines(text))
    return re.sub(r"\x01(\d+)\x01", lambda m: blocks[int(m.group(1))], converted)
