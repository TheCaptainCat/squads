"""The view-tag engine: placing a ``sq:view:<name>`` tag in a body, finding and stripping them,
and expanding each into its view's rendered output at read time.

A tag names a view and nothing else; this module owns where tags may sit, how a placement
resolves conflicting states, and how a body reads once its tags are expanded. Resolving and
rendering a view's source stays in :mod:`squads._views`.
"""

import re
from itertools import pairwise
from pathlib import Path

from squads._errors import SquadsError
from squads._interactions._models import PlaybookSpec
from squads._language import WorkingLanguage
from squads._models import _markers as markers
from squads._models._index import SquadsDB
from squads._models._item import (
    Item,
)
from squads._roles._models import CatalogSource
from squads._sections import get_section, iter_marker_spans, split_frontmatter, strip_marker_lines
from squads._transform import TransformLoader
from squads._view_remedies import view_placement_invocation
from squads._views import (
    RosterProvider,
    render_resolved_source_or_raise,
    resolve_source,
    resolve_view_target,
)
from squads._workflow._models import (
    ROSTER_ROLE,
    ROSTER_SKILL,
    WorkflowSpec,
    parse_view_position,
)

# --------------------------------------------------------------------------- placement


def view_tag_states(region: str, name: str) -> set[bool]:
    """Every state *name*'s view tag currently carries in *region* — empty, one state, or two
    for a conflicting pair. Answers "what state does it render as", not "how many copies"; use
    :func:`view_tag_settled` to check whether placing a tag would be a no-op."""
    _prose, parts = _region_view_tags(region)
    return {p.disabled for p in parts if p.name == name}


def view_tag_settled(region: str, name: str, *, disabled: bool) -> bool:
    """Whether *region* already carries exactly one copy of *name*'s tag in *disabled*'s
    state — the "nothing to do" condition ``view add``/``view disable`` gate their no-op
    return on. Stricter than :func:`view_tag_states`: a same-state duplicate must fall through
    to placement, never read as already settled."""
    _prose, parts = _region_view_tags(region)
    matches = [p for p in parts if p.name == name]
    return len(matches) == 1 and matches[0].disabled == disabled


def out_of_region_view_tags(text: str) -> list[str]:
    """Every ``sq:view:*`` tag in *text* that sits outside the ``sq:body`` region, in file
    order. Those tags neither render nor answer to ``view add``/``view disable``. Empty when the
    file has no complete ``sq:body`` region, which is reported on its own."""
    open_tag, close_tag = markers.open_marker(markers.BODY), markers.close_marker(markers.BODY)
    start = text.find(open_tag)
    end = text.find(close_tag, start + len(open_tag)) if start != -1 else -1
    if end == -1:
        return []
    region_end = end + len(close_tag)
    return [
        tag
        for tag, tag_start, _tag_end in iter_marker_spans(text)
        if markers.view_tag_parts(tag) is not None and not start <= tag_start < region_end
    ]


def out_of_region_view_warning(tag: str) -> str:
    """The ``sq check`` line for one out-of-region view tag."""
    return (
        f"view tag <!-- {tag} --> sits outside sq:body, so it never renders; move it inside sq:body"
    )


def out_of_region_view_error(item_id: str, name: str, text: str) -> str | None:
    """The refusal message when *text* carries a tag for view *name* outside ``sq:body``, else
    ``None``. ``view add``/``view disable`` manage in-region tags only and would otherwise
    place a second copy."""
    stray = [
        tag
        for tag in out_of_region_view_tags(text)
        if (parts := markers.view_tag_parts(tag)) is not None and parts.name == name
    ]
    if not stray:
        return None
    return (
        f"{item_id}: view {name} has a tag outside sq:body (<!-- {stray[0]} -->), which "
        "`view add`/`view disable` do not manage; move it inside the sq:body region first"
    )


def unplaced_view_tags(region: str, incoming: str) -> list[str]:
    """The view tags in *incoming*, as written, that *region* does not already carry with the
    same name and state. A body read back from the item holds only placed tags, so it answers
    empty."""
    _prose, placed = _region_view_tags(region)
    return [
        raw
        for raw, _start, _end in iter_marker_spans(incoming)
        if (parts := markers.view_tag_parts(raw)) is not None and parts not in placed
    ]


