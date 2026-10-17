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

Invoked by ``sq migrate up`` via ``_migrations._registry`` — never run directly (this module is
private).
"""

import re
from collections import defaultdict
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, NamedTuple

from squads import _aio
from squads._errors import SquadsError
from squads._index._store import IndexStore
from squads._itemfile import read_frontmatter, write_text
from squads._migrations._context import MigrationContext
from squads._migrations._outcome import MigrationOutcome
from squads._models import _markers as markers
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._sections import find_markers
from squads._workflow._models import ROSTER_OPERATOR, ROSTER_ROLE

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
_OPERATOR_PREFIX = "op-"


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
    odd_operator_notes: tuple[str, ...]


async def _read_roster(ctx: MigrationContext, db: SquadsDB) -> _Roster:
    """Every role and operator, live or retired, read from its own file's frontmatter."""
    by_name: dict[str, set[str]] = defaultdict(set)
    notes: list[str] = []
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
        if it.type == ROSTER_OPERATOR:
            name = str(extra.get("full_name") or slug)
            if not slug.startswith(_OPERATOR_PREFIX):
                notes.append(
                    f"operator {name!r} has slug {slug!r}, which does not start with "
                    f"{_OPERATOR_PREFIX!r}"
                )
        else:
            name = str(data.get("title") or it.title)
        by_name[name].add(slug)
    return _Roster(dict(by_name), tuple(notes))


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
        *roster.odd_operator_notes,
    )
    if tally.failures:
        return Planned(failures=tuple(tally.failures), notes=_failure_notes(tally), report=report)

    async def write(wctx: MigrationContext) -> int:
        return await _write_headers(wctx, tally.files, resolved)

    return Planned(report=report, write=write)


async def _tally_file(ctx: MigrationContext, it: Item, roster: _Roster, tally: _Tally) -> None:
    text = (await _aio.read_bytes(ctx.paths.abspath(it.path))).decode("utf-8")
    holds_legacy = False
    for event in _scan(text.splitlines()):
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
        kept = text.splitlines(keepends=True)
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
    """``line`` without the one line terminator ``str.splitlines`` ended it with."""
    return "".join(line.splitlines())


# --------------------------------------------------------------------------- the step

_HEADER_MANUAL = """\
### Comment headers name the author's slug

Every comment header changes from `- [<timestamp>] <name>:` to
`` - [<timestamp>] `<slug>` <name>: ``. `sq migrate up` rewrites the header line of every
comment, in each item's discussion and in each story's, subtask's and finding's, and nothing
else: a comment's own lines stay byte for byte and no frontmatter changes. It reports how many
headers it rewrote and in how many files. Review the diff before you commit it.

The slug is found from the name. Each name is looked up among the squad's roles and operators,
retired ones included, and the two names sq writes itself (`Operator` and `squads`). A role is
known by its name (the `Name` column of `sq role list`); an operator by its full name, or by its
slug when it has none, which is what the earlier release wrote in its comments. Every name is
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
  `title:` for a role, `full_name:` under `extra:` for an operator. After the migration, edit it
  back and run `sq repair`.
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

An operator whose slug does not start with `op-` is listed in the run's report; nothing is
refused for it.
"""

CONTRIBUTIONS: tuple[Contribution, ...] = (
    Contribution(
        name="comment-headers",
        plan=_plan_headers,
        manual=_HEADER_MANUAL,
        summary="Comment headers name the author's permanent slug.",
    ),
)

_MANUAL_PREAMBLE = """\
This step checks every part before it writes any file: if any part finds a problem, this step
writes nothing, the schema stamp stays as it is and the command lists every problem at once.

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
