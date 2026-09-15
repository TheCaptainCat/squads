"""Schema 0.14 → 0.15 runner: seed the milestone roll-up view tag onto every existing milestone.

The architecture ruling behind this runner retires the milestone roll-up's old
type-attachment (``items.milestone.views``) in favour of the general ``sq:view:<name>`` tag
mechanism: a milestone created
after this change gets the tag for free, straight from ``templates/items/milestone.md.j2``
(``ServiceCore._create_core``, unrelated to this runner) — but type-attachment applied
retroactively to every existing item of a type, and a tag does not. Without this one-time
pass, every milestone already on disk would quietly lose its roll-up the moment the type
attachment is dropped, because its body carries no tag and nothing else places one.

**The licence is inherited, not reimplemented.** Insert-only, the one deterministic anchor
(the end of the ``sq:body`` region), idempotent-skip, and the predicate that decides whether a
name can resolve at all live in :func:`~squads._sections.insert_unpaired_marker` and
:func:`~squads._views.resolve_view_target` — the exact two primitives
``ServiceCore._locked_section_edit``/``ViewsMixin.insert_view`` compose into the placement
verb. This runner does not call that verb directly, but the reason is narrower than an import
cycle: the *static* cycle (``squads._services`` reaching this module through the migration
registry) is real, but a deferred import inside a function body is not blocked by it — this
codebase uses that pattern freely elsewhere, including one in this very module (see the
transaction-shape paragraph below). What the verb genuinely cannot provide is this runner's
own transaction shape: one open ``store.transaction()`` for every eligible item, not one per
item. So this runner drives the same two primitives itself, through the same leaf modules
(``_sections``, ``_itemfile``, ``_views``) the verb is built from, rather than inventing a
second spelling of any of the properties those primitives already guarantee.

**Scope: every non-roster type whose creation template seeds a view tag, today that is
exactly milestone/milestone_rollup.** :func:`~squads._views.template_seeded_view_names` is the
one derivation this runner and the sibling ``sq check`` advisory both read (never a second
implementation of "which view names a type's creation template places"); this runner restricts
its own iteration to :meth:`WorkflowSpec.non_roster_types` deliberately, on top of that shared
derivation, because a roster type's body is owned by a wholly different, already-existing
convergence sweep (``MaintenanceMixin._backfill_roster_body_tags``/``_converge_body_tag``,
``_services/_maintenance.py``) that already keeps a role's/system-skill's own seeded tag
current on every ``sq repair``/``sq sync`` — extending that machinery, or this runner, onto the
other's territory is exactly what that ruling fences off ("not a convergence sweep"). A project
whose own override seeds a tag on a *custom* non-roster type is migrated by the same pass the
derivation resolves it through; a project that dropped the bundled tag is not touched, since
the derivation then answers empty for that type.

**Transaction shape: one open transaction for the whole run**, mirroring the bulk importer's
own precedent (``ImportMixin._apply_import`` opening one ``store.transaction()`` and driving
``_section_edit_core`` per event) rather than ``insert_view``'s one-transaction-per-item shape
— chosen deliberately, not forced by any cycle, because it inlines the identical read →
skew-check → mutate → write sequence itself and avoids N separate lock acquisitions and N
separate index commits for what is, in practice, a handful of milestones.

**Nothing this runner meets aborts the run — every condition it cannot act on is a skip,
reported by item id, never a raise.** A run that always completes always reaches the ``async
with store.transaction() as db:`` block's own exit, which is the only place the schema stamp
that follows gets written — so a run that can raise is a run that can leave a squad with
markdown ahead of an uncommitted index and no working command to reconcile the two with
(``sq repair`` needs the very stamp a raised transaction never writes). Skip-and-report closes
that off structurally: there is no path left on which this runner raises, so there is no
partial-pass state to reach.

Three conditions this runner meets and does not act on, each a skip rather than a refusal:

- **An unresolvable ``(type, name)`` pair** — :func:`~squads._views.resolve_view_target` names
  a reason (undeclared, no resolvable template, or a source that cannot apply to *item_type*).
  Asked once per pair, before any item of that type is visited, the same predicate
  ``insert_view`` itself gates its own single write on — only the consequence differs: this
  runner skips the whole pair and moves to the next one, rather than raising for the entire
  run. An adopter who dropped a bundled view through ``[selected].views`` is not a corpus
  defect to halt on; they said they do not want that view. The tag a template still seeds for
  a dropped view is not lost track of either way — ``sq check``'s dangling-name finding names
  it, reachable the moment the run that skipped it has also stamped the squad current.
- **A skewed item** — on-disk frontmatter has diverged from the index
  (:func:`~squads._itemfile.ensure_no_skew`). Skipped, left untouched on disk, the pass moves
  to the next item. The stamp still lands once the transaction closes, so ``sq repair`` — the
  skewed item's actual remedy — is reachable by the ordinary route afterwards, the same as any
  other skew this tool ever reports.
- **A missing indexed file, or a body with no ``sq:body`` region** —
  :func:`~squads._itemfile.read_item_text` and
  :func:`~squads._sections.insert_unpaired_marker` each raise for their own condition; caught
  here and turned into the same per-item skip. A hand-adopted corpus, or a hand-edited item,
  can carry either shape without it being a defect this migration should decide anything about.
- **The tag already present, but outside ``sq:body``** —
  :func:`~squads._sections.insert_unpaired_marker`'s own idempotence check is
  **region-scoped, deliberately** (a wider, whole-file check regressed the placement verb —
  see its own docstring), so calling it unconditionally here would not see a copy an author
  moved out of the region and would insert a second, in-region one: two markers naming the
  same tag, on a file that had exactly one before this migration ever touched it. Driven: `sq
  check` reports that duplicate at error level the moment the squad is current enough to run
  it — a migration whose own write leaves the corpus failing `sq check`, which is the one
  outcome this runner exists to avoid, not merely an unhelpful skip. This runner asks the
  whole-file question itself, once, before ever calling the region-scoped primitive, and skips
  rather than risk seeding that second copy — the same disposition as skew and a missing file,
  and the same remedy: `sq view add`, reachable once the run has stamped the squad current.

Invoked by ``sq migrate up`` via ``_migrations._registry`` — never run directly (this module is
private).
"""