def strip_view_tags(text: str) -> str:
    """*text* with every view tag stripped, each together with its own line — so a tag's state
    or location never by itself makes a body count as authored when the authored-content guard
    compares through this."""
    stripped, _tags = _region_view_tags(text)
    return stripped


def body_is_unwritten(body: str, scaffold: str | None) -> bool:
    """Whether *body* is still unwritten: no prose once view tags are stripped, or prose equal
    to *scaffold* (also stripped of its tags) after trimming whitespace. An absent scaffold
    counts as written whenever there is prose, so the answer errs towards "authored". The one
    definition the body-overwrite guard and ``body_written`` both read."""
    prose = strip_view_tags(body).strip()
    if not prose:
        return True
    return scaffold is not None and prose == strip_view_tags(scaffold).strip()


def _region_view_tags(region: str) -> tuple[str, list[markers.ViewTagParts]]:
    """*region* with every view tag — enabled or disabled, named or not — stripped together
    with its own line, and the parsed tags taken out, in file order (duplicates included). The
    read half of :func:`place_view_tags`, built on
    :func:`~squads._sections.strip_marker_lines`."""
    stripped, raw = strip_marker_lines(region, lambda tag: markers.view_tag_parts(tag) is None)
    parts = [p for tag in raw if (p := markers.view_tag_parts(tag)) is not None]
    return stripped, parts


def reinstate_absent_body_region(text: str) -> str | None:
    """*text* with a fresh ``sq:body`` pair after the frontmatter, if it has neither marker.

    It reclaims only the leading run of view tags plus, if present, exactly one heading line
    immediately followed by the real ``sq:discussion`` marker. Anything else (real prose, or a
    heading not bounding that marker) refuses by returning ``None`` rather than guessing, as it
    does when there is no frontmatter to anchor on. A caller getting ``None`` leaves the file
    untouched and never raises.
    """
    if get_section(text, markers.BODY) is not None:
        return None
    _fm, rest = split_frontmatter(text)
    if rest == text:  # no frontmatter at all — nothing to anchor the search from
        return None
    fm_len = len(text) - len(rest)
    pos = 0
    next_marker_start = len(rest)
    stop_raw: str | None = None
    for raw, start, end in iter_marker_spans(rest):
        if rest[pos:start].strip("\n \t") or markers.view_tag_parts(raw) is None:
            next_marker_start = start
            stop_raw = raw
            break
        line_end = rest.find("\n", end)
        pos = line_end + 1 if line_end != -1 else len(rest)
    else:
        next_marker_start = len(rest)
    after = rest[pos:next_marker_start].strip("\n \t")
    if after:
        # Accept a heading only when *after* is one non-blank line, a heading, and the next
        # marker is the discussion open tag: a body can start with a heading and run on before
        # its own "## Discussion", which the first-character check alone would accept.
        after_lines = [line for line in after.splitlines() if line.strip()]
        is_discussion_heading = (
            len(after_lines) == 1
            and after_lines[0].lstrip().startswith("#")
            and stop_raw == f"{markers.PREFIX}{markers.DISCUSSION}"
        )
        if not is_discussion_heading:
            return None
    boundary = fm_len + pos
    inner = text[fm_len:boundary].strip("\n")
    return (
        text[:fm_len]
        + markers.open_marker(markers.BODY)
        + "\n"
        + (f"{inner}\n" if inner else "")
        + markers.close_marker(markers.BODY)
        + "\n"
        + text[boundary:]
    )


class ConflictingViewStateError(SquadsError):
    """:func:`place_view_tags`'s own refusal when one view's tags disagree on state (an
    enabled copy and a disabled copy both present) — a distinct type so a caller that must
    catch it apart from every other :class:`SquadsError` can."""


