"""The commands that tie one item to its tracker issue: ``show --refresh``, ``source unlink``,
``source relink``, and the listing of the declared sources."""

from datetime import UTC

from squads import _aio as aio
from squads import _clock as clock
from squads import _sections as sections
from squads._api import (
    ProbeLine,
    Response,
    SourceChecked,
    SourceChecklist,
    SourceCheckRequest,
    SourceListed,
    SourceListRequest,
    SourceRefreshed,
    SourceRefreshRequest,
    SourceRelinked,
    SourceRelinkRequest,
    SourceRow,
    SourceUnlinked,
    SourceUnlinkRequest,
)
from squads._errors import SquadsError
from squads._models import (
    OUT_OF_FILTER,
    SOURCE_AUTHOR_PREFIX,
    AttributeKey,
    Item,
    SquadsDB,
    map_attribute,
    markers,
    source_of,
)
from squads._paths import number_for_id
from squads._services._comment_view import AUTHOR_HANDLE, AUTHOR_ID
from squads._services._fetch import (
    connector_for,
    fetch_issue,
    fetch_referenced_issue,
    require_credential,
    require_enabled,
)
from squads._services._item_ops import ItemOpsMixin
from squads._services._pull import (
    DESCRIPTION_VIEW,
    Compiled,
    CompileJob,
    Compiler,
    Fetched,
    PullMixin,
)
from squads._sources import (
    Expected,
    ProbeResult,
    SourceSpec,
    missing_credential,
    run_probes,
)
from squads._view_bodies import find_view_pairs
from squads._workflow import ROSTER_OPERATOR


def _address(item: Item) -> str:
    return f"{item.type} {number_for_id(item.id)}"


def _raise_if_dropped(compiled: Compiled) -> None:
    """Refuse a run whose issue the pre-pass dropped: nothing was written."""
    if compiled.dropped:
        raise SquadsError("; ".join(f"{key}: {why}" for key, why in compiled.dropped.items()))


