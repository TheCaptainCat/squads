"""The skill DTOs: a skill's row and its show, its refs, and the requests and reports of the skill
verbs."""

from pydantic import ConfigDict, Field, JsonValue

from squads._api._dto._base import DTO
from squads._api._dto._items import Comment
from squads._api._dto._roster import RosterAddress, SeveredRef


def _absent(value: object) -> bool:
    return value is None


class SkillRow(DTO):
    """A skill: its fields, whether the person at the keyboard is offered it and whether this
    squad set that, and its file."""

    id: str
    slug: str
    title: str
    status: str
    description: str
    when_to_use: str
    allowed_tools: str
    operator_invocable: bool
    operator_invocable_set: bool
    path: str
    origin: str | None = Field(default=None, exclude_if=_absent)


class SkillWrite(DTO):
    """A write that reports nothing beside the skill it wrote: the skill after the
    write, or as it was for a removal."""

    entry: SkillRow


class SkillShowDisplay(DTO):
    """How a skill's show is displayed beyond its fields: its body with view tags expanded, the
    hint an empty one gets, and its discussion."""

    body: str
    empty_hint: str
    discussion: list[Comment]


class SkillShow(SkillRow):
    """A skill with its stored body, each view's data and its display."""

    body: str
    views: dict[str, JsonValue]
    display: SkillShowDisplay


class SkillAddRequest(DTO):
    """Create a skill named *name*; *parent* is an item id or number."""

    name: str
    description: str = ""
    when_to_use: str = ""
    allowed_tools: str = ""
    parent: str | None = None
    operator_invocable: str | None = None


class SkillUpdateRequest(RosterAddress):
    """Edit a skill's display fields."""

    title: str | None = None
    description: str | None = None
    when_to_use: str | None = None
    operator_invocable: str | None = None


class SkillRefsRequest(RosterAddress):
    """The skill's refs: those it carries (*out*, the default) and those other items carry to it
    (*incoming*)."""

    out: bool = False
    incoming: bool = False


class RefEntry(DTO):
    """One ref: the item at its other end, and its kind."""

    id: str
    kind: str


class SkillRefs(DTO):
    """The refs a skill carries and the refs carried to it, each present when asked for."""

    model_config = ConfigDict(serialize_by_alias=True, validate_by_name=True)

    out: list[RefEntry] | None = Field(default=None, exclude_if=_absent)
    incoming: list[RefEntry] | None = Field(default=None, alias="in", exclude_if=_absent)


class SkillRefRequest(RosterAddress):
    """Add a ref from the skill to *target* (an id or number, ``ID:kind`` setting the kind); an
    empty *kind* takes the default kind."""

    target: str
    kind: str = ""


class SkillRefRemoveRequest(RosterAddress):
    """Remove the skill's ref to *target*."""

    target: str


class SkillRefChange(DTO):
    """The skill after a ref change, the ref's target and, for an added ref, its kind."""

    entry: SkillRow
    target: str
    kind: str | None


class SkillRoleRequest(RosterAddress):
    """Scope the skill to *role*, or unscope it; *role* is a slug, an id or a number."""

    role: str


class SkillRoleLink(DTO):
    """The skill after a scope change, and the role's id."""

    entry: SkillRow
    role: str


class SkillStatusMove(DTO):
    """The skill after a status move, and the refs a retirement removed."""

    entry: SkillRow
    severed: list[SeveredRef]


class SkillViewChange(DTO):
    """The skill after a view tag change: the view, whether the tag changed, and whether it was
    in the body before."""

    entry: SkillRow
    view: str
    changed: bool
    was_present: bool
