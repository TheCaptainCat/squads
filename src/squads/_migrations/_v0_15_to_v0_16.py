"""Schema 0.15 → 0.16 runner: the release's one migration step, built as a list of contributions.

A **contribution** has a name, a planning function, a ``MANUAL`` section and a summary clause. The
planning function is read-only: it takes the run's context and the index transaction's ``db`` and
returns a :class:`Planned` value holding the failures it found, the report lines for a run that
completes, the notes that follow a failure count, and (optionally) a writing closure over its own
plan. :func:`run_contributions` plans every contribution first, refuses with one error listing
every failure when any contribution reported one, and only then runs the writers in order, so a
refused run writes nothing.

A later contributor appends one :class:`Contribution` to :data:`CONTRIBUTIONS` and one row to the
runner's test table; nothing else in this module, the registry or the CLI changes.

The comment-header contribution rewrites each comment header from ``- [<ts>] <name>:`` to
``- [<ts>] `<slug>` <name>:``. Every legacy name is resolved to the slug of the roster entry that
holds it across the whole corpus before any file is written. The patterns below are frozen copies
of the live header grammar and the grammar it replaces: a migration reads what it reads at this
schema, whatever the live parser later becomes.

The flat-frontmatter contribution lifts the nested ``extra`` block of every item file to
top-level keys, folds the operator's ``full_name`` into its ``title``, gives every roster file a
top-level ``slug``. Its per-file transform,
:func:`flatten_frontmatter`, is a pure function over a frontmatter mapping, so a contribution
that follows plans against the shape this one writes.

Invoked by ``sq migrate up`` via ``_migrations._registry`` — never run directly (this module is
private).
"""

import re
from collections import Counter, defaultdict
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, NamedTuple, cast

from squads import _aio
from squads._errors import RoleNotFoundError, SquadsError
from squads._index._store import IndexStore
from squads._interactions._skills import role_origin, skill_origin
from squads._itemfile import read_frontmatter, write_text
from squads._migrations._context import MigrationContext
from squads._migrations._outcome import MigrationOutcome
from squads._models import _markers as markers
from squads._models._attributes import AttributeKey
from squads._models._index import SquadsDB
from squads._models._item import Item, slug_from_stem
from squads._models._participants import roster_slug_breaches
from squads._roles._models import DEV_TEMPLATE_NAME
from squads._roles._resolver import resolve_role_with_base, role_defined_by_file
from squads._sections import (
    find_markers,
    has_section,
    replace_frontmatter,
    split_lines,
    with_discussion_region,
)
from squads._workflow._models import ROSTER_OPERATOR, ROSTER_ROLE, ROSTER_SKILL, ROSTER_TYPES

# --------------------------------------------------------------------------- contributions


@dataclass(frozen=True)
class Planned:
    """What one contribution's planning pass found: nothing here has been written."""

    failures: tuple[str, ...] = ()
    report: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    write: Callable[[MigrationContext], Awaitable[int]] | None = None


type Planner = Callable[[MigrationContext, SquadsDB], Awaitable[Planned]]


@dataclass(frozen=True)
class Contribution:
    """One part of the step: ``plan`` reads, ``Planned.write`` (if any) writes."""

    name: str
    plan: Planner
    manual: str
    summary: str


async def run_contributions(
    contributions: Sequence[Contribution], ctx: MigrationContext, db: SquadsDB
) -> MigrationOutcome:
    """Plan every contribution, refuse on any failure, then run the writers in order."""
    planned = [(c, await c.plan(ctx, db)) for c in contributions]
    failed = [(c, p) for c, p in planned if p.failures]
    if failed:
        raise SquadsError(_failure_message(failed))
    count = 0
    report: list[str] = []
    for _contribution, plan in planned:
        if plan.write is not None:
            count += await plan.write(ctx)
        report.extend(plan.report)
    return MigrationOutcome(count=count, report=tuple(report))


def _failure_message(failed: Sequence[tuple[Contribution, Planned]]) -> str:
    lines = [line for _c, plan in failed for line in plan.failures]
    out = [*lines, f"{len(lines)} problem(s) found."]
    for _c, plan in failed:
        out.extend(plan.notes)
    out.append("This step wrote nothing and the schema stamp is unchanged.")
    return "\n".join(out)


# --------------------------------------------------------------------------- headers

_LEGACY_HEADER_RE = re.compile(r"^- \[([^\]]+)\] (.+?):$")
_HEADER_RE = re.compile(
    r"^- \[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\] `([a-z0-9][a-z0-9-]*)` (.+):$"
)
_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_END_SUFFIX = ":end"

_ANONYMOUS = ("Operator", "operator")
_SYSTEM = ("squads", "squads")


class _Event(NamedTuple):
    """One thing the scan saw in a discussion region."""

    line_no: int  # 1-based
    kind: str  # "legacy", "migrated", "bad-timestamp", or a region problem (see _REGION_FAILURES)
    detail: str  # the bracket text, the name, or the region tag
    timestamp: str = ""


def compose_header(timestamp: str, slug: str, name: str) -> str:
    """The new-grammar header line for a legacy header's timestamp and name."""
    return f"- [{timestamp}] `{slug}` {name}:"


def _is_discussion_tag(tag: str) -> bool:
    """Whether *tag* (as ``find_markers`` returns it) opens a discussion region: the item's own
    or a sub-entity's, never a view placement tag."""
    bare = tag.removeprefix(markers.PREFIX)
    if bare.startswith(f"{markers.VIEW}:"):
        return False
    return bare == markers.DISCUSSION or bare.endswith(f":{markers.DISCUSSION}")


