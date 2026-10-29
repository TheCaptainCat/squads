"""The tracked item — the unit behind every ID."""

from datetime import UTC, datetime
from typing import Any, cast

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_core import to_jsonable_python

from squads import _clock as clock
from squads._errors import SquadsError
from squads._models._attributes import CORE_KEYS, NON_FRONTMATTER_KEYS, ROW_ADDED_KEYS
from squads._models._subentity import SubEntity
from squads._util import NonEmpty

REF_SEP = ":"

#: The default (and minimum) number of zero-padded digits in a *filename* (e.g.
#: ``PREFIX-000007-slug.md``). Changing this requires a ``sq migrate repad`` run.
#: Never used for display — see :data:`DISPLAY_ID_PADDING`.
DEFAULT_ID_PADDING: int = 6

#: Display padding is fixed at 0 (``PREFIX-7``): a constant, never stored or configurable, used by
#: every human-facing surface (frontmatter ``id:``, refs, prose, CLI output). Filenames stay padded
#: at :data:`DEFAULT_ID_PADDING` or the squad's ``SquadsDB.padding``, deliberately; format them with
#: ``format_item_id(prefix, sequence_id, db.padding)``, never from ``item.id``.
DISPLAY_ID_PADDING: int = 0


def format_item_id(prefix: str, sequence_id: int, padding: int = DEFAULT_ID_PADDING) -> str:
    """Format a typed item ID from its prefix, sequence number, and zero-pad width.

    This is the single canonical formatter; all `:0Nd` formatting elsewhere must route through it.
    """
    return f"{prefix}-{sequence_id:0{padding}d}"


#: Obviously-synthetic stand-in for "no real prefix resolved yet", used only by the acyclic
#: formatters and matchers that cannot raise or import ``_workflow``; real resolution
#: (``prefix_for``) raises on an unknown type. A leaked pre-resolution id reads ``UNRESOLVED-42``,
#: loud and test-visible, never a plausible-but-wrong ``type.upper()`` guess (decision would render
#: "DECISION", not "ADR").
UNRESOLVED_PREFIX = "UNRESOLVED"


def effective_prefix(prefix: str) -> str:
    """Return *prefix* if set, else the diagnosable :data:`UNRESOLVED_PREFIX`: the one shared "best
    prefix without resolving vocabulary" helper for ``Item.id``, ``SquadsDB.format_id`` and the
    ref-matching helpers. The fallback branch never runs in production, since ``prefix`` is stamped
    at create/retype and backfilled at every load boundary; it is a guard, never a vocabulary
    source.
    """
    return prefix or UNRESOLVED_PREFIX


def parse_item_token(token: str) -> tuple[int, str | None]:
    """An item token as ``(sequence_number, prefix_or_None)``.

    A bare number (``"35"``, ``"000035"``) gives ``(seq, None)``; a full ID (``"PREFIX-000035"``)
    gives ``(seq, head_upper)``. Raises :class:`SquadsError` on unparseable input.
    """
    t = token.strip()
    if t.isdigit():
        return int(t), None
    head, sep, num = t.rpartition("-")
    if sep and num.isdigit():
        return int(num), head.upper()
    raise SquadsError(
        f"invalid item id {token!r} (use a bare number or a full ID like TYPE-NNNNNN)"
    )


def prefix_from_id(item_id: str) -> str:
    """The type-prefix segment of a formatted id (``"INC-49"`` -> ``"INC"``).

    Pure string parsing (rsplit on the last ``-``) — the id is durable (written to every
    item's frontmatter, and included in the JSON index dump) so the prefix is always
    recoverable from it without resolving vocabulary. Returns ``""`` when *item_id* has no
    hyphen (not a well-formed id).
    """
    prefix, sep, _ = item_id.rpartition("-")
    return prefix if sep else ""


def split_ref(ref: str) -> tuple[str, str]:
    """``"ID"`` -> ``(ID, "")``; ``"ID:kind"`` -> ``(ID, kind)``; IDs never contain ``:``. It is
    structural: ``_models/`` resolves no ref-kind vocabulary (the acyclic import invariant), so a
    bare ref decodes to an unspelled kind (``""``), and a caller holding the spec resolves it to the
    ``role = "default"`` entry (``WorkflowSpec.default_ref_kind``).
    """
    rid, _, kind = ref.partition(REF_SEP)
    return rid, kind


