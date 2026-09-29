"""Schema 0.14 → 0.15 runner: seed every non-roster type's own creation-template-seeded view
tag onto existing items of that type, and reclaim a pre-0.14 role/permanently-system-skill or
per-item-type-skill body still carrying legacy rendered text.

The architecture ruling behind this runner retires the milestone roll-up's old
type-attachment (``items.milestone.views``) in favour of the general ``sq:view:<name>`` tag
mechanism: a milestone created
after this change gets the tag for free, straight from ``templates/items/milestone.md.j2``
(``ServiceCore._create_core``, unrelated to this runner) — but type-attachment applied
retroactively to every existing item of a type, and a tag does not. Without this one-time
pass, every milestone already on disk would quietly lose its roll-up the moment the type
attachment is dropped, because its body carries no tag and nothing else places one.

**Placement is the one re-placement routine, not a bespoke insert.** Both steps below call
:func:`~squads._views.place_view_tags`, the same function every
other ``sq:body`` writer drives, so the bytes this migration produces for a tag-only or
``bottom``-positioned region are identical to what a fresh write would produce. This runner
does not call ``ServiceCore._locked_section_edit``/the ``view add`` verb directly — the reason
is narrower than an import cycle: the *static* cycle (``squads._services`` reaching this module
through the migration registry) is real, but a deferred import inside a function body is not
blocked by it — this codebase uses that pattern freely elsewhere. What the verb genuinely
cannot provide is this runner's own transaction shape: one open ``store.transaction()`` for
every eligible item, not one per item. So this runner drives the same primitives the verb is
built from (``_sections``, ``_itemfile``, ``_views``) directly, rather than inventing a second
spelling of any of the properties they already guarantee.

**Scope, step one: every non-roster type whose creation template seeds a view tag** — today
that is exactly milestone/``milestone_rollup``.
:func:`~squads._views.template_seeded_view_names` is the one derivation this runner and the
sibling ``sq check`` finding both read (never a second implementation of "which view names a
type's creation template places"); this runner restricts its own iteration to
:meth:`WorkflowSpec.non_roster_types` deliberately, on top of that shared derivation, because a
roster type's body is owned by a wholly different, already-existing convergence sweep
(``MaintenanceMixin._backfill_roster_body_tags``/``_converge_body_tag``,
``_services/_maintenance.py``) that already keeps a role's/system-skill's own seeded tag
current on every ``sq repair``/``sq sync`` — extending that machinery, or this runner, onto the
other's territory is exactly what that ruling fences off ("not a convergence sweep"). A project
whose own override seeds a tag on a *custom* non-roster type is migrated by the same pass the
derivation resolves it through; a project that dropped the bundled tag is not touched, since
the derivation then answers empty for that type.

**Scope, step two: the pre-0.14 legacy-body reclaim, covering per-item-type skills too.**
At v0.13.1,
``_write_managed_skill`` wrote the rendered body into the ``sq:body`` of **every** managed
skill, ``sq-<type>`` included (``_write_item_skills`` calls it) — not only the three
permanently-system slugs, as the original scope assumed. Every squad initialised before 0.14
therefore carries that legacy text in each per-item-type skill too. Before this release,
``_converge_body_tag``'s standing sweep (``_services/_maintenance.py``) held a *wide*
convergence licence for a role's and a permanently-system skill's body — reasoning that
``set_body`` refused both unconditionally, so no code path could have authored either region.
This release's roster write refusal narrows that premise (a role or permanently-system skill
whose view is dropped from ``[selected]`` now admits an ordinary authored body), so the
standing sweep is strict unconditionally from here on and leaves a marker-free non-empty
region untouched. The one real shape that wide licence existed for — a genuine pre-0.14 legacy
rendering — still needs reclaiming exactly once, and a migration is where that closed,
release-scoped licence belongs: it knows which release a corpus is arriving from, so it can
know a role's or a permanently-system skill's own marker-free content is a superseded
rendering rather than authored prose, a fact the standing sweep cannot ever re-derive on its
own. A per-item-type skill's classification depends on which type the *active spec* currently
declares rather than on anything fixed at creation, but that distinction changes nothing about
what this reclaim does with it: every roster-classified body is in scope alike, next.

**The legacy reclaim set is the roster classification itself, and nothing narrower.** A role, a
permanently-system skill, or a per-item-type ``sq-<type>`` skill is in scope exactly when
:func:`~squads._views.roster_body_view_name` names a declared view for it, with no further test
applied — its marker-free, non-empty body is overwritten onto its tag unconditionally, whatever
that body holds. There is no sound signal on disk that tells a genuine pre-0.14 rendering apart
from an author's own runbook that happens to share a slug with a type declared later: a skill
created by ``sq import``, ``sq adopt``, or by hand carries the identical shape a tool-seeded one
does, so a provenance test would only be a heuristic wrong on exactly the files it matters most
to get right. Before 1.0, this reclaim does not try. A custom skill matching no declared type is
never in scope, because ``roster_body_view_name`` already answers ``None`` for it.

**Mid-chain skew: judged against the on-disk file alone.** Both steps read the
file's own frontmatter fresh at write time (:func:`_write_body_change`) rather than trusting
the ``db``-loaded ``Item`` this transaction opened with — that in-memory item can be stale
relative to disk, because ``run_pending_migrations`` runs every applied migration inside its
own transaction *before* the trailing corpus-wide ``repair()`` ever reconciles the index
against what earlier steps in the same chain rewrote on disk. An older runner earlier in the
same chain rewriting a file's frontmatter without also rebuilding this transaction's index
snapshot is exactly that mid-chain skew, and comparing this step's own write against that stale
in-memory snapshot instead of the file's own on-disk frontmatter would make this step a silent
no-op for every role/system-skill coming from an old corpus (v0_1 through v0_7): the comparison
would always find a mismatch, so the write would always be skipped. Reading the frontmatter to
write straight off the text this step
itself just read removes the possibility of that mismatch by construction — this step can never
clobber a real on-disk value it did not itself just observe, since it is the value it writes
back verbatim (touching only ``updated_at``/``modified_session`` and the body region). ``db`` is
still used to find candidate items (type, slug) and to know their file path — identity facts
that do not drift mid-chain — never to source what gets written back.

**Transaction shape: one open transaction for the whole run**, mirroring the bulk importer's
own precedent (``ImportMixin._apply_import`` opening one ``store.transaction()`` and driving
``_section_edit_core`` per event) rather than the ``view add`` verb's one-transaction-per-item
shape — chosen deliberately, not forced by any cycle, because it inlines the identical read →
mutate → write sequence itself and avoids N separate lock acquisitions and N separate index
commits for what is, in practice, a handful of items.

**Nothing this runner meets aborts the run — every condition it cannot act on is a skip,
reported by item id, never a raise.** A run that always completes always reaches the ``async
with store.transaction() as db:`` block's own exit, which is the only place the schema stamp
that follows gets written — so a run that can raise is a run that can leave a squad with
markdown ahead of an uncommitted index and no working command to reconcile the two with
(``sq repair`` needs the very stamp a raised transaction never writes). Skip-and-report closes
that off structurally: there is no path left on which this runner raises, so there is no
partial-pass state to reach.

Conditions this runner meets and does not act on, each a skip rather than a refusal:

- **An unresolvable ``(type, name)`` pair** (step one) — :func:`~squads._views
  .resolve_view_target` names a reason (undeclared, no resolvable template, or a source that
  cannot apply to *item_type*). Asked once per pair, before any item of that type is visited,
  the same predicate the ``view add`` verb itself gates its own single write on — only the
  consequence differs: this runner skips the whole pair and moves to the next one, rather than
  raising for the entire run. An adopter who dropped a bundled view through
  ``[selected].views`` is not a corpus defect to halt on; they said they do not want that view.
- **A missing indexed file, or a body with no ``sq:body`` region** (either step) —
  :func:`~squads._itemfile.read_item_text` raises for the former;
  :func:`~squads._sections.get_section` answers ``None`` for the latter. Caught and turned into
  the same per-item skip. A hand-adopted corpus, or a hand-edited item, can carry either shape
  without it being a defect this migration should decide anything about.
- **The tag already present, but outside ``sq:body``** (step one) — the placement routine only
  ever reads and writes inside the region, so a copy an author moved outside it by hand is
  invisible to it; asked here, once, before the routine ever runs, so this runner never seeds a
  second, in-region copy alongside one already live elsewhere in the file (which `sq check`'s
  duplicate-marker finding would then report). Skipping here, rather than inserting blindly,
  keeps a migration's own write from leaving the corpus failing `sq check` the moment it is
  current enough to run — the same disposition as a missing file, and the same remedy once the
  squad is current: place or disable the tag explicitly.
- **A role/permanently-system-skill/per-item-type-skill body carrying marker-shaped content**
  (step two only) — this reclaim has no model for what that is (another tag, a nested region,
  corruption) and, like the standing sweep's own strict convergence, skips rather than guess at
  overwriting something structured.

The reclaim is a corpus-wide sweep, not a single-item mutation gated the ordinary way, so it
belongs in a migration, and the runner's own skip-messaging rule is what ``_cli/_migrate.py``'s
skip text follows.

Invoked by ``sq migrate up`` via ``_migrations._registry`` — never run directly (this module is
private).
"""

