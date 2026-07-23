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
from squads._services._base import ServiceCore, reject_markers
from squads._services._results import SearchHit, SearchResult
from squads._workflow import WorkflowSpec

_SNIPPET_WIDTH = 160
_SNIPPET_LEAD = 40
"""Chars of left context kept before the match once the window has to shift off column 0."""


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
    """

    start: int
    end: int
    region: str
    comment_headers: list[tuple[int, str, str]] = field(
        default_factory=lambda: list[tuple[int, str, str]]()
    )


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

    def _add(tag: str, region_name: str, *, with_comments: bool = False) -> None:
        bounds = sections.region_lines(text, tag)
        if bounds is None:
            return
        headers = _scan_comment_headers(lines, bounds) if with_comments else []
        regions.append(_Region(bounds[0], bounds[1], region_name, headers))

    _add(markers.BODY, "body")
    _add(markers.SUMMARY, "summary")
    _add(markers.DISCUSSION, "discussion", with_comments=True)

    kind = spec.item_subentity_kind(item.type)
    if kind:
        for se in item.subentities:
            tag = f"{kind}:{se.local_id}"
            _add(tag, tag)  # block-level fallback: heading + head badge line
            _add(f"{tag}:body", tag)
            _add(markers.discussion_tag(tag), f"{tag}:discussion", with_comments=True)

    return regions


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
            self.store._log(  # pyright: ignore[reportPrivateUsage]
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

    async def inbox(self, slug: str) -> list[tuple[Item, list[str]]]:
        """Open items whose body/discussion mentions ``@slug``, with the matching lines."""
        slug = slug.lstrip("@").lower()
        out: list[tuple[Item, list[str]]] = []
        for item in await self.list_items():
            if not self.spec.is_open(item.status):
                continue
            path = item_file(self.paths, item)
            if not await _aio.path_exists(path):
                continue
            text = await _aio.read_text(path)
            if slug not in discussion.extract_mentions(text):
                continue
            hits = [ln.strip() for ln in text.splitlines() if f"@{slug}" in ln.lower()]
            out.append((item, hits))
        return out

    async def search(
        self, text: str, *, item_type: str | None = None, status: str | None = None
    ) -> list[SearchResult]:
        """Items whose title, summary, or body/discussion contains ``text`` (case-insensitive).

        ``item_type``/``status`` AND-compose with the query (the same filter dimensions
        ``list_items`` exposes to ``sq list``/``sq tree``). Each result's hits carry the
        region they matched — see :class:`SearchHit`.
        """
        needle = text.strip().lower()
        if not needle:
            raise SquadsError("search needs a non-empty query")
        out: list[SearchResult] = []
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
            path = item_file(self.paths, item)
            if await _aio.path_exists(path):
                full_text = await _aio.read_text(path)
                lines = full_text.splitlines()
                regions = _build_regions(full_text, item, self.spec)
                for line_no in range(_frontmatter_end_line(full_text) + 1, len(lines) + 1):
                    raw = lines[line_no - 1]
                    if raw.strip() and needle in raw.lower():
                        hits.append(_hit_for_line(regions, lines, line_no, needle))
            if hits:
                out.append(SearchResult(item=item, hits=hits))
        return out