from squads import _clock as clock
from squads._actor import current_session
from squads._errors import SquadsError
from squads._index._store import IndexStore
from squads._interactions import get_playbook_spec
from squads._interactions._loader import PLAYBOOK_OVERRIDE_FILENAME, load_playbook
from squads._interactions._models import PlaybookSpec
from squads._itemfile import ensure_no_skew, read_item_text, write_text
from squads._migrations._outcome import MigrationOutcome
from squads._models import _markers as markers
from squads._paths import SquadPaths
from squads._roles._catalog import get_catalog
from squads._sections import get_section, insert_unpaired_marker, replace_frontmatter
from squads._views import resolve_view_target, template_seeded_view_names
from squads._workflow import bundled_spec
from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME, load_workflow_spec
from squads._workflow._models import WorkflowSpec

MANUAL = """\
## Schema 0.14 → 0.15 — the milestone roll-up moves onto its view tag

The milestone roll-up (`sq milestone <n> show`) used to be a type-attached view
(`items.milestone.views`); it is now placed by a `sq:view:milestone_rollup` tag inside the
milestone's own `sq:body` region — the same mechanism a role's own definition, and each
system skill's text, already render through.

This migration inserts that tag into every existing milestone body that does not already carry
one, through the tool's own marker-safe placement primitive (never a bespoke write into
authored prose) — so **every milestone body in your corpus gains one line**. `sq migrate up`
reports how many; review the diff before committing, the same posture every migration that
touches your corpus asks for. A milestone whose body you had already hand-edited to carry the
tag, or that carries no `sq:body` region at all, is left exactly as it was.

A milestone this migration cannot safely place the tag on is **skipped, not aborted**: the run
still completes and the rest of your corpus is still migrated. `sq migrate up` names every
skipped item by id, and `sq check` (reachable again once the run completes) reports what each
one still needs — a skewed item needs `sq repair`, a missing file needs restoring or
re-adopting, a body with no `sq:body` region needs one added by hand. Once that item's own
problem is fixed, place the tag with `sq milestone <n> view add milestone_rollup`.

A milestone whose tag you had already moved outside `sq:body` by hand is skipped too, for a
different reason and with a different remedy: it already carries the tag, so it is left exactly
as it was rather than have this migration insert a second, in-region copy alongside it (which
would duplicate it, not recognise it). **Do not run `sq view add` on one of these** — it would
do exactly that duplication itself, the same way this migration would have. There is nothing to
fix here; the tag is present, just not where a freshly-created milestone's is.

No other item type is touched by this step: only a type whose *creation template* currently
seeds a view tag is in scope, and today that is milestone alone.
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


def _tag_present_outside_region(text: str, region_tag: str, marker_tag: str) -> bool:
    """Whether *marker_tag*'s marker appears somewhere in *text* but not inside
    *region_tag*'s own section — the shape a hand-moved tag produces (see module docstring).
    Deliberately a runner-local question, never a change to
    :func:`~squads._sections.insert_unpaired_marker`'s own region-scoped idempotence check:
    asking it here, before that primitive is ever called, is what keeps this runner from
    seeding a second, in-region copy alongside one already live elsewhere in the file.

    ``False`` when *region_tag*'s section is absent — that shape is the missing-region skip
    the caller already reaches through :func:`~squads._sections.insert_unpaired_marker`'s own
    ``KeyError``, not this one, so this function never doubles as that check."""
    marker = markers.open_marker(marker_tag)
    if marker not in text:
        return False
    inner = get_section(text, region_tag)
    return inner is not None and marker not in inner


async def migrate(paths: SquadPaths) -> MigrationOutcome:
    """Seed ``sq:view:<name>`` onto every existing item whose type's creation template seeds
    *name*, restricted to non-roster types (see module docstring). ``count`` is the number of
    item bodies actually changed — ``0`` on a corpus with no eligible type, no eligible item,
    every eligible pair unresolvable, or one already fully tagged (a re-run's own
    idempotent-skip result, matching what the placement primitive it is built from already
    promises). ``skipped`` names, by id, every item this pass left untouched rather than acting
    on — skew, a missing indexed file, no ``sq:body`` region, or the tag already present
    outside it (see module docstring) — always empty when ``count`` alone tells the whole
    story."""
    spec = _active_spec(paths)
    playbook = _active_playbook(paths, spec)

    # (item_type, view_name) pairs to place, resolved once against the shared derivation and
    # restricted to non-roster types — never against a hand-pinned "milestone"/"milestone_rollup"
    # literal, so a project's own re-templated non-roster type is migrated the same way.
    targets: list[tuple[str, str]] = [
        (item_type, name)
        for item_type in sorted(spec.non_roster_types())
        for name in sorted(template_seeded_view_names(item_type, spec))
    ]
    if not targets:
        return MigrationOutcome(count=0)

    # Asked once per (type, name) pair — never per item — the same predicate insert_view
    # itself gates its own single write on. A name the derivation found seeded in a template
    # but that cannot actually resolve (undeclared, template missing, or a source inapplicable
    # to this host type) skips the whole pair rather than the run: see module docstring.
    resolvable = [
        (item_type, name)
        for item_type, name in targets
        if resolve_view_target(name, item_type, spec, playbook) is None
    ]
    if not resolvable:
        return MigrationOutcome(count=0)

    changed = 0
    skipped: list[str] = []
    store = IndexStore(paths.index_path, paths.lock_path, spec=spec)
    async with store.transaction() as db:
        for item_type, name in resolvable:
            tag = markers.view_tag(name)
            items = sorted(
                (it for it in db.items.values() if it.type == item_type),
                key=lambda it: it.sequence_id,
            )
            for it in items:
                base = it.model_copy(deep=True)
                path = paths.abspath(it.path)
                try:
                    text = await read_item_text(path, it.id)
                    ensure_no_skew(text, base, default_kind=spec.default_ref_kind())
                except SquadsError:
                    # A missing indexed file or a real frontmatter skew — this item's own
                    # problem, not this migration's to raise the whole run over. Left
                    # untouched on disk; the pass moves on to the next item.
                    skipped.append(it.id)
                    continue
                if _tag_present_outside_region(text, markers.BODY, tag):
                    # A copy already lives outside sq:body (an author moved it by hand).
                    # insert_unpaired_marker's own idempotence check is region-scoped and
                    # would not see it, so calling it unconditionally would seed a second,
                    # in-region copy — a duplicate marker sq check reports at error level.
                    # Skip rather than risk it; see module docstring.
                    skipped.append(it.id)
                    continue
                try:
                    new_text, inserted = insert_unpaired_marker(text, markers.BODY, tag)
                except KeyError:
                    # No sq:body region to place the tag in (a hand-adopted or hand-edited
                    # file). Same disposition as the skew/missing-file case above.
                    skipped.append(it.id)
                    continue
                if not inserted:
                    continue
                it.updated_at = clock.now()
                it.modified_session, _ = current_session()
                await write_text(path, replace_frontmatter(new_text, it.to_frontmatter_dict()))
                changed += 1
    return MigrationOutcome(count=changed, skipped=tuple(skipped))
