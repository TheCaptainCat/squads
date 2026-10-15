"""The shared fixtures of the selection table: the type rows, the override text that selects a
validator on one of them, and the item builders for the status-banner and title-length input
shapes. Several test modules (service, CLI, meta) drive the same rows through different
surfaces, so the rows live in one place.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _helpers import create_item
from squads import __version__
from squads._services import _service as service

#: Bundled types whose spec ships its own ``validators`` list: a selection on them must open
#: with the splat of it, or the bundled entry is silently lost.
SHIPPED_LIST_TYPES = frozenset({"epic", "skill"})

BANNER_FRAGMENT = "status/lifecycle banner"
SUBENTITY_TITLE_FRAGMENT = "a sub-entity title is a one-line handle"
SUBENTITY_BODY_FRAGMENT = "still the placeholder stub"
ITEM_TITLE_FRAGMENT = "an item title is a one-line handle"

ROSTER_TYPES = ("role", "skill", "operator")

#: What the load refusal of a policy check on a roster type says.
ROSTER_REFUSAL = "cannot apply to a roster type"

BANNER_MESSAGE_BODY = "body opens with a status/lifecycle banner"
BANNER_MESSAGE_DESCRIPTION = "description opens with a status/lifecycle banner"


@dataclass(frozen=True)
class TypeRow:
    """One row of the selection table.

    *declaration* holds the lines that declare the type (or move its category) inside its
    ``[items.<type>]`` table; *keep* is the entries every spec of the row carries so the type
    loads at all; *kind* is the sub-entity kind it hosts; *slug* is the stem a roster item needs
    at create; *body_authorable* is False for a type whose body is rendered, not authored.
    """

    id: str
    type: str
    declaration: str = ""
    keep: tuple[str, ...] = ()
    kind: str | None = None
    slug: str | None = None
    body_authorable: bool = True


BUNDLED_ROWS: tuple[TypeRow, ...] = (
    TypeRow("feature", "feature", kind="story"),
    TypeRow("task", "task", kind="subtask"),
    TypeRow("review", "review", kind="finding"),
    TypeRow("epic", "epic"),
    TypeRow("bug", "bug"),
    TypeRow("decision", "decision"),
    TypeRow("guide", "guide"),
    TypeRow("contract", "contract"),
    TypeRow("milestone", "milestone"),
    TypeRow("role", "role", slug="role-x", body_authorable=False),
    TypeRow("skill", "skill", slug="skill-x"),
    TypeRow("operator", "operator", slug="op-x"),
)

DECLARED_ROWS: tuple[TypeRow, ...] = (
    TypeRow(
        "declared-work",
        "incident",
        declaration=(
            'prefix = "INC"\nfolder = "incidents"\nlifecycle = "work"\n'
            'aliases = ["inc"]\ncategory = "work"\norder = 66\n'
        ),
    ),
    TypeRow(
        "declared-records",
        "policy",
        declaration=(
            'prefix = "POL"\nfolder = "policies"\nlifecycle = "contract"\n'
            'aliases = ["pol"]\ncategory = "records"\norder = 65\n'
        ),
    ),
    TypeRow(
        "records-hosting-a-kind",
        "review",
        declaration='category = "records"\n',
        keep=("subentity_status_valid",),
        kind="finding",
    ),
)

ALL_ROWS: tuple[TypeRow, ...] = BUNDLED_ROWS + DECLARED_ROWS

#: A body or description the banner detector reports, with the message it earns.
BANNER_OFFENDERS: dict[str, tuple[str | None, str | None, str]] = {
    "body-status-colon": ("STATUS: Proposed", None, BANNER_MESSAGE_BODY),
    "body-bold-status": ("**Status:** Draft", None, BANNER_MESSAGE_BODY),
    "body-h2-status": ("## Status\n\nStill drafting.", None, BANNER_MESSAGE_BODY),
    "body-h3-status": ("### Status\n\nStill drafting.", None, BANNER_MESSAGE_BODY),
    "description-status-colon": (None, "STATUS: Draft", BANNER_MESSAGE_DESCRIPTION),
}

#: Inputs the detector must leave alone.
BANNER_CLEAN: dict[str, tuple[str | None, str | None]] = {
    "mid-body-mention": ("The work moves toward STATUS: Done once the schema lands.", None),
    "topical-mention": ("Describes the Draft to Ready transition this builds.", None),
    "no-body": (None, None),
}


def override_toml(
    row: TypeRow,
    entries: tuple[str, ...],
    *,
    others: dict[str, tuple[str, ...]] | None = None,
    splat: bool = True,
) -> str:
    """The override text declaring *row* and selecting *entries* on its type, plus a selection
    on each type of *others* (a bare ``[items.<t>]`` table opening with the shipped-list splat
    where the type ships one, unless *splat* is False and the list replaces the bundled one)."""
    tables: list[str] = []
    selections: dict[str, tuple[str, ...]] = {row.type: row.keep + entries, **(others or {})}
    for type_name, names in selections.items():
        header = row.declaration if type_name == row.type else ""
        shipped = splat and type_name in SHIPPED_LIST_TYPES
        lines = [f'"$(*items.{type_name}.validators)"'] if shipped else []
        lines += [f'"{n}"' for n in names]
        if not lines and not header:
            continue
        body = f"validators = [{', '.join(lines)}]\n" if lines else ""
        tables.append(f"[items.{type_name}]\n{header}{body}")
    return "\n".join(tables)


def write_override(squad_dir: Path, toml_text: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{toml_text}", encoding="utf-8"
    )


def service_with(squad_dir: Path, toml_text: str) -> service.Service:
    """A service whose workflow spec is the bundled one merged with *toml_text*."""
    write_override(squad_dir, toml_text)
    return service.open_service()


async def plant_banner_items(svc: service.Service, row: TypeRow) -> dict[str, str]:
    """One item of *row*'s type per banner input shape (offenders and clean), by shape name.
    A type whose body is rendered carries only the description shapes."""
    planted: dict[str, str] = {}

    async def make(name: str, body: str | None, description: str | None) -> None:
        kwargs: dict[str, Any] = {}
        if row.slug is not None:
            kwargs["slug"] = f"{row.slug}-{name}"
        item = (await create_item(svc, row.type, f"{row.type} {name}", **kwargs)).item
        if body is not None:
            await svc.set_body(item.id, body)
        if description is not None:
            await svc.update(item.id, description=description)
        planted[name] = item.id

    for name, (body, description, _message) in BANNER_OFFENDERS.items():
        if body is not None and not row.body_authorable:
            continue
        await make(name, body, description)
    for name, (body, description) in BANNER_CLEAN.items():
        if body is not None and not row.body_authorable:
            continue
        await make(name, body, description)
    return planted


def banner_findings(issues: list[Any], planted: dict[str, str]) -> dict[str, tuple[str, str]]:
    """The banner findings among *issues*, keyed by the planted shape name, as (level, text)."""
    by_id = {item_id: name for name, item_id in planted.items()}
    found: dict[str, tuple[str, str]] = {}
    for issue in issues:
        if "status/lifecycle banner" in issue.message and issue.item in by_id:
            found[by_id[issue.item]] = (issue.level, issue.message)
    return found


#: Rows that host a sub-entity kind, and the three bundled ones among them.
HOSTING_ROWS: tuple[TypeRow, ...] = tuple(r for r in ALL_ROWS if r.kind is not None)
BUNDLED_HOSTING_ROWS: tuple[TypeRow, ...] = tuple(r for r in BUNDLED_ROWS if r.kind is not None)

#: Title-length selection shape -> (validators entries, threshold the type runs or None,
#: level of the finding).
TITLE_SHAPES: dict[str, tuple[tuple[str, ...], int | None, str | None]] = {
    "unselected": ((), None, None),
    "bare": (("subentity_title_max",), 120, "warn"),
    "number": (("subentity_title_max:80",), 80, "warn"),
    "warn-suffix": (("subentity_title_max@warn",), 120, "warn"),
    "number-and-error": (("subentity_title_max:80@error",), 80, "error"),
}

BODY_WRITTEN = "Written."


@dataclass(frozen=True)
class Shape:
    """One selection shape of a member: the entries a type names, and the level its findings
    carry (``None`` when the type does not run the check)."""

    entries: tuple[str, ...]
    level: str | None


@dataclass(frozen=True)
class Planted:
    """The ids of one offender and one clean neighbour planted on a row."""

    offender: str
    clean: str


@dataclass(frozen=True)
class Member:
    """One opt-in per-item check of the catalog and everything the shared tests need to drive it.

    *fragment* is the text of its message that no other message holds; *shapes* maps a shape
    name to its entries and finding level; *cells* decides every row of :data:`ALL_ROWS`: ``None``
    when the member's plain entry loads there, otherwise the text its load refusal carries;
    *plant* creates an offender and a clean neighbour on a row (under a spec that does not yet
    select the member); *message* is the full text one planted offender earns.
    """

    name: str
    fragment: str
    can_refuse: bool
    shapes: dict[str, Shape]
    cells: dict[str, str | None]
    plant: Callable[[service.Service, TypeRow], Awaitable[Planted]]
    message: str
    plain: tuple[str, ...] = field(default=())

    def accepting_rows(self) -> tuple[TypeRow, ...]:
        return tuple(r for r in ALL_ROWS if self.cells[r.id] is None)

    def refusing_rows(self) -> tuple[TypeRow, ...]:
        return tuple(r for r in ALL_ROWS if self.cells[r.id] is not None)


def roster_refused(accepting: set[str] | frozenset[str] | None = None) -> dict[str, str | None]:
    """The cell table of a member that applies to every non-roster row: the three roster rows
    are refused, every other row loads. *accepting* narrows the loading rows."""
    cells: dict[str, str | None] = {}
    for row in ALL_ROWS:
        if row.type in ROSTER_TYPES:
            cells[row.id] = ROSTER_REFUSAL
        else:
            cells[row.id] = None if accepting is None or row.id in accepting else ""
    return cells


#: Every row but the roster ones: the rows a policy check applies to.
WORK_AND_RECORDS_ROWS: tuple[TypeRow, ...] = tuple(
    r for r in ALL_ROWS if r.type not in ROSTER_TYPES
)

TITLE_THRESHOLD = 80


async def _plant_over_and_at_title(svc: service.Service, row: TypeRow) -> Planted:
    over = (await create_item(svc, row.type, "x" * (TITLE_THRESHOLD + 1))).item
    at = (await create_item(svc, row.type, "x" * TITLE_THRESHOLD)).item
    return Planted(over.id, at.id)


ITEM_TITLE_MAX = Member(
    name="item_title_max",
    fragment=ITEM_TITLE_FRAGMENT,
    can_refuse=True,
    plain=(f"item_title_max:{TITLE_THRESHOLD}",),
    shapes={
        "unselected": Shape((), None),
        "plain": Shape((f"item_title_max:{TITLE_THRESHOLD}",), "warn"),
        "warn-suffix": Shape((f"item_title_max:{TITLE_THRESHOLD}@warn",), "warn"),
        "error-suffix": Shape((f"item_title_max:{TITLE_THRESHOLD}@error",), "error"),
    },
    cells=roster_refused(),
    plant=_plant_over_and_at_title,
    message=(
        f"advisory: title is {TITLE_THRESHOLD + 1} chars (threshold: {TITLE_THRESHOLD})"
        " — an item title is a one-line handle; put the detail in the body"
    ),
)

#: Every member this table drives, by name.
MEMBERS: dict[str, Member] = {m.name: m for m in (ITEM_TITLE_MAX,)}

#: The fixed message fragments of every check that is selected rather than always on.
ALL_FRAGMENTS: dict[str, str] = {
    "no_status_banner": BANNER_FRAGMENT,
    "subentity_title_max": SUBENTITY_TITLE_FRAGMENT,
    "subentity_body_written": SUBENTITY_BODY_FRAGMENT,
    **{m.name: m.fragment for m in MEMBERS.values()},
}


def member_findings(issues: list[Any], member: Member) -> list[tuple[str, str, str]]:
    """The findings among *issues* that carry *member*'s fragment, as (level, item, message)."""
    return [(i.level, i.item, i.message) for i in issues if member.fragment in i.message]
