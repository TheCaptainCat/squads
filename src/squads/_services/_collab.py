"""Discussion: comments, author resolution, and the @mention inbox."""

import re
from dataclasses import dataclass, field

from squads import _aio
from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._omission import Omission
from squads._models._participants import ANONYMOUS_SLUG, refuse_system_actor
from squads._paths import SquadPaths
from squads._services._base import ServiceCore, reject_markers
from squads._services._results import (
    EditedComment,
    FoundComment,
    InboxHit,
    InboxLine,
    RemovedComments,
    SearchHit,
    SearchResult,
    UnreadableItems,
)
from squads._workflow import WorkflowSpec
from squads._workflow._models import ROSTER_OPERATOR, ROSTER_ROLE

_SNIPPET_WIDTH = 160
_SNIPPET_LEAD = 40
"""Chars of left context kept before the match once the window has to shift off column 0."""


async def _read_or_report(paths: SquadPaths, item: Item, unreadable: UnreadableItems) -> str | None:
    """*item*'s file text, or ``None`` after recording why it could not be obtained.

    The per-file guard both corpus walks in this module go through, so one bad item costs its
    own results and nothing else (see :data:`UnreadableItems`).

    It takes the **item**, not a resolved path, deliberately. Turning the item's stored ``path``
    into an absolute one is itself a failing step: ``SquadPaths.abspath`` resolves symlinks and
    raises :class:`~squads._errors.InvalidIdError` (a ``SquadsError``) for anything landing
    outside the squad folder — reachable from an item file replaced by a symlink to an
    out-of-squad target, and from a tampered or badly-imported index ``path`` with no symlink
    involved at all. Resolving in the caller's argument list put that call *outside* the guard,
    so it aborted the whole walk exactly the way an unguarded read would, on shapes this
    function was believed to cover. Owning both halves of "get me this item's text" is what
    makes "one bad item is one reported line" true rather than nearly true.

    The reported/skipped cases, mirroring the board store's split because they are the same
    questions:

    - a path that will not resolve inside the squad folder — reported, named by item id, since
      there is no trustworthy path to name it by;
    - a decode failure or an OS refusal (permission, I/O) from ``_aio.read_text``, which
      surfaces as a :class:`SquadsError` naming the file — reported;
    - a ``FileNotFoundError`` is present-vs-absent, not another unreadable shape. A broken
      symlink is a *present* dirent whose target read failed, and is reported like any other
      unreadable file; a file the index still lists but that is genuinely gone is skipped with
      nothing said here — the missing direction is ``repair``'s report to make, and saying it
      again on every search would just be noise.
    """
    try:
        path = item_file(paths, item)
    except SquadsError as exc:
        unreadable.append(Omission(source=item.id, message=f"{item.id}: {exc}"))
        return None
    try:
        return await _aio.read_text(path)
    except FileNotFoundError:
        if await _aio.path_is_symlink(path):
            message = f"{path} is a broken symlink (its target does not exist)"
            unreadable.append(Omission(source=item.id, message=message))
        return None
    except SquadsError as exc:
        unreadable.append(Omission(source=item.id, message=str(exc)))
        return None


def _frontmatter_end_line(text: str) -> int:
    """1-based line number of the frontmatter block's closing ``---``, or 0 if there is none."""
    lines = sections.split_lines(text)
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return i + 1
    return 0


@dataclass
class _Region:
    """A named, line-bounded region of an item file, used to attribute a search hit.

    ``comment_headers`` (only populated for discussion regions) is ``(line_no, timestamp,
    author, hash)`` for each comment header found in the region, in file order — the basis for
    naming *which* comment a hit landed in.

    ``is_subentity`` is set at construction by :func:`_build_regions` (``True`` for every
    region added inside its sub-entity loop, ``False`` for the three top-level ones) — the
    authoritative sub-entity-vs-item-level signal a caller reads instead of re-deriving it from
    the ``region`` string's shape (e.g. testing for a colon), which is only safe by the
    accident that no item-level region name happens to contain one.
    """

    start: int
    end: int
    region: str
    comment_headers: list[tuple[int, str, str, str]] = field(
        default_factory=lambda: list[tuple[int, str, str, str]]()
    )
    is_subentity: bool = False


