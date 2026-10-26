"""Schema 0.14 → 0.15 runner: seed every non-roster type's creation-template-seeded view tag onto
its existing items, and reclaim a pre-0.14 role, permanently-system skill or per-item-type skill
body still carrying legacy rendered text.

The milestone roll-up's old type attachment (``items.milestone.views``) is replaced by the general
``sq:view:<name>`` tag. A new milestone gets the tag from ``templates/items/milestone.md.j2``, but
the attachment applied retroactively to every item of a type and a tag does not, so without this
one-time pass existing milestones would lose their roll-up. Both steps call
:func:`~squads._view_tags.place_view_tags`, the routine every other ``sq:body`` writer drives, so a
tag-only or ``bottom``-positioned region comes out byte-identical to a fresh write. The runner
drives the primitives under ``view add`` (``_sections``, ``_itemfile``, ``_views``) directly rather
than the verb, because it needs one open ``store.transaction()`` for every eligible item (the bulk
importer's precedent) rather than one per item, avoiding N lock acquisitions and N index commits.

**Step one: every non-roster type whose creation template seeds a view tag** (today
milestone/``milestone_rollup``). :func:`~squads._views.template_seeded_view_names` is the one
derivation this runner and the sibling ``sq check`` finding both read, and the runner restricts
itself to :meth:`WorkflowSpec.non_roster_types`, since a roster type's body belongs to the standing
convergence sweep (``MaintenanceMixin._backfill_roster_body_tags``/``_converge_body_tag``), and this
step must not extend into that territory. A custom non-roster type whose override seeds a tag is
migrated the same way, and a project that dropped the bundled tag is untouched, the derivation
answering empty.

**Step two: the legacy-body reclaim.** At 0.13.1 ``_write_managed_skill`` wrote the rendered body
into the ``sq:body`` of every managed skill, ``sq-<type>`` included, so every squad initialised
before 0.14 carries that text. ``_converge_body_tag``'s standing sweep once held a wide convergence
licence for a role's and a permanently-system skill's body, on the premise that ``set_body`` refused
both unconditionally. The roster write refusal now narrows that premise (a role or system skill
whose view was dropped from ``[selected]`` admits an authored body), so the sweep is strict from
here on and leaves a marker-free non-empty region untouched. A genuine pre-0.14 rendering still
needs reclaiming once, and a migration is where that release-scoped licence belongs, since it knows
which release the corpus comes from.

The reclaim set is the roster classification and nothing narrower: a role, permanently-system skill
or ``sq-<type>`` skill is in scope exactly when :func:`~squads._views.roster_body_view_name` names a
declared view for it, and its marker-free non-empty body is overwritten onto its tag whatever it
holds. No on-disk signal separates a pre-0.14 rendering from an author's runbook sharing a slug with
a later-declared type (a skill from ``sq import``, ``sq adopt`` or by hand has the identical shape),
so a provenance test would be wrong on exactly the files that matter. A custom skill matching no
declared type classifies to ``None`` and is never in scope.

**Mid-chain skew: judged against the on-disk file alone.** Both steps read the file's own
frontmatter fresh at write time (:func:`_write_body_change`), not the ``db``-loaded ``Item``, which
can be stale because ``run_pending_migrations`` runs each migration in its own transaction before
the trailing ``repair()`` reconciles the index, and an older runner may have rewritten the file
earlier in the chain. Comparing against that stale snapshot would make this step a silent no-op for
every role and system skill from an old corpus (0.1 through 0.7). Writing back the frontmatter it
just read cannot clobber a value it did not observe (only ``updated_at``/``modified_session`` and
the body region change), and ``db`` supplies only identity facts (type, slug, file path).

**Every condition declined is a skip reported by item id**, each a skip rather than a refusal: an
unresolvable ``(type, name)`` pair (step one; :func:`~squads._views.resolve_view_target`, the
predicate ``view add`` gates on, asked once per pair so the whole pair is skipped, since an adopter
who dropped a bundled view through ``[selected].views`` is no defect to halt on); a body with no
``sq:body`` region (either step; hand-adopted or hand-edited files carry that shape); the tag
already present outside ``sq:body`` (step one; the routine works only inside the region, so seeding
would add a second copy that ``sq check``'s duplicate-marker finding reports as an error, and the
remedy is to place or disable the tag explicitly); and marker-shaped content in a roster body (step
two; another tag, a nested region or corruption, where, like the standing strict convergence, it
will not guess at overwriting something structured). What it calls can still raise (say a file
becoming unreadable), and re-running ``sq migrate up`` resumes, rebuilding the index from the files
first; an unparseable item file refuses the run before any runner.

The reclaim is a corpus-wide sweep, not a single-item mutation gated the ordinary way, which is why
it belongs in a migration; ``_cli/_migrate.py``'s skip text follows this runner's skip-messaging
rule. It runs only through ``sq migrate up`` via ``_migrations._registry``.
"""

