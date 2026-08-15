"""Discussion: comments, author resolution, and the @mention inbox."""

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
from squads._paths import SquadPaths
from squads._services._base import ServiceCore, reject_markers
from squads._services._results import (
    InboxHit,
    InboxLine,
    SearchHit,
    SearchResult,
    UnreadableItems,
)
from squads._workflow import WorkflowSpec

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
        unreadable.append(f"{item.id}: {exc}")
        return None
    try:
        return await _aio.read_text(path)
    except FileNotFoundError:
        if await _aio.path_is_symlink(path):
            unreadable.append(f"{path} is a broken symlink (its target does not exist)")
        return None
    except SquadsError as exc:
        unreadable.append(str(exc))
        return None


def _frontmatter_end_line(text: str) -> int:
    """1-based line number of the frontmatter block's closing ``---``, or 0 if there is none."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return i + 1
    return 0


@dataclass
class _Region:
    """A named, line-bounded region of an item file, used to attribute a search hit.

    ``comment_headers`` (only populated for discussion regions) is ``(line_no, timestamp,
    author)`` for each comment header found in the region, in file order — the basis for
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
    comment_headers: list[tuple[int, str, str]] = field(
        default_factory=lambda: list[tuple[int, str, str]]()
    )
    is_subentity: bool = False


def _scan_comment_headers(lines: list[str], bounds: tuple[int, int]) -> list[tuple[int, str, str]]:
    """Comment headers strictly inside a region's ``(open_line, close_line)`` marker bounds."""
    start, end = bounds
    headers: list[tuple[int, str, str]] = []
    for line_no in range(start + 1, end):
        m = discussion.match_comment_header(lines[line_no - 1].strip())
        if m is not None:
            headers.append((line_no, m[0], m[1]))
    return headers


def _build_regions(text: str, item: Item, spec: WorkflowSpec) -> list[_Region]:
    """The named regions of ``item``'s file: top-level body/discussion/summary, plus each
    sub-entity's own block (heading+body) and discussion, keyed by ``<kind>:<local_id>``.

    Regions can nest (a sub-entity's discussion sits inside its block); classification always
    picks the narrowest containing region, so nesting order here doesn't matter.
    """
    lines = text.splitlines()
    regions: list[_Region] = []

    def _add(
        tag: str, region_name: str, *, with_comments: bool = False, is_subentity: bool = False
    ) -> None:
        bounds = sections.region_lines(text, tag)
        if bounds is None:
            return
        headers = _scan_comment_headers(lines, bounds) if with_comments else []
        regions.append(_Region(bounds[0], bounds[1], region_name, headers, is_subentity))

    _add(markers.BODY, "body")
    _add(markers.SUMMARY, "summary")
    _add(markers.DISCUSSION, "discussion", with_comments=True)

    kind = spec.item_subentity_kind(item.type)
    if kind:
        for se in item.subentities:
            tag = f"{kind}:{se.local_id}"
            _add(tag, tag, is_subentity=True)  # block-level fallback: heading + head badge line
            _add(f"{tag}:body", tag, is_subentity=True)
            _add(
                markers.discussion_tag(tag),
                f"{tag}:discussion",
                with_comments=True,
                is_subentity=True,
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
    headers: list[tuple[int, str, str]], line_no: int
) -> tuple[int, str, str] | None:
    """The last ``(ordinal, timestamp, author)`` header at or before ``line_no``, if any."""
    found: tuple[int, str, str] | None = None
    for ordinal, (header_line, ts, author) in enumerate(headers, start=1):
        if header_line > line_no:
            break
        found = (ordinal, ts, author)
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
            ordinal, ts, author = hit_comment
            token = f"{region.region}#{ordinal}"
            location = f"{region.region} — comment {ordinal} ({author}, {ts})"
            snippet = f"[{ts}] {author}: {lines[line_no - 1].strip()}"
            return SearchHit(region=token, location=location, snippet=snippet)
    return SearchHit(
        region=region.region,
        location=region.region,
        snippet=_windowed_snippet(lines, line_no, needle),
    )


class CollabMixin(ServiceCore):
    async def comment(
        self,
        item_id: str,
        messages: list[str],
        *,
        as_slug: str = "operator",
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
        as_slug: str = "operator",
        story: str | None = None,
        subtask: str | None = None,
        finding: str | None = None,
        sub: tuple[str, str] | None = None,
    ) -> Item:
        """The comment mutation core: takes an already-open transaction's ``db`` (so the author
        display name resolves against in-memory state, not a fresh disk load — see
        :meth:`~squads._services._base.ServiceCore._author_of`)."""
        if not messages:
            raise SquadsError("a comment needs at least one -m message")
        for msg in messages:
            reject_markers(msg, "comment message")
        tag = self._discussion_tag(story, subtask, finding, sub)
        entry = discussion.format_comment(
            clock.iso(clock.now()), self._author_of(db, as_slug), messages
        )

        def mutate(text: str, _item: Item) -> str:
            if not sections.has_section(text, tag):
                raise SquadsError(
                    f"no discussion section {tag!r} in {item_id} (was it scaffolded?)"
                )
            self.store.log(
                "comment",
                _item.id,
                {"author": as_slug},
            )
            return sections.append_to_section(text, tag, entry)

        return await self._section_edit_core(db, item_id, mutate)

    @staticmethod
    def _discussion_tag(
        story: str | None,
        subtask: str | None,
        finding: str | None,
        sub: tuple[str, str] | None = None,
    ) -> str:
        """Resolve the discussion region to append to.

        ``story``/``subtask``/``finding`` are the built-in kinds' historical named params
        (kept for existing call sites); ``sub`` is the generic ``(kind, local_id)`` pair the
        CLI's spec-driven sub-entity comment verb uses for any kind, built-in or custom.
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

        Two sq-managed sources are excluded from the *line scan*, because neither is ever
        authored text and reporting them would misattribute or duplicate a real hit: the raw
        frontmatter block (a sub-entity's own ``title`` lives there, and would otherwise surface
        as an unattributed item-level mention) and the ``:summary`` roll-up table (a rendered
        duplicate of each sub-entity's own title, already attributed via its heading region).
        The item's own authored frontmatter fields are not sq-managed and *are* reported — see
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
            lines = text.splitlines()
            regions = _build_regions(text, item, self.spec)
            needle = f"@{slug}"
            matched: list[InboxLine] = _authored_field_lines(item, needle)
            for line_no in range(_frontmatter_end_line(text) + 1, len(lines) + 1):
                raw = lines[line_no - 1]
                if needle not in raw.lower():
                    continue
                region_obj = _classify_line(regions, line_no)
                if region_obj is not None and region_obj.region == "summary":
                    continue  # sq-managed roll-up table; duplicates the sub-entity's own hit
                hit = _hit_for_line(regions, lines, line_no, needle)
                region = hit.region if region_obj is not None and region_obj.is_subentity else None
                matched.append(InboxLine(text=raw.strip(), region=region))
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
                lines = full_text.splitlines()
                regions = _build_regions(full_text, item, self.spec)
                for line_no in range(_frontmatter_end_line(full_text) + 1, len(lines) + 1):
                    raw = lines[line_no - 1]
                    if raw.strip() and needle in raw.lower():
                        hits.append(_hit_for_line(regions, lines, line_no, needle))
            if hits:
                out.append(SearchResult(item=item, hits=hits))
        return out, unreadable