from pathlib import Path

from squads import _clock as clock
from squads._actor import current_session
from squads._errors import SquadsError
from squads._index._store import IndexStore
from squads._interactions import get_playbook_spec
from squads._interactions._loader import PLAYBOOK_OVERRIDE_FILENAME, load_playbook
from squads._interactions._models import PlaybookSpec
from squads._itemfile import read_frontmatter, read_item_text, write_text
from squads._migrations._outcome import MigrationOutcome
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._paths import SquadPaths, number_for_id
from squads._roles._catalog import get_catalog
from squads._sections import find_markers, get_section, replace_frontmatter, replace_section
from squads._views import (
    place_view_tags,
    resolve_view_target,
    roster_body_view_name,
    template_seeded_view_names,
)
from squads._workflow import bundled_spec
from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME, load_workflow_spec
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
still needs — a missing file needs restoring or re-adopting, a body with no `sq:body` region
needs one added by hand. Once that item's own problem is fixed, place the tag with
`sq milestone <n> view add milestone_rollup`.

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


def _active_spec(paths: SquadPaths) -> WorkflowSpec:
    """The spec this runner reads the milestone declaration and view catalog against — the
    bundled singleton, or a squad's own ``.overrides/workflow.toml`` merge when one is present.
    Mirrors how every other runner/``init``/``adopt`` resolve the spec they act against, so a
    squad whose override renamed, re-templated or dropped the milestone type gets exactly what
    its own declaration says, never the bundled default."""
    override_path = paths.squad_dir / WORKFLOW_OVERRIDE_FILENAME
    if not override_path.is_file():
        return bundled_spec()
    return load_workflow_spec(squad_dir=paths.squad_dir)


