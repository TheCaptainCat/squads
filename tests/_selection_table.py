"""The shared fixtures of the selection table: the type rows, the override text that selects a
validator on one of them, and the item builders for the status-banner and title-length input
shapes. Several test modules (service, CLI, meta) drive the same rows through different
surfaces, so the rows live in one place.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from _helpers import create_item
from squads import __version__
from squads._services import _service as service
from squads._workflow import bundled_spec
from squads._workflow._models import WorkflowSpec
from squads._workflow._validator_names import (
    DEFAULT_VALIDATOR_LEVEL,
    effective_validator_names,
    parse_validator_entry,
)

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


def toml_string(text: str) -> str:
    """*text* as a TOML string: a literal (single-quoted) string when it holds a backslash, so a
    regular expression is written as it reads, otherwise a basic string."""
    return f"'{text}'" if "\\" in text else f'"{text}"'


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
        lines += [toml_string(n) for n in names]
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
        # A role's description is set at creation: a later update of it is refused.
        at_creation = row.type == "role" and description is not None
        if row.type == "role":
            # A role that defines itself, so its base resolves and `sq check` stays quiet about it.
            kwargs["description"] = description or "A role."
            kwargs["attributes"] = {"job_title": "role", "mission": "Do the work."}
        item = (await create_item(svc, row.type, f"{row.type} {name}", **kwargs)).item
        if body is not None:
            await svc.set_body(item.id, body)
        if description is not None and not at_creation:
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
    """The ids of one offender and one clean neighbour planted on a row, and the full text the
    offender's finding carries."""

    offender: str
    clean: str
    message: str


@dataclass(frozen=True)
class Member:
    """One opt-in per-item check of the catalog and everything the shared tests need to drive it.

    *fragment* is the text of its message that no other message holds; *shapes* maps a shape
    name to its entries and finding level; *cells* decides every row of :data:`ALL_ROWS`: ``None``
    when the member's plain entry loads there, otherwise the text its load refusal carries;
    *plant* creates an offender and a clean neighbour on a row (under a spec that does not yet
    select the member).
    """

    name: str
    fragment: str
    can_refuse: bool
    shapes: dict[str, Shape]
    cells: dict[str, str | None]
    plant: Callable[[service.Service, TypeRow], Awaitable[Planted]]
    plain: tuple[str, ...] = field(default=())
    extra_rows: tuple[TypeRow, ...] = field(default=())

    def all_rows(self) -> tuple[TypeRow, ...]:
        """The rows the registry decides: the table's, and those that declare what the member
        needs (a row from :attr:`extra_rows`)."""
        return ALL_ROWS + self.extra_rows

    def accepting_rows(self) -> tuple[TypeRow, ...]:
        return tuple(r for r in self.all_rows() if self.cells[r.id] is None)

    def refusing_rows(self) -> tuple[TypeRow, ...]:
        return tuple(r for r in self.all_rows() if self.cells[r.id] is not None)


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
    return Planted(
        over.id,
        at.id,
        f"title is {TITLE_THRESHOLD + 1} chars (threshold: {TITLE_THRESHOLD})"
        " — an item title is a one-line handle; put the detail in the body",
    )


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
)

TYPED_RULE = 'ref_rules = [{ kind = "implements", target = "contract" }]\n'


def with_typed_rule(row: TypeRow) -> TypeRow:
    """*row* whose type also declares a ref rule typing an ``implements`` edge to a contract."""
    return replace(row, id=f"{row.id}+rule", declaration=row.declaration + TYPED_RULE)


#: Rows that already satisfy ``ref_rule_target_typed``'s precondition (the bundled feature) and
#: the rows that need an override to declare it.
_TYPED_ACCEPTING = frozenset({"feature"})
_TYPED_EXTRA_ROWS: tuple[TypeRow, ...] = tuple(
    with_typed_rule(r) for r in WORK_AND_RECORDS_ROWS if r.id not in _TYPED_ACCEPTING
)
TYPED_REFUSAL = "needs a ref_rules entry with a target"