from pathlib import Path

from squads import _clock as clock
from squads._actor import current_session
from squads._errors import SquadsError
from squads._index._store import IndexStore
from squads._itemfile import read_frontmatter, read_item_text, write_text
from squads._migrations._context import MigrationContext
from squads._migrations._legacy_extra import legacy_extra
from squads._migrations._outcome import MigrationOutcome
from squads._models import _markers as markers
from squads._models._index import SquadsDB
from squads._paths import SquadPaths, number_for_id
from squads._sections import find_markers, get_section, replace_frontmatter, replace_section
from squads._view_tags import place_view_tags
from squads._views import resolve_view_target, roster_body_view_name, template_seeded_view_names
from squads._workflow._models import ROSTER_ROLE, ROSTER_SKILL, WorkflowSpec

MANUAL = """\
## Schema 0.14 → 0.15 — views are positioned, disabled rather than removed

The milestone roll-up (`sq milestone <n> show`) used to be a type-attached view
(`items.milestone.views`); it is now placed by a `sq:view:milestone_rollup` tag inside the
milestone's own `sq:body` region — the same mechanism a role's own definition, and each
system/per-item-type skill's text, already render through.

This migration inserts that tag into every existing milestone body that does not already carry
one, through the tool's own marker-safe placement routine (never a bespoke write into authored
prose) — so **every milestone body in your corpus gains one line**. `sq migrate up` reports how
many; review the diff before committing, the same posture every migration that touches your
corpus asks for. A milestone whose body you had already hand-edited to carry the tag, or that
carries no `sq:body` region at all, is left exactly as it was.

A milestone this migration cannot safely place the tag on is **skipped, not aborted**: the run
still completes and the rest of your corpus is still migrated. `sq migrate up` names every
skipped item by id, and `sq check` (reachable again once the run completes) reports what it
still needs — a body with no `sq:body` region needs one added by hand. Once that item's own
problem is fixed, place the tag with `sq milestone <n> view add milestone_rollup`.

A milestone whose tag you had already moved outside `sq:body` by hand is skipped too, for a
different reason: it already carries the tag, so this migration leaves it exactly as it was
rather than insert a second, in-region copy alongside it (which would duplicate it, not
recognise it). That out-of-region placement is not a shape to leave, though — every body write
now re-inserts any seeded tag missing from inside `sq:body`, so the next one (a plain `body`
call, `--append`, or this same `view add`) plants a second, in-region copy next to the
out-of-region one, and `sq check` then reports `duplicate sq:view:milestone_rollup tag`. Fix it
before that happens: delete the out-of-region line from the file by hand, then run
`sq milestone <n> view add milestone_rollup` to place it back inside `sq:body`, where every
other milestone's already is.

No other item type is touched by this step: only a type whose *creation template* currently
seeds a view tag is in scope, and today that is milestone alone.

## The same step also reclaims pre-0.14 role/skill bodies

A role's own definition, each permanently-system skill's (`squads`, `greeting`, `sq-memory`)
text, and each per-item-type `sq-<type>` skill's guidance has rendered off a
`sq:view:<name>` tag since 0.14. Before that, every one of those writers rendered the resolved
text straight into the body instead. If your corpus still carries one of those pre-0.14
renderings — plain prose, no marker of any kind — this step converges it onto its own tag the
same marker-safe way, and reports how many bodies it changed.

An empty body and an already-tagged one are both left exactly as they are — this step only
ever touches the legacy shape named above, on a document whose current roster classification
names a declared view. Every other marker-free, non-empty body this step reaches is overwritten
onto its tag unconditionally, whatever it holds: before 1.0, this step does not try to tell a
genuine pre-0.14 rendering apart from an author's own runbook that happens to share a
per-item-type skill's slug. A custom skill matching no declared type is never touched, because
it carries no such tag to begin with.

A body carrying marker-shaped content this step doesn't recognise is skipped the same way,
named by id, with nothing written; `sq check` (reachable once the schema stamp lands) names the
finding. `sq repair`'s own convergence sweep does not touch it either — it converges only a
genuinely empty region. Once you have taken the marker-shaped content out by hand, the document
is in exactly the "prose beside a missing tag" shape an adopted pre-0.14 corpus reaches too —
`sq check` then names the same four-step remedy either way, the only one that converges to a
single live rendering: (1) drop `<name>` from `[selected]` in `.overrides/workflow.toml` — this
makes the host briefly not roster-classified, which is what lifts its body write refusal long
enough for step 2; (2) clear the text — `sq skill <slug> body -m "" --force` for a skill, or,
for a role (which has no `body` verb at all), a single-event bulk import against its own id,
piped over stdin: `echo '{"op":"body","target":"<id>","body":"","force":true}' | sq import -`;
(3) restore `<name>` to `[selected]`; (4) `sq role|skill <slug> view add <name>`. `view disable
<name>` alone does not achieve this: it renders nothing, but the legacy prose it leaves beside
the disabled tag can never be cleared afterward — the roster write refusal has no
`[selected]`-dropped window open once the tag (disabled or not) is back in place, so this
stranded prose becomes permanent. Reach for `view disable` only when you genuinely want the
document to render nothing (the escape the roster refusal's own message already names), never
as a stand-in for the four-step remedy above.
"""