def _active_playbook(paths: SquadPaths, spec: WorkflowSpec) -> PlaybookSpec:
    """The playbook :func:`~squads._views.resolve_view_target` needs in hand (only a
    ``playbook``-sourced view ever reads it; the ``ref``-sourced ``milestone_rollup`` does not,
    but the predicate's signature is uniform across every source kind) — mirrors
    ``resolve_playbook``'s own fast-path/merge split (``_services/_service.py``): the bundled
    singleton with no reparse when *spec* is the untouched bundled spec and no playbook
    override file exists, the merged document otherwise."""
    override_path = paths.squad_dir / PLAYBOOK_OVERRIDE_FILENAME
    if spec is bundled_spec() and not override_path.is_file():
        return get_playbook_spec()
    return load_playbook(get_catalog(), spec=spec, squad_dir=paths.squad_dir)


def _tag_present_outside_region(text: str, region_tag: str, name: str) -> bool:
    """Whether view *name*'s tag (either state) appears somewhere in *text* but not inside
    *region_tag*'s own section — the shape a hand-moved tag produces (see module docstring).
    Deliberately a runner-local question, asked before the placement routine (which only ever
    reads/writes inside the region) ever runs, so this runner never seeds a second, in-region
    copy alongside one already live elsewhere in the file.

    ``False`` when *region_tag*'s section is absent — that shape is the missing-region skip the
    caller reaches separately (:func:`~squads._sections.get_section` answering ``None``), not
    this one, so this function never doubles as that check."""
    inner = get_section(text, region_tag)
    if inner is None:
        return False
    enabled = markers.open_marker(markers.view_tag(name))
    disabled = markers.open_marker(markers.view_tag(name, disabled=True))
    return any(raw in text and raw not in inner for raw in (enabled, disabled))


