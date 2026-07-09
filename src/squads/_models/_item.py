"""The tracked item — the unit behind every ID."""

from datetime import UTC, datetime
from typing import Any, cast

from pydantic import BaseModel, Field, computed_field, field_validator

from squads import _clock as clock
from squads._models._enums import (  # noqa: F401 — re-exported for callers
    Priority,
    Status,  # pyright: ignore[reportUnusedImport]
)
from squads._models._subentity import SubEntity
from squads._util import NonEmpty

REF_SEP = ":"
DEFAULT_KIND = "related"

#: The default (and minimum) number of zero-padded digits in a *filename* (e.g.
#: ``PREFIX-000007-slug.md``). Changing this requires a ``sq migrate repad`` run.
#: Never used for display — see :data:`DISPLAY_ID_PADDING`.
DEFAULT_ID_PADDING: int = 6

#: Display padding is fixed at 0 (JIRA-style, e.g. ``PREFIX-7``) — it is a constant, never a
#: stored or configurable field. Every human-facing surface (frontmatter ``id:``,
#: refs, prose, CLI output) formats at this width. Filenames stay padded at
#: :data:`DEFAULT_ID_PADDING` / the squad's stored ``SquadsDB.padding`` — that divergence is
#: deliberate; format filenames explicitly via
#: ``format_item_id(prefix, sequence_id, db.padding)``, never from ``item.id``.
DISPLAY_ID_PADDING: int = 0


def format_item_id(prefix: str, sequence_id: int, padding: int = DEFAULT_ID_PADDING) -> str:
    """Format a typed item ID from its prefix, sequence number, and zero-pad width.

    This is the single canonical formatter; all `:0Nd` formatting elsewhere must route through it.
    """
    return f"{prefix}-{sequence_id:0{padding}d}"


#: Obviously-synthetic sentinel for "no real prefix resolved yet" — never a real prefix, and
#: never mistaken for one. Real vocabulary resolution (``prefix_for``) always raises on an
#: unknown/absent type rather than guessing; this sentinel is strictly the last-resort stand-in
#: for the handful of acyclic formatters/matchers below that cannot raise (they render ids for
#: reprs, logs, filenames, and ref-matching) and cannot import ``_workflow`` to resolve real
#: vocabulary (the acyclic invariant). A leaked pre-resolution id then reads e.g.
#: ``UNRESOLVED-42`` — loud and test-visible — never a plausible-but-wrong ``type.upper()``
#: guess (which would silently mis-render e.g. decision -> "DECISION" instead of "ADR").
UNRESOLVED_PREFIX = "UNRESOLVED"


def effective_prefix(prefix: str, item_type: str) -> str:
    """Return *prefix* if set, else the diagnosable :data:`UNRESOLVED_PREFIX` sentinel.

    The one shared "best prefix we have right now, without resolving real vocabulary" helper —
    every acyclic formatter/matcher that used to fall back to ``item_type.upper()`` (Item.id,
    ``SquadsDB.format_id``, the ref-matching helpers in ``_services``/``_cli``) routes through
    this instead. ``item_type`` is accepted (rather than making this a bare ``prefix or
    UNRESOLVED_PREFIX`` one-liner at every call site) so the signature stays self-documenting
    about what it's a stand-in prefix *for*, and so a future refinement (e.g. logging the type
    on a sentinel hit) has a natural home.

    In production this branch should never actually run: ``prefix`` is spec-resolved at
    create/retype time and backfilled at every load boundary before ``.id``/matching is
    consumed. It exists purely as a never-should-happen guard, never a vocabulary source.
    """
    return prefix or UNRESOLVED_PREFIX


#: The closed vocabulary of ref kinds — exhaustive, no custom-kind escape hatch.
#: Consumers: blocks/depends-on → sq blocked; fixes/addresses → sq check
#: task rules; supersedes → decision checks; the rest → navigation.
VALID_REF_KINDS: frozenset[str] = frozenset(
    {
        "related",
        "blocks",
        "depends-on",
        "implements",
        "fixes",
        "addresses",
        "supersedes",
        "duplicates",
    }
)


def split_ref(ref: str) -> tuple[str, str]:
    """``"ID"`` → ``(ID, "related")``; ``"ID:kind"`` → ``(ID, kind)``. IDs never contain ``:``."""
    rid, _, kind = ref.partition(REF_SEP)
    return rid, (kind or DEFAULT_KIND)


def make_ref(item_id: str, kind: str = DEFAULT_KIND) -> str:
    """A bare ID for the default kind, else ``"ID:kind"`` (kind carried with the edge)."""
    return item_id if not kind or kind == DEFAULT_KIND else f"{item_id}{REF_SEP}{kind}"