def _scan_comment_headers(
    lines: list[str], bounds: tuple[int, int], sequence_id: int, scope: str
) -> list[tuple[int, str, str, str]]:
    """Comment headers strictly inside a region's ``(open_line, close_line)`` marker bounds, as
    ``(line_no, timestamp, name, hash)``."""
    start, end = bounds
    region = "\n".join(lines[start : end - 1])
    found = discussion.split_discussion(region, sequence_id=sequence_id, scope=scope)
    return [(start + 1 + c.span[0], c.timestamp, c.author, c.hash) for c in found]


def _build_regions(text: str, item: Item, spec: WorkflowSpec) -> list[_Region]:
    """The named regions of ``item``'s file: top-level body/discussion, plus each sub-entity's
    own block (heading+body) and discussion, keyed by ``<kind>:<local_id>``.

    Regions can nest (a sub-entity's discussion sits inside its block); classification always
    picks the narrowest containing region, so nesting order here doesn't matter.
    """
    lines = sections.split_lines(text)
    regions: list[_Region] = []

    def _add(
        tag: str,
        region_name: str,
        *,
        with_comments: bool = False,
        is_subentity: bool = False,
        scope: str = "",
    ) -> None:
        bounds = sections.region_lines(text, tag)
        if bounds is None:
            return
        headers = (
            _scan_comment_headers(lines, bounds, item.sequence_id, scope) if with_comments else []
        )
        regions.append(_Region(bounds[0], bounds[1], region_name, headers, is_subentity))

    _add(markers.BODY, "body")
    _add(markers.DISCUSSION, "discussion", with_comments=True)

    kind = spec.item_subentity_kind(item.type)
    if kind:
        for se in item.subentities:
            tag = f"{kind}:{se.local_id}"
            _add(tag, tag, is_subentity=True)  # block-level fallback: the heading line
            _add(f"{tag}:body", tag, is_subentity=True)
            _add(
                markers.discussion_tag(tag),
                f"{tag}:discussion",
                with_comments=True,
                is_subentity=True,
                scope=tag,
            )

    return regions


def _authored_field_lines(item: Item, needle: str) -> list[InboxLine]:
    """Mention hits in the item's *own authored* frontmatter fields, as item-level lines.

    ``title``, ``description`` and ``labels`` are first-class authored input (``sq create``,
    ``sq update --desc``/``--label``) whose only copy in the file is inside the frontmatter
    block — which the line scan excludes. So they are surfaced here explicitly, exactly the way
    :meth:`CollabMixin.search` surfaces the same fields, and item-level (``region=None``)
    because that is genuinely what they are.

    The exclusion is right for a *sub-entity's* title, which recurs in its own heading region
    and is therefore already attributed there; an item's own title has no second occurrence
    anywhere, so excluding the block removed its only copy. That asymmetry is the whole reason
    this exists — the two must not be treated as one thing.

    Everything else in the frontmatter block is sq-managed machine metadata (ids, statuses,
    slugs, the ``extra`` config map), where an ``@`` token is not a mention anyone authored.
    See :meth:`CollabMixin.inbox` for what that means for admission.
    """
    values = [item.title, item.description, *item.labels]
    return [InboxLine(text=v.strip(), region=None) for v in values if needle in v.lower()]


def _classify_line(regions: list[_Region], line_no: int) -> _Region | None:
    """The narrowest region containing ``line_no``, or ``None`` if it falls outside all of them."""
    containing = [r for r in regions if r.start <= line_no <= r.end]
    return min(containing, key=lambda r: r.end - r.start) if containing else None


def _windowed_snippet(lines: list[str], line_no: int, needle: str) -> str:
    """In-context text around ``line_no``: itself plus a neighbor on each side, marker lines
    dropped, collapsed to one line and capped at :data:`_SNIPPET_WIDTH` characters.

    Windowed around the first occurrence of ``needle`` (case-insensitive) so a match deep in a
    long line stays inside the returned snippet instead of being truncated out."""
    idx = line_no - 1
    window = [
        s
        for i in range(max(0, idx - 1), min(len(lines), idx + 2))
        if (s := lines[i].strip()) and not s.startswith("<!--")
    ]
    text = " / ".join(window) if window else lines[idx].strip()
    if len(text) <= _SNIPPET_WIDTH:
        return text
    match_idx = text.lower().find(needle.lower()) if needle else -1
    if match_idx == -1 or match_idx + len(needle) <= _SNIPPET_WIDTH:
        return text[: _SNIPPET_WIDTH - 1].rstrip() + "…"
    start = max(0, match_idx - _SNIPPET_LEAD)
    end = min(len(text), start + _SNIPPET_WIDTH)
    start = max(0, end - _SNIPPET_WIDTH)
    snippet = text[start:end].strip()
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{snippet}{suffix}"