async def _plant_misdirected_and_correct_edge(svc: service.Service, row: TypeRow) -> Planted:
    wrong = (await create_item(svc, "task", "wrong target")).item
    right = (await create_item(svc, "contract", "right target")).item
    offender = (await create_item(svc, row.type, "o", refs=[f"{wrong.id}:implements"])).item
    clean = (await create_item(svc, row.type, "c", refs=[f"{right.id}:implements"])).item
    return Planted(
        offender.id,
        clean.id,
        f"implements edge to {wrong.id} points at a task, but a {row.type}'s implements refs "
        "must point at a contract",
    )


REF_RULE_TARGET_TYPED = Member(
    name="ref_rule_target_typed",
    fragment="refs must point at a",
    can_refuse=True,
    plain=("ref_rule_target_typed",),
    shapes={
        "unselected": Shape((), None),
        "plain": Shape(("ref_rule_target_typed",), "warn"),
        "warn-suffix": Shape(("ref_rule_target_typed@warn",), "warn"),
        "error-suffix": Shape(("ref_rule_target_typed@error",), "error"),
    },
    cells={
        **{
            r.id: (
                ROSTER_REFUSAL
                if r.type in ROSTER_TYPES
                else None
                if r.id in _TYPED_ACCEPTING
                else TYPED_REFUSAL
            )
            for r in ALL_ROWS
        },
        **{r.id: None for r in _TYPED_EXTRA_ROWS},
    },
    plant=_plant_misdirected_and_correct_edge,
    extra_rows=_TYPED_EXTRA_ROWS,
)


async def _plant_unwritten_and_written_body(svc: service.Service, row: TypeRow) -> Planted:
    offender = (await create_item(svc, row.type, "unwritten")).item
    clean = (await create_item(svc, row.type, "written", body=BODY_WRITTEN)).item
    return Planted(
        offender.id,
        clean.id,
        "body is unwritten (still the template scaffold)"
        f' — write it with `sq {row.type} {offender.sequence_id} body -m "..."`',
    )


BODY_WRITTEN_MEMBER = Member(
    name="body_written",
    fragment="still the template scaffold",
    can_refuse=False,
    plain=("body_written",),
    shapes={
        "unselected": Shape((), None),
        "plain": Shape(("body_written",), "warn"),
        "warn-suffix": Shape(("body_written@warn",), "warn"),
        "error-suffix": Shape(("body_written@error",), "error"),
    },
    cells=roster_refused(),
    plant=_plant_unwritten_and_written_body,
)


async def _plant_without_and_with_a_summary(svc: service.Service, row: TypeRow) -> Planted:
    offender = (await create_item(svc, row.type, "no summary")).item
    clean = (await create_item(svc, row.type, "summarised", description="A summary.")).item
    return Planted(
        offender.id,
        clean.id,
        "description is empty — set a summary: `--desc` on create, `update --desc` after",
    )


DESCRIPTION_PRESENT = Member(
    name="description_present",
    fragment="description is empty",
    can_refuse=True,
    plain=("description_present",),
    shapes={
        "unselected": Shape((), None),
        "plain": Shape(("description_present",), "warn"),
        "warn-suffix": Shape(("description_present@warn",), "warn"),
        "error-suffix": Shape(("description_present@error",), "error"),
    },
    cells=roster_refused(),
    plant=_plant_without_and_with_a_summary,
)

NO_LIVE_STATUS = "needs a status of a role declaring live = true"
#: Rows whose bundled lifecycle holds no status of a live role.
_NO_LIVE_ROWS = frozenset({"decision", "guide"})
_LIVE_EXTRA_ROWS: tuple[TypeRow, ...] = (
    TypeRow("decision+live", "decision", declaration='lifecycle = "work"\n'),
    TypeRow("guide+live", "guide", declaration='lifecycle = "work"\n'),
)


async def _plant_unassigned_and_assigned_active_items(
    svc: service.Service, row: TypeRow
) -> Planted:
    status = svc.spec.first_active_status(row.type)
    assert status is not None
    offender = (await create_item(svc, row.type, "unassigned")).item
    await svc.update(offender.id, status=status, force=True)
    clean = (await create_item(svc, row.type, "assigned", assignee="manager")).item
    await svc.update(clean.id, status=status, force=True)
    return Planted(offender.id, clean.id, f"status is {status} but nobody is assigned")