def make_ref(item_id: str, kind: str = "") -> str:
    """A bare ID when *kind* is unspelled (``""``), else ``"ID:kind"``.

    Purely mechanical — it does not know which kind is the declared default, so it cannot
    decide *whether* a given kind should be written bare. That decision (comparing a resolved
    kind against ``WorkflowSpec.default_ref_kind`` and passing ``""`` here when they match) is
    the caller's, made where the active spec is in hand."""
    return item_id if not kind else f"{item_id}{REF_SEP}{kind}"


def ref_id_matches(stored_ref_id: str, prefix: str, seq: int) -> bool:
    """Return True when *stored_ref_id* refers to the same item as *(prefix, seq)*. The comparison
    is width-tolerant, since a stored ref keeps its old zero-pad width after ``sq migrate repad``,
    and prefix-matched, so two items sharing a sequence number (during renumber) do not collide.
    With :func:`split_ref` and :func:`make_ref` it is the shared ref-ID primitive; import it rather
    than duplicating it.
    """
    head, _, digits = stored_ref_id.rpartition("-")
    if not digits.isdigit():
        return False
    return head.upper() == prefix.upper() and int(digits) == seq


def normalise_ref_kinds(refs: list[str], *, default_kind: str) -> list[str]:
    """Normalise every ``ID[:kind]`` ref against *default_kind*, so an edge whose kind IS the
    declared default is always written bare, however the file spelled it. *default_kind* is
    resolved by the caller (``WorkflowSpec.default_ref_kind``); this stays a pure mechanical
    pass over its input, never resolving vocabulary itself.
    """
    result: list[str] = []
    for rid, kind in (split_ref(r) for r in refs):
        result.append(make_ref(rid, "" if kind == default_kind else kind))
    return result


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
    #: Item-level severity (the bundled spec declares it on bug only): the badge code, top-level
    #: like ``priority``.
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
    #: Session id at creation time: best-effort, untrusted, observability-only. squads records
    #: ``SQUADS_SESSION_ID`` from its own invocation environment when present and never mints,
    #: injects or verifies it; absent means no session env was set. Never an authorisation input.
    created_session: str | None = None
    #: Session id at last mutation time.  Same untrusted guarantee as
    #: :attr:`created_session`.  Updated on every frontmatter-touching mutation (status, update,
    #: body, comment, subentity, ref).
    modified_session: str | None = None
    #: Every frontmatter key that is not a core key, declared or not, kept as written. The
    #: spec says which of them are declared; storage never splits on it.
    attributes: dict[str, Any] = {}
    #: Whether ``slug`` is a key of the item's file: always for a roster item, and for any other
    #: item whose file carried it. The file name spells the slug otherwise.
    slug_in_file: bool = False
    #: The resolved ID prefix (e.g. ``"TASK"``) for every type. Set at create/retype from the
    #: active spec, else re-derived from a persisted ``id`` by :meth:`_derive_prefix_from_id`. It is
    #: not written to frontmatter or the index, being recoverable from ``id``, so ``_models`` stays
    #: spec-decoupled.
    prefix: str = Field(default="", exclude=True, repr=False)

    model_config = {"use_enum_values": False}

    @model_validator(mode="before")
    @classmethod
    def _derive_prefix_from_id(cls, data: Any) -> Any:
        """Populate ``prefix`` from a persisted ``id`` string when one is given, on the two read
        paths that carry ``id`` but no ``prefix`` (the JSON index round trip and
        ``from_frontmatter``); explicit constructors that pass ``prefix`` are untouched. The derived
        value always wins over an input ``prefix`` key, so a stray legacy ``prefix:`` line is
        overwritten, never trusted. A non-string ``id`` (``id: 5``, ``id: [a, b]``) raises
        ``ValueError``, surfacing as the single ``ValidationError`` channel ``from_frontmatter``
        reports, since skipping it would mint an item rendering as ``UNRESOLVED``.
        """
        if not isinstance(data, dict):
            return data
        d = cast("dict[str, Any]", data)
        raw_id = d.get("id")
        if raw_id is None:
            return d
        if not isinstance(raw_id, str):
            raise ValueError(f"expected str for `id`, got {type(raw_id).__name__!r}: {raw_id!r}")  # noqa: TRY004
        return {**d, "prefix": prefix_from_id(raw_id)}

    @field_validator("type", "status", mode="before")
    @classmethod
    def _coerce_str_fields(cls, v: object) -> str:
        """Coerce ``str`` subclasses such as ``StrEnum`` members to plain ``str`` so YAML
        serialisation and identity checks stay clean. Anything that is not a ``str`` (``int``,
        ``None``) raises ``ValueError``, surfacing as a ``ValidationError`` rather than being
        stringified.
        """
        if not isinstance(v, str):
            raise ValueError(f"expected str, got {type(v).__name__!r}: {v!r}")  # noqa: TRY004
        return str(v)

    @computed_field
    @property
    def id(self) -> str:
        """The formatted id (``PREFIX-7``), derived from ``prefix`` and ``sequence_id`` at
        :data:`DISPLAY_ID_PADDING` (0) whatever the squad's filename width, and written to
        frontmatter as the durable human id. ``prefix`` is stamped by the service or re-derived from
        a persisted ``id`` by :meth:`_derive_prefix_from_id` (string parsing, never a vocabulary
        lookup); if it is empty the id degrades to :data:`UNRESOLVED_PREFIX`, because the model must
        not import ``_workflow``.
        """
        return format_item_id(effective_prefix(self.prefix), self.sequence_id, DISPLAY_ID_PADDING)

    def badge_value(self, code: str) -> str | None:
        """Generic badge-code getter for any spec-declared field on this item.

        ``priority``/``severity`` are real attributes; any other declared field code
        (e.g. a custom ``impact``) has no dedicated field and is stored as an attribute.
        No spec needed to read — the code is the stored, authoritative value.
        """
        return getattr(self, code, None) if hasattr(self, code) else self.attributes.get(code)

    def attribute(self, key: str, default: Any = None) -> Any:
        """The stored value of attribute *key*, or *default* when the item does not carry it.

        The one accessor internals read attributes through, by an ``AttributeKey`` constant."""
        return self.attributes.get(key, default)

    def set_badge_value(self, code: str, value: str | None) -> None:
        """Generic badge-code setter — the write-side mirror of :meth:`badge_value`."""
        if hasattr(self, code):
            setattr(self, code, value)
        elif value is None:
            self.attributes.pop(code, None)
        else:
            self.attributes[code] = value

    def to_row(self) -> dict[str, Any]:
        """The item as a ``--json`` row: its fields, then each stored attribute flat at the top
        level. An attribute named like a field of the row, or like a key a command adds to it,
        stays in the file and is left out of the row, so that name keeps its one meaning."""
        row = self.model_dump(mode="json", exclude={"attributes", "slug_in_file"})
        flat: dict[str, Any] = self.model_dump(mode="json", include={"attributes"})["attributes"]
        for key, value in flat.items():
            if key not in row and key not in ROW_ADDED_KEYS and key not in NON_FRONTMATTER_KEYS:
                row[key] = value
        return row

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
        data: dict[str, Any] = {
            "id": self.id,
            "sequence_id": self.sequence_id,
            "type": self.type,
            "title": self.title,
        }
        if self.slug_in_file:
            data["slug"] = self.slug
        data["status"] = self.status
        return data

    @classmethod
    def from_frontmatter(cls, data: dict[str, Any], *, path: str, default_kind: str) -> Item:
        """Reconstruct an Item from parsed frontmatter, as ``sq repair`` does. ``type`` and
        ``status`` stay plain strings; vocabulary validation happens at the service load boundary.
        *default_kind* is the active spec's ``role = "default"`` ref kind, a required keyword so
        omitting it is a type error; it goes to :func:`_read_refs`/:func:`normalise_ref_kinds`,
        which fold an edge of the default kind to the bare wire form, so ``_models/`` still resolves
        no vocabulary. ``prefix`` is derived from the frontmatter ``id:`` (``"INC-49"`` ->
        ``"INC"``) and a legacy ``prefix:`` key is never read.

        This is the load boundary: whatever is wrong with the data, callers get one
        :class:`~squads._errors.SquadsError` naming *path*, never a raw third-party exception, so
        scanning callers (``sq check``, ``sq repair``) catch it once per file and degrade. Exactly
        two things fail. A missing **required key** (:data:`REQUIRED_FRONTMATTER_KEYS`) is checked
        by name up front, because catching ``KeyError`` would also swallow an internal spec-lookup
        bug and send an operator to edit a good file. A **type-invalid value** is rejected by
        ``model_validate`` alone, since :func:`_frontmatter_payload` never raises (coercing there
        would raise ``TypeError``/``ValueError`` outside the ``except``); its text comes from
        :func:`_validation_message`.
        """
        return cls._build(data, path=path, default_kind=default_kind)

    @classmethod
    def from_frontmatter_verbatim(cls, data: dict[str, Any], *, path: str) -> Item:
        """Like :meth:`from_frontmatter`, but resolves no vocabulary: ``refs`` are kept exactly
        as the file spells them, with no default ref kind folded in. For a reader that must not
        depend on any spec."""
        return cls._build(data, path=path, default_kind=None)

    @classmethod
    def _build(cls, data: dict[str, Any], *, path: str, default_kind: str | None) -> Item:
        missing = [key for key in REQUIRED_FRONTMATTER_KEYS if key not in data]
        if missing:
            keys = ", ".join(repr(key) for key in missing)
            raise SquadsError(f"invalid item data in {path}: missing required frontmatter {keys}")
        try:
            return cls.model_validate(_frontmatter_payload(data, path, default_kind=default_kind))
        except ValidationError as exc:
            raise SquadsError(f"invalid item data in {path}: {_validation_message(exc)}") from exc