class SourceLinksMixin(ItemOpsMixin, PullMixin):
    """The single-item counterparts of the pull, and what unlinks an item from its issue."""

    async def list_sources(self, req: SourceListRequest) -> Response[SourceListed]:
        """Every declared source with its connector, state, whether a credential is stored, and
        the items it holds."""
        del req
        declared = self.sources()
        db = await self.store.load()
        held = db.source_ids()
        rows = [
            SourceRow(
                name=name,
                connector=source.connector,
                version=source.version,
                enabled=source.enabled,
                credential=self.credentials.has_entry(source.base_url),
                items=sum(len(ids) for (owner, _), ids in held.items() if owner == name),
                newest_updated_at=max(
                    (
                        it.source.updated_at
                        for it in db.items.values()
                        if it.source is not None and it.source.name == name and it.source.updated_at
                    ),
                    default=None,
                ),
            )
            for name, source in sorted(declared.sources.items())
        ]
        return Response(data=SourceListed(sources=rows))

    async def check_sources(self, req: SourceCheckRequest) -> Response[SourceChecked]:
        """Run the probes of one declared source, or of each, disabled ones included, with the
        credential the pull reads."""
        declared = self.sources()
        chosen = (
            [declared.source(req.name)]
            if req.name is not None
            else [source for _, source in sorted(declared.sources.items())]
        )
        db = await self.store.load()
        lists = [await self._checklist(source, db) for source in chosen]
        return Response(data=SourceChecked(ok=all(entry.ok for entry in lists), sources=lists))

    async def _commenters(
        self, source: SourceSpec, db: SquadsDB
    ) -> tuple[tuple[str, str, str], ...]:
        """The authors of the comments *source* already imported, as ``(ID, handle, item)``."""
        actor = f"{SOURCE_AUTHOR_PREFIX}{source.name}"
        found: dict[tuple[str, str], str] = {}
        for item in sorted(db.items.values(), key=lambda it: it.sequence_id):
            if item.source is None or item.source.name != source.name:
                continue
            for comment in await self.comments(item.id):
                if comment.author_slug == actor and AUTHOR_ID in comment.attributes:
                    pair = (
                        comment.attributes[AUTHOR_ID],
                        comment.attributes.get(AUTHOR_HANDLE, ""),
                    )
                    found.setdefault(pair, f"a comment on {item.id}")
        return tuple((user_id, handle, where) for (user_id, handle), where in found.items())

    async def _checklist(self, source: SourceSpec, db: SquadsDB) -> SourceChecklist:
        credential = self.credentials.read_entry(source.base_url)
        results: list[ProbeResult]
        if credential is None:
            results = [missing_credential(source.name)]
        else:
            connector = connector_for(source, credential)
            held = tuple(
                (item.slug, user_id)
                for item in sorted(db.items.values(), key=lambda it: it.sequence_id)
                if item.type == ROSTER_OPERATOR
                for name, user_id in (map_attribute(item, AttributeKey.IDENTITIES) or {}).items()
                if name == source.name
            )
            expected = Expected(
                source.name, source.maps, source.filter, held, await self._commenters(source, db)
            )
            results = await aio.to_thread(
                lambda: run_probes(lambda family: connector.probes(family, expected))
            )
        return SourceChecklist(
            name=source.name,
            connector=source.connector,
            version=source.version,
            enabled=source.enabled,
            ok=not any(r.blocking for r in results),
            lines=[
                ProbeLine(family=r.family, verdict=r.verdict, text=r.text, fix=r.fix)
                for r in results
            ],
        )

    async def refresh_item(self, req: SourceRefreshRequest) -> Response[SourceRefreshed]:
        """Fetch the issue behind an item again and write what changed, in one transaction."""
        item = await self.addressed_item(req)
        record = item.source
        if record is None:
            raise SquadsError(
                f"{item.id} has no source record, so there is no issue to refresh it from"
            )
        source = self.sources().source(record.name)
        require_enabled(source)
        fetch = await fetch_issue(
            source, require_credential(self.credentials, source), record.id, record.key
        )
        entry = Fetched(source, fetch)
        now = clock.now().astimezone(UTC).replace(microsecond=0)

        async def compile_job(txn: SquadsDB, before: frozenset[str]) -> Compiled:
            current = txn.get(item.id)
            if (
                current is None
                or current.source is None
                or ((current.source.name, current.source.id) != (record.name, record.id))
            ):
                raise SquadsError(f"{item.id} changed while the issue was fetched; run it again")
            return await self._compile_source(txn, entry, now, before)

        compiled, written = await self._apply_jobs([(source, compile_job)])
        return Response(data=SourceRefreshed(id=item.id, changed=written, lines=compiled.lines))

    async def unlink_item(self, req: SourceUnlinkRequest) -> Response[SourceUnlinked]:
        """Remove an item's source record and turn its stored description into plain body prose."""
        item = await self.addressed_item(req)
        record = item.source
        if record is None:
            raise SquadsError(f"{item.id} has no source record, so there is nothing to unlink")

        def mutate(text: str, held: Item) -> tuple[str, bool]:
            region = sections.get_section(text, markers.BODY) or ""
            pair = next(
                (p for p in find_view_pairs(region) if p.parts.name == DESCRIPTION_VIEW), None
            )
            if pair is not None:
                prose = pair.inner.removeprefix("\n").removesuffix("\n")
                after = region[pair.end :]
                kept = region[: pair.start] + prose + (after if prose else after.removeprefix("\n"))
                text = sections.replace_section(text, markers.BODY, kept)
            held.source = None
            self.store.log("source", held.id, {"source": None})
            return text, True

        await self._locked_section_edit(item.id, mutate)
        warnings = (
            [
                f"{record.key} is still in the scope of source '{record.name}' and accepted by "
                "its filter: the next `sq source pull` imports it again as a new item; to "
                "prevent that, narrow the scope or the filter in sources.toml, or change the "
                "issue on the tracker so neither selects it"
            ]
            if record.state in ("open", "closed")
            else []
        )
        return Response(
            data=SourceUnlinked(id=item.id, source=record.name, key=record.key), warnings=warnings
        )

    async def relink_item(self, req: SourceRelinkRequest) -> Response[SourceRelinked]:
        """Attach an item its source created to an issue of that source and refresh it at once."""
        item = await self.addressed_item(req)
        self._refuse_relink(item, req.source)
        source = self.sources().source(req.source)
        require_enabled(source)
        issue_id, fetch = await fetch_referenced_issue(
            source, require_credential(self.credentials, source), req.issue
        )
        fetched = fetch.changed[0] if fetch.changed else fetch.linked[issue_id]
        assert fetched is not None
        accepted = bool(fetch.changed) and source.accepts(fetched.issue)
        state = fetched.issue.state if accepted else OUT_OF_FILTER
        now = clock.now().astimezone(UTC).replace(microsecond=0)

        async def compile_job(txn: SquadsDB, before: frozenset[str]) -> Compiled:
            current = txn.get(item.id)
            if current is None or current.source is not None:
                raise SquadsError(f"{item.id} changed while the issue was fetched; run it again")
            held = txn.source_ids()
            for name in sorted(self.sources().peers(source.name)):
                for seq in held.get((name, issue_id), []):
                    raise SquadsError(
                        f"issue {req.issue!r} of source {source.name!r} is already held by "
                        f"{txn.items[seq].id} of source {name!r}"
                    )
            compiler = Compiler(self, txn, source, now, before)
            compiler.by_id[(source.name, issue_id)] = [current.sequence_id]
            label = f"{source.name} {fetched.issue.key}"
            await compiler.refresh(label, current, fetched, state)
            compiler.links({issue_id: fetched})
            return compiler.out

        compiled, _written = await self._apply_jobs([(source, compile_job)])
        return Response(
            data=SourceRelinked(
                id=item.id, source=source.name, key=fetched.issue.key, lines=compiled.lines
            )
        )

    @staticmethod
    def _refuse_relink(item: Item, source: str) -> None:
        """Refuse an item that a relink to *source* cannot take, naming why."""
        address = _address(item)
        if item.source is not None:
            raise SquadsError(
                f"{item.id} still holds a source record ({item.source.name} {item.source.key}); "
                f"run `sq {address} source unlink` first"
            )
        created_by = source_of(item.author or "")
        if created_by is None:
            raise SquadsError(f"{item.id} was not created by a source, so it cannot be relinked")
        if created_by != source:
            raise SquadsError(
                f"{item.id} was created by source {created_by!r}, not {source!r}; "
                f"relink it to {created_by!r}"
            )

    async def _apply_jobs(self, jobs: list[CompileJob]) -> tuple[Compiled, bool]:
        reports, applied = await self._compile_and_apply(jobs, dry_run=False)
        compiled = reports[0][1]
        _raise_if_dropped(compiled)
        return compiled, applied is not None