def _marker_problem(line: str, canonical: str, tags: Sequence[str]) -> str | None:
    """Why a region marker line is unusable, or ``None``: ``malformed-marker`` for a marker alone
    on its line but not spelled as sq writes it, ``shared-line`` for a marker beside other text."""
    text = line.strip()
    if text == canonical:
        return None
    alone = len(tags) == 1 and text.startswith("<!--") and text.endswith("-->")
    return "malformed-marker" if alone else "shared-line"


def _scan(lines: Sequence[str]) -> list[_Event]:
    """Every header-shaped column-0 line inside a discussion region, plus any region left open
    and any region marker that shares its line with other text.

    ``lines`` carry no line terminator. Lines outside a region, and any other line inside one,
    are not looked at.
    """
    events: list[_Event] = []
    current: str | None = None
    opened_at = 0
    for index, line in enumerate(lines):
        line_no = index + 1
        tags = find_markers(line)
        if current is None:
            opened = next((t for t in tags if _is_discussion_tag(t)), None)
            if opened is None:
                continue
            problem = _marker_problem(line, f"<!-- {opened} -->", tags)
            if problem:
                events.append(_Event(line_no, problem, opened.removeprefix(markers.PREFIX)))
            if f"{opened}{_END_SUFFIX}" not in tags:
                current, opened_at = opened, line_no
            continue
        if f"{current}{_END_SUFFIX}" in tags:
            problem = _marker_problem(line, f"<!-- {current}{_END_SUFFIX} -->", tags)
            if problem:
                events.append(_Event(line_no, problem, current.removeprefix(markers.PREFIX)))
            current = None
            continue
        if _HEADER_RE.match(line):
            events.append(_Event(line_no, "migrated", ""))
            continue
        legacy = _LEGACY_HEADER_RE.match(line)
        if legacy is None:
            continue
        if _TIMESTAMP_RE.fullmatch(legacy.group(1)):
            events.append(_Event(line_no, "legacy", legacy.group(2), legacy.group(1)))
        else:
            events.append(_Event(line_no, "bad-timestamp", legacy.group(1)))
    if current is not None:
        events.append(_Event(opened_at, "unclosed", current.removeprefix(markers.PREFIX)))
    return events


# --------------------------------------------------------------------------- the roster


@dataclass(frozen=True)
class _Roster:
    slugs_by_name: dict[str, set[str]]
    breaches: tuple[str, ...]


async def _read_roster(ctx: MigrationContext, db: SquadsDB) -> _Roster:
    """Every role and operator, live or retired, read from its own file's frontmatter."""
    by_name: dict[str, set[str]] = defaultdict(set)
    roles: list[Item] = []
    operators: list[Item] = []
    for name, slug in (_ANONYMOUS, _SYSTEM):
        by_name[name].add(slug)
    items = sorted(
        (it for it in db.items.values() if it.type in (ROSTER_ROLE, ROSTER_OPERATOR)),
        key=lambda it: it.sequence_id,
    )
    for it in items:
        text = (await _aio.read_bytes(ctx.paths.abspath(it.path))).decode("utf-8")
        data = read_frontmatter(text=text, source=it.path)
        extra: dict[str, Any] = data.get("extra") or {}
        slug = str(extra.get("slug") or data.get("slug") or it.slug)
        stored = it.model_copy(update={"slug": slug})
        if it.type == ROSTER_OPERATOR:
            name = str(extra.get("full_name") or slug)
            operators.append(stored)
        else:
            name = str(data.get("title") or it.title)
            roles.append(stored)
        by_name[name].add(slug)
    breaches = tuple(
        f"{b.item.path}: {b.text('also held by')}" for b in roster_slug_breaches(roles, operators)
    )
    return _Roster(dict(by_name), breaches)


# --------------------------------------------------------------------------- planning


@dataclass
class _Tally:
    failures: list[str] = field(default_factory=list[str])
    headers_by_name: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    files_by_name: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    legacy: int = 0
    migrated: int = 0
    files: list[str] = field(default_factory=list[str])


_REGION_FAILURES: tuple[tuple[str, str], ...] = (
    ("unclosed", "discussion region `{}` is not closed"),
    (
        "malformed-marker",
        "the marker of discussion region `{}` is not a well-formed sq marker "
        "(one space on each side of the tag)",
    ),
    ("shared-line", "the marker of discussion region `{}` shares its line with text"),
)


def _failure_for(path: str, event: _Event, roster: _Roster) -> str | None:
    """The printable failure for one scanned event, or ``None`` when it resolves."""
    where = f"{path}:{event.line_no}"
    if event.kind == "bad-timestamp":
        return f"{where}: {event.detail!r} is not a timestamp sq writes"
    for kind, text in _REGION_FAILURES:
        if event.kind == kind:
            return f"{where}: {text.format(event.detail)}"
    slugs = roster.slugs_by_name.get(event.detail, set())
    if not slugs:
        return f"{where}: {event.detail!r} matches no roster entry"
    if len(slugs) > 1:
        return f"{where}: {event.detail!r} matches {len(slugs)} entries: {', '.join(sorted(slugs))}"
    return None