def _validation_message(exc: ValidationError) -> str:
    """One clause per rejected frontmatter field, in project vocabulary: the text
    :meth:`Item.from_frontmatter` reports, in place of ``str(exc)``, whose pydantic internals (a
    docs link, the ``[type=…]`` tail, a truncated ``repr`` of every other field) bury the one bad
    field. From ``exc.errors()`` it uses ``loc`` (the dotted path, empty for a model-level validator
    that names its own field), ``msg`` (minus the ``Value error, ``/``Assertion failed, `` prefix)
    and ``input`` as a type name, appended only for a genuine type mismatch (kind ending ``_type``
    or ``_parsing``), which excludes ``missing`` (whose input is the enclosing mapping),
    string-length errors and this module's own validators. It falls back to ``str(exc)`` on an empty
    error list.
    """
    parts: list[str] = []
    for err in exc.errors():
        msg = err["msg"].removeprefix("Value error, ").removeprefix("Assertion failed, ")
        loc = ".".join(str(part) for part in err["loc"])
        if loc and err["type"].endswith(("_type", "_parsing")):
            msg = f"{msg} (got {type(err['input']).__name__})"
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts) or str(exc)


#: The frontmatter keys an item cannot be reconstructed without, having no defensible default;
#: :meth:`Item.from_frontmatter` reads them by name before building the payload rather than catching
#: ``KeyError``.
REQUIRED_FRONTMATTER_KEYS: tuple[str, ...] = ("type", "sequence_id", "status")


