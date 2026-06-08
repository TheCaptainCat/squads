"""Build and parse the marker-delimited collaboration content: comments, stories, subtasks.

Stories and subtasks are scaffolded with three regions:
  - the heading line (``### US1`` / ``### ST1 — [ ] label``),
  - a ``…:body`` region the **agent** writes freely (paragraphs or bullets), and
  - a ``…:discussion`` region ``sq`` appends comments to.
The CLI returns the body region's location so the agent edits within the markers.
"""

import re

from squads.models import markers
from squads.sections import get_section

_MENTION_RE = re.compile(r"(?<![A-Za-z0-9_])@([a-z0-9][a-z0-9-]*)")
_LOCAL_ID_PREFIX = {"story": "US", "subtask": "ST"}

_STORY_PLACEHOLDER = (
    "_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance "
    "criteria here — free-form paragraphs or bullet lists._"
)
_SUBTASK_PLACEHOLDER = "_Describe this subtask here — free-form paragraphs or bullet lists._"


# --------------------------------------------------------------------------- comments


def format_comment(timestamp_iso: str, author: str, messages: list[str]) -> str:
    """One discussion entry: a timestamped author line with one sub-item per message."""
    lines = [f"- [{timestamp_iso}] {author}:"]
    for msg in messages:
        lines.append(f"  - {msg}")
    return "\n".join(lines)


def extract_mentions(text: str) -> set[str]:
    """All ``@slug`` mentions in a blob of text (lowercased slugs)."""
    return {m.lower() for m in _MENTION_RE.findall(text)}


# --------------------------------------------------------------------------- ids


def _existing_ids(text: str, kind: str) -> list[int]:
    # only the bare block opener (e.g. sq:story:US1), not :body / :discussion
    pat = re.compile(rf"<!--\s*sq:{kind}:{_LOCAL_ID_PREFIX[kind]}(\d+)\s*-->")
    return [int(n) for n in pat.findall(text)]


def next_local_id(text: str, kind: str) -> str:
    nums = _existing_ids(text, kind)
    return f"{_LOCAL_ID_PREFIX[kind]}{(max(nums) + 1) if nums else 1}"


def body_tag(kind: str, local_id: str) -> str:
    return f"{kind}:{local_id}:body"


# --------------------------------------------------------------------------- block builders


def build_story_block(local_id: str, title: str = "") -> str:
    tag = markers.story_tag(local_id)
    btag = body_tag("story", local_id)
    dtag = markers.discussion_tag(tag)
    heading = f"### {local_id}" + (f" — {title}" if title else "")
    return (
        f"\n{markers.open_marker(tag)}\n"
        f"{heading}\n\n"
        f"{markers.open_marker(btag)}\n{_STORY_PLACEHOLDER}\n{markers.close_marker(btag)}\n\n"
        f"{markers.open_marker(dtag)}\n{markers.close_marker(dtag)}\n"
        f"{markers.close_marker(tag)}\n"
    )


def build_subtask_block(local_id: str, title: str = "") -> str:
    tag = markers.subtask_tag(local_id)
    btag = body_tag("subtask", local_id)
    dtag = markers.discussion_tag(tag)
    heading = f"### {local_id} — [ ] {title}".rstrip()
    return (
        f"\n{markers.open_marker(tag)}\n"
        f"{heading}\n\n"
        f"{markers.open_marker(btag)}\n{_SUBTASK_PLACEHOLDER}\n{markers.close_marker(btag)}\n\n"
        f"{markers.open_marker(dtag)}\n{markers.close_marker(dtag)}\n"
        f"{markers.close_marker(tag)}\n"
    )


# --------------------------------------------------------------------------- parsing


def _iter_blocks(text: str, kind: str):
    prefix = _LOCAL_ID_PREFIX[kind]
    open_pat = re.compile(rf"<!--\s*sq:{kind}:({prefix}\d+)\s*-->")
    for m in open_pat.finditer(text):
        lid = m.group(1)
        end = text.find(markers.close_marker(f"{kind}:{lid}"), m.end())
        yield lid, text[m.end() : end if end != -1 else len(text)]


def _heading(block: str, local_id: str) -> tuple[str, bool]:
    # stay on the heading line: only horizontal whitespace, title is the rest of the line
    m = re.search(
        rf"###[ \t]*{re.escape(local_id)}[ \t]*(?:—[ \t]*)?(?:\[([ xX])\][ \t]*)?([^\n]*)",
        block,
    )
    if not m:
        return "", False
    done = (m.group(1) or "").lower() == "x"
    return m.group(2).strip(), done


def _body_first_line(block: str, kind: str, local_id: str) -> str:
    inner = get_section(block, body_tag(kind, local_id)) or ""
    for line in inner.splitlines():
        s = line.strip()
        if not s or (s.startswith("_") and s.endswith("_")):
            continue  # blank or placeholder italics
        return re.sub(r"^[-*#>\s]+", "", s)
    return ""


def list_blocks(text: str, kind: str) -> list[tuple[str, str]]:
    """[(local_id, summary), …]. Subtask summaries carry the ``[x]``/``[ ]`` checkbox."""
    out: list[tuple[str, str]] = []
    for lid, block in _iter_blocks(text, kind):
        title, done = _heading(block, lid)
        if kind == "subtask":
            summary = f"[{'x' if done else ' '}] {title}".rstrip()
        else:
            summary = title or _body_first_line(block, kind, lid)
        out.append((lid, summary))
    return out


def set_subtask_checkbox(text: str, local_id: str, done: bool) -> str:
    mark = "x" if done else " "
    pat = re.compile(rf"(###[ \t]*{re.escape(local_id)}[ \t]*—[ \t]*)\[[ xX]\]")
    new, count = pat.subn(rf"\1[{mark}]", text)
    if count == 0:
        raise KeyError(local_id)
    return new