async def _plan_headers(ctx: MigrationContext, db: SquadsDB) -> Planned:
    roster = await _read_roster(ctx, db)
    tally = _Tally()
    for it in sorted(db.items.values(), key=lambda it: it.sequence_id):
        await _tally_file(ctx, it, roster, tally)
    resolved = {n: next(iter(s)) for n, s in roster.slugs_by_name.items() if len(s) == 1}
    report = (
        f"{tally.legacy} comment header(s) rewritten in {len(tally.files)} file(s); "
        f"{tally.migrated} already carried a slug",
    )
    failures = (*roster.breaches, *tally.failures)
    if failures:
        return Planned(failures=failures, notes=_failure_notes(tally), report=report)

    async def write(wctx: MigrationContext) -> int:
        return await _write_headers(wctx, tally.files, resolved)

    return Planned(report=report, write=write)


async def _tally_file(ctx: MigrationContext, it: Item, roster: _Roster, tally: _Tally) -> None:
    text = (await _aio.read_bytes(ctx.paths.abspath(it.path))).decode("utf-8")
    holds_legacy = False
    for event in _scan(split_lines(text)):
        if event.kind == "migrated":
            tally.migrated += 1
            continue
        if event.kind == "legacy":
            tally.legacy += 1
            holds_legacy = True
        failure = _failure_for(it.path, event, roster)
        if failure is not None:
            tally.failures.append(failure)
            if event.kind == "legacy":
                tally.headers_by_name[event.detail] += 1
                tally.files_by_name[event.detail].add(it.path)
    if holds_legacy:
        tally.files.append(it.path)


def _failure_notes(tally: _Tally) -> tuple[str, ...]:
    """The lines after the failure count: one per distinct failing name, then the remedy."""
    notes = [
        f"  {name!r}: {count} header(s) in {len(tally.files_by_name[name])} file(s)"
        for name, count in sorted(tally.headers_by_name.items())
    ]
    remedy = (
        "Correct the roster, or correct the line by hand, then run `sq migrate up` again; "
        "`sq migrate chlog v0.15.0..v0.16.0` has the steps."
    )
    return (*notes, remedy)


# --------------------------------------------------------------------------- writing


async def _write_headers(ctx: MigrationContext, paths: Sequence[str], slugs: dict[str, str]) -> int:
    """Rewrite each planned file's legacy header lines; return the number of files changed."""
    changed = 0
    for rel in paths:
        path = ctx.paths.abspath(rel)
        text = (await _aio.read_bytes(path)).decode("utf-8")
        kept = split_lines(text, keepends=True)
        bare = [_strip_eol(ln) for ln in kept]
        rewritten = list(kept)
        touched = False
        for event in _scan(bare):
            if event.kind != "legacy":
                continue
            index = event.line_no - 1
            header = compose_header(event.timestamp, slugs[event.detail], event.detail)
            rewritten[index] = header + kept[index][len(bare[index]) :]
            touched = True
        if touched:
            await write_text(path, "".join(rewritten))
            changed += 1
    return changed


def _strip_eol(line: str) -> str:
    """``line`` without the one line terminator :func:`split_lines` ended it with."""
    return line.rstrip("\r\n")


# --------------------------------------------------------------------------- flat frontmatter

#: The core keys in the order the item writer emits them. A flattened file lists these first, in
#: this order, then every other top-level key in the file's own order, then the keys lifted from
#: ``extra``, so loading and writing a migrated file gives the same bytes.
_CORE_ORDER: tuple[str, ...] = (
    "id",
    "sequence_id",
    "type",
    "title",
    "slug",
    "status",
    "parent",
    "author",
    "assignee",
    "priority",
    "severity",
    "refs",
    "labels",
    "description",
    "subentities",
    "created_at",
    "updated_at",
    "created_session",
    "modified_session",
)

#: The keys an earlier release mirrored onto a role from its resolved definition, which no writer
#: produces any more. They are dropped, not lifted.
_RETIRED_ROLE_KEYS: frozenset[str] = frozenset(
    {
        "title",
        "mission",
        "responsibilities",
        "agreements",
        "color",
        "can_spawn",
        "description",
        "full_name",
        "skills",
    }
)

#: Names that are not attributes of an item: the nested block itself and the two model fields
#: that are not frontmatter. An `extra` key of such a name cannot be lifted as it stands.
_UNLIFTABLE: frozenset[str] = frozenset({"extra", "path", "prefix"})


@dataclass(frozen=True)
class FlatFrontmatter:
    """One file's frontmatter after the flattening, and what the transform did to get there.

    ``changed`` is false when the file needs nothing, in which case ``data`` is the input as it
    stands. ``problems`` are the reasons the file cannot be flattened; ``data`` is then the
    input unchanged.
    """

    data: dict[str, Any]
    changed: bool = False
    lifted: tuple[str, ...] = ()
    description_dropped: bool = False
    description_differed: bool = False
    path_removed: bool = False
    retitled: bool = False
    problems: tuple[str, ...] = ()


def _fold_ref_kinds(refs: list[str], legacy: dict[str, str], default_kind: str) -> list[str]:
    """*refs* with each id's kind from the pre-0.2 ``{id: kind}`` map written inline as
    ``ID:kind``; the squad's default kind is written bare."""
    out: list[str] = []
    for ref in refs:
        rid, _, kind = ref.partition(":")
        resolved = legacy.get(rid, kind)
        out.append(rid if not resolved or resolved == default_kind else f"{rid}:{resolved}")
    return out


