"""A sub-entity — a user story, subtask, or review finding — tracked on its parent item.

Its **machine state** (status / assignee / mapping / field values) lives here, in the parent
item's frontmatter (single-sourced and validated, like every other item field). The sub-entity's
**prose** — its ``:body`` and ``:discussion`` — stays in the parent's markdown markers; the heading
and the derived ``:head`` badge line are re-rendered from this state.
"""

from typing import Any, cast

from pydantic import BaseModel, field_validator, model_validator

#: The frontmatter keys of a sub-entity entry that the model itself holds. Every other key of an
#: entry is an attribute: a declared field under its code, or an unknown key kept as written.
SUBENTITY_CORE_KEYS: tuple[str, ...] = (
    "local_id",
    "title",
    "status",
    "assignee",
    "maps_to",
    "deferred_to",
)

#: The key the model dumps its attributes under, which is also how the index stores them.
_ATTRIBUTES_KEY = "attributes"


class SubEntity(BaseModel):
    #: Local id within its parent, kind-prefixed (the kind's ``local_prefix`` and a number).
    local_id: str
    title: str = ""
    #: The sub-entity's status: a plain string, spec-vocabulary.
    status: str
    #: Registered agent slug responsible for it (optional).
    assignee: str | None = None
    #: The local id of the sub-entity of the parent's required type that this one maps to.
    maps_to: str | None = None
    #: Only in a status whose role declares ``deferred`` — the formatted id of the item that
    #: carries the work.
    deferred_to: str | None = None
    #: Every other key of the entry: each declared field's badge code under its field code, and any
    #: unknown key as written. The spec says which are declared; storage never splits on it.
    attributes: dict[str, Any] = {}

    model_config = {"use_enum_values": False}

    @model_validator(mode="before")
    @classmethod
    def _gather_attributes(cls, data: Any) -> Any:
        """Gather every non-core key of a frontmatter entry into ``attributes``, dropping a key
        whose value is empty (``""`` or ``null``), which means "not set". A non-mapping input
        (``subentities: [5]``) is returned untouched for pydantic to report, since
        :meth:`Item.from_frontmatter <squads._models._item.Item.from_frontmatter>` passes the raw
        list to ``model_validate``, the single thing allowed to reject a type-invalid sub-entity.
        """
        if not isinstance(data, dict):
            return data
        raw = cast("dict[str, Any]", data)
        out = {key: raw[key] for key in SUBENTITY_CORE_KEYS if key in raw}
        held = raw.get(_ATTRIBUTES_KEY)
        attributes: dict[str, Any] = (
            dict(cast("dict[str, Any]", held)) if isinstance(held, dict) else {}
        )
        for key, value in raw.items():
            if key in SUBENTITY_CORE_KEYS or (key == _ATTRIBUTES_KEY and isinstance(held, dict)):
                continue
            if value is not None and value != "":
                attributes[key] = value
        out[_ATTRIBUTES_KEY] = attributes
        return out

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, v: object) -> str:
        """Coerce StrEnum members to plain str (use_enum_values=False prevents auto-coercion).

        Only ``str`` (and subclasses such as ``StrEnum``) are accepted.  Anything else
        — ``int``, ``None``, etc. — raises ``ValueError`` so Pydantic surfaces a
        ``ValidationError`` rather than silently stringifying the bad value.
        """
        if not isinstance(v, str):
            raise ValueError(f"expected str, got {type(v).__name__!r}: {v!r}")  # noqa: TRY004
        return str(v)

    def badge_value(self, code: str) -> str | None:
        """The badge code stored under field *code*, ``None`` when the entry stores none. No spec
        needed to read — the code is the stored, authoritative value."""
        return self.attributes.get(code) or None

    def set_badge_value(self, code: str, value: str | None) -> None:
        """Generic badge-code setter — the write-side mirror of :meth:`badge_value`."""
        if value is None:
            self.attributes.pop(code, None)
        else:
            self.attributes[code] = value

    def to_frontmatter_dict(self) -> dict[str, Any]:
        """The compact mapping written into the parent's ``subentities`` frontmatter list: the
        core keys that are set, then each attribute flat."""
        data: dict[str, Any] = {
            "local_id": self.local_id,
            "title": self.title,
            "status": self.status,
        }
        if self.assignee:
            data["assignee"] = self.assignee
        if self.maps_to:
            data["maps_to"] = self.maps_to
        if self.deferred_to:
            data["deferred_to"] = self.deferred_to
        for key, value in self.attributes.items():
            data.setdefault(key, value)
        return data