def _comment_at_or_before(
    headers: list[tuple[int, str, str, str]], line_no: int
) -> tuple[int, str, str, str] | None:
    """The last ``(ordinal, timestamp, author, hash)`` header at or before ``line_no``, if any."""
    found: tuple[int, str, str, str] | None = None
    for ordinal, (header_line, ts, author, digest) in enumerate(headers, start=1):
        if header_line > line_no:
            break
        found = (ordinal, ts, author, digest)
    return found


def _hit_for_line(regions: list[_Region], lines: list[str], line_no: int, needle: str) -> SearchHit:
    """Build the :class:`SearchHit` for a matched line, resolving its region/location/snippet."""
    region = _classify_line(regions, line_no)
    if region is None:
        return SearchHit(
            region="other", location="other", snippet=_windowed_snippet(lines, line_no, needle)
        )
    if region.comment_headers:
        hit_comment = _comment_at_or_before(region.comment_headers, line_no)
        if hit_comment is not None:
            ordinal, ts, author, digest = hit_comment
            token = f"{region.region}#{ordinal}"
            location = f"{region.region} — comment {ordinal} ({author}, {ts})"
            snippet = f"[{ts}] {author}: {lines[line_no - 1].strip()}"
            return SearchHit(region=token, location=location, snippet=snippet, hash=digest)
    return SearchHit(
        region=region.region,
        location=region.region,
        snippet=_windowed_snippet(lines, line_no, needle),
    )


def _reflog_comments(
    group: list[discussion.Comment], tag: str, after_hash: str | None = None
) -> dict[str, list[dict[str, str]]]:
    """The reflog delta of a comment change: one entry per comment touched, as it was."""
    entries = [
        {
            "author": c.author_slug,
            "hash": c.hash,
            "region": tag,
            "ts": c.timestamp,
            "before": c.body,
        }
        | ({} if after_hash is None else {"after_hash": after_hash})
        for c in group
    ]
    return {"comments": entries}


@dataclass
class _Located:
    """A hash resolved inside the text of one item file."""

    scope: str
    tag: str
    region: str  # the raw inner text of the scope's discussion section
    comments: list[discussion.Comment]  # every comment of the scope
    group: list[discussion.Comment]  # the duplicate group the hash addresses


_TERMINATOR_RE = re.compile(r"\r\n|\r|\n")


def _shown_by_hash(comments: list[discussion.Comment]) -> dict[str, str]:
    """Each hash of a discussion mapped to its displayed form."""
    return {c.hash: s for c, s in zip(comments, discussion.short_hashes(comments), strict=True)}


def _scope_of(sub: tuple[str, str] | None) -> str:
    return "" if sub is None else f"{sub[0]}:{sub[1]}"


def _require_comment_author(group: list[discussion.Comment], as_slug: str, *, where: str) -> None:
    """Refuse unless the group's author slug is ``as_slug``: a guard against a slip, not a
    permission (``--as`` is not authenticated)."""
    slug = group[0].author_slug
    if slug != as_slug:
        raise SquadsError(f"{where} was written by {slug}; --as {as_slug} cannot change it")