@dataclass
class _Lift:
    """The working state of one file's flattening."""

    item_type: Any
    top: dict[str, Any]
    lifted: dict[str, Any] = field(default_factory=dict[str, Any])
    problems: list[str] = field(default_factory=list[str])
    description_dropped: bool = False
    description_differed: bool = False
    retitled: bool = False

    def lift_slug(self, stored: Any, file_slug: str, source: str) -> None:
        roster = self.item_type in ROSTER_TYPES
        if roster and stored is not None and stored != file_slug:
            self.problems.append(
                f"{source}: extra.slug {stored!r} differs from the file name's slug {file_slug!r}"
            )
        if not roster and stored is not None and stored != file_slug:
            self.problems.append(
                f"{source}: extra.slug {stored!r} differs from the file name's slug {file_slug!r}"
            )
        if "slug" not in self.top:
            if roster or stored is not None:
                self.top["slug"] = stored if stored is not None else file_slug
        elif stored is not None and self.top["slug"] != stored:
            self.problems.append(
                f"{source}: extra.slug and the top-level slug hold different values"
            )

    def fold_legacy(self, legacy_kinds: Any, legacy_severity: Any, default_kind: str) -> None:
        refs = self.top.get("refs")
        if isinstance(legacy_kinds, dict) and isinstance(refs, list):
            self.top["refs"] = _fold_ref_kinds(
                [str(r) for r in cast("list[Any]", refs)],
                cast("dict[str, str]", legacy_kinds),
                default_kind,
            )
        if legacy_severity and not self.top.get("severity"):
            self.top["severity"] = legacy_severity

    def lift(self, key: str, value: Any, source: str) -> None:
        """Place one `extra` key: lifted as it stands, folded into a core key, or dropped."""
        if self.item_type == ROSTER_ROLE and key in _RETIRED_ROLE_KEYS:
            return
        if self.item_type == ROSTER_OPERATOR and key == "full_name":
            if isinstance(value, str) and value.strip() and value != self.top.get("title"):
                self.top["title"] = value
                self.retitled = True
            return
        if self.item_type == ROSTER_SKILL and key == "description":
            keep = (
                not self.top.get("description")
                and isinstance(value, str)
                and value != self.top.get("title")
            )
            if keep:
                self.top["description"] = value
            else:
                self.description_dropped = True
                kept = self.top.get("description") or self.top.get("title")
                self.description_differed = isinstance(value, str) and value != kept
            return
        if key in self.top:
            if self.top[key] != value:
                self.problems.append(
                    f"{source}: extra.{key} and the top-level {key} hold different values"
                )
            return
        if key in _CORE_ORDER or key in _UNLIFTABLE:
            self.problems.append(
                f"{source}: extra.{key} would become the item's own {key!r}; "
                "move it out of `extra` by hand"
            )
            return
        self.lifted[key] = value


def flatten_frontmatter(
    data: dict[str, Any], *, file_slug: str, default_kind: str, source: str
) -> FlatFrontmatter:
    """The flat form of the frontmatter mapping *data* of one item file.

    Each ``extra`` key is lifted to the top level with its value unchanged, except ``ref_kinds``
    (folded into inline refs), ``severity`` (the top-level value wins), ``slug`` (the file's slug,
    written for every roster file), a skill's ``description`` (dropped when the top-level one is
    non-empty, else kept unless it equals the title), an operator's ``full_name`` (dropped, and
    ``title`` takes its value when they differ) and the keys listed in ``_RETIRED_ROLE_KEYS`` on
    a role (dropped). The top-level ``path`` a skill file carries is removed, and ``extra`` with
    it. *file_slug* is the slug the file name spells; *source* names the file in a problem.
    Never raises: a file that cannot be flattened comes back with ``problems`` and its input.
    """
    item_type = data.get("type")
    raw_extra = data.get("extra")
    path_present = item_type == ROSTER_SKILL and "path" in data
    needs_slug = item_type in ROSTER_TYPES and "slug" not in data
    if "extra" not in data and not path_present and not needs_slug:
        return FlatFrontmatter(data)
    if raw_extra is not None and not isinstance(raw_extra, dict):
        return FlatFrontmatter(data, problems=(f"{source}: extra is not a mapping",))
    extra = dict(cast("dict[str, Any]", raw_extra or {}))

    work = _Lift(
        item_type,
        {k: v for k, v in data.items() if k != "extra" and not (path_present and k == "path")},
    )
    work.lift_slug(extra.pop("slug", None), file_slug, source)
    work.fold_legacy(extra.pop("ref_kinds", None), extra.pop("severity", None), default_kind)
    for key, value in extra.items():
        work.lift(key, value, source)
    if work.problems:
        return FlatFrontmatter(data, problems=tuple(work.problems))
    return FlatFrontmatter(
        _in_writer_order({**work.top, **work.lifted}),
        changed=True,
        lifted=tuple(work.lifted),
        description_dropped=work.description_dropped,
        description_differed=work.description_differed,
        path_removed=path_present,
        retitled=work.retitled,
    )


def _in_writer_order(data: dict[str, Any]) -> dict[str, Any]:
    """*data* with the core keys first, in the item writer's order, then the rest as they stand."""
    core = {k: data[k] for k in _CORE_ORDER if k in data}
    return {**core, **{k: v for k, v in data.items() if k not in core}}


@dataclass
class _FlatTally:
    files: list[tuple[str, FlatFrontmatter]] = field(
        default_factory=list[tuple[str, FlatFrontmatter]]
    )
    slugs: dict[str, str] = field(default_factory=dict[str, str])
    failures: list[str] = field(default_factory=list[str])