def _tag_present_outside_region(text: str, region_tag: str, name: str) -> bool:
    """Whether view *name*'s tag (either state) appears in *text* outside *region_tag*'s section,
    the shape a hand-moved tag produces. It is a runner-local question asked before the placement
    routine (which works only inside the region), so no second in-region copy is seeded. ``False``
    when the section is absent, which is the missing-region skip the caller reaches separately.
    """
    inner = get_section(text, region_tag)
    if inner is None:
        return False
    enabled = markers.open_marker(markers.view_tag(name))
    disabled = markers.open_marker(markers.view_tag(name, disabled=True))
    return any(raw in text and raw not in inner for raw in (enabled, disabled))


async def _write_body_change(path: Path, text: str, new_inner: str) -> str:
    """*text* with its ``sq:body`` region replaced by *new_inner* and ``updated_at`` bumped on the
    file's own frontmatter, read fresh from *text* and not from a possibly mid-chain-stale ``Item``
    (see the module docstring). It writes the result and returns it. ``modified_session`` is set
    only when *sid* is real, as ``Item.to_frontmatter_dict`` does, so a file no session touched does
    not gain ``modified_session: null``.
    """
    data = read_frontmatter(text=text, source=str(path))
    data["updated_at"] = clock.iso(clock.now())
    sid, _ = current_session()
    if sid is not None:
        data["modified_session"] = sid
    new_text = replace_frontmatter(replace_section(text, markers.BODY, new_inner), data)
    await write_text(path, new_text)
    return new_text