#: The frontmatter keys whose absent-value default is invented at load (:func:`_parse_dt` falls back
#: to ``clock.now()``), so two loads of the same file differ. A skew comparison must leave them out
#: when the file has no value, or it would report a divergence on every read that ``sq repair``
#: cannot clear (repair never rewrites markdown); the first write persists the whole
#: ``to_frontmatter_dict()`` and heals it. A timestamp the file does carry is compared normally, and
#: an unparseable one still fails the load boundary.
INVENTED_WHEN_ABSENT: frozenset[str] = frozenset({"created_at", "updated_at"})


def _frontmatter_payload(
    data: dict[str, Any], path: str, *, default_kind: str | None
) -> dict[str, Any]:
    """The ``model_validate`` payload for :meth:`Item.from_frontmatter`, which never raises: each
    value passes through or is folded by a helper that returns an unexpected shape unchanged, so
    ``model_validate`` is the one thing that rejects a type-invalid field. Nothing here may iterate,
    subscript or parse an untrusted value, as that would raise outside the boundary's ``except``.
    Callers must check :data:`REQUIRED_FRONTMATTER_KEYS` first, which is what makes the three
    ``data[...]`` subscripts safe.
    """
    raw_id = data.get("id")
    return {
        # Judged by _derive_prefix_from_id, which rejects a non-string id as a ValidationError.
        "id": raw_id,
        "sequence_id": data["sequence_id"],
        "type": data["type"],
        "title": data.get("title", ""),
        # _slug_from_path does string surgery, so it only ever sees a genuine str id.
        "slug": data.get("slug")
        or _slug_from_path(path, raw_id if isinstance(raw_id, str) else None),
        "status": data["status"],
        "description": data.get("description", ""),
        "parent": data.get("parent"),
        "author": data.get("author"),
        "assignee": data.get("assignee"),
        "priority": data.get("priority") or None,
        "severity": data.get("severity") or None,
        "labels": _empty_list_if_unset(data.get("labels")),
        "refs": _read_refs(data, default_kind=default_kind),
        # Otherwise handed over raw: SubEntity's own validators fold the loose spellings, and
        # pydantic reports anything that is not a list of mappings.
        "subentities": _empty_list_if_unset(data.get("subentities")),
        "path": path,
        "created_at": _parse_dt(data.get("created_at")),
        "updated_at": _parse_dt(data.get("updated_at")),
        # Session fields are optional — absent from legacy files; None == unset.
        "created_session": data.get("created_session") or None,
        "modified_session": data.get("modified_session") or None,
        "slug_in_file": "slug" in data,
        "attributes": {
            key: _json_form(value) for key, value in data.items() if key not in CORE_KEYS
        },
    }


