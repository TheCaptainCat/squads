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

from squads import _clock as clock
from squads._errors import SquadsError
from squads._models._extras import ExtraKey as X
from squads._models._subentity import SubEntity
from squads._util import NonEmpty

REF_SEP = ":"

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


def split_ref(ref: str) -> tuple[str, str]:
    """``"ID"`` → ``(ID, "")``; ``"ID:kind"`` → ``(ID, kind)``. IDs never contain ``:``.

    Structural, not vocabulary: ``_models/`` resolves no ref-kind vocabulary (the acyclic
    import invariant — see ``_workflow``'s own module docstring), so a bare ref decodes to an
    **unspelled** kind (``""``) rather than a resolved name. Which declared kind an unspelled
    ref actually means is the ``role = "default"`` entry of the active spec's ``ref_kinds``
    (``WorkflowSpec.default_ref_kind``) — resolved by a caller where that spec is already in
    hand, never here.
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


def fold_legacy_kinds(refs: list[str], legacy: dict[str, str], *, default_kind: str) -> list[str]:
    """Merge a pre-0.2 ``extra.ref_kinds`` ``{ID: kind}`` map into inline ``ID:kind`` ref
    strings, and normalise every resulting edge against *default_kind* so an edge whose
    resolved kind IS the declared default is always written bare — never spelled out, whether
    it arrived via the legacy map or was already spelled inline (e.g. by a repair run before
    this normalisation existed). *default_kind* is resolved by the caller
    (``WorkflowSpec.default_ref_kind``), where the active spec is in hand; this stays a pure
    mechanical merge over its input, never resolving vocabulary itself.
    """
    result: list[str] = []
    for rid, kind in (split_ref(r) for r in refs):
        resolved = legacy.get(rid, kind)
        result.append(make_ref(rid, "" if resolved == default_kind else resolved))
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

        A non-string ``id`` (a hand-edited ``id: 5``, a merge artifact leaving ``id: [a, b]``)
        raises here rather than being skipped: the id is a durable frontmatter field, and
        silently ignoring a corrupt one would mint an item whose ``prefix`` never resolved and
        whose ``.id`` then rendered as the :data:`UNRESOLVED_PREFIX` sentinel. Raising
        ``ValueError`` from a ``before`` validator makes it a ``ValidationError``, i.e. the
        single failure channel ``from_frontmatter`` reports — not a raw ``AttributeError``
        from ``prefix_from_id``.
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
    def from_frontmatter(cls, data: dict[str, Any], *, path: str, default_kind: str) -> Item:
        """Reconstruct an Item from parsed frontmatter — used by ``sq repair``.

        ``type`` and ``status`` are stored as plain strings; the vocabulary
        validation (against WorkflowSpec) runs at the service load boundary, not here.

        *default_kind* is the active spec's declared ``role = "default"`` ref kind
        (``WorkflowSpec.default_ref_kind()``) — a **required** keyword, not a default
        parameter, so omitting it is a type error rather than a silent regression. It is
        handed straight to :func:`_read_refs`/:func:`fold_legacy_kinds`, which is the one
        point every ``refs`` value passes through on its way into an ``Item``: an edge whose
        kind is the declared default is always folded to the bare wire form here, never left
        (or produced) spelled out. ``_models/`` still resolves no vocabulary itself — this
        parameter is data handed in by a caller that already has the active spec, exactly the
        split :func:`make_ref`/:func:`split_ref` already draw.

        ``prefix`` is derived from the frontmatter's own ``id:`` line (rsplit on the last
        ``-``, e.g. ``"INC-49"`` -> ``"INC"``) by :meth:`Item._derive_prefix_from_id` — the
        ``id`` key below is passed through for that validator to consume; it is not a
        settable field, so it never surfaces on the constructed ``Item`` itself. A stray
        legacy ``prefix:`` key in *data* (written by an older build) is tolerated: it is
        simply never read here, and the derived value always wins if both are present.

        This is the load boundary between parsed-but-untrusted frontmatter and a validated
        ``Item``: whatever is wrong with the file's data, every caller learns the same one
        thing — *this file's data cannot become an* ``Item`` — as a single
        :class:`~squads._errors.SquadsError` naming *path*, never as a raw
        third-party/builtin exception. Callers that scan many files (``sq check``/``sq
        repair``) catch ``SquadsError`` once per file and degrade; a caller loading a single
        known-good file still fails just as hard, only with a clean message instead of a
        traceback.

        Exactly two things can fail here, and both raise ``SquadsError``:

        * a **required key** (:data:`REQUIRED_FRONTMATTER_KEYS`) missing outright — checked by
          name up front, so the message names the key and ``KeyError`` never has to be caught
          at this boundary. Catching it would have swallowed a class of *internal* bug too:
          ``KeyError`` is this codebase's usual symptom of a spec-lookup miss, and reporting
          one as "invalid item data in <path>" would send an operator to hand-edit a file that
          is perfectly fine.
        * a **type-invalid value** anywhere, reported by ``model_validate``. It is the only
          validator: :func:`_frontmatter_payload` is deliberately non-raising and every fold it
          applies passes an unexpected shape through untouched for pydantic to reject. Coercing
          in the payload instead (``list(...)``/``dict(...)``/``fromisoformat``) is what put
          half a dozen ``TypeError``/``ValueError`` raisers *outside* this ``except`` clause.
          Its text is rendered by :func:`_validation_message`, not ``str(exc)`` — see there for
          why the raw dump is not what an operator should be shown.
        """
        missing = [key for key in REQUIRED_FRONTMATTER_KEYS if key not in data]
        if missing:
            keys = ", ".join(repr(key) for key in missing)
            raise SquadsError(f"invalid item data in {path}: missing required frontmatter {keys}")
        try:
            return cls.model_validate(_frontmatter_payload(data, path, default_kind=default_kind))
        except ValidationError as exc:
            raise SquadsError(f"invalid item data in {path}: {_validation_message(exc)}") from exc


def _validation_message(exc: ValidationError) -> str:
    """One clause per rejected frontmatter field, in project vocabulary — the text
    :meth:`Item.from_frontmatter` reports for a type-invalid value.

    ``str(exc)`` is a pydantic *internal* dump and three parts of it are actively unhelpful to
    the operator holding the bad file: a link to ``errors.pydantic.dev`` (naming a library they
    did not install and cannot act on), the ``[type=…, input_value=…, input_type=…]`` machine
    tail, and — for a model-level validator — a truncated ``repr`` of *every other field in the
    file*, which buries the one field that is actually wrong. Making ``model_validate`` the
    single failure channel was the right call; paying this small formatting cost is what keeps
    that from regressing the message, since this is the text every degrade-per-file surface
    (``sq check``, ``sq repair``, and every single-item verb on a corrupt file) prints.

    ``exc.errors()`` gives the three usable parts directly:

    * ``loc`` — the dotted field path (``labels``, ``subentities.0.status``). Empty for a
      model-level ``before`` validator, whose own message already names its field, so no path is
      prefixed and no ``(got …)`` suffix is added: that error's ``input`` is the whole payload,
      and its type (``dict``) would be noise.
    * ``msg`` — pydantic's human sentence, minus the ``Value error, ``/``Assertion failed, ``
      prefix it stamps on messages raised from a custom validator (internal provenance, not
      information about the file).
    * ``input`` — the offending value, reported as its *type name* rather than its ``repr``: the
      type is what makes the message actionable, and a ``repr`` is what produced the truncated
      payload dump in the first place. Appended only when ``type`` names a genuine type mismatch
      (a kind ending in ``_type`` or ``_parsing``, e.g. ``string_type``, ``int_parsing``,
      ``datetime_from_date_parsing``) — what matters is whether the type is the missing
      information, not who raised the error. That one predicate keeps out both of the kinds it
      would otherwise misdescribe: a ``missing`` error's ``input`` is the *enclosing mapping*,
      not the absent field's value (the field has none, that being the fault, so
      ``(got dict)`` would describe a value the operator never wrote), and a
      ``string_too_short``/``string_too_long`` already names the value as a string in its own
      sentence, so repeating the type is a stutter. It also naturally excludes a
      ``value_error``/``assertion_error`` from one of this module's own validators, whose message
      already names what it got (``expected str, got 'int': 5``) — no separate carve-out needed.

    Falls back to ``str(exc)`` for the (unreachable in pydantic v2) empty error list rather than
    reporting an empty message: a degraded message still beats no message.
    """
    parts: list[str] = []
    for err in exc.errors():
        msg = err["msg"].removeprefix("Value error, ").removeprefix("Assertion failed, ")
        loc = ".".join(str(part) for part in err["loc"])
        if loc and err["type"].endswith(("_type", "_parsing")):
            msg = f"{msg} (got {type(err['input']).__name__})"
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts) or str(exc)


#: The frontmatter keys an item cannot be reconstructed without — there is no defensible
#: default for any of them, unlike every other field. Read by name in
#: :meth:`Item.from_frontmatter` before the payload is built; see that docstring for why the
#: boundary reads them explicitly rather than catching ``KeyError``.
REQUIRED_FRONTMATTER_KEYS: tuple[str, ...] = ("type", "sequence_id", "status")


def _frontmatter_payload(data: dict[str, Any], path: str, *, default_kind: str) -> dict[str, Any]:
    """The ``model_validate`` payload for :meth:`Item.from_frontmatter` — **never raises**.

    Every value is either passed straight through or folded by a helper that returns an
    unexpected shape *unchanged*, so ``model_validate`` is the single thing that can reject a
    type-invalid frontmatter field. Nothing here may iterate, subscript, index or parse an
    untrusted value: doing so raises outside the boundary's ``except`` clause, which is
    precisely the escape this replaced.

    Callers must have checked :data:`REQUIRED_FRONTMATTER_KEYS` first — the three ``data[...]``
    subscripts below are the only ones in this function, and they are safe only because of it.
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
        "severity": _read_severity(data),
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
        "extra": _read_extra(data),
    }