ASSIGNEE_PRESENT = Member(
    name="assignee_present",
    fragment="nobody is assigned",
    can_refuse=True,
    plain=("assignee_present",),
    shapes={
        "unselected": Shape((), None),
        "plain": Shape(("assignee_present",), "warn"),
        "warn-suffix": Shape(("assignee_present@warn",), "warn"),
        "error-suffix": Shape(("assignee_present@error",), "error"),
    },
    cells={
        **{
            r.id: (
                ROSTER_REFUSAL
                if r.type in ROSTER_TYPES
                else NO_LIVE_STATUS
                if r.id in _NO_LIVE_ROWS
                else None
            )
            for r in ALL_ROWS
        },
        **{r.id: None for r in _LIVE_EXTRA_ROWS},
    },
    plant=_plant_unassigned_and_assigned_active_items,
    extra_rows=_LIVE_EXTRA_ROWS,
)


NO_BLOCKED_STATUS = "needs a status of a role declaring blocked = true"
#: Rows whose lifecycle holds no status of a blocked role, in the bundled spec.
_NO_BLOCKED_ROWS = frozenset(
    {
        "review",
        "decision",
        "contract",
        "milestone",
        "guide",
        "declared-records",
        "records-hosting-a-kind",
    }
)


def _with_work_lifecycle(row: TypeRow) -> TypeRow:
    """*row* whose type runs the ``work`` lifecycle, which holds a status of a blocked role."""
    kept = "".join(
        line for line in row.declaration.splitlines(keepends=True) if "lifecycle" not in line
    )
    return replace(row, id=f"{row.id}+blocked", declaration=kept + 'lifecycle = "work"\n')


_BLOCKED_EXTRA_ROWS: tuple[TypeRow, ...] = tuple(
    _with_work_lifecycle(r) for r in ALL_ROWS if r.id in _NO_BLOCKED_ROWS
)


def dependency_kinds_text(spec: WorkflowSpec) -> str:
    """The dependency kinds a ``blocked_has_blocker`` message lists, as it writes them."""
    return ", ".join(sorted(spec.dependency_ref_kinds()))


async def _plant_blocked_without_and_with_an_edge(svc: service.Service, row: TypeRow) -> Planted:
    (status,) = (s for s in svc.spec.machine_for(row.type).states if svc.spec.role_for(s).blocked)
    target = (await create_item(svc, row.type, "blocker")).item
    offender = (await create_item(svc, row.type, "stranded")).item
    await svc.update(offender.id, status=status, force=True)
    clean = (await create_item(svc, row.type, "waiting", refs=[f"{target.id}:depends-on"])).item
    await svc.update(clean.id, status=status, force=True)
    return Planted(
        offender.id,
        clean.id,
        f"status is {status} but no dependency edge is recorded "
        f"(kinds: {dependency_kinds_text(svc.spec)}) "
        "— record a dependency edge (`--ref <id>:<kind>` on create, `ref add` after)",
    )


BLOCKED_HAS_BLOCKER = Member(
    name="blocked_has_blocker",
    fragment="no dependency edge is recorded",
    can_refuse=True,
    plain=("blocked_has_blocker",),
    shapes={
        "unselected": Shape((), None),
        "plain": Shape(("blocked_has_blocker",), "warn"),
        "warn-suffix": Shape(("blocked_has_blocker@warn",), "warn"),
        "error-suffix": Shape(("blocked_has_blocker@error",), "error"),
    },
    cells={
        **{
            r.id: (
                ROSTER_REFUSAL
                if r.type in ROSTER_TYPES
                else NO_BLOCKED_STATUS
                if r.id in _NO_BLOCKED_ROWS
                else None
            )
            for r in ALL_ROWS
        },
        **{r.id: None for r in _BLOCKED_EXTRA_ROWS},
    },
    plant=_plant_blocked_without_and_with_an_edge,
    extra_rows=_BLOCKED_EXTRA_ROWS,
)


async def _plant_settled_without_and_with_a_comment(svc: service.Service, row: TypeRow) -> Planted:
    status = svc.spec.first_settled_status(row.type)
    assert status is not None
    offender = (await create_item(svc, row.type, "silent")).item
    await svc.update(offender.id, status=status, force=True)
    clean = (await create_item(svc, row.type, "discussed")).item
    await svc.update(clean.id, status=status, force=True)
    await svc.comment(clean.id, ["Closed out."], as_slug="manager")
    return Planted(offender.id, clean.id, f"status is {status} but its discussion holds no comment")