def _file_slug(ctx: MigrationContext, item: Item) -> str:
    """The slug the item's file name spells, after the prefix the squad's spec declares."""
    declared = ctx.spec.items.get(item.type)
    prefix = declared.prefix if declared is not None else item.prefix
    return slug_from_stem(ctx.paths.abspath(item.path).stem, prefix)


async def _plan_flat_frontmatter(ctx: MigrationContext, db: SquadsDB) -> Planned:
    tally = _FlatTally()
    default_kind = ctx.spec.default_ref_kind()
    for it in sorted(db.items.values(), key=lambda i: i.sequence_id):
        text = (await _aio.read_bytes(ctx.paths.abspath(it.path))).decode("utf-8")
        data = read_frontmatter(text=text, source=it.path)
        flat = flatten_frontmatter(
            data,
            file_slug=_file_slug(ctx, it),
            default_kind=default_kind,
            source=it.path,
        )
        tally.failures.extend(flat.problems)
        if flat.changed:
            tally.files.append((it.path, flat))
            tally.slugs[it.path] = _file_slug(ctx, it)
    if tally.failures:
        return Planned(failures=tuple(tally.failures), notes=(_FLAT_REMEDY,))

    async def write(wctx: MigrationContext) -> int:
        return await _write_flat(wctx, tally, default_kind)

    return Planned(report=_flat_report(tally), write=write if tally.files else None)


_FLAT_REMEDY = (
    "Correct each file by hand (a stray `extra:` that is not a mapping, a key that exists both "
    "under `extra:` and at the top level with different values, a role or operator whose "
    "`extra.slug` differs from its file name, an `extra` key that is a core key, `extra`, "
    "`path` or `prefix`), then run `sq migrate up` again; "
    "`sq migrate chlog v0.15.0..v0.16.0` has the steps."
)


def _flat_report(tally: _FlatTally) -> tuple[str, ...]:
    flats = [flat for _path, flat in tally.files]
    per_key = Counter(key for flat in flats for key in flat.lifted)
    keys = ", ".join(f"{k} {n}" for k, n in sorted(per_key.items())) or "none"
    lines = [
        f"{len(flats)} file(s) flattened; {sum(per_key.values())} key(s) lifted ({keys}); "
        f"{sum(f.description_dropped for f in flats)} skill description(s) dropped; "
        f"{sum(f.path_removed for f in flats)} `path:` key(s) removed",
        f"{sum(f.retitled for f in flats)} operator title(s) set from the stored full name",
        *(f"  {path}" for path, flat in tally.files if flat.retitled),
        f"{sum(f.description_differed for f in flats)} dropped skill description(s) differed "
        "from the one kept",
        *(f"  {path}" for path, flat in tally.files if flat.description_differed),
    ]
    return tuple(lines)


def _origin_of(ctx: MigrationContext, flat: dict[str, Any], file_slug: str) -> str | None:
    """The origin a role or skill file with flat frontmatter *flat* is to be stamped with, or
    ``None`` for another type or a file that already stores one (whatever its value)."""
    item_type = flat.get("type")
    if item_type not in (ROSTER_ROLE, ROSTER_SKILL) or AttributeKey.ORIGIN in flat:
        return None
    slug = str(flat.get("slug") or file_slug)
    if item_type == ROSTER_SKILL:
        return skill_origin(slug, ctx.spec)
    return role_origin(slug, template=DEV_TEMPLATE_NAME if flat.get(AttributeKey.TECH) else None)


def _skill_text(text: str, item_type: object) -> str:
    """*text* as a skill file is left by this step: with its discussion region. Every writer
    that rewrites a skill file ends with this, so the file is written once."""
    return with_discussion_region(text) if item_type == ROSTER_SKILL else text


async def _write_flat(ctx: MigrationContext, tally: _FlatTally, default_kind: str) -> int:
    """Rewrite each planned file's frontmatter, re-read at write time so it composes with the
    comment-header writer on the same file. A role or skill file is stamped with its origin in
    this same write, so no file is written twice."""
    for rel, _flat in tally.files:
        path = ctx.paths.abspath(rel)
        text = (await _aio.read_bytes(path)).decode("utf-8")
        data = read_frontmatter(text=text, source=rel)
        flat = flatten_frontmatter(
            data, file_slug=tally.slugs[rel], default_kind=default_kind, source=rel
        )
        data = dict(flat.data)
        if (origin := _origin_of(ctx, data, tally.slugs[rel])) is not None:
            data[AttributeKey.ORIGIN] = origin
        await write_text(
            path, _skill_text(replace_frontmatter(text, data, source=rel), data.get("type"))
        )
    return len(tally.files)


# --------------------------------------------------------------------------- the step