def _empty_list_if_unset(value: Any) -> Any:
    """``None`` (absent, or an explicit ``labels:`` with nothing after it) and ``""`` both mean
    "no entries" and become ``[]``; every other value is passed through for ``model_validate``.

    The empty string is here purely to preserve compatibility: the coercion this replaced spelled
    the default ``list(data.get(key, []) or [])``, whose ``or`` swallowed ``""`` too, so a file
    carrying ``labels: ''`` loaded. Tightening that would mean a file that loaded yesterday
    failing today — the wrong direction for a boundary whose job is to keep legacy files
    readable. A *non-empty* string is a different matter and is now rejected rather than silently
    exploded into one entry per character, which is what ``list("abc")`` did.

    That rule is only worth stating if it holds over its whole scope, so **all three** list-valued
    frontmatter keys the old coercions covered go through here — ``labels``, ``refs`` and
    ``subentities`` — with :func:`_empty_dict_if_unset` covering the fourth, ``extra``. Wiring two
    of the four and leaving the others to reject ``""`` is the asymmetry, not a stricter policy:
    the old ``subentities``/``extra`` expressions swallowed ``""`` exactly as these two did.
    """
    return [] if value is None or value == "" else value


def _empty_dict_if_unset(value: Any) -> Any:
    """``None`` and ``""`` both mean "no entries" and become ``{}``; every other value is passed
    through for ``model_validate``. The mapping-valued sibling of :func:`_empty_list_if_unset` —
    same compatibility carve-out, same reason, for the one frontmatter container key that is a
    mapping rather than a list (the replaced coercion spelled ``dict(data.get("extra", {}) or
    {})``, whose ``or`` swallowed ``""``)."""
    return {} if value is None or value == "" else value