SETTLED_REQUIRES_DISCUSSION = Member(
    name="settled_requires_discussion",
    fragment="discussion holds no comment",
    can_refuse=False,
    plain=("settled_requires_discussion",),
    shapes={
        "unselected": Shape((), None),
        "plain": Shape(("settled_requires_discussion",), "warn"),
        "warn-suffix": Shape(("settled_requires_discussion@warn",), "warn"),
        "error-suffix": Shape(("settled_requires_discussion@error",), "error"),
    },
    cells=roster_refused(),
    plant=_plant_settled_without_and_with_a_comment,
)

TRACKER_KEY = r"[A-Z]+-\d+"


async def _plant_a_tracker_key_and_a_clean_title(svc: service.Service, row: TypeRow) -> Planted:
    offender = (await create_item(svc, row.type, "Fix ABC-123 flake")).item
    clean = (await create_item(svc, row.type, "Fix the flake")).item
    return Planted(
        offender.id,
        clean.id,
        f"title holds `ABC-123` (matches the external-id pattern `{TRACKER_KEY}`)"
        " — keep tracker ids out of the title",
    )


EXTERNAL_ID_NOT_IN_TITLE = Member(
    name="external_id_not_in_title",
    fragment="matches the external-id pattern",
    can_refuse=True,
    plain=(f"external_id_not_in_title:{TRACKER_KEY}",),
    shapes={
        "unselected": Shape((), None),
        "plain": Shape((f"external_id_not_in_title:{TRACKER_KEY}",), "warn"),
        "warn-suffix": Shape((f"external_id_not_in_title:{TRACKER_KEY}@warn",), "warn"),
        "error-suffix": Shape((f"external_id_not_in_title:{TRACKER_KEY}@error",), "error"),
    },
    cells=roster_refused(),
    plant=_plant_a_tracker_key_and_a_clean_title,
)

#: Every member this table drives, by name.
MEMBERS: dict[str, Member] = {
    m.name: m
    for m in (
        ITEM_TITLE_MAX,
        REF_RULE_TARGET_TYPED,
        BODY_WRITTEN_MEMBER,
        DESCRIPTION_PRESENT,
        ASSIGNEE_PRESENT,
        BLOCKED_HAS_BLOCKER,
        SETTLED_REQUIRES_DISCUSSION,
        EXTERNAL_ID_NOT_IN_TITLE,
    )
}

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


def two_check_override(*, older_checks: bool = False) -> str:
    """The override text a squad writes to select ``item_title_max:120`` and ``body_written`` on
    every bundled ``work`` and ``records`` type, built from the bundled spec: each table opens
    with the splat of the type's bundled list where it ships one. The roster types get no
    table. With *older_checks* it also selects ``no_status_banner`` on every type, roster ones
    included, and ``subentity_title_max:120`` on the ``work`` types."""
    base = bundled_spec()
    tables: list[str] = []
    for type_name, spec in base.items.items():
        roster = spec.category == "roster"
        if roster and not older_checks:
            continue
        entries: list[str] = []
        if spec.validators:
            entries.append(f'"$(*items.{type_name}.validators)"')
        if not roster:
            entries += ['"item_title_max:120"', '"body_written"']
        if older_checks:
            entries.append('"no_status_banner"')
            if spec.category == "work":
                entries.append('"subentity_title_max:120"')
        if entries:
            tables.append(f"[items.{type_name}]\nvalidators = [{', '.join(entries)}]\n")
    return "\n".join(tables)


def effective_triples(spec: WorkflowSpec, item_type: str) -> set[tuple[str, str | None, str]]:
    """*item_type*'s effective validators as (name, parameter, resolved level)."""
    ts = spec.items[item_type]
    triples: set[tuple[str, str | None, str]] = set()
    for entry in effective_validator_names(ts.category, extra=tuple(ts.validators)):
        bare, param, level = parse_validator_entry(entry)
        triples.add((bare, param, level or DEFAULT_VALIDATOR_LEVEL[bare]))
    return triples