def place_view_tags(
    region: str,
    edit: str | None,
    *,
    append: bool = False,
    seeded: frozenset[str],
    spec: WorkflowSpec,
    item_type: str,
    addr: int | str,
    force: tuple[str, bool] | None = None,
) -> str:
    """The one re-placement routine every ``sq:body`` writer drives.

    It strips every view tag out of *region*, applies the prose edit, and re-inserts one tag per
    view at its declared position and prior state, plus any *seeded* view that was missing, so no
    caller inserts, removes or moves a tag itself. A tag mirrors the separator already at its
    landing spot (never manufacturing a blank line), which makes stripping it back out the exact
    inverse. Conflicting states raise :class:`ConflictingViewStateError`; *force* is how ``view
    add``/``view disable`` settle one. The result has LF line endings whatever *region* had; the
    write seam restores the file's own.
    """
    prose, existing = _region_view_tags(region.replace("\r\n", "\n"))
    prose = prose.strip("\n")
    if edit is not None:
        prose = (f"{prose}\n\n{edit}" if prose else edit) if append else edit

    final, first_seen = _resolve_final_states(existing, seeded, force, item_type, addr)
    decl_order = {name: i for i, name in enumerate(spec.views)}
    declared = [n for n in final if n in decl_order]
    undeclared = sorted(
        (n for n in final if n not in decl_order),
        key=lambda n: first_seen.get(n, len(existing)),
    )

    name_cut_points = _resolve_cut_points(prose, declared, decl_order, spec)
    tag_cut_points = {
        off: [markers.open_marker(markers.view_tag(n, disabled=final[n])) for n in names]
        for off, names in name_cut_points.items()
    }
    atoms = _build_segments(prose, tag_cut_points)
    atoms.extend(
        (markers.open_marker(markers.view_tag(n, disabled=final[n])), len(prose), len(prose))
        for n in undeclared
    )
    seps = _boundary_separators(prose, atoms)
    out = atoms[0][0] if atoms else ""
    for (text, _left, _right), sep in zip(atoms[1:], seps, strict=True):
        out += sep + text
    return out


def _resolve_final_states(
    existing: list[markers.ViewTagParts],
    seeded: frozenset[str],
    force: tuple[str, bool] | None,
    item_type: str,
    addr: int | str,
) -> tuple[dict[str, bool], dict[str, int]]:
    """The final ``name -> disabled`` map :func:`place_view_tags` re-inserts, plus indexes.

    The indexes are each name's position in *existing*, used only to order undeclared tags among
    themselves. It collapses same-state duplicates, raises :class:`ConflictingViewStateError` for
    a name in both states unless *force* names it, adds every absent *seeded* name as enabled, then
    applies *force* last so it wins. Split out to keep :func:`place_view_tags` under the complexity
    ceiling.
    """
    states: dict[str, set[bool]] = {}
    first_seen: dict[str, int] = {}
    for i, part in enumerate(existing):
        states.setdefault(part.name, set()).add(part.disabled)
        first_seen.setdefault(part.name, i)

    final: dict[str, bool] = {}
    for name, seen in states.items():
        if force is not None and force[0] == name:
            continue
        if len(seen) > 1:
            settle = f"`{view_placement_invocation(item_type, addr, 'add', name)}`"
            if item_type not in (ROSTER_ROLE, ROSTER_SKILL):
                settle += f" or `{view_placement_invocation(item_type, addr, 'disable', name)}`"
            raise ConflictingViewStateError(
                f"{item_type} {addr}: {markers.PREFIX}{markers.view_tag(name)} carries both an "
                f"enabled and a disabled tag; settle its state with {settle}"
            )
        final[name] = next(iter(seen))
    for name in seeded:
        final.setdefault(name, False)
    if force is not None:
        final[force[0]] = force[1]
    return final, first_seen