async def _write_body_change(path: Path, text: str, new_inner: str) -> str:
    """*text* with its ``sq:body`` region replaced by *new_inner*, and ``updated_at`` bumped on
    the file's **own** frontmatter — read fresh from *text* itself, never from a possibly
    mid-chain-stale index-derived ``Item`` (see the module docstring's mid-chain-skew
    paragraph). Writes the result and returns it.

    ``modified_session`` is set only when there is a real session id to record — the same
    convention ``Item.to_frontmatter_dict`` follows (``_models/_item.py``: "Session fields are
    omitted when unset to keep legacy files unchanged"). Outside a session, *sid* is ``None``,
    and this leaves the key exactly as it already reads in *data* — present with its stored
    value if one is already there, absent otherwise — rather than writing a stray
    ``modified_session: null`` onto a file no session ever touched."""
    data = read_frontmatter(text=text, source=str(path))
    data["updated_at"] = clock.iso(clock.now())
    sid, _ = current_session()
    if sid is not None:
        data["modified_session"] = sid
    new_text = replace_frontmatter(replace_section(text, markers.BODY, new_inner), data)
    await write_text(path, new_text)
    return new_text


async def migrate(paths: SquadPaths) -> MigrationOutcome:
    """Two independent steps, one run, one transaction, one reported outcome (see the module
    docstring for why each belongs here):

    - Seed every resolvable ``sq:view:<name>`` a non-roster type's creation template declares
      onto every existing item of that type — today that is milestone/``milestone_rollup``
      alone.
    - Reclaim a pre-0.14 role's, permanently-system skill's, or per-item-type skill's legacy
      plain-prose body onto its own view tag — the one-time licence
      :func:`~squads._services._maintenance._converge_body_tag`'s standing sweep gave up in
      this same release.

    ``count`` is the number of bodies either step actually changed — ``0`` on a corpus with
    nothing eligible for either, or one already fully converged (a re-run's own idempotent-skip
    result). ``skipped`` names, by id, every item either step left untouched rather than acting
    on — a missing indexed file, no ``sq:body`` region, the tag already present outside it, or
    (the second step only) marker-shaped content it has no model for — always empty when
    ``count`` alone tells the whole story."""
    spec = _active_spec(paths)
    playbook = _active_playbook(paths, spec)

    # (item_type, view names to seed) — resolved once against the shared derivation and
    # restricted to non-roster types — never against a hand-pinned "milestone"/"milestone_rollup"
    # literal, so a project's own re-templated non-roster type is migrated the same way. Only a
    # name that can actually resolve against its host type is placed (the same gate the `view
    # add` verb itself asks); an unresolvable one skips the whole pair, not the run.
    seeded_by_type: dict[str, frozenset[str]] = {}
    for item_type in sorted(spec.non_roster_types()):
        names = frozenset(
            name
            for name in template_seeded_view_names(item_type, spec)
            if resolve_view_target(name, item_type, spec, playbook) is None
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
                    # A missing indexed file — this item's own problem, not this migration's
                    # to raise the whole run over. Left untouched on disk; the pass moves on.
                    skipped.append(it.id)
                    continue
                if any(_tag_present_outside_region(text, markers.BODY, n) for n in names):
                    # A copy already lives outside sq:body (an author moved it by hand). The
                    # placement routine only ever reads/writes inside the region and would not
                    # see it, so calling it unconditionally would seed a second, in-region
                    # copy — a duplicate marker `sq check` reports at error level. Skip rather
                    # than risk it; see module docstring.
                    skipped.append(it.id)
                    continue
                region = get_section(text, markers.BODY)
                if region is None:
                    # No sq:body region to place the tag in (a hand-adopted or hand-edited
                    # file). Same disposition as the missing-file case above.
                    skipped.append(it.id)
                    continue
                # `get_section` returns the region padded with its own opening/closing
                # newline; the placement routine never pads its output that way (its own
                # spacing rule keeps the region's edges bare), so the no-op comparison below
                # strips that padding first — otherwise an already-seeded region would never
                # compare equal to its own re-placement and every idempotent re-run would
                # report a change it did not make.
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

        # Second step, same transaction: reclaim a pre-0.14 role's, permanently-system skill's,
        # or per-item-type skill's legacy plain-prose body — see the module docstring's
        # "second step" paragraph and :func:`_reclaim_legacy_roster_bodies`.
        step_changed, step_skipped = await _reclaim_legacy_roster_bodies(db, spec, paths)
        changed += step_changed
        skipped.extend(step_skipped)
    return MigrationOutcome(count=changed, skipped=tuple(skipped))


async def _reclaim_legacy_roster_bodies(
    db: SquadsDB, spec: WorkflowSpec, paths: SquadPaths
) -> tuple[int, list[str]]:
    """``(changed, skipped)`` for the pre-0.14 role/permanently-system-skill/per-item-type-skill
    legacy-body reclaim — see the module docstring's "second step" paragraph. Split out of
    :func:`migrate` purely to keep that function under the complexity ceiling; every write
    happens inside the caller's already-open transaction, over the same ``db`` and *spec*.

    :func:`~squads._views.roster_body_view_name` is the same classification the roster write
    refusal and ``sq check``'s finding both read — the legacy reclaim set **is** that
    classification, with no further test applied: every marker-free, non-empty roster body is
    overwritten onto its tag, whatever it holds, and a custom skill matching no declared type is
    never in scope at all, because it classifies to ``None``."""
    changed = 0
    skipped: list[str] = []
    roster_items = sorted(
        (it for it in db.items.values() if it.type in (ROSTER_ROLE, ROSTER_SKILL)),
        key=lambda it: it.sequence_id,
    )
    for it in roster_items:
        slug = it.extra.get(X.SLUG, it.slug) if it.type == ROSTER_SKILL else it.slug
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
            # The region itself is absent, not merely empty — the module docstring's "a body
            # with no sq:body region (either step)" condition, reported here the same way step
            # one already reports it: this reclaim is not the standing sweep, and is not the
            # place to decide whether a hand-edited or corrupted file's missing region is safe
            # to reinstate either — that is `_converge_body_tag`'s own, separate licence.
            skipped.append(it.id)
            continue
        current = region.strip()
        tag_line = markers.open_marker(markers.view_tag(view_name))
        if not current or current == tag_line:
            # Empty is the standing sweep's job, unconditionally; already-tagged needs no
            # write. Neither is this one-time pass's to act on.
            continue
        if find_markers(current):
            # Marker-shaped content this reclaim has no model for (another tag, a nested
            # region, corruption) — skip rather than guess at overwriting something
            # structured, the same posture the standing sweep's own strict convergence takes
            # for the identical shape.
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