_HEADER_MANUAL = """\
### Comment headers name the author's slug

Every comment header changes from `- [<timestamp>] <name>:` to
`` - [<timestamp>] `<slug>` <name>: ``. `sq migrate up` rewrites the header line of every
comment, in each item's discussion and in each story's, subtask's and finding's, and nothing
else in a discussion: a comment's own lines stay byte for byte. It reports how many headers it
rewrote and in how many files. The next section changes the frontmatter. Review the diff before
you commit it.

The slug is found from the name. Each name is looked up among the squad's roles and operators,
retired ones included, and the two names sq writes itself (`Operator` and `squads`). A role is
known by its name (the `Name` column of `sq role list`); an operator by the full name its file
stores under `extra:`, or by its slug when it stores none, which is what the earlier release
wrote in its comments. The next section then makes that full name the operator's `title`.
Every name is
resolved before any file is written. If one cannot be, this step writes nothing, the schema stamp
is unchanged and the command exits 1 with one line per header, then a count, then one line per
distinct name:

    tasks/TASK-NNNNNN-add-login.md:41: 'Hugo Ops' matches no roster entry
    tasks/TASK-NNNNNN-add-login.md:57: 'Sam Lee' matches 2 entries: op-sam, qa
    bugs/BUG-NNNNNN-crash.md:33: '2026-06-07 10:00' is not a timestamp sq writes
    3 problem(s) found.
      'Hugo Ops': 1 header(s) in 1 file(s)
      'Sam Lee': 1 header(s) in 1 file(s)

What to do for each, before running `sq migrate up` again:

- **A name that matches no entry.** The role or operator that wrote those comments is no longer
  in the squad. Add it back under that name with the earlier release: `sq role activate <slug>
  --name "<name>"` for a role (`sq role catalog` lists the slugs), `sq dev add --tech <tech>
  --name "<name>"` for a developer role, `sq operator add "<name>" --slug <old-slug>` for an
  operator. A retired entry counts, so it can be retired again afterwards. If the entry is still
  there under a newer name, both names cannot resolve at once: replace the older name in those
  header lines by hand.
- **A name that matches several entries.** Two entries share that name, and every header with it
  will belong to one of them. Give the other a distinct name for the run by editing its file:
  `title:` for a role, `full_name:` under `extra:` for an operator (the file still has the
  earlier shape). The run keeps a role's `title:` and makes the operator's `full_name` its
  `title:`, so the name typed for the run stays until you edit the `title:` line back to the real
  name and run `sq repair`.
- **A timestamp sq does not write.** The line starts at the left margin inside a discussion and
  looks like a header. If it is text that was pasted there, indent it under its comment. If it
  is a header, correct its timestamp to the form `2026-06-07T10:00:00Z`.
- **A discussion that is never closed.** Its closing marker line is missing. Restore it.
- **A discussion marker that shares its line with text, or is not spelled as sq writes it.** Put
  each `sq:` marker on a line of its own, spelled as sq writes it (the tag between `<!--` and
  `-->`, one space on each side).

Changes to the roster are made with a squads release that reads the squad's schema; the refusal
names one. Until the migration completes, this release runs nothing on the squad but
`sq migrate up`, `sq migrate help` and `sq migrate chlog`. On a squad stamped below 0.15, run
`sq migrate up` with 0.15.0 first, then change the roster with it. There is no option that maps
a name to a slug by hand.

A header already in the new form is left as it is, so the command can be run again safely.

### A role or operator whose slug breaks the rules refuses the run

Before it resolves any header, the step checks every role and operator, retired ones included.
An operator's slug is `op-` followed by lowercase letters, digits and hyphens. A role's slug is
lowercase letters, digits and hyphens, and is neither `operator` nor `squads` nor anything that
starts with `op-`. No slug is held by two entries. An entry that breaks a rule refuses the run
like an unresolvable header: nothing is written, the schema stamp is unchanged and the command
exits 1, with one line for the entry, naming its file, its slug, the rule and the other holders:

    operators/OP-000012-qa.md: operator slug 'qa' does not start with 'op-'; also held by ROLE-5

It is refused, and not only reported, because this is the last point where the slug can change.
Once the headers carry it no later step rewrites them, so a reserved slug would turn comments
into system entries, `operator` would make them anonymous, and a slug shared with a role would
make them editable by whoever holds it.

What to do for each, with the release the squad is stamped for, before running `sq migrate up`
again:

- **An operator.** Run `sq operator <id> rm --purge`, using the ID in the line, then
  `sq operator add "<the same full name>"`, which takes `op-` and the first name unless you pass
  a compliant `--slug`. The purge is required: a plain `rm` drops the entry from the index but
  keeps its file, and the next run reads that file again. The comments that named the operator
  then resolve to the new slug. Reassign the open items assigned to the old slug with
  `sq <type> <n> update --assignee <new slug>`. An item's `author` keeps the old slug, and
  `sq check` reports it as not registered.
- **A role.** Give the role's project definition a compliant slug (the file under
  `<squad folder>/.overrides/roles/`, renamed, and its `slug` line with it), run
  `sq role activate <new slug>`, then `sq role <id> rm --purge` for the old entry.
- **A slug held by two entries.** Both entries are listed, each naming the other. Replace the one
  that breaks a rule above, or the one you can spare, the same way.
"""

_FLAT_MANUAL = """\
### The frontmatter is flat

An item file keeps its fields as top-level keys; the nested `extra:` block is gone. `sq migrate
up` lifts each key of `extra:` to the top level with its value unchanged, in every item file, and
rewrites nothing in the file but its frontmatter. The exceptions:

- `slug` becomes the top-level `slug`, written on every role, skill and operator file. A roster
  file that stores none (an operator an earlier importer created) gets the slug its file name
  spells.
- A skill's `description` under `extra:` is dropped when its top-level `description` is not
  empty, and otherwise becomes the `description` unless it is the skill's title.
- An operator's `full_name` is dropped. The operator's `title` takes its value when the two
  differ, because that is the name every operator surface showed; the run lists those files.
- A role's mirrored definition keys (`title`, `mission`, `responsibilities`, `agreements`,
  `color`, `can_spawn`, `description`, `full_name`, `skills`) are dropped: the role catalog answers
  them.
- `ref_kinds` is folded into the item's refs and `severity` becomes the top-level `severity`
  when that is absent.
- The top-level `path:` key that an old release wrote on skill files is removed.

Every other key, one this squad's spec declares or one an adopter added, is kept as written, and
the `extra:` key is removed. A file that needs nothing is not touched, so a second run changes
nothing. The run reports how many files it flattened, how many keys it lifted per key, how many
skill descriptions and `path:` keys it removed and which operators it retitled. When a dropped
skill description differed from the one kept, the run also lists those files.

A role keeps the name it stores, whatever the configuration says: the step changes no name, and
`sq sync` never renames a role. A new role takes its name from `--name`, else from the
configuration, when it is created.

Like the comment headers, the flattening is checked before anything is written. These make the
step write nothing, leave the schema stamp as it is and exit 1, one line per file:

    tasks/TASK-NNNNNN-add-login.md: extra is not a mapping
    guides/GUIDE-NNNNNN-notes.md: extra.tech and the top-level tech hold different values
    agents/roles/ROLE-NNNNNN-qa.md: extra.slug 'quality' differs from the file name's slug 'qa'
    guides/GUIDE-NNNNNN-notes.md: extra.path would become the item's own 'path'; move it out by hand

Edit the file so the two places agree (drop the one you do not want), then run `sq migrate up`
again.
"""