def _resolve_cut_points(
    prose: str,
    declared: list[str],
    decl_order: dict[str, int],
    spec: WorkflowSpec,
) -> dict[int, list[str]]:
    """Every declared view's resolved insertion offset into *prose*, grouped by offset and
    ordered by declaration order within each group. ``"top"`` is offset 0, ``"bottom"`` (or a
    non-matching ``"after(<regex>)"``) is ``len(prose)``, and a matching ``"after(<regex>)"``
    resolves right after the line holding the match's last character."""
    entries: list[tuple[int, int, str]] = []
    for name in declared:
        pos = parse_view_position(spec.views[name].position)
        if pos.kind == "top":
            offset = 0
        elif pos.kind == "bottom" or pos.pattern is None:
            offset = len(prose)
        else:
            m = pos.pattern.search(prose)
            if m is None:
                offset = len(prose)
            else:
                anchor = m.end() - 1 if m.end() > m.start() else m.end()
                nl = prose.find("\n", anchor)
                offset = nl + 1 if nl != -1 else len(prose)
        entries.append((offset, decl_order[name], name))
    entries.sort(key=lambda e: (e[0], e[1]))

    cut_points: dict[int, list[str]] = {}
    for offset, _idx, name in entries:
        cut_points.setdefault(offset, []).append(name)
    return cut_points


#: A leading/trailing run of newline-delimited blank lines, whitespace-only lines included —
#: the same shape :func:`_local_separator` reads by character count, spelled as a regex here
#: because :func:`_build_segments` strips a whole run at once rather than counting it.
_LEADING_BLANK_RUN_RE = re.compile(r"^(?:[ \t]*\n)+")


_TRAILING_BLANK_RUN_RE = re.compile(r"(?:\n[ \t]*)+$")


def _build_segments(prose: str, cut_points: dict[int, list[str]]) -> list[tuple[str, int, int]]:
    """*prose* sliced at every offset in *cut_points* and interleaved with the tag lines
    declared there, as an ordered list of ``(text, left_offset, right_offset)`` atoms. Each
    prose slice is trimmed of its own leading/trailing separator (a run of newlines,
    whitespace-only lines included) — never interior content — and an empty slice contributes
    no atom at all."""
    atoms: list[tuple[str, int, int]] = []
    prev = 0
    for off in sorted(set(cut_points) | {0, len(prose)}):
        if off > prev:
            slice_ = _LEADING_BLANK_RUN_RE.sub("", prose[prev:off])
            slice_ = _TRAILING_BLANK_RUN_RE.sub("", slice_)
            if slice_:
                atoms.append((slice_, prev, off))
        prev = off
        if off in cut_points:
            atoms.extend((tag, off, off) for tag in cut_points[off])
    return atoms


def _blank_run_length(text: str, offset: int, *, forward: bool, limit: int = 2) -> int:
    """How many newlines bound *offset* on one side, up to *limit* — a line holding only
    spaces/tabs between two newlines counts as blank too, the same as an empty line, since
    that is how Markdown (and an author's own eye) reads it."""
    count = 0
    pos = offset if forward else offset - 1
    step = 1 if forward else -1
    n = len(text)
    while count < limit:
        scan = pos
        while 0 <= scan < n and text[scan] in " \t":
            scan += step
        if not (0 <= scan < n and text[scan] == "\n"):
            break
        count += 1
        pos = scan + step
    return count


def _local_separator(prose: str, offset: int) -> str:
    """The separator a tag placed at *offset* shares with the prose beside it, mirroring
    whatever newline run already sat there — a run of 2 or more newlines (a blank line, or
    several, whitespace-only lines included) collapses to exactly one blank line; a single
    newline (no blank line at all) stays a single newline."""
    lead = _blank_run_length(prose, offset, forward=False)
    trail = _blank_run_length(prose, offset, forward=True)
    return "\n\n" if lead + trail >= 2 else "\n"


def _boundary_separators(prose: str, atoms: list[tuple[str, int, int]]) -> list[str]:
    """One separator per gap between consecutive *atoms*: always one blank line between two
    tags, :func:`_local_separator` between a tag and prose at an interior cut point, and one
    blank line at the region's own edges (nothing there to mirror either way)."""
    seps: list[str] = []
    for (_lt, _ll, left_right), (_rt, right_left, _rr) in pairwise(atoms):
        boundary = left_right  # == right_left, by construction
        left_is_tag = _ll == left_right
        right_is_tag = right_left == _rr
        if left_is_tag and right_is_tag:
            seps.append("\n\n")
        elif 0 < boundary < len(prose):
            seps.append(_local_separator(prose, boundary))
        else:
            seps.append("\n\n")
    return seps


