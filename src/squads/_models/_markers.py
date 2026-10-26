"""sq section markers: every sq-managed file carries invisible HTML-comment anchors so the CLI can
update specific sections without disturbing agent-authored prose, and agents must never alter them.
A section ``tag`` is delimited by::

    <!-- sq:<tag> -->
    ...content...
    <!-- sq:<tag>:end -->
"""

from dataclasses import dataclass

# Top-level section tags shared by most item files.
BODY = "body"
DISCUSSION = "discussion"
#: sq-managed roll-up table of a parent's sub-entities (regenerated on every change).
SUMMARY = "summary"

#: Marker prefix; used to detect sq markers when linting.
PREFIX = "sq:"


def open_marker(tag: str) -> str:
    return f"<!-- sq:{tag} -->"


def close_marker(tag: str) -> str:
    return f"<!-- sq:{tag}:end -->"


def subentity_tag(kind: str, local_id: str) -> str:
    """Anchor tag of one sub-entity block (``<kind>:<local id>``), for any declared *kind*."""
    return f"{kind}:{local_id}"


def discussion_tag(base: str | None = None) -> str:
    """Discussion anchor for the whole ticket, or nested under a story/subtask block."""
    return f"{base}:{DISCUSSION}" if base else DISCUSSION


#: Namespace of the unpaired view-placement tag family: ``sq:view:<name>`` marks where a declared
#: view renders on read. It deliberately has no ``close_marker`` and none may be added: a pair
#: defines a span something is written into, while this tag names a view and has no span, so no code
#: path can write rendered content into it. Giving it a body or paired form would rebuild a stored
#: region this design refuses.
VIEW = "view"

#: The disabled-state suffix, colon-delimited so it stays inside
#: :data:`~squads._sections.MARKER_RE`'s character class; a bracketed spelling would make a disabled
#: tag invisible to ``find_markers``/``reject_markers``, which this family depends on.
_DISABLED_SUFFIX = ":disabled"


@dataclass(frozen=True)
class ViewTagParts:
    """A parsed ``sq:view:<name>`` tag's two independent facts: which view it names, and
    whether it is disabled. Returned together, never as a single string, so no caller can
    mistake ``"<name>:disabled"`` for the name itself — the shape :func:`view_tag_parts`
    replaces."""

    name: str
    disabled: bool


def view_tag(name: str, *, disabled: bool = False) -> str:
    """The bare tag (``sq:`` stripped, no wrapper) for *name*'s unpaired view marker, e.g.
    ``"view:milestone_rollup"`` or ``"view:milestone_rollup:disabled"``, composed like
    :func:`subentity_tag` and fed to :func:`open_marker`. It has no ``close_marker`` (see
    :data:`VIEW`), and the disabled suffix is spelled only here.
    """
    return f"{VIEW}:{name}{_DISABLED_SUFFIX if disabled else ''}"


def view_tag_parts(tag: str) -> ViewTagParts | None:
    """*tag*'s name and state (:class:`ViewTagParts`) if it belongs to the unpaired view-tag family,
    else ``None``. It accepts the bare form (``"view:milestone_rollup"``) and the on-disk form with
    ``sq:`` attached (what :func:`~squads._sections.find_markers` emits), so callers pass a
    producer's raw tag straight through (a bare-only recogniser would return ``None``, read as "not
    a view tag", for every real producer's output). A close-marker spelling (``:end``) never matches
    in either form, checked before the disabled-suffix strip, so ``sq:view:end`` (a name refused at
    spec load) is not read as a disabled view named ``end``.
    """
    if tag.endswith(":end"):
        return None
    if tag.startswith(PREFIX):
        tag = tag[len(PREFIX) :]
    prefix = f"{VIEW}:"
    if not tag.startswith(prefix):
        return None
    name = tag[len(prefix) :]
    disabled = name.endswith(_DISABLED_SUFFIX)
    if disabled:
        name = name[: -len(_DISABLED_SUFFIX)]
    return ViewTagParts(name, disabled) if name else None