def _held_capabilities(
    ctx: MigrationContext, front: dict[str, Any], developer: frozenset[str]
) -> tuple[str, ...] | None:
    """The capabilities the role whose flat frontmatter is *front* holds, or ``None`` when no
    definition is left to say. A templated role holds the ``dev`` template's."""
    slug = cast("str", front["slug"])
    if front.get("tech"):
        return tuple(developer)
    try:
        try:
            return resolve_role_with_base(
                slug, ctx.paths.squad_dir, base=None, catalog=ctx.catalog
            ).capabilities
        except RoleNotFoundError:
            defined = role_defined_by_file(slug, ctx.paths.squad_dir)
            return None if defined is None else defined.capabilities
    except SquadsError:
        return ()


async def _plan_developer_capability(ctx: MigrationContext, db: SquadsDB) -> Planned:
    """Report every role named ``-dev`` that holds no capability the ``[dev]`` table declares:
    it is an ordinary role from now on. Nothing is written; the developer marker leaves through
    the retired role keys and the rebuild after the runners.

    A role file is read as the flatten step will leave it, since this plans before that writer.
    """
    live = ctx.spec.live_statuses(ROSTER_ROLE)
    developer = ctx.catalog().developer_capabilities()
    default_kind = ctx.spec.default_ref_kind()
    reported: list[str] = []
    for it in sorted(db.items.values(), key=lambda i: i.sequence_id):
        if it.type != ROSTER_ROLE:
            continue
        text = (await _aio.read_bytes(ctx.paths.abspath(it.path))).decode("utf-8")
        data = read_frontmatter(text=text, source=it.path)
        flat = flatten_frontmatter(
            data, file_slug=_file_slug(ctx, it), default_kind=default_kind, source=it.path
        )
        front = flat.data
        slug = front.get("slug")
        if flat.problems or not isinstance(slug, str) or not slug.endswith("-dev"):
            continue
        held = _held_capabilities(ctx, front, developer)
        if held is not None and developer.intersection(held):
            continue
        notes = [] if it.status in live else ["retired"]
        if held is None:
            notes.append("no role file left")
        reported.append(f"  {slug}" + (f" ({', '.join(notes)})" if notes else ""))
    if not reported:
        return Planned()
    return Planned(
        report=(
            f"{len(reported)} role(s) named -dev hold no developer capability and are now "
            "ordinary roles; declare the capability in the role file and run `sq sync` to "
            "restore the developer guidance:",
            *reported,
        )
    )


_DEVELOPER_MANUAL = """\
### A developer is a role that declares a capability

A developer is now a role whose role file declares a capability the `[dev]` table of the role
catalog also declares (the bundled catalog declares `dev`). The stored `is_dev` marker is gone.
`sq migrate up` removes it from developer items and changes nothing else in them: the name,
`tech` and `model` stay as they were.

- A role the run reports keeps working as an ordinary role. It regains the developer guidance
  when its role file declares the capability and `sq sync` runs; there is no automatic fix.
- An override file written for a developer that was not added yet is now reported by `sq check`;
  the ways out are `sq dev add` or removing the file.
- An existing developer picks up a project `[dev]` colour on the next `sq sync` and keeps the
  model and the name it was created with.
- A stamped catalog, playbook, workflow or per-slug role override reports "may be stale" because
  the bundled documents changed: run `sq override diff`, then `sq override update`.
"""


# --------------------------------------------------------------------------- origin


async def _plan_origin(ctx: MigrationContext, db: SquadsDB) -> Planned:
    """Stamp ``origin`` on every role and skill file that stores none. A file is read as the
    flatten step will leave it; one that already carries the key, whatever its value, is skipped.
    A file the flatten step rewrites is stamped by that write, so only the rest are written here.
    """
    default_kind = ctx.spec.default_ref_kind()
    stamps: dict[str, str] = {}
    counts: Counter[tuple[str, str]] = Counter()
    for it in sorted(db.items.values(), key=lambda i: i.sequence_id):
        if it.type not in (ROSTER_ROLE, ROSTER_SKILL):
            continue
        text = (await _aio.read_bytes(ctx.paths.abspath(it.path))).decode("utf-8")
        data = read_frontmatter(text=text, source=it.path)
        file_slug = _file_slug(ctx, it)
        flat = flatten_frontmatter(
            data, file_slug=file_slug, default_kind=default_kind, source=it.path
        )
        origin = _origin_of(ctx, flat.data, file_slug)
        if origin is None:
            continue
        counts[(it.type, origin)] += 1
        if not flat.changed:
            stamps[it.path] = origin

    async def write(wctx: MigrationContext) -> int:
        for rel, origin in stamps.items():
            path = wctx.paths.abspath(rel)
            text = (await _aio.read_bytes(path)).decode("utf-8")
            front = read_frontmatter(text=text, source=rel)
            front[AttributeKey.ORIGIN] = origin
            await write_text(
                path, _skill_text(replace_frontmatter(text, front, source=rel), front.get("type"))
            )
        return len(stamps)

    report = tuple(
        f"{counts[(kind, origin)]} {kind}(s) stamped origin {origin}"
        for kind in (ROSTER_ROLE, ROSTER_SKILL)
        for origin in ("system", "project")
        if counts[(kind, origin)]
    )
    return Planned(report=report, write=write if stamps else None)