def _extra_mapping(data: dict[str, Any]) -> dict[str, Any]:
    """*data*'s ``extra`` block when it really is a mapping, else an empty one.

    The two legacy folds below only read keys *inside* ``extra``; a non-mapping ``extra`` has
    nothing to fold, and is left for ``model_validate`` to reject through the ``extra`` field
    itself (see :func:`_read_extra`) rather than raising a ``TypeError``/``ValueError`` out
    here, outside the load boundary.
    """
    raw = data.get("extra")
    return cast("dict[str, Any]", raw) if isinstance(raw, dict) else {}


def _is_str_list(value: object) -> bool:
    """True only for a list of ``str`` — the one shape :func:`fold_legacy_kinds` can parse."""
    return isinstance(value, list) and all(isinstance(v, str) for v in cast("list[Any]", value))


def _read_refs(data: dict[str, Any], *, default_kind: str) -> Any:
    """Refs as inline ``ID[:kind]`` strings, folding a pre-0.2 ``extra.ref_kinds`` map if
    present, and normalising every ref against *default_kind* either way (see
    :func:`fold_legacy_kinds`) — the one point on this load path where an edge already
    spelled with the declared default (no legacy map involved at all, e.g. a repair run
    before this normalisation existed) is folded back to bare too.

    Returns the raw value untouched when it is not a list of strings (``refs: 5``,
    ``refs: [5]``) — the fold has nothing to do with such a value, and ``model_validate``
    reports it. Empty/unset short-circuits before ``extra`` is even read: there is nothing to
    fold onto, so the legacy lookup would be wasted work on the overwhelmingly common case.
    """
    refs: Any = _empty_list_if_unset(data.get("refs"))
    if not refs or not _is_str_list(refs):
        return refs
    legacy: Any = _extra_mapping(data).get("ref_kinds")
    legacy_map = cast("dict[str, str]", legacy) if isinstance(legacy, dict) else {}
    return fold_legacy_kinds(cast("list[str]", refs), legacy_map, default_kind=default_kind)


