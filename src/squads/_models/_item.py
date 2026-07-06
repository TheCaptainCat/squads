"""The tracked item — the unit behind every ID."""

from datetime import UTC, datetime
from typing import Any, cast

from pydantic import BaseModel, Field, computed_field, field_validator

from squads import _clock as clock
from squads._models._enums import (  # noqa: F401 — re-exported for callers
    ItemType,  # pyright: ignore[reportUnusedImport]
    Priority,
    Status,  # pyright: ignore[reportUnusedImport]
)
from squads._models._subentity import SubEntity
from squads._models._vocab import RESERVED_PREFIX as _RESERVED_PREFIX
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
    #: Item type as a plain string.
    #: Reserved vocabulary is validated at the service load boundary via ``WorkflowSpec``.
    #: ``ItemType`` members compare equal to their plain string values (StrEnum), so callers
    #: may compare ``item.type == ItemType.TASK`` or ``item.type == "task"`` interchangeably.
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
    #: The resolved ID prefix for this item (e.g. ``"TASK"``, ``"INC"``).
    #: Stamped at create/retype time from the active spec (or the reserved map for built-ins).
    #: Excluded from the JSON index (never persisted there) but written to frontmatter for
    #: custom (non-reserved) types so it survives round-trips without a spec in hand.
    #: For reserved built-in types, ``prefix`` is always re-derived from ``RESERVED_PREFIX``
    #: on load — their frontmatter stays byte-identical with no new ``prefix:`` line.
    prefix: str = Field(default="", exclude=True, repr=False)

    model_config = {"use_enum_values": False}

    @field_validator("type", "status", mode="before")
    @classmethod
    def _coerce_str_fields(cls, v: object) -> str:
        """Coerce StrEnum members to plain str so pydantic stores a clean string.

        ``use_enum_values=False`` prevents auto-coercion; callers may pass ``ItemType``
        or ``Status`` members (both StrEnum, which IS a str subclass) which are
        assignment-compatible but must be stored as plain ``str`` to keep YAML
        serialisation and identity checks clean.

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
        it formats from whatever prefix string it was given.

        If ``prefix`` is empty (e.g. a bare ``Item(...)`` constructed in a test without one),
        fall back to the reserved map so built-in items always render correctly even when the
        prefix was not explicitly supplied.
        """
        effective_prefix = self.prefix or _RESERVED_PREFIX.get(self.type, self.type.upper())
        return format_item_id(effective_prefix, self.sequence_id, DISPLAY_ID_PADDING)

    def to_frontmatter_dict(self) -> dict[str, Any]:
        """The mapping written into the markdown file's YAML frontmatter (durable truth).

        For custom (non-reserved) types, ``prefix`` is written as a frontmatter line so the
        correct prefix survives a round-trip without a spec (e.g. ``sq repair``).  Reserved
        built-in types always re-derive their prefix from the reserved map on load, so no
        ``prefix:`` line is written — their files stay byte-identical.
        """
        data: dict[str, Any] = self._core_frontmatter_fields()
        # Write prefix frontmatter ONLY for custom (non-reserved) types.
        # Built-ins re-derive from RESERVED_PREFIX on load; no frontmatter change needed.
        if self.prefix and self.type not in _RESERVED_PREFIX:
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

        ``type`` and ``status`` are stored as plain strings; the reserved-vocab
        validation (against WorkflowSpec) runs at the service load boundary, not here.

        ``prefix`` is read back when present in frontmatter (custom types write it so the
        correct prefix survives a round-trip without a spec).  When absent (legacy files and
        all built-in types), ``prefix`` is left as ``""`` and the store's post-load pass fills
        it via ``prefix_for`` before returning the DB (parallel to ``_propagate_padding``).
        """
        item_type: str = data["type"]
        # Read stored prefix when present; for built-ins it is always absent (re-derived later).
        stored_prefix: str = data.get("prefix") or ""
        # For reserved types, always use the authoritative RESERVED_PREFIX — never trust a
        # stored value (protects against a corrupt/hand-edited frontmatter).
        if item_type in _RESERVED_PREFIX:
            stored_prefix = _RESERVED_PREFIX[item_type]
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