def ref_id_matches(stored_ref_id: str, prefix: str, seq: int) -> bool:
    """Return True when *stored_ref_id* refers to the same item as *(prefix, seq)*.

    Comparison is width-tolerant: a stored ref may carry an old zero-pad width after a
    ``sq migrate repad`` while *seq* is the canonical integer identity.  Type-prefix
    matching prevents false positives when two items share a sequence number (collision
    state during renumber).

    Alongside :func:`split_ref` and :func:`make_ref` as the shared ref-ID primitive; import
    from here rather than duplicating in service modules.
    """
    head, _, digits = stored_ref_id.rpartition("-")
    if not digits.isdigit():
        return False
    return head.upper() == prefix.upper() and int(digits) == seq


def fold_legacy_kinds(refs: list[str], legacy: dict[str, str]) -> list[str]:
    """Merge a pre-2 ``extra.ref_kinds`` ``{ID: kind}`` map into inline ``ID:kind`` ref strings."""
    return [make_ref(rid, legacy.get(rid, kind)) for rid, kind in (split_ref(r) for r in refs)]


class Item(BaseModel):
    #: The global counter number — the item's real identity. ``id`` is derived from it + ``type``.
    sequence_id: int
    #: Item type as a plain string. The loaded ``WorkflowSpec`` is the sole vocabulary
    #: authority; validated against it at the service load boundary.
    type: str
    title: NonEmpty
    slug: NonEmpty
    #: Status as a plain string.
    #: Same reserved-vocab guarantee and StrEnum equality as ``type``.
    status: str
    description: str = ""
    parent: str | None = None
    #: The registered agent (role slug) who authored the item.
    author: str | None = None
    assignee: str | None = None
    #: Optional importance, independent of status. Unset means no priority assigned.
    priority: Priority | None = None
    labels: list[str] = []
    #: Forward edges only. Backrefs are computed by inverting these across all items.
    refs: list[str] = []
    #: Body-local sub-entities (stories/subtasks/findings). A given item type hosts exactly one
    #: kind; their prose stays in the markdown markers, their state lives here.
    subentities: list[SubEntity] = []
    #: Squad-folder-relative path to the item's markdown file.
    path: NonEmpty
    created_at: datetime
    updated_at: datetime
    #: Session id at creation time.  **Best-effort, untrusted, observability-only.**
    #: squads reads ``SQUADS_SESSION_ID`` from its own invocation environment and records it here
    #: when present.  Absent == legacy item (no session env was set).  This is a self-declaration
    #: from the invocation environment — squads never mints, injects, spawns, or verifies it.
    #: Must NOT be used as an authorisation input.
    created_session: str | None = None
    #: Session id at last mutation time.  Same untrusted guarantee as
    #: :attr:`created_session`.  Updated on every frontmatter-touching mutation (status, update,
    #: body, comment, subentity, ref).
    modified_session: str | None = None
    #: Type-specific fields (e.g. agent role config, dev tech, adr context).
    extra: dict[str, Any] = {}
    #: The resolved ID prefix for this item (e.g. ``"TASK"``, ``"INC"``), for EVERY type
    #: (built-in or custom). Stamped at create/retype time from the active spec.
    #: Excluded from the JSON index (never persisted there — see ``IndexStore``'s post-load
    #: backfill) but always written to frontmatter, so a file round-trips through
    #: ``from_frontmatter``/``to_frontmatter_dict`` with no spec in hand (``_models`` stays
    #: spec-decoupled and never imports ``_workflow``).
    prefix: str = Field(default="", exclude=True, repr=False)

    model_config = {"use_enum_values": False}

    @field_validator("type", "status", mode="before")
    @classmethod
    def _coerce_str_fields(cls, v: object) -> str:
        """Coerce StrEnum members to plain str so pydantic stores a clean string.

        ``use_enum_values=False`` prevents auto-coercion; callers may pass a ``Status``
        member (StrEnum, which IS a str subclass) which is assignment-compatible but must
        be stored as plain ``str`` to keep YAML serialisation and identity checks clean.

        Only ``str`` (and subclasses such as ``StrEnum``) are accepted.  Anything else
        — ``int``, ``None``, etc. — raises ``ValueError`` so Pydantic surfaces a
        ``ValidationError`` rather than silently stringifying the bad value.
        """
        if not isinstance(v, str):
            raise ValueError(f"expected str, got {type(v).__name__!r}: {v!r}")  # noqa: TRY004
        return str(v)

    @computed_field
    @property
    def id(self) -> str:
        """The formatted id (``PREFIX-7``) — derived from ``prefix`` + ``sequence_id``.

        Display width is always :data:`DISPLAY_ID_PADDING` (0) — every human-facing
        surface (frontmatter ``id:``, refs, prose, CLI output) reads unpadded, regardless of the
        squad's stored filename width (``SquadsDB.padding``). Written to frontmatter as the
        durable human id; reconstructed via ``from_frontmatter``.

        ``prefix`` is stamped at create/retype time by the service (which holds the spec)
        and propagated by the index store after load.  The model itself never derives vocab:
        it formats purely from whatever prefix string it was given.

        If ``prefix`` is empty (e.g. a bare ``Item(...)`` constructed in a test without one,
        or a legacy file read before the load-boundary backfill), the id degrades to the
        :data:`UNRESOLVED_PREFIX` sentinel rather than crashing or guessing — the model itself
        never derives real vocabulary (that would require importing ``_workflow``, breaking the
        acyclic invariant).
        """
        return format_item_id(
            effective_prefix(self.prefix, self.type), self.sequence_id, DISPLAY_ID_PADDING
        )

    def to_frontmatter_dict(self) -> dict[str, Any]:
        """The mapping written into the markdown file's YAML frontmatter (durable truth).

        ``prefix`` is written as a frontmatter line for EVERY type, built-in or custom —
        this is what lets a file round-trip through ``from_frontmatter``
        with no spec in hand (e.g. ``sq repair``).
        """
        data: dict[str, Any] = self._core_frontmatter_fields()
        if self.prefix:
            data["prefix"] = self.prefix
        _add_optional_frontmatter_fields(data, self)
        return data

    def _core_frontmatter_fields(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sequence_id": self.sequence_id,
            "type": self.type,
            "title": self.title,
            "status": self.status,
        }

    @classmethod
    def from_frontmatter(cls, data: dict[str, Any], *, path: str) -> Item:
        """Reconstruct an Item from parsed frontmatter — used by ``sq repair``.

        ``type`` and ``status`` are stored as plain strings; the vocabulary
        validation (against WorkflowSpec) runs at the service load boundary, not here.

        ``prefix`` is read back straight from frontmatter when present (every type, built-in
        or custom, writes it).  When absent (legacy files predating the
        ``prefix:`` line), ``prefix`` is left as ``""`` and the store's post-load pass fills
        it via ``prefix_for`` before returning the DB (parallel to ``_propagate_padding``).
        """
        item_type: str = data["type"]
        stored_prefix: str = data.get("prefix") or ""
        return cls(
            sequence_id=data["sequence_id"],
            type=item_type,
            prefix=stored_prefix,
            title=data.get("title", ""),
            slug=data.get("slug") or _slug_from_path(path),
            status=data["status"],
            description=data.get("description", ""),
            parent=data.get("parent"),
            author=data.get("author"),
            assignee=data.get("assignee"),
            priority=Priority(data["priority"]) if data.get("priority") else None,
            labels=list(data.get("labels", []) or []),
            refs=_read_refs(data),
            subentities=[
                SubEntity.from_frontmatter(s)
                for s in cast("list[dict[str, Any]]", data.get("subentities") or [])
            ],
            path=path,
            created_at=_parse_dt(data.get("created_at")),
            updated_at=_parse_dt(data.get("updated_at")),
            # Session fields are optional — absent from legacy files; None == unset.
            created_session=data.get("created_session") or None,
            modified_session=data.get("modified_session") or None,
            extra=_read_extra(data),
        )