def _read_severity(data: dict[str, Any]) -> Any:
    """``severity`` top-level, falling back to the legacy ``extra[X.SEVERITY]`` location (a
    bug file predating this field). Tolerant read only — relocating the value on disk is a
    separate, later one-way migration, not this. A non-string value is passed through for
    ``model_validate`` to reject."""
    top = data.get("severity")
    if top:
        return top
    return _extra_mapping(data).get(X.SEVERITY) or None


def _read_extra(data: dict[str, Any]) -> Any:
    """Item ``extra``, minus the legacy ``ref_kinds`` (now inline on the refs) and the legacy
    ``severity`` key (now read top-level via :func:`_read_severity`).

    Unset (``None`` or ``""``, via :func:`_empty_dict_if_unset`) is an empty mapping. A
    non-mapping ``extra`` (``extra: oops``, ``extra: [1, 2]``) is returned **unchanged** for
    ``model_validate`` to reject — never coerced with ``dict(...)`` (which raises
    ``TypeError``/``ValueError`` out here) and never quietly dropped."""
    raw = _empty_dict_if_unset(data.get("extra"))
    if not isinstance(raw, dict):
        return raw
    extra: dict[str, Any] = dict(cast("dict[str, Any]", raw))
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


def _slug_from_path(path: str, item_id: str | None) -> str:
    """Derive the filename's slug segment (``PREFIX-NNNNNN-<slug>.md`` -> ``<slug>``).

    ``item_id`` (the frontmatter's own ``id:``, when present — it always is for a
    convention-written file) is the shared primitive's input: :func:`prefix_from_id` finds
    the prefix boundary with ``rpartition`` on the LAST hyphen, so a hyphenated prefix (e.g.
    ``"RUN-BOOK"``) is stripped whole via ``removeprefix`` rather than re-derived by counting
    hyphens from the front — the same shape as ``_services._maintenance._scan_records``.
    Falls back to the bare stem (never a corrupt front-hyphen split) when *item_id* is
    missing or the stem doesn't actually start with its prefix (a legacy/hand-edited file).
    """
    name = path.rsplit("/", 1)[-1].removesuffix(".md")
    prefix = prefix_from_id(item_id) if item_id else ""
    if not prefix or not name.startswith(f"{prefix}-"):
        return name
    remainder = name.removeprefix(f"{prefix}-")
    _digit_run, sep, slug = remainder.partition("-")
    return slug if sep else name


def _parse_dt(value: object) -> Any:
    """A frontmatter timestamp, normalised to a tz-aware UTC ``datetime``.

    Absent or ``null`` means "this file predates the field" and defaults to
    :func:`clock.now`, which is what lets a legacy or hand-authored file load at all. Two
    consequences of that default the callers must respect, because it is the one value here
    that is *invented* rather than read:

    - It goes through the injectable clock, never ``datetime.now()`` directly, so a frozen-time
      test or a ``--at`` migration sees the timestamp it forged rather than wall-clock now.
    - It is **not stable across reads** — each load of the same absent-timestamp file invents a
      later value. Anything that compares two loads of the same file (or a load against an
      index-derived item) must therefore exclude a key the file does not actually carry, or it
      compares against a value the file never said: see
      :data:`squads._itemfile.INVENTED_WHEN_ABSENT`, which is what stops such a file from being
      permanently refused as skewed. A write heals it, since every write seam persists the
      whole frontmatter dict.

    A ``datetime`` (PyYAML resolves an unquoted timestamp to one) or an ISO-8601 string
    (including the ``Z`` spelling ``fromisoformat`` needs help with) is normalised here.

    Anything else — including a string that does not parse — is returned **unchanged** for
    ``model_validate`` to accept or reject. An unparseable timestamp must surface as a
    ``ValidationError`` at the single load boundary, not as a raw ``ValueError`` thrown from
    outside it; and a value pydantic *does* accept (it reads a number as a Unix timestamp) is
    at least derived from what the file actually says, rather than a silently invented ``now``.
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
