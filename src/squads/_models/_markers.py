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