def _read_refs(data: dict[str, Any]) -> list[str]:
    """Refs as inline ``ID[:kind]`` strings, folding a pre-2 ``extra.ref_kinds`` map if present."""
    refs: list[str] = list(data.get("refs", []) or [])
    legacy: Any = dict(data.get("extra", {}) or {}).get("ref_kinds")
    if isinstance(legacy, dict):
        return fold_legacy_kinds(refs, cast("dict[str, str]", legacy))
    return refs


def _read_extra(data: dict[str, Any]) -> dict[str, Any]:
    """Item ``extra``, minus the legacy ``ref_kinds`` (now carried inline on the refs)."""
    extra: dict[str, Any] = dict(data.get("extra", {}) or {})
    extra.pop("ref_kinds", None)
    return extra


def _add_optional_frontmatter_fields(data: dict[str, Any], item: Item) -> None:
    """Populate *data* with the optional / conditional frontmatter fields of *item*.

    Extracted to keep :meth:`Item.to_frontmatter_dict` below the C901 complexity ceiling.
    """
    if item.parent:
        data["parent"] = item.parent
    if item.author:
        data["author"] = item.author
    if item.assignee:
        data["assignee"] = item.assignee
    if item.priority:
        data["priority"] = item.priority.value
    if item.refs:
        data["refs"] = list(item.refs)
    if item.labels:
        data["labels"] = list(item.labels)
    if item.description:
        data["description"] = item.description
    if item.subentities:
        data["subentities"] = [s.to_frontmatter_dict() for s in item.subentities]
    data["created_at"] = clock.iso(item.created_at)
    data["updated_at"] = clock.iso(item.updated_at)
    # Session fields are omitted when unset to keep legacy files unchanged.
    if item.created_session is not None:
        data["created_session"] = item.created_session
    if item.modified_session is not None:
        data["modified_session"] = item.modified_session
    if item.extra:
        data["extra"] = item.extra


def _slug_from_path(path: str) -> str:
    name = path.rsplit("/", 1)[-1].removesuffix(".md")
    # strip leading "PREFIX-NNNNNN-"
    parts = name.split("-", 2)
    return parts[2] if len(parts) == 3 else name


def _parse_dt(value: object) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        return datetime.now(UTC).replace(microsecond=0)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt
