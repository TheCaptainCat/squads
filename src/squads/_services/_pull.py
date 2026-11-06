"""``sq source pull``: fetch what changed on each source, compile it to import events against the
items as they stand, and apply the events in one transaction."""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from squads import _clock as clock
from squads import _discussion as discussion
from squads._api import Response, SourcePulled, SourcePullReport, SourcePullRequest
from squads._errors import SquadsError
from squads._models import (
    GONE,
    OUT_OF_FILTER,
    SOURCE_AUTHOR_PREFIX,
    Item,
    SquadsDB,
    prefix_for,
    split_ref,
)
from squads._services._fetch import connector_for, fetch_source, open_connector, require_enabled
from squads._services._import import ImportMixin
from squads._services._import_model import (
    CommentEditEvent,
    CommentEvent,
    CreateEvent,
    ImportEvent,
    RefEvent,
    ResolvedEvent,
    SourceEvent,
    StatusEvent,
    UpdateEvent,
    ViewBodyEvent,
)
from squads._services._validators import ValidatorEngine
from squads._sources import (
    Comment,
    Connector,
    FetchedIssue,
    Issue,
    SourceFetch,
    SourceSpec,
    StatusChoice,
    load_converter,
    mapped_status,
    mapped_types,
    mapped_values,
    missing_credential,
)

#: Why a held issue reads out-of-filter, as the report says it.
REJECTED_BY_FILTER = "rejected by the filter"
OUTSIDE_THE_SCOPE = "outside the scope"
#: The stored view that holds an issue's description.
DESCRIPTION_VIEW = "source_description"
#: The comment attribute that holds the tracker's ID of the comment.
COMMENT_ID = "source_id"
#: The comment attribute that holds when the tracker last changed the comment.
COMMENT_UPDATED = "source_updated_at"


@dataclass
class Compiled:
    """The events a source compiled to, the issue each belongs to, and the report so far."""

    events: list[ResolvedEvent] = field(default_factory=list[ResolvedEvent])
    issue_of: dict[int, str] = field(default_factory=dict[int, str])
    lines: list[str] = field(default_factory=list[str])
    created: set[str] = field(default_factory=set[str])
    #: The handle each created issue's item was planned under, by issue label.
    handle_of: dict[str, str] = field(default_factory=dict[str, str])
    refreshed: int = 0
    unchanged: int = 0
    gone: int = 0
    held_elsewhere: int = 0
    #: The labels of the held issues compiled, which count as refreshed or unchanged once the
    #: pre-pass has settled which events survive.
    held_labels: list[str] = field(default_factory=list[str])
    #: The labels of the issues counted as gone, so a drop can uncount them.
    gone_labels: set[str] = field(default_factory=set[str])
    restricted: int = 0
    filtered_out: int = 0
    skipped_no_type: int = 0
    #: Keys of the issues whose events were dropped, with the reason.
    dropped: dict[str, str] = field(default_factory=dict[str, str])
    #: Per host issue key, the (ID, key) of each link target no item held when the source compiled.
    unfollowed: list[tuple[str, list[tuple[str, str]]]] = field(
        default_factory=list[tuple[str, list[tuple[str, str]]]]
    )

    #: The sources on the tracker, whose items may hold a link's target.
    peers: frozenset[str] = frozenset()

    def uncount(self, label: str) -> None:
        """Take the issue *label* out of the gone counter once it is dropped."""
        if label in self.gone_labels:
            self.gone -= 1
            self.gone_labels.discard(label)


@dataclass
class Fetched:
    source: SourceSpec
    fetch: SourceFetch


#: One source's compile step: the source and the function that compiles its fetch against the
#: index inside the pull's transaction.
#: It also receives the handles of the items the sources compiled before it in the run create.
type CompileJob = tuple[SourceSpec, Callable[[SquadsDB, frozenset[str]], Awaitable[Compiled]]]


def _second(text: str, fallback: datetime) -> datetime:
    """The tracker's timestamp *text* as a UTC instant to the second, or *fallback*."""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return fallback
    return parsed.astimezone(UTC).replace(microsecond=0)


def _lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


class ConversionError(SquadsError):
    """A converter failed on one text; the issue holding it is dropped, the rest go on."""


class Compiler:
    """Compiles the fetch of one source into events, against the index *db* and the pull's time."""

    def __init__(
        self,
        service: PullMixin,
        db: SquadsDB,
        source: SourceSpec,
        now: datetime,
        created_before: frozenset[str] = frozenset(),
        *,
        dry_run: bool = False,
    ):
        self.service = service
        self.dry_run = dry_run
        self.db = db
        self.source = source
        self.now = now
        self.actor = f"{SOURCE_AUTHOR_PREFIX}{source.name}"
        self.out = Compiled()
        self._emitted_refs: set[tuple[str, str, str]] = set()
        self.by_id = db.source_ids()
        #: The sources on this source's tracker, whose items may hold the same issues.
        self.peers = service.sources().peers(source.name) or frozenset({source.name})
        self.created_before = created_before
        self.converter = load_converter(source.converter)
        self.issue_url = connector_for(source, {}).issue_url

    def convert(self, text: str, key: str) -> str:
        """*text* of the issue *key* through the source's converter; any failure is a
        :class:`ConversionError`."""
        try:
            return self.converter(text, self.source.base_url, self.issue_url(key))
        except Exception as exc:  # a converter reads hostile text and must not stop the pull
            raise ConversionError(f"its text cannot be converted ({type(exc).__name__})") from exc

    async def attempt(self, fetched: FetchedIssue, state: str, why: str = "") -> None:
        """Compile one issue; when its text cannot be converted, undo what it emitted and report
        it."""
        events = len(self.out.events)
        created, handles = set(self.out.created), dict(self.out.handle_of)
        held_elsewhere = self.out.held_elsewhere
        try:
            await self.issue(fetched, state, why)
        except ConversionError as exc:
            del self.out.events[events:]
            for line in [n for n in self.out.issue_of if n > events]:
                del self.out.issue_of[line]
            self.out.created, self.out.handle_of = created, handles
            self.out.held_elsewhere = held_elsewhere
            key = fetched.issue.key
            self.out.dropped[key] = str(exc)
            self.say(f"{key}: dropped, {exc}")

    # ------------------------------------------------------------------ emit
    def emit(self, label: str, event: ImportEvent, at: datetime | None = None) -> None:
        line = len(self.out.events) + 1
        self.out.events.append(
            ResolvedEvent(
                line=line,
                event=event,
                op_name=event.op,
                at=at or self.now,
                actor=self.actor,
            )
        )
        self.out.issue_of[line] = label

    def say(self, text: str) -> None:
        self.out.lines.append(text)

    # ------------------------------------------------------------------ mapping
    def mapped_type(self, issue: Issue) -> str | None:
        found = mapped_types(self.source.maps, issue)
        return next(iter(found)) if len(found) == 1 else None

    def mapped_fields(self, issue: Issue) -> dict[str, str]:
        out: dict[str, str] = {}
        for code in self.source.maps.fields:
            values = mapped_values(self.source.maps, code, issue)
            if len(values) == 1:
                out[code] = next(iter(values))
            elif values:
                self.say(
                    f"{issue.key}: {code} left alone, its values map to {', '.join(sorted(values))}"
                )
        return out

    def mapped_status(self, issue: Issue, item_type: str) -> StatusChoice | None:
        """The status the source's map gives *issue* as an item of *item_type*, or ``None`` when
        the source has no status map or no side maps the issue."""
        if not self.source.maps.statuses:
            return None
        states = self.service.spec.workflow_for(item_type).states
        return mapped_status(self.source, issue, item_type, states)

    def record(self, issue: Issue, state: str) -> dict[str, str]:
        return {
            "name": self.source.name,
            "id": issue.id,
            "key": issue.key,
            "state": state,
            "updated_at": issue.updated_at,
            "author_id": issue.author_id,
            "author_handle": issue.author_handle,
        }

    # ------------------------------------------------------------------ one issue
    async def issue(self, fetched: FetchedIssue, state: str, why: str = "") -> None:
        issue = fetched.issue
        label = f"{self.source.name} {issue.key}"
        held = [self.db.items[n] for n in self.by_id.get((self.source.name, issue.id), [])]
        if held:
            if len(held) > 1:
                ids = ", ".join(it.id for it in held)
                self.say(f"{issue.key}: held by {ids}; each is refreshed")
            for item in held:
                await self.refresh(label, item, fetched, state, why)
            self.out.held_labels.append(label)
            return
        if holder := self.other_holder(issue.id):
            self.say(f"{issue.key}: held by {holder}")
            self.out.held_elsewhere += 1
            return
        await self.create(label, fetched, state)

    def other_holder(self, issue_id: str) -> str:
        """How the report names the item of another source on this tracker that holds the issue,
        or an empty string when none does."""
        for name in sorted(self.peers - {self.source.name}):
            if seqs := self.by_id.get((name, issue_id)):
                return f"{self.db.items[seqs[0]].id} of source {name!r}"
            if f"{name}:{issue_id}" in self.created_before:
                return f"the item source {name!r} creates in this pull"
        return ""

    def holders(self, issue_id: str) -> list[str]:
        """The IDs, or the handles of the items this pull creates, of every item on the tracker
        that holds the issue."""
        seqs = sorted({n for name in self.peers for n in self.by_id.get((name, issue_id), [])})
        found = [self.db.items[n].id for n in seqs]
        created = self.out.created | self.created_before
        return found or [h for name in sorted(self.peers) if (h := f"{name}:{issue_id}") in created]

    def handle(self, issue: Issue) -> str:
        return f"{self.source.name}:{issue.id}"

    async def create(self, label: str, fetched: FetchedIssue, state: str) -> None:
        issue = fetched.issue
        item_type = self.mapped_type(issue)
        if item_type is None:
            return
        declared = {f.code for f in self.service.spec.fields_for(item_type)}
        fields = {c: v for c, v in self.mapped_fields(issue).items() if c in declared}
        handle = self.handle(issue)
        choice = self.mapped_status(issue, item_type)
        if choice is not None and choice.problem:
            self.say(f"{issue.key}: {choice.problem}")
        elif choice is not None and choice.status != (
            initial := self.service.spec.initial_status(item_type)
        ):
            candidate = Item(
                sequence_id=self.db.counter + 1,
                type=item_type,
                prefix=prefix_for(item_type, self.service.spec),
                title=issue.title or item_type,
                slug="candidate",
                status=choice.status,
                author=self.actor,
                path="candidate.md",
                created_at=self.now,
                updated_at=self.now,
            )
            if self.refusal(candidate.model_copy(update={"status": initial})) is not None:
                choice = None  # refused at any status: the pull's own drop line says why
            elif (why := self.refusal(candidate)) is not None:
                self.say(f"{issue.key}: status left alone, {choice.status} is refused: {why}")
                choice = None
        self.emit(
            label,
            CreateEvent(
                type=item_type,
                title=issue.title,
                fields=fields,
                handle=handle,
                status=(choice.status or None) if choice is not None else None,
            ),
        )
        self.emit(label, SourceEvent(target=handle, record=self.record(issue, state)))
        self.emit(
            label,
            ViewBodyEvent(
                target=handle,
                view=DESCRIPTION_VIEW,
                text=self.convert(issue.description, issue.key),
            ),
        )
        self.comments(label, handle, fetched.comments, existing=[], seq=None, issue_key=issue.key)
        self.out.created.add(handle)
        self.out.handle_of[label] = handle

    async def refresh(
        self, label: str, item: Item, fetched: FetchedIssue, state: str, why: str = ""
    ) -> None:
        """Compile the changes of *item* from its issue."""
        issue = fetched.issue
        title_changed = item.title != issue.title
        declared = {f.code for f in self.service.spec.fields_for(item.type)}
        fields: dict[str, str] = {}
        for code, value in self.mapped_fields(issue).items():
            if code not in declared:
                self.say(f"{issue.key}: {code} skipped, {item.type} items have no such field")
            elif item.badge_value(code) != value:
                fields[code] = value
        if title_changed or fields:
            self.emit(
                label,
                UpdateEvent(
                    target=item.id, title=issue.title if title_changed else None, fields=fields
                ),
            )
        record = self.record(issue, state)
        text = _lf(self.convert(issue.description, issue.key))
        moved = self.move_status(label, item, issue, state)
        if item.source is None or item.source.model_dump() != record:
            if (
                item.source is not None
                and item.source.state != state
                and state != "open"
                and not moved
            ):
                reason = f" ({why})" if why else ""
                self.say(f"{issue.key}: {state}{reason}; {item.id} stays")
            self.emit(label, SourceEvent(target=item.id, record=record))
        if await self.service.stored_description(item, DESCRIPTION_VIEW) != text:
            self.emit(label, ViewBodyEvent(target=item.id, view=DESCRIPTION_VIEW, text=text))
        existing = await self.service.comments(item.id)
        self.comments(
            label, item.id, fetched.comments, existing=existing, seq=item, issue_key=issue.key
        )

    def refusal(self, candidate: Item) -> str | None:
        """Why the squad's per-item validators refuse *candidate*, or ``None`` if they accept it."""
        engine = ValidatorEngine(
            spec=self.service.spec, playbook=self.service.playbook, paths=self.service.paths
        )
        try:
            engine.gate(candidate, self.db)
        except SquadsError as exc:
            return str(exc)
        return None

    def move_status(self, label: str, item: Item, issue: Issue, state: str) -> bool:
        """Set the status the source's map gives *issue* on *item* without the transition rule, when
        it differs, the issue is selected and the squad's checks accept it; whether it moved."""
        choice = self.mapped_status(issue, item.type) if state in ("open", "closed") else None
        if choice is None:
            return False
        if choice.problem:
            self.say(f"{issue.key}: {choice.problem}")
            return False
        if choice.status == item.status:
            return False
        candidate = item.model_copy(deep=True)
        candidate.status = choice.status
        if (why := self.refusal(candidate)) is not None:
            if self.refusal(item) is None:
                self.say(f"{issue.key}: status left alone, {choice.status} is refused: {why}")
            return False  # refused at both statuses: the pull's drop line says why
        self.emit(label, StatusEvent(target=item.id, status=choice.status, force=True))
        verb = "would move" if self.dry_run else "moved"
        self.say(f"{issue.key}: {item.id} {verb} to {choice.status} ({choice.side} {choice.value})")
        return True

    def comments(
        self,
        label: str,
        target: str,
        fetched: Sequence[Comment],
        *,
        existing: Sequence[discussion.Comment],
        seq: Item | None,
        issue_key: str,
    ) -> None:
        sourced = {
            c.attributes[COMMENT_ID]: c
            for c in existing
            if c.author_slug == self.actor and COMMENT_ID in c.attributes
        }
        seen: dict[tuple[str, str], str] = {}
        taken = {(c.timestamp, c.hash) for c in existing if c.author_slug == self.actor}
        for note in fetched:
            attrs = {
                "author_id": note.author_id,
                "author_handle": note.author_handle,
                "author_name": note.author_name,
                COMMENT_ID: note.id,
                COMMENT_UPDATED: note.updated_at,
            }
            text = self.convert(note.body, issue_key)
            when = _second(note.created_at, self.now)
            stamp = clock.iso(when)
            old = sourced.get(note.id)
            if old is not None:
                if old.attributes.get(COMMENT_UPDATED) != note.updated_at:
                    self.emit(
                        label,
                        CommentEditEvent(
                            target=target,
                            key=COMMENT_ID,
                            value=note.id,
                            messages=[text],
                            attributes=attrs,
                        ),
                    )
                continue
            key = (stamp, text)
            if key in seen:
                self.say(
                    f"{target}: comment {note.id} has the text and second of comment "
                    f"{seen[key]}; skipped"
                )
                continue
            if seq is not None and self.same_as_existing(seq, stamp, text, taken):
                self.say(f"{target}: comment {note.id} equals a comment already there; skipped")
                continue
            seen[key] = note.id
            self.emit(label, CommentEvent(target=target, messages=[text], attributes=attrs), when)
        for gone_id in sorted(set(sourced) - {n.id for n in fetched}):
            self.say(f"{target}: comment {gone_id} was deleted on the tracker; kept")

    def same_as_existing(
        self, item: Item, stamp: str, text: str, taken: set[tuple[str, str]]
    ) -> bool:
        entry = discussion.format_comment(stamp, self.actor, self.source.name, [text])
        digest = discussion.comment_hash(
            item.sequence_id, "", self.actor, stamp, discussion.entry_text(entry)
        )
        return (stamp, digest) in taken

    # ------------------------------------------------------------------ links
    def links(self, fetched: Mapping[str, FetchedIssue]) -> None:
        """Emit the refs the links of *fetched* make: from the item holding the issue read to the
        item holding the other end by the link type, and the other way by its inverse, each only
        when the source maps that name, so a link gives the same refs whichever end is read."""
        for fi in fetched.values():
            label = f"{self.source.name} {fi.issue.key}"
            host_ids = self.holders(fi.issue.id)
            unheld: list[tuple[str, str]] = []
            for link in fi.links:
                targets = self.holders(link.target_id)
                maps = self.source.maps.links
                if host_ids and not targets and (link.link_type in maps or link.inverse in maps):
                    unheld.append((link.target_id, link.target_key))
                for name, holders, others in (
                    (link.link_type, host_ids, targets),
                    (link.inverse, targets, host_ids),
                ):
                    kind = maps.get(name)
                    if kind is None:
                        continue
                    for holder in holders:
                        for other in others:
                            if self._new_ref(holder, other, kind):
                                self.emit(label, RefEvent(target=holder, to=other, kind=kind))
            if unheld:
                self.out.unfollowed.append((fi.issue.key, unheld))

    def _new_ref(self, holder: str, other: str, kind: str) -> bool:
        """Whether the ref *holder* to *other* of *kind* is neither held nor emitted yet."""
        wanted = (holder, other, kind)
        if wanted in self._emitted_refs or self.has_ref(holder, other, kind):
            return False
        self._emitted_refs.add(wanted)
        return True

    def has_ref(self, host: str, target: str, kind: str) -> bool:
        item = self.db.get(host)
        if item is None:
            return False
        default = self.service.spec.default_ref_kind()
        wanted = (target, kind or default)
        return any((t, k or default) == wanted for t, k in map(split_ref, item.refs))


def renumbered(ev: ResolvedEvent, line: int) -> ResolvedEvent:
    """*ev* as event number *line* of a combined stream."""
    return ResolvedEvent(line=line, event=ev.event, op_name=ev.op_name, at=ev.at, actor=ev.actor)


class PullMixin(ImportMixin):
    """The pull: the one writer that turns tracker issues into items."""

    async def stored_description(self, item: Item, view: str) -> str:
        """The unescaped stored body of *view* on *item*."""
        return await self._stored_view_body(item, view)

    @staticmethod
    async def _fetch_one_source(
        db: SquadsDB,
        source: SourceSpec,
        connector: Connector,
        peers: frozenset[str],
        *,
        full: bool,
    ) -> SourceFetch:
        """The fetch of *source*: what the items already hold of it decides what is read in
        detail."""
        held = [
            it.source
            for it in db.items.values()
            if it.source is not None and it.source.name == source.name
        ]
        stored: dict[str, frozenset[tuple[str, str]]] = {}
        for record in held:
            stored[record.id] = stored.get(record.id, frozenset()) | {
                (record.updated_at, record.state)
            }
        elsewhere: dict[str, str] = {}
        for seq in sorted(db.items):
            record = db.items[seq].source
            if record is not None and record.name in peers - {source.name}:
                elsewhere.setdefault(record.id, f"{db.items[seq].id} of source {record.name!r}")
        return await fetch_source(
            connector,
            source,
            stored,
            {record.id: record.key for record in held},
            elsewhere,
            full=full,
        )

    async def pull_sources(self, req: SourcePullRequest) -> Response[SourcePulled]:
        """Fetch the sources, compile their issues to events and apply them in one transaction."""
        declared = self.sources()
        warnings: list[str] = []
        skipped: dict[str, str] = {}
        if req.name is not None:
            named = declared.source(req.name)
            require_enabled(named)
            chosen = [named]
        else:
            chosen = [s for s in declared.sources.values() if s.enabled]
        fetched: list[Fetched] = []
        db = await self.store.load()
        ready: list[tuple[SourceSpec, Connector]] = []
        failed: set[str] = set()
        for source in chosen:
            credential = self.credentials.read_entry(source.base_url)
            if credential is None:
                absent = missing_credential(source.name)
                if req.name is not None:
                    raise SquadsError(absent.message())
                note = f"no stored credential; {absent.fix}"
                skipped[source.name] = note
                warnings.append(f"source {source.name!r} skipped: {note}")
                continue
            try:
                ready.append((source, await open_connector(source, credential)))
            except SquadsError as exc:
                if req.name is not None:
                    raise
                skipped[source.name] = str(exc)
                failed.add(source.name)
        for source, connector in ready:
            try:
                peers = declared.peers(source.name)
                fetched.append(
                    Fetched(
                        source,
                        await self._fetch_one_source(db, source, connector, peers, full=req.full),
                    )
                )
            except SquadsError as exc:
                if req.name is not None:
                    raise
                skipped[source.name] = str(exc)
                failed.add(source.name)
        now = clock.now().astimezone(UTC).replace(microsecond=0)
        jobs: list[CompileJob] = [
            (
                entry.source,
                lambda db, before, entry=entry: self._compile_source(
                    db, entry, now, before, dry_run=req.dry_run
                ),
            )
            for entry in fetched
        ]
        reports, applied = await self._compile_and_apply(jobs, dry_run=req.dry_run)
        out = [
            SourcePullReport(
                name=name,
                created=[],
                refreshed=0,
                unchanged=0,
                left_out=why,
                lines=[],
                failed=name in failed,
            )
            for name, why in skipped.items()
        ]
        for source, compiled in reports:
            created = sorted(
                (applied.handle_to_id[h] for h in compiled.created if h in applied.handle_to_id)
                if applied is not None
                else compiled.created
                if req.dry_run
                else set()
            )
            out.append(
                SourcePullReport(
                    name=source.name,
                    created=created,
                    refreshed=compiled.refreshed,
                    unchanged=compiled.unchanged,
                    dropped=len(compiled.dropped),
                    gone=compiled.gone,
                    held_elsewhere=compiled.held_elsewhere,
                    restricted=compiled.restricted,
                    filtered_out=compiled.filtered_out,
                    skipped_no_type=compiled.skipped_no_type,
                    left_out=None,
                    lines=compiled.lines,
                )
            )
        if applied is not None:
            warnings.extend(applied.warnings)
        return Response(data=SourcePulled(dry_run=req.dry_run, sources=out), warnings=warnings)

    async def _compile_and_apply(self, jobs: list[CompileJob], *, dry_run: bool):
        async with self.store.transaction() as db, self._deferred_item_writes():
            reports: list[tuple[SourceSpec, Compiled]] = []
            events: list[ResolvedEvent] = []
            issue_of: dict[int, str] = {}
            created: frozenset[str] = frozenset()
            for source, compile_job in jobs:
                compiled = await compile_job(db, created)
                created |= compiled.created
                shift = len(events)
                events.extend(renumbered(ev, ev.line + shift) for ev in compiled.events)
                for line, label in compiled.issue_of.items():
                    issue_of[line + shift] = label
                reports.append((source, compiled))
            for _source, compiled in reports:
                self._report_unfollowed(compiled, created)
            live = await self._without_failing_issues(db, events, issue_of, reports)
            applied = None
            if live and not dry_run:
                applied = await self._apply_events(db, live)
        if applied is not None:
            applied = await self._with_findings(applied)
        return reports, applied

    @staticmethod
    def _report_unfollowed(compiled: Compiled, created: frozenset[str]) -> None:
        """Say which links stay unfollowed once every source of the pull has compiled: a target
        a later source created is no longer one."""
        for key, targets in compiled.unfollowed:
            left = [
                target_key
                for target_id, target_key in targets
                if not any(f"{name}:{target_id}" in created for name in compiled.peers)
            ]
            if left:
                compiled.lines.append(
                    f"{key}: {len(left)} link(s) not followed, no item holds {', '.join(left)}"
                )

    async def _compile_source(
        self,
        db: SquadsDB,
        entry: Fetched,
        now: datetime,
        before: frozenset[str] = frozenset(),
        *,
        dry_run: bool = False,
    ) -> Compiled:
        compiler = Compiler(self, db, entry.source, now, before, dry_run=dry_run)
        fetch = entry.fetch
        compiler.out.unchanged += fetch.untouched
        compiler.out.restricted = fetch.restricted
        compiler.out.filtered_out = fetch.filtered_out
        compiler.out.skipped_no_type = fetch.skipped_no_type
        compiler.out.held_elsewhere = fetch.held_elsewhere
        for line in fetch.skipped:
            compiler.say(line)
        by_id = {fi.issue.id: fi for fi in fetch.changed}
        for fi in fetch.changed:
            if entry.source.accepts(fi.issue):
                await compiler.attempt(fi, fi.issue.state)
            else:
                await compiler.attempt(fi, OUT_OF_FILTER, REJECTED_BY_FILTER)
        for issue_id, found in sorted(fetch.linked.items()):
            if found is not None:
                by_id[issue_id] = found
                await compiler.attempt(found, OUT_OF_FILTER, OUTSIDE_THE_SCOPE)
                continue
            held = [db.items[seq] for seq in compiler.by_id.get((entry.source.name, issue_id), [])]
            linked_key = next((it.source.key for it in held if it.source is not None), "")
            if held and all(it.source is not None and it.source.state == GONE for it in held):
                compiler.out.unchanged += 1
            elif held:
                compiler.out.gone += 1
                compiler.out.gone_labels.add(f"{entry.source.name} {linked_key}")
            for item in held:
                assert item.source is not None
                if item.source.state != GONE:
                    compiler.say(
                        f"{item.source.key}: deleted or no longer readable; {item.id} stays"
                    )
                    record = {**item.source.model_dump(), "state": GONE}
                    compiler.emit(
                        f"{entry.source.name} {item.source.key}",
                        SourceEvent(target=item.id, record=record),
                    )
        compiler.links(by_id)
        compiler.out.peers = compiler.peers
        return compiler.out

    @staticmethod
    def _keeping_stored_time(
        db: SquadsDB, pair: tuple[ResolvedEvent, str]
    ) -> tuple[ResolvedEvent, str] | None:
        """*pair* with the ``updated_at`` of its ``source`` event set back to the stored one, or to
        ``""`` for an item this pull creates, so the next pull fetches the issue again and retries
        what was dropped; ``None`` when the record then equals the stored one, so nothing is
        written."""
        ev, label = pair
        event = ev.event
        if not isinstance(event, SourceEvent):
            return pair
        if event.record is None:
            return pair
        item = db.get(event.target)
        kept_time = item.source.updated_at if item is not None and item.source else ""
        record = {**event.record, "updated_at": kept_time}
        if item is not None and item.source is not None and item.source.model_dump() == record:
            return None
        kept = ResolvedEvent(
            line=ev.line,
            event=event.model_copy(update={"record": record}),
            op_name=ev.op_name,
            at=ev.at,
            actor=ev.actor,
        )
        return kept, label

    @staticmethod
    def _count_held(reports: list[tuple[SourceSpec, Compiled]], written: set[str]) -> None:
        """Count each held issue that was not dropped as refreshed when an event of it survives
        the pre-pass, else as unchanged."""
        for source, compiled in reports:
            for label in compiled.held_labels:
                if label[len(source.name) + 1 :] in compiled.dropped:
                    continue
                if label in written:
                    compiled.refreshed += 1
                else:
                    compiled.unchanged += 1

    async def _without_failing_issues(
        self,
        db: SquadsDB,
        events: list[ResolvedEvent],
        issue_of: dict[int, str],
        reports: list[tuple[SourceSpec, Compiled]],
    ) -> list[ResolvedEvent]:
        """*events* minus those of every issue the pre-pass refuses, each reported once."""
        pairs = [(ev, issue_of[ev.line]) for ev in events]
        live = events
        while live:
            plan = await self._plan_import(live, base=db)
            bad: dict[str, str] = {}
            dangling: dict[int, str] = {}
            for found in plan.issues:
                event, label = pairs[found.line - 1]
                if isinstance(event.event, RefEvent):
                    dangling[found.line - 1] = found.message
                else:
                    bad.setdefault(label, found.message)
            if not bad and not dangling:
                break
            for i, message in dangling.items():
                label = pairs[i][1]
                for source, compiled in reports:
                    if label.startswith(f"{source.name} "):
                        key = label[len(source.name) + 1 :]
                        compiled.lines.append(f"{key}: a link was dropped, {message}")
            for source, compiled in reports:
                for label, message in bad.items():
                    if label.startswith(f"{source.name} "):
                        key = label[len(source.name) + 1 :]
                        compiled.dropped[key] = message
                        compiled.uncount(label)
                        compiled.lines.append(f"{key}: dropped, {message}")
                        compiled.created.discard(compiled.handle_of.get(label, ""))
            held_back = {pairs[i][1] for i in dangling}
            kept = (
                self._keeping_stored_time(db, pair) if pair[1] in held_back else pair
                for i, pair in enumerate(pairs)
                if i not in dangling and pair[1] not in bad
            )
            pairs = [pair for pair in kept if pair is not None]
            live = [renumbered(ev, n) for n, (ev, _label) in enumerate(pairs, 1)]
        self._count_held(reports, {label for _ev, label in pairs})
        return live
