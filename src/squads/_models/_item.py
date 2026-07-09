"""The tracked item — the unit behind every ID."""

from datetime import UTC, datetime
from typing import Any, cast

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from squads import _clock as clock
from squads._models._extras import ExtraKey as X
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


def effective_prefix(prefix: str) -> str:
    """Return *prefix* if set, else the diagnosable :data:`UNRESOLVED_PREFIX` sentinel.

    The one shared "best prefix we have right now, without resolving real vocabulary" helper —
    every acyclic formatter/matcher that used to fall back to ``item_type.upper()`` (Item.id,
    ``SquadsDB.format_id``, the ref-matching helpers in ``_services``/``_cli``) routes through
    this instead.

    In production this branch should never actually run: ``prefix`` is spec-resolved at
    create/retype time and backfilled at every load boundary before ``.id``/matching is
    consumed. It exists purely as a never-should-happen guard, never a vocabulary source.
    """
    return prefix or UNRESOLVED_PREFIX


def prefix_from_id(item_id: str) -> str:
    """The type-prefix segment of a formatted id (``"INC-49"`` -> ``"INC"``).

    Pure string parsing (rsplit on the last ``-``) — the id is durable (written to every
    item's frontmatter, and included in the JSON index dump) so the prefix is always
    recoverable from it without resolving vocabulary. Returns ``""`` when *item_id* has no
    hyphen (not a well-formed id).
    """
    prefix, sep, _ = item_id.rpartition("-")
    return prefix if sep else ""


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
    #: The item's status: a plain string. The loaded ``WorkflowSpec`` is the sole vocabulary
    #: authority; validated against it at the service load boundary, same as ``type``.
    status: str
    description: str = ""
    parent: str | None = None
    #: The registered agent (role slug) who authored the item.
    author: str | None = None
    assignee: str | None = None
    #: Optional importance, independent of status. Unset means no priority assigned. Stores
    #: only the badge code (spec-declared ``priority`` collection); label/emoji resolve at
    #: render time.
    priority: str | None = None
    #: Item-level severity (today: bug only) — the badge code, top-level like ``priority``. A
    #: legacy file predating this field may still carry it in ``extra[X.SEVERITY]``;
    #: :meth:`from_frontmatter` backfills it from there when this key is absent (never the reverse).
    severity: str | None = None
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
    #: (built-in or custom). Set at create/retype time from the active spec (explicit
    #: constructors pass it directly); otherwise re-derived from a persisted ``id`` by
    #: :meth:`_derive_prefix_from_id` — see that validator for the two read paths it covers.
    #: Not itself written to frontmatter or the JSON index; recoverable from ``id`` alone,
    #: so ``_models`` stays spec-decoupled and never imports ``_workflow``.
    prefix: str = Field(default="", exclude=True, repr=False)

    model_config = {"use_enum_values": False}

    @model_validator(mode="before")
    @classmethod
    def _derive_prefix_from_id(cls, data: Any) -> Any:
        """Populate ``prefix`` from a persisted ``id`` string, when one is given.

        Covers both read paths that carry a durable ``id`` but no ``prefix``: the JSON
        index round-trip (``id`` is a computed field, included in the dump but not itself
        assignable, so it reappears here as plain input data) and ``from_frontmatter``
        (which passes the frontmatter's own ``id:`` line through under this same key).
        Explicit constructors that resolve ``prefix`` directly at creation time (and never
        pass ``id``) are left untouched.

        Always wins over the input's own ``prefix`` key when ``id`` is present — this is
        what lets a stray legacy ``prefix:`` frontmatter line be tolerated rather than
        trusted: it is silently overwritten with the value re-derived from ``id``, never
        read.
        """
        if not isinstance(data, dict):
            return data
        d = cast("dict[str, Any]", data)
        raw_id = d.get("id")
        if isinstance(raw_id, str):
            d = {**d, "prefix": prefix_from_id(raw_id)}
        return d

    @field_validator("type", "status", mode="before")
    @classmethod
    def _coerce_str_fields(cls, v: object) -> str:
        """Coerce StrEnum members to plain str so pydantic stores a clean string.

        ``use_enum_values=False`` prevents auto-coercion; a caller may still pass a StrEnum
        member (assignment-compatible, since StrEnum IS a str subclass) which must be stored
        as plain ``str`` to keep YAML serialisation and identity checks clean.

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

        ``prefix`` is either stamped at create/retype time by the service (which holds the
        spec) or, on any read path that hands the model a persisted ``id`` (the JSON index,
        ``from_frontmatter``), re-derived from it by :meth:`_derive_prefix_from_id` — pure
        string parsing, never a vocabulary lookup.

        If ``prefix`` is empty (e.g. a bare ``Item(...)`` constructed in a test with neither
        an ``id`` nor a ``prefix``), the id degrades to the :data:`UNRESOLVED_PREFIX`
        sentinel rather than crashing or guessing — the model itself never derives real
        vocabulary (that would require importing ``_workflow``, breaking the acyclic
        invariant).
        """
        return format_item_id(effective_prefix(self.prefix), self.sequence_id, DISPLAY_ID_PADDING)

    def badge_value(self, code: str) -> str | None:
        """Generic badge-code getter for any spec-declared field on this item.

        ``priority``/``severity`` are real attributes; any other declared field code
        (e.g. a custom ``impact``) has no dedicated attribute and is stored in ``extra``.
        No spec needed to read — the code is the stored, authoritative value.
        """
        return getattr(self, code, None) if hasattr(self, code) else self.extra.get(code)

    def set_badge_value(self, code: str, value: str | None) -> None:
        """Generic badge-code setter — the write-side mirror of :meth:`badge_value`."""
        if hasattr(self, code):
            setattr(self, code, value)
        elif value is None:
            self.extra.pop(code, None)
        else:
            self.extra[code] = value

    def to_frontmatter_dict(self) -> dict[str, Any]:
        """The mapping written into the markdown file's YAML frontmatter (durable truth).

        No ``prefix`` key is written — the prefix is recoverable from ``id`` alone (see
        :func:`prefix_from_id`), so this is the only place needed to round-trip through
        ``from_frontmatter`` with no spec in hand (e.g. ``sq repair``).
        """
        data: dict[str, Any] = self._core_frontmatter_fields()
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

        ``prefix`` is derived from the frontmatter's own ``id:`` line (rsplit on the last
        ``-``, e.g. ``"INC-49"`` -> ``"INC"``) by :meth:`Item._derive_prefix_from_id` — the
        ``id`` key below is passed through for that validator to consume; it is not a
        settable field, so it never surfaces on the constructed ``Item`` itself. A stray
        legacy ``prefix:`` key in *data* (written by an older build) is tolerated: it is
        simply never read here, and the derived value always wins if both are present.
        """
        item_type: str = data["type"]
        return cls.model_validate(
            {
                "id": data.get("id"),
                "sequence_id": data["sequence_id"],
                "type": item_type,
                "title": data.get("title", ""),
                "slug": data.get("slug") or _slug_from_path(path),
                "status": data["status"],
                "description": data.get("description", ""),
                "parent": data.get("parent"),
                "author": data.get("author"),
                "assignee": data.get("assignee"),
                "priority": data.get("priority") or None,
                "severity": _read_severity(data),
                "labels": list(data.get("labels", []) or []),
                "refs": _read_refs(data),
                "subentities": [
                    SubEntity.from_frontmatter(s)
                    for s in cast("list[dict[str, Any]]", data.get("subentities") or [])
                ],
                "path": path,
                "created_at": _parse_dt(data.get("created_at")),
                "updated_at": _parse_dt(data.get("updated_at")),
                # Session fields are optional — absent from legacy files; None == unset.
                "created_session": data.get("created_session") or None,
                "modified_session": data.get("modified_session") or None,
                "extra": _read_extra(data),
            }
        )


def _read_refs(data: dict[str, Any]) -> list[str]:
    """Refs as inline ``ID[:kind]`` strings, folding a pre-2 ``extra.ref_kinds`` map if present."""
    refs: list[str] = list(data.get("refs", []) or [])
    legacy: Any = dict(data.get("extra", {}) or {}).get("ref_kinds")
    if isinstance(legacy, dict):
        return fold_legacy_kinds(refs, cast("dict[str, str]", legacy))
    return refs


def _read_severity(data: dict[str, Any]) -> str | None:
    """``severity`` top-level, falling back to the legacy ``extra[X.SEVERITY]`` location (a
    bug file predating this field). Tolerant read only — relocating the value on disk is a
    separate, later one-way migration, not this."""
    top = data.get("severity")
    if top:
        return top
    legacy = dict(data.get("extra", {}) or {}).get(X.SEVERITY)
    return legacy or None


def _read_extra(data: dict[str, Any]) -> dict[str, Any]:
    """Item ``extra``, minus the legacy ``ref_kinds`` (now inline on the refs) and the legacy
    ``severity`` key (now read top-level via :func:`_read_severity`)."""
    extra: dict[str, Any] = dict(data.get("extra", {}) or {})
    extra.pop("ref_kinds", None)
    extra.pop(X.SEVERITY, None)
    return extra


def _add_badge_fields(data: dict[str, Any], item: Item) -> None:
    """The two top-level badge-code fields (priority/severity) — split out of
    :func:`_add_optional_frontmatter_fields` to keep it below the C901 ceiling."""
    if item.priority:
        data["priority"] = item.priority
    if item.severity:
        data["severity"] = item.severity


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
    _add_badge_fields(data, item)
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
