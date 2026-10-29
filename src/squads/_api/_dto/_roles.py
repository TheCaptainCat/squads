"""The role DTOs: the catalog, the roster listing and its row, a role's show, the requests and
reports of the role verbs, and the developer listing."""

from pydantic import Field

from squads._api._dto._base import DTO
from squads._api._dto._display import Column
from squads._api._dto._items import Comment
from squads._api._dto._roster import NameDisplay, RosterAddress, SeveredRef


def _absent(value: object) -> bool:
    return value is None


class RoleCatalogRequest(DTO):
    """The roles a squad can activate."""


class RoleCatalogRow(DTO):
    """One role of the catalog, or one activated role the catalog does not declare. The default
    holder repeats on every row."""

    slug: str
    full_name: str
    title: str
    is_default: bool
    origin: str
    capabilities: list[str]
    default_role: str | None
    default_role_source: str


class RoleCatalog(DTO):
    """The catalog's rows and the columns its table shows."""

    items: list[RoleCatalogRow]
    columns: list[Column]


class RoleListRequest(DTO):
    """The activated roles."""


class RoleDisplay(NameDisplay):
    """How a role is shown in a listing: its name, and whether its status is live."""

    live: bool


class RoleRow(DTO):
    """An activated role as resolved: its fields, its status and its display."""

    id: str
    slug: str
    full_name: str
    pronouns: str | None
    title: str
    description: str
    is_default: bool
    capabilities: list[str]
    status: str
    origin: str | None = Field(default=None, exclude_if=_absent)
    display: RoleDisplay


class RoleWrite(DTO):
    """A write that reports nothing beside the role it wrote: the role after the
    write, or as it was for a removal."""

    entry: RoleRow


class RoleList(DTO):
    """The activated roles and the columns their table shows."""

    items: list[RoleRow]
    columns: list[Column]


class RoleActivateRequest(DTO):
    """Activate a catalog role, or build one from *from_template* for *tech*."""

    slug: str | None = None
    name: str | None = None
    model: str | None = None
    pronouns: str | None = None
    from_template: str | None = None
    tech: str | None = None


class RoleAddRequest(DTO):
    """Create a role that defines itself; *definition* is the text of a definition file, and
    *source* names it in messages."""

    slug: str
    name: str | None = None
    job_title: str | None = None
    description: str | None = None
    mission: str | None = None
    capabilities: list[str] | None = None
    model: str | None = None
    pronouns: str | None = None
    definition: str | None = None
    source: str | None = None


class RoleUpdateRequest(RosterAddress):
    """Edit a role's name, pronouns or model, or a definition it holds itself; *definition* is
    the text of a definition delta file, and *source* names it in messages."""

    title: str | None = None
    pronouns: str | None = None
    model: str | None = None
    job_title: str | None = None
    description: str | None = None
    mission: str | None = None
    capabilities: list[str] | None = None
    color: str | None = None
    can_spawn: bool | None = None
    definition: str | None = None
    source: str | None = None


class RoleShowDisplay(NameDisplay):
    """How a role's show is displayed beyond its fields: its colour, its body with view tags
    expanded (``None`` for a role not activated) and the hint an empty one gets, whether its
    definition resolves, how to change it, and its discussion."""

    color: str | None
    body: str | None
    empty_hint: str | None
    definition_resolves: bool
    change_hint: str
    discussion: list[Comment]


class RoleShow(DTO):
    """A role, activated or only declared by the catalog, as resolved."""

    slug: str
    id: str | None
    activated: bool
    origin: str | None = Field(default=None, exclude_if=_absent)
    full_name: str
    pronouns: str | None
    title: str
    mission: str
    model: str | None
    is_default: bool
    can_spawn: bool
    capabilities: list[str]
    create_lane: list[str]
    responsibilities: list[str]
    skills: list[str]
    display: RoleShowDisplay


class RoleDefaultMove(DTO):
    """The role now holding the default designation, whether it moved, and the roles it left."""

    entry: RoleRow
    changed: bool
    cleared: list[str]


class RoleStatusMove(DTO):
    """The role after a status move, and the refs a retirement removed."""

    entry: RoleRow
    severed: list[SeveredRef]


class RoleViewChange(DTO):
    """The role after a view tag change: the view, whether the tag changed, and whether it was
    in the body before."""

    entry: RoleRow
    view: str
    changed: bool
    was_present: bool


class DeveloperListRequest(DTO):
    """The live developer roles."""


class DeveloperRow(DTO):
    """A live developer role: its fields, the technology it is for, and its display."""

    id: str
    slug: str
    full_name: str
    pronouns: str | None
    tech: str | None
    display: NameDisplay


class DeveloperList(DTO):
    """The live developer roles, the columns their table shows, and whether the catalog has the
    template a developer is added from."""

    items: list[DeveloperRow]
    columns: list[Column]
    template_available: bool