class CollabMixin(ServiceCore):
    async def comment(
        self,
        item_id: str,
        messages: list[str],
        *,
        as_slug: str = ANONYMOUS_SLUG,
        story: str | None = None,
        subtask: str | None = None,
        finding: str | None = None,
        sub: tuple[str, str] | None = None,
    ) -> Item:
        """Opens its own transaction, then delegates to :meth:`_comment_core` — the bulk
        importer calls that core directly (its own transaction is already open)."""
        async with self.store.transaction() as db:
            return await self._comment_core(
                db,
                item_id,
                messages,
                as_slug=as_slug,
                story=story,
                subtask=subtask,
                finding=finding,
                sub=sub,
            )

    async def _comment_core(
        self,
        db: SquadsDB,
        item_id: str,
        messages: list[str],
        *,
        as_slug: str = ANONYMOUS_SLUG,
        story: str | None = None,
        subtask: str | None = None,
        finding: str | None = None,
        sub: tuple[str, str] | None = None,
    ) -> Item:
        """The comment mutation core: takes an already-open transaction's ``db`` (so the author
        display name resolves against in-memory state, not a fresh disk load — see
        :meth:`~squads._services._base.ServiceCore._author_of`)."""
        refuse_system_actor(as_slug)
        if not messages:
            raise SquadsError("a comment needs at least one -m message")
        for msg in messages:
            reject_markers(msg, "comment message")
        tag = self._discussion_tag(story, subtask, finding, sub)
        scope = "" if tag == markers.DISCUSSION else tag.removesuffix(f":{markers.DISCUSSION}")
        now_iso = clock.iso(clock.now())
        entry = discussion.format_comment(now_iso, as_slug, self._author_of(db, as_slug), messages)

        def mutate(text: str, _item: Item) -> tuple[str, bool]:
            region = sections.get_section(text, tag)
            if region is None:
                raise SquadsError(
                    f"no discussion section {tag!r} in {item_id} (was it scaffolded?)"
                )
            self._refuse_duplicate_comment(_item, region, scope, as_slug, now_iso, entry)
            self.store.log(
                "comment",
                _item.id,
                {"author": as_slug},
            )
            return sections.append_to_section(text, tag, entry), True

        item, _changed = await self._section_edit_core(db, item_id, mutate)
        return item

    # ------------------------------------------------------------------ comments by hash
    def _discussion_scopes(self, item: Item) -> list[tuple[str, str]]:
        """``(scope, region tag)`` for each of the item's discussions."""
        scopes = [("", markers.DISCUSSION)]
        kind = self.spec.item_subentity_kind(item.type)
        if kind:
            for se in item.subentities:
                scope = f"{kind}:{se.local_id}"
                scopes.append((scope, markers.discussion_tag(scope)))
        return scopes

    def _locate_comment(
        self, item: Item, text: str, token: str, sub: tuple[str, str] | None
    ) -> _Located:
        """Resolve a hash prefix to its duplicate group inside the discussion it is addressed
        in, refusing one that lives in another discussion of the item."""
        want = _scope_of(sub)
        parsed: dict[str, _Located] = {}
        for scope, tag in self._discussion_scopes(item):
            region = sections.get_section(text, tag)
            if region is None:
                continue
            cmts = discussion.split_discussion(region, sequence_id=item.sequence_id, scope=scope)
            parsed[scope] = _Located(scope, tag, region, cmts, [])
        here = parsed.get(want)
        if here is None:
            raise SquadsError(
                f"no discussion section for {sub[1] if sub else 'the item'} in {item.id}"
            )
        elsewhere: list[discussion.OtherScope] = []
        for scope, other in parsed.items():
            if scope == want:
                continue
            base = f"sq {item.type} {item.sequence_id}"
            if scope == "":
                elsewhere.append(
                    discussion.OtherScope(
                        f"{item.id}'s discussion", f"{base} comment", other.comments
                    )
                )
                continue
            kind, local_id = scope.split(":", 1)
            num = "".join(ch for ch in local_id if ch.isdigit())
            elsewhere.append(
                discussion.OtherScope(
                    f"{kind} {local_id}", f"{base} {kind} {num} comment", other.comments
                )
            )
        where = f"{item.id}'s discussion" if sub is None else f"{item.id} {sub[1]}'s discussion"
        here.group = discussion.resolve_hash(here.comments, token, where=where, elsewhere=elsewhere)
        return here

    def _refuse_legacy_headers(self, item: Item, text: str) -> None:
        """Refuse when any discussion of the item holds a column-0 ``- [`` line the grammar does
        not read: it would be folded into the comment above and travel with an edit or removal."""
        for _scope, tag in self._discussion_scopes(item):
            region = sections.get_section(text, tag)
            if region is None:
                continue
            bad = discussion.legacy_header_lines(region)
            if bad:
                open_at = text.find(markers.open_marker(tag))
                marker_line = len(_TERMINATOR_RE.findall(text, 0, open_at)) + 1
                line_no, line = marker_line + bad[0][0] - 1, bad[0][1]
                raise SquadsError(
                    f"{item.path} line {line_no} looks like a comment header but is not in the "
                    f"current format ({line!r}); fix or remove it first"
                )

    async def _require_live_author(self, slug: str) -> None:
        """Refuse a slug that is not a live participant: a retired author's comments stay
        frozen until the author is reactivated, whoever calls."""
        if slug == ANONYMOUS_SLUG:
            return
        live = {r.slug for r in await self.roster()} | {o.slug for o in await self.operators()}
        if slug in live:
            return
        for kind in (ROSTER_ROLE, ROSTER_OPERATOR):
            entry = await self.roster_item(kind, slug)
            if entry is not None:
                target = self.spec.live_initial(kind)
                raise SquadsError(
                    f"{slug!r} ({entry.id}) is retired; reactivate it with "
                    f"`sq {kind} {slug} status {target}`"
                )
        raise SquadsError(f"unknown slug {slug!r}")

    async def find_comment(
        self,
        item_id: str,
        token: str,
        *,
        sub: tuple[str, str] | None = None,
        as_slug: str | None = None,
    ) -> FoundComment:
        """The comment (or duplicate group) a hash prefix addresses in one discussion; with
        ``as_slug``, refused unless that slug wrote it."""
        item = await self.get(item_id)
        text = await self._read_item_file(item, item_file(self.paths, item))
        located = self._locate_comment(item, text, token, sub)
        shorts = _shown_by_hash(located.comments)
        shown = shorts[located.group[0].hash]
        if as_slug is not None:
            _require_comment_author(located.group, as_slug, where=f"{shown} on {item.id}")
        return FoundComment(item, located.scope, located.group, shown)

    async def edit_comment(
        self,
        item_id: str,
        token: str,
        messages: list[str],
        *,
        as_slug: str,
        sub: tuple[str, str] | None = None,
    ) -> EditedComment:
        """Replace the text of the comment a hash addresses, as its author.

        The header keeps its timestamp, slug and name and gains the edit mark; a duplicate group
        collapses into its first member. Unchanged text writes nothing. The result carries the
        new hash, computed from the lines as written.
        """
        refuse_system_actor(as_slug)
        await self._require_live_author(as_slug)
        if not messages:
            raise SquadsError("an edit needs at least one -m message")
        for msg in messages:
            reject_markers(msg, "comment message")
        done: list[EditedComment] = []

        def mutate(text: str, item: Item) -> tuple[str, bool]:
            self._refuse_legacy_headers(item, text)
            loc = self._locate_comment(item, text, token, sub)
            first = loc.group[0]
            shorts = _shown_by_hash(loc.comments)
            _require_comment_author(loc.group, as_slug, where=f"{shorts[first.hash]} on {item.id}")
            entry = discussion.format_comment(
                first.timestamp,
                first.author_slug,
                first.author,
                messages,
                edited_ts=clock.iso(clock.now()),
            )
            new_hash = discussion.comment_hash(
                item.sequence_id,
                loc.scope,
                first.author_slug,
                first.timestamp,
                discussion.canonical_text(entry.split("\n")[1:]),
            )
            if new_hash == first.hash:
                done.append(
                    EditedComment(
                        item, loc.scope, first, shorts[first.hash], first, shorts[first.hash], False
                    )
                )
                return text, False
            clash = next((c for c in loc.comments if c.hash == new_hash), None)
            if clash is not None:
                raise SquadsError(
                    f"{item.id} already has this comment by {clash.author_slug} "
                    f"at {clash.timestamp} ({new_hash[:7]})"
                )
            changes: list[tuple[discussion.Comment, str | None]] = [(first, entry)]
            changes += [(c, None) for c in loc.group[1:]]
            region = discussion.replace_comments(
                loc.region, changes, sequence_id=item.sequence_id, scope=loc.scope
            )
            after = discussion.split_discussion(
                region, sequence_id=item.sequence_id, scope=loc.scope
            )
            new = next((c for c in after if c.hash == new_hash), None)
            if new is None:
                raise SquadsError(f"the edit of {first.hash[:7]} on {item.id} did not round-trip")
            new_shown = _shown_by_hash(after)
            self.store.log("comment_edit", item.id, _reflog_comments(loc.group, loc.tag, new_hash))
            done.append(
                EditedComment(
                    item, loc.scope, first, shorts[first.hash], new, new_shown[new_hash], True
                )
            )
            return sections.replace_section(text, loc.tag, region), True

        await self._locked_section_edit(item_id, mutate)
        return done[0]

    async def remove_comment(
        self,
        item_id: str,
        token: str,
        *,
        as_slug: str,
        sub: tuple[str, str] | None = None,
    ) -> RemovedComments:
        """Delete the comment a hash addresses (every member of a duplicate group), as its
        author."""
        refuse_system_actor(as_slug)
        await self._require_live_author(as_slug)
        done: list[RemovedComments] = []

        def mutate(text: str, item: Item) -> tuple[str, bool]:
            self._refuse_legacy_headers(item, text)
            loc = self._locate_comment(item, text, token, sub)
            shorts = _shown_by_hash(loc.comments)
            shown = shorts[loc.group[0].hash]
            _require_comment_author(loc.group, as_slug, where=f"{shown} on {item.id}")
            region = discussion.replace_comments(
                loc.region,
                [(c, None) for c in loc.group],
                sequence_id=item.sequence_id,
                scope=loc.scope,
            )
            self.store.log("comment_remove", item.id, _reflog_comments(loc.group, loc.tag))
            done.append(RemovedComments(item, loc.scope, loc.group, shown))
            return sections.replace_section(text, loc.tag, region), True

        await self._locked_section_edit(item_id, mutate)
        return done[0]

    @staticmethod
    def _refuse_duplicate_comment(
        item: Item, region: str, scope: str, slug: str, ts: str, entry: str
    ) -> None:
        """Refuse a comment equal to one already in its discussion: same author, second and text."""
        new_hash = discussion.comment_hash(
            item.sequence_id, scope, slug, ts, discussion.canonical_text(entry.split("\n")[1:])
        )
        existing = discussion.split_discussion(region, sequence_id=item.sequence_id, scope=scope)
        if any(c.hash == new_hash for c in existing):
            raise SquadsError(
                f"{item.id} already has this comment by {slug} at {ts} ({new_hash[:7]})"
            )

    @staticmethod
    def _discussion_tag(
        story: str | None,
        subtask: str | None,
        finding: str | None,
        sub: tuple[str, str] | None = None,
    ) -> str:
        """Resolve the discussion region to append to.

        ``story``/``subtask``/``finding`` are the built-in kinds' named params;
        ``sub`` is the generic ``(kind, local_id)`` pair the CLI's
        spec-driven sub-entity comment verb uses for any kind, built-in or custom.
        """
        if sum(bool(t) for t in (story, subtask, finding, sub)) > 1:
            raise SquadsError("target only one of --story / --subtask / --finding")
        if sub is not None:
            kind, local_id = sub
            return markers.discussion_tag(f"{kind}:{local_id}")
        if story:
            return markers.discussion_tag(markers.story_tag(story))
        if subtask:
            return markers.discussion_tag(markers.subtask_tag(subtask))
        if finding:
            return markers.discussion_tag(markers.finding_tag(finding))
        return markers.DISCUSSION

    async def inbox(self, slug: str) -> tuple[list[InboxHit], UnreadableItems]:
        """Open items whose body/discussion mentions ``@slug``, with the matching lines.

        Attribution only — mention-driven, not assignee-driven: it answers "who was called
        out", not "who owns this" (a different, out-of-scope view). Each matched line carries
        the sub-entity region it falls in, when any — ``region=None`` for an item-level mention,
        so the two are distinguishable. This is narrower than `search`'s locator vocabulary,
        not the same one: a sub-entity hit is spelled identically
        (``<kind>:<local_id>[:discussion#<n>]``), but every item-level region `search`
        distinguishes (``body``, ``discussion``, ``discussion#<n>``, ``other``) collapses here
        to the single ``None``, because attributing sub-entity-vs-item is the only distinction
        this surface makes.

        The raw frontmatter block is excluded from the *line scan* — a sub-entity's own
        ``title`` lives there, and would otherwise surface as an unattributed item-level
        mention, never authored text a human wrote in place. The item's own authored
        frontmatter fields are not sq-managed and *are* reported — see
        :func:`_authored_field_lines`, which surfaces them explicitly rather than by line.

        **An item is reported only if it contributes at least one line.** A hit with no lines is
        not a report, it is a puzzle: the human render prints the item with nothing under it and
        no clue what called the reader out, and a per-line ``--json`` consumer renders an empty
        entry. That is what you get whenever the admission gate is wider than what the scan can
        emit, so the gate is the emit itself — ``extract_mentions`` (which reads the whole file,
        frontmatter included) stays only as the cheap prefilter that skips the region build.
        The residual case it admits and nothing emits is a mention inside sq-managed metadata,
        which is not a mention at all; the item is left out, never listed empty.

        Returns the hits plus one message per item file that could not be read (see
        :data:`UnreadableItems`) — a corrupt or unreadable item costs its own mentions, never
        the whole inbox.
        """
        slug = slug.lstrip("@").lower()
        out: list[InboxHit] = []
        unreadable: UnreadableItems = []
        for item in await self.list_items():
            if not self.spec.is_open(item.status):
                continue
            text = await _read_or_report(self.paths, item, unreadable)
            if text is None:
                continue
            if slug not in discussion.extract_mentions(text):
                continue
            lines = sections.split_lines(text)
            regions = _build_regions(text, item, self.spec)
            needle = f"@{slug}"
            matched: list[InboxLine] = _authored_field_lines(item, needle)
            for line_no in range(_frontmatter_end_line(text) + 1, len(lines) + 1):
                raw = lines[line_no - 1]
                if needle not in raw.lower():
                    continue
                region_obj = _classify_line(regions, line_no)
                hit = _hit_for_line(regions, lines, line_no, needle)
                region = hit.region if region_obj is not None and region_obj.is_subentity else None
                found = (
                    _comment_at_or_before(region_obj.comment_headers, line_no)
                    if region_obj is not None
                    else None
                )
                matched.append(
                    InboxLine(text=raw.strip(), region=region, hash=found[3] if found else None)
                )
            if not matched:
                continue
            out.append(InboxHit(item=item, lines=matched))
        return out, unreadable

    async def search(
        self, text: str, *, item_type: str | None = None, status: str | None = None
    ) -> tuple[list[SearchResult], UnreadableItems]:
        """Items whose title, summary, or body/discussion contains ``text`` (case-insensitive).

        ``item_type``/``status`` AND-compose with the query (the same filter dimensions
        ``list_items`` exposes to ``sq list``/``sq tree``). Each result's hits carry the
        region they matched — see :class:`SearchHit`.

        Returns the results plus one message per item file that could not be read (see
        :data:`UnreadableItems`). Such an item still contributes whatever the *index* already
        knows — a title or description match needs no file read — so it drops out of the
        answer only as far as it actually has to.
        """
        needle = text.strip().lower()
        if not needle:
            raise SquadsError("search needs a non-empty query")
        out: list[SearchResult] = []
        unreadable: UnreadableItems = []
        for item in await self.list_items(item_type=item_type, status=status):
            hits: list[SearchHit] = []
            if item.title and needle in item.title.lower():
                hits.append(SearchHit(region="title", location="title", snippet=item.title.strip()))
            if item.description and needle in item.description.lower():
                hits.append(
                    SearchHit(
                        region="description",
                        location="description",
                        snippet=item.description.strip(),
                    )
                )
            full_text = await _read_or_report(self.paths, item, unreadable)
            if full_text is not None:
                lines = sections.split_lines(full_text)
                regions = _build_regions(full_text, item, self.spec)
                for line_no in range(_frontmatter_end_line(full_text) + 1, len(lines) + 1):
                    raw = lines[line_no - 1]
                    if raw.strip() and needle in raw.lower():
                        hits.append(_hit_for_line(regions, lines, line_no, needle))
            if hits:
                out.append(SearchResult(item=item, hits=hits))
        return out, unreadable
