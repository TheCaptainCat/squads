"""sq section markers.

Every sq-managed file carries invisible HTML-comment anchors so the CLI can locate and
update specific sections without disturbing agent-authored prose. Agents must never alter
these marker lines.

A section ``tag`` is delimited by::

    <!-- sq:<tag> -->
    ...content...
    <!-- sq:<tag>:end -->
"""

# Top-level section tags shared by most item files.
BODY = "body"
DISCUSSION = "discussion"
#: sq-managed roll-up table of a parent's sub-entities (regenerated on every change).
SUMMARY = "summary"
# Containers that hold scaffolded sub-blocks.
STORIES = "stories"
SUBTASKS = "subtasks"
FINDINGS = "findings"

#: Marker prefix; used to detect sq markers when linting.
PREFIX = "sq:"


def open_marker(tag: str) -> str:
    return f"<!-- sq:{tag} -->"


def close_marker(tag: str) -> str:
    return f"<!-- sq:{tag}:end -->"


def story_tag(local_id: str) -> str:
    return f"story:{local_id}"


def subtask_tag(local_id: str) -> str:
    return f"subtask:{local_id}"


def finding_tag(local_id: str) -> str:
    return f"finding:{local_id}"


def discussion_tag(base: str | None = None) -> str:
    """Discussion anchor for the whole ticket, or nested under a story/subtask block."""
    return f"{base}:{DISCUSSION}" if base else DISCUSSION


#: Namespace of the unpaired view-placement tag family: ``sq:view:<name>`` marks where a
#: declared view renders on read. **Deliberately has no `close_marker` counterpart
#: and none may ever be added** — every other tag in this module is a pair, and a pair defines
#: a span for something to be written into. This one names a view and nothing else; there is
#: no span, so there is no code path that could write rendered content into it. A view tag's
#: bytes carry a name, which has no freshness dimension to lose — that is what separates it
#: from the stored regions (``SUMMARY``, a sub-entity's ``:head``) this design refuses.
#: Any future proposal to give this tag a body or a paired form is the proposal to rebuild a
#: stored region, and should be read and refused as exactly that.
VIEW = "view"


def view_tag(name: str) -> str:
    """The bare tag (``sq:`` prefix stripped, no HTML-comment wrapper) naming *name*'s
    unpaired view-placement marker, e.g. ``"view:milestone_rollup"``. Composed the same way
    :func:`story_tag`/:func:`subtask_tag`/:func:`finding_tag` compose theirs — feed it to
    :func:`open_marker` for the on-disk form. There is deliberately no matching
    ``close_marker`` counterpart; see :data:`VIEW`."""
    return f"{VIEW}:{name}"


def view_tag_name(tag: str) -> str | None:
    """*tag* if it belongs to the unpaired view-tag family — the view name it then names —
    else ``None``.

    Accepts **either** the bare form (``"view:milestone_rollup"``, what :func:`view_tag`
    composes) **or** the full on-disk form with its ``sq:`` prefix still attached
    (``"sq:view:milestone_rollup"`` — the exact string :func:`~squads._sections.find_markers`
    and :func:`~squads._sections.iter_marker_spans` actually emit, since neither strips
    :data:`PREFIX` before returning a tag). A recogniser that only accepted the bare form
    rejected the one form its only producers ever hand it, and did so the worst possible way
    — silently, by returning ``None``, which every caller reads as "not a view tag". Accepting
    both means every caller (read-time expansion, ``sq check``'s marker-balance exemption and
    its view-target finding) can pass a producer's raw tag straight through, with no hand-strip
    at the call site re-deriving :data:`PREFIX` on its own.

    A close-marker spelling (a tag ending in ``:end``) never matches, in either form: this
    family has no closing counterpart by design (see :data:`VIEW`), so "unpaired" is a property
    of the tag's own shape, not an artifact of how a caller happens to have found it.
    """
    if tag.endswith(":end"):
        return None
    if tag.startswith(PREFIX):
        tag = tag[len(PREFIX) :]
    prefix = f"{VIEW}:"
    if not tag.startswith(prefix):
        return None
    name = tag[len(prefix) :]
    return name or None