async def migrate(ctx: MigrationContext) -> MigrationOutcome:
    """Two independent steps in one run, transaction and reported outcome (see the module
    docstring): seed every resolvable ``sq:view:<name>`` a non-roster type's creation template
    declares onto its existing items (today milestone/``milestone_rollup``), and reclaim a pre-0.14
    role's, system skill's or per-item-type skill's plain-prose body onto its view tag, the one-time
    licence :func:`~squads._services._maintenance._converge_body_tag`'s standing sweep gave up.
    ``count`` is the bodies either step changed (``0`` for nothing eligible or a re-run);
    ``skipped`` names by id every item left untouched (missing file, no ``sq:body``, tag already
    outside it, or marker-shaped content in step two).
    """
    paths, spec, playbook = ctx.paths, ctx.spec, ctx.playbook

    # (item_type, view names to seed), resolved once from the shared derivation and restricted to
    # non-roster types, never a pinned "milestone" literal, so a re-templated custom type migrates
    # too. Only a name that resolves against its host type is placed (the gate `view add` uses); an
    # unresolvable one skips the pair, not the run.
    seeded_by_type: dict[str, frozenset[str]] = {}
    for item_type in sorted(spec.non_roster_types()):
        names = frozenset(
            name
            for name in template_seeded_view_names(item_type, spec, from_squad=paths.squad_dir)
            if resolve_view_target(name, item_type, spec, playbook, from_squad=paths.squad_dir)
            is None
        )
        if names:
            seeded_by_type[item_type] = names

    changed = 0
    skipped: list[str] = []
    store = IndexStore(paths.index_path, paths.lock_path, spec=spec)
    async with store.transaction() as db:
        for item_type, names in seeded_by_type.items():
            items = sorted(
                (it for it in db.items.values() if it.type == item_type),
                key=lambda it: it.sequence_id,
            )
            for it in items:
                path = paths.abspath(it.path)
                try:
                    text = await read_item_text(path, it.id)
                except SquadsError:
                    # A file that became unreadable after the index was rebuilt — this item's own
                    # problem, not this migration's to raise the whole run over.
                    skipped.append(it.id)
                    continue
                if any(_tag_present_outside_region(text, markers.BODY, n) for n in names):
                    # A copy already lives outside sq:body (an author moved it). The routine works
                    # only inside the region, so calling it would seed a second copy, a duplicate
                    # marker `sq check` reports as an error. Skip (see module docstring).
                    skipped.append(it.id)
                    continue
                region = get_section(text, markers.BODY)
                if region is None:
                    # No sq:body region to place the tag in (a hand-adopted or hand-edited
                    # file). Same disposition as the unreadable-file case above.
                    skipped.append(it.id)
                    continue
                # `get_section` pads the region with an opening/closing newline that the placement
                # routine never emits, so the no-op comparison below strips it first; otherwise an
                # already-seeded region never equals its re-placement and every re-run reports a
                # change it did not make.
                region = region.strip("\n")
                new_inner = place_view_tags(
                    region,
                    None,
                    seeded=names,
                    spec=spec,
                    item_type=item_type,
                    addr=number_for_id(it.id),
                )
                if new_inner == region:
                    continue
                text = await _write_body_change(path, text, new_inner)
                changed += 1

        # Second step, same transaction: the legacy-body reclaim (see the module docstring and
        # :func:`_reclaim_legacy_roster_bodies`).
        step_changed, step_skipped = await _reclaim_legacy_roster_bodies(db, spec, paths)
        changed += step_changed
        skipped.extend(step_skipped)
    return MigrationOutcome(count=changed, skipped=tuple(skipped))


async def _reclaim_legacy_roster_bodies(
    db: SquadsDB, spec: WorkflowSpec, paths: SquadPaths
) -> tuple[int, list[str]]:
    """``(changed, skipped)`` for the legacy-body reclaim (module docstring), split out of
    :func:`migrate` to keep it under the complexity ceiling; every write is in the caller's open
    transaction over the same ``db`` and *spec*. The reclaim set is
    :func:`~squads._views.roster_body_view_name`'s classification, the one the roster write refusal
    and ``sq check`` read: every marker-free non-empty roster body is overwritten onto its tag
    whatever it holds, and a custom skill matching no declared type classifies to ``None`` and is
    out of scope.
    """
    changed = 0
    skipped: list[str] = []
    roster_items = sorted(
        (it for it in db.items.values() if it.type in (ROSTER_ROLE, ROSTER_SKILL)),
        key=lambda it: it.sequence_id,
    )
    for it in roster_items:
        slug = legacy_extra(it).get("slug", it.slug) if it.type == ROSTER_SKILL else it.slug
        view_name = roster_body_view_name(it.type, slug, spec)
        if view_name is None:
            continue
        path = paths.abspath(it.path)
        try:
            text = await read_item_text(path, it.id)
        except SquadsError:
            skipped.append(it.id)
            continue
        region = get_section(text, markers.BODY)
        if region is None:
            # The region is absent, not merely empty: reported as step one reports it. This reclaim
            # is not the standing sweep and is not the place to decide whether reinstating a missing
            # region is safe, which is `_converge_body_tag`'s separate licence.
            skipped.append(it.id)
            continue
        current = region.strip()
        tag_line = markers.open_marker(markers.view_tag(view_name))
        if not current or current == tag_line:
            # Empty is the standing sweep's job, unconditionally; already-tagged needs no
            # write. Neither is this one-time pass's to act on.
            continue
        if find_markers(current):
            # Marker-shaped content this reclaim has no model for (another tag, a nested region,
            # corruption): skip rather than guess at overwriting something structured, as the
            # standing strict convergence does.
            skipped.append(it.id)
            continue
        # The legacy rendering is converged onto its tag, not kept beside it: the edit clears
        # the region's prose outright, so the only thing left after placement is the seeded
        # tag itself — a stale copy of what the view now renders live, not authored content.
        new_inner = place_view_tags(
            get_section(text, markers.BODY) or "",
            "",
            seeded=frozenset({view_name}),
            spec=spec,
            item_type=it.type,
            addr=slug,
        )
        await _write_body_change(path, text, new_inner)
        changed += 1
    return changed, skipped
