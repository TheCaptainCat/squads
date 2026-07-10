"""A sub-entity — a user story, subtask, or review finding — tracked on its parent item.

Its **machine state** (status / assignee / severity / mapped story) lives here, in the parent
item's frontmatter (single-sourced and validated, like every other item field). The sub-entity's
**prose** — its ``:body`` and ``:discussion`` — stays in the parent's markdown markers; the heading
and the derived ``:head`` badge line are re-rendered from this state.
"""

from typing import Any

from pydantic import BaseModel, field_validator


class SubEntity(BaseModel):
    #: Local id within its parent, kind-prefixed: ``US<n>`` story / ``ST<n>`` subtask /
    #: ``F<n>`` finding.
    local_id: str
    title: str = ""
    #: The sub-entity's status: a plain string, spec-vocabulary.
    status: str
    #: Registered agent slug responsible for it (optional).
    assignee: str | None = None
    #: Findings only — the finding's severity badge code (spec-declared ``severity`` field).
    severity: str | None = None
    #: Subtasks only — the mapped user story's local id (e.g. ``US<n>``).
    story: str | None = None
    #: Any other spec-declared field's badge code, keyed by field code (e.g. a custom
    #: ``urgency``). ``severity`` keeps its own typed slot above for byte-identical
    #: round-trip; this is the generic overflow, the direct analog of ``Item.extra``.
    extra: dict[str, Any] = {}

    model_config = {"use_enum_values": False}

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
        """Generic badge-code getter for any spec-declared field on this sub-entity.

        ``severity`` is a real attribute; any other declared field code (e.g. a custom
        ``urgency``) has no dedicated attribute and is stored in ``extra`` — the direct
        analog of :meth:`Item.badge_value <squads._models._item.Item.badge_value>`. No
        spec needed to read — the code is the stored, authoritative value.
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
        """The compact mapping written into the parent's ``subentities`` frontmatter list."""
        data: dict[str, Any] = {
            "local_id": self.local_id,
            "title": self.title,
            "status": self.status,
        }
        if self.assignee:
            data["assignee"] = self.assignee
        if self.severity:
            data["severity"] = self.severity
        if self.story:
            data["story"] = self.story
        if self.extra:
            data["extra"] = self.extra
        return data

    @classmethod
    def from_frontmatter(cls, data: dict[str, Any]) -> SubEntity:
        return cls(
            local_id=data["local_id"],
            title=data.get("title", ""),
            status=data["status"],
            assignee=data.get("assignee"),
            severity=data.get("severity") or None,
            story=data.get("story"),
            extra=dict(data.get("extra", {}) or {}),
        )