def _json_form(value: Any) -> Any:
    """*value* as the index stores it: a YAML date or timestamp as its ISO string, a mapping key
    as a string. Applying it on load makes the file side of the skew comparison and the index
    agree on one shape for a value YAML types on its own."""
    try:
        return to_jsonable_python(value)
    except (TypeError, ValueError):  # fmt: skip
        return value


def _empty_list_if_unset(value: Any) -> Any:
    """``None`` (absent, or a bare ``labels:``) and ``""`` become ``[]``; every other value passes
    through for ``model_validate``. The empty string is kept so a legacy file
    with ``labels: ''`` keeps loading, while a non-empty string is rejected rather than exploded
    into characters. The rule covers ``labels``,
    ``refs`` and ``subentities``.
    """
    return [] if value is None or value == "" else value


def _is_str_list(value: object) -> bool:
    """True only for a list of ``str`` — the one shape :func:`normalise_ref_kinds` can parse."""
    return isinstance(value, list) and all(isinstance(v, str) for v in cast("list[Any]", value))


def _read_refs(data: dict[str, Any], *, default_kind: str | None) -> Any:
    """Refs as inline ``ID[:kind]`` strings, normalised against *default_kind* (see
    :func:`normalise_ref_kinds`) so an edge of the declared default kind is always bare.

    Returns the raw value untouched when it is not a list of strings (``refs: 5``,
    ``refs: [5]``) — the normalisation has nothing to do with such a value, and ``model_validate``
    reports it. With no *default_kind* the refs are kept exactly as the file spells them.
    """
    refs: Any = _empty_list_if_unset(data.get("refs"))
    if default_kind is None or not refs or not _is_str_list(refs):
        return refs
    return normalise_ref_kinds(cast("list[str]", refs), default_kind=default_kind)


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
    for key, value in item.attributes.items():
        data.setdefault(key, value)


def slug_from_stem(stem: str, prefix: str) -> str:
    """Derive a filename stem's slug segment (``PREFIX-NNNNNN-<slug>`` -> ``<slug>``) from an
    already-resolved *prefix*, the primitive shared by :func:`_slug_from_path` (prefix from the
    frontmatter ``id``) and ``_services._maintenance._stem_slug`` (prefix from the type folder, read
    before frontmatter parses; see :func:`_slug_from_path` for which wins). It falls back to the
    bare stem when *prefix* is empty or the stem does not start with it.
    """
    if not prefix or not stem.startswith(f"{prefix}-"):
        return stem
    remainder = stem.removeprefix(f"{prefix}-")
    _digit_run, sep, slug = remainder.partition("-")
    return slug if sep else stem


def _slug_from_path(path: str, item_id: str | None) -> str:
    """Derive the filename's slug segment (``PREFIX-NNNNNN-<slug>.md`` -> ``<slug>``) using the
    frontmatter ``id:`` as input: :func:`prefix_from_id` splits on the last hyphen, so a hyphenated
    prefix (``"RUN-BOOK"``) is stripped whole by ``removeprefix``. It falls back to the bare stem
    when *item_id* is missing or the stem does not start with its prefix. On a hand-renamed skill
    file this prefix is the frontmatter's declared identity, while ``_stem_slug`` runs before
    frontmatter can be read and uses the type folder; the two agree on every file ``sq`` writes.
    """
    name = path.rsplit("/", 1)[-1].removesuffix(".md")
    prefix = prefix_from_id(item_id) if item_id else ""
    return slug_from_stem(name, prefix)


def _parse_dt(value: object) -> Any:
    """A frontmatter timestamp normalised to a tz-aware UTC ``datetime``: a ``datetime`` (PyYAML's
    reading of an unquoted timestamp) or an ISO-8601 string, ``Z`` included. Absent or ``null``
    defaults to :func:`clock.now` (never ``datetime.now()``, so frozen-time tests and ``--at`` see
    the forged value), which is invented rather than read and not stable across loads, so
    comparisons exclude it (:data:`INVENTED_WHEN_ABSENT`) and a write heals it. Anything else,
    including an unparseable string, is returned unchanged for ``model_validate`` to accept or
    reject, so it surfaces as a ``ValidationError`` at the boundary and a value pydantic accepts is
    at least what the file says.
    """
    if value is None:
        return clock.now()
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    if not isinstance(value, datetime):
        return value
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