def _keep_unless_disabled_view_tag(raw: str) -> bool:
    """False only for a disabled view tag — what ``strip_marker_lines`` should remove."""
    parts = markers.view_tag_parts(raw)
    return parts is None or not parts.disabled


def expand_view_tags(  # noqa: PLR0913 — read-time expansion needs the whole squad context
    text: str,
    item: Item,
    db: SquadsDB,
    spec: WorkflowSpec,
    playbook: PlaybookSpec,
    roster: RosterProvider,
    squad_dir: Path | None,
    catalog: CatalogSource,
    squad_dir_display: str | None,
    working_language: WorkingLanguage,
    keep: str | None = None,
) -> str:
    """*text* with every well-formed ``sq:view:<name>`` tag replaced by that view's rendered
    output, in place, except the tag of the view *keep* names, which stays as written. A disabled
    tag is removed the way ``strip_marker_lines`` removes a marker, never left as a blank line; an
    unresolvable enabled tag stays literal. Read-only, and pads a rendered view with a blank line
    against neighbouring prose. A view that declares a transform runs it once per tag; a failing
    transform raises rather than leaving the tag."""
    text, _ = strip_marker_lines(text, _keep_unless_disabled_view_tag)
    loader = TransformLoader(squad_dir)
    segments: list[tuple[str, str]] = []
    pending = ""
    last = 0
    changed = False
    for raw, start, end in iter_marker_spans(text):
        # `iter_marker_spans`/`find_markers` emit the tag with its "sq:" prefix still on (e.g.
        # "sq:view:milestone_rollup") — `view_tag_parts` accepts that on-disk form directly, no
        # hand-strip needed at this call site.
        parts = markers.view_tag_parts(raw)
        if parts is None:
            continue  # not a view tag — left literal
        name = parts.name
        if name == keep:
            continue  # the view being resolved: its own input never holds its output
        reason = resolve_view_target(name, item.type, spec, playbook, from_squad=squad_dir)
        if reason is not None:
            continue  # undeclared, template missing, or source inapplicable — left literal
        view = spec.views[name]
        result = resolve_source(view, name, item, db, spec, playbook, roster, squad_dir, catalog)
        data = (
            loader.run(name, view.transform, result, item=item, spec=spec)
            if view.transform is not None
            else None
        )
        rendered = render_resolved_source_or_raise(
            name,
            result,
            item,
            spec,
            squad_dir_display,
            working_language,
            data,
            from_squad=squad_dir,
        )
        pending += text[last:start]
        segments.append(("literal", pending))
        # Stripped of its own leading/trailing newlines so the padding this function adds is
        # the only source of blank lines at its edges — a template ending in its own trailing
        # newline must not stack with that padding into a double blank line.
        segments.append(("rendered", rendered.strip("\n")))
        pending = ""
        last = end
        changed = True
    if not changed:
        return text
    pending += text[last:]
    segments.append(("literal", pending))
    return _assemble_padded_expansion(segments)


def _pad_between(chunk: str, *, pad_before: bool, pad_after: bool) -> str:
    """Normalise *chunk* to a full blank line on each side that borders a rendered view, never
    at a body edge and never stacking beyond one blank line."""
    if pad_before:
        chunk = chunk.lstrip("\n")
    if pad_after:
        chunk = chunk.rstrip("\n")
    if not chunk:
        return "\n\n" if (pad_before and pad_after) else ""
    if pad_before:
        chunk = "\n\n" + chunk
    if pad_after:
        chunk = chunk + "\n\n"
    return chunk


def _assemble_padded_expansion(segments: list[tuple[str, str]]) -> str:
    """Join alternating literal/rendered segments, padding each literal one against any
    rendered neighbour so a view never merges into surrounding prose."""
    out: list[str] = []
    for i, (kind, content) in enumerate(segments):
        if kind == "rendered":
            out.append(content)
            continue
        pad_before = i > 0 and segments[i - 1][0] == "rendered"
        pad_after = i < len(segments) - 1 and segments[i + 1][0] == "rendered"
        out.append(_pad_between(content, pad_before=pad_before, pad_after=pad_after))
    return "".join(out)