_ORIGIN_MANUAL = """\
### Every role and skill records its origin

Each role and skill file stores `origin: system` or `origin: project`. `sq migrate up` adds it
to every role and skill that stores none, and reports how many of each it stamped. A role or
skill the bundled catalog or the spec's generated skills name is `system`, and so is a templated
developer (a role that stores `tech`); everything else, a declared developer included, is
`project`. A bundled role the project overrides stays `system`. A file that already stores an
`origin` is left as it is, so a second run changes nothing.
"""


# --------------------------------------------------------------------------- skill discussion


async def _plan_skill_discussion(ctx: MigrationContext, db: SquadsDB) -> Planned:
    """Give every skill file that lacks one a top-level discussion region. A file the flatten or
    origin writer rewrites gets the region in that same write; the rest are written here, each
    re-read at write time, and a file that has the region by then is left alone."""
    lacking: list[str] = []
    for it in sorted(db.items.values(), key=lambda i: i.sequence_id):
        if it.type != ROSTER_SKILL:
            continue
        text = (await _aio.read_bytes(ctx.paths.abspath(it.path))).decode("utf-8")
        if with_discussion_region(text) != text:
            lacking.append(it.path)

    async def write(wctx: MigrationContext) -> int:
        written = 0
        for rel in lacking:
            path = wctx.paths.abspath(rel)
            text = (await _aio.read_bytes(path)).decode("utf-8")
            if has_section(text, markers.DISCUSSION):
                continue
            await write_text(path, with_discussion_region(text))
            written += 1
        return written

    report = (f"{len(lacking)} skill(s) given a discussion region",) if lacking else ()
    return Planned(report=report, write=write if lacking else None)


_DISCUSSION_MANUAL = """\
### Every skill has a discussion

Each skill file now carries a `## Discussion` heading and an empty discussion region after its
body region, as role and operator files do, so a skill takes comments. `sq migrate up` appends
them to every skill file that has none, byte for byte and in the file's own line endings, and
leaves a file that already has one as it is, so a second run changes nothing.
"""


CONTRIBUTIONS: tuple[Contribution, ...] = (
    Contribution(
        name="comment-headers",
        plan=_plan_headers,
        manual=_HEADER_MANUAL,
        summary="Comment headers name the author's permanent slug.",
    ),
    Contribution(
        name="flat-frontmatter",
        plan=_plan_flat_frontmatter,
        manual=_FLAT_MANUAL,
        summary=("Item frontmatter is flat: the extra block is lifted to top-level keys."),
    ),
    Contribution(
        name="developer-capability",
        plan=_plan_developer_capability,
        manual=_DEVELOPER_MANUAL,
        summary=(
            "The developer marker is dropped from role items, and roles named -dev that "
            "declare no capability are reported."
        ),
    ),
    Contribution(
        name="origin",
        plan=_plan_origin,
        manual=_ORIGIN_MANUAL,
        summary="Every role and skill records whether it is system or project.",
    ),
    Contribution(
        name="skill-discussion",
        plan=_plan_skill_discussion,
        manual=_DISCUSSION_MANUAL,
        summary="Every skill file has a discussion region.",
    ),
)

_MANUAL_PREAMBLE = """\
This step checks every part before it writes any file: if any part finds a problem, this step
writes nothing, the schema stamp stays as it is and the command lists every problem at once.

On a squad still behind the package, `sq migrate up`, `sq migrate help`, `sq migrate chlog`,
`sq override list`, `sq override diff` and `sq override update` run; every other command is
refused. The purge steps below use `rm --purge`, which both the 0.15 tool and 0.16 accept (0.16
also accepts `remove`).

"""


def assemble_manual(contributions: Sequence[Contribution]) -> str:
    """The step's ``MANUAL``: a preamble, then each contribution's section once, in order."""
    return _MANUAL_PREAMBLE + "\n".join(c.manual for c in contributions)


def assemble_summary(contributions: Sequence[Contribution]) -> str:
    """The step's one-line summary: each contribution's clause, in order."""
    return " ".join(c.summary for c in contributions)


MANUAL = assemble_manual(CONTRIBUTIONS)
SUMMARY = assemble_summary(CONTRIBUTIONS)


async def migrate(ctx: MigrationContext) -> MigrationOutcome:
    """Plan every contribution, refuse on any failure, then write — inside one index
    transaction opened under the run's spec."""
    store = IndexStore(ctx.paths.index_path, ctx.paths.lock_path, spec=ctx.spec)
    async with store.transaction() as db:
        return await run_contributions(CONTRIBUTIONS, ctx, db)
