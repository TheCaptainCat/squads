"""Schema 0.11 → 0.14 runner: two new bundled item types join the vocabulary.

Both types are declared entirely in code already shipped ahead of this runner (one
``[items.<type>]`` block plus one ``[lifecycles.<type>]`` block each, in the bundled workflow
spec) — this runner owns none of that declaration. What it owes an existing squad is the two
things a declaration alone never produces on disk: the type's own folder, and its generated
agent-facing surface (a managed ``sq-<type>`` skill body, that skill's ``.claude`` pointer, and
the compiled ``CLAUDE.md``/``AGENTS.md`` regions that reference it) — every one of which ``sq
init``/``sq adopt`` already write for a squad created after the declaration landed, and none of
which a squad created *before* it ever gets on its own.

No existing item data is rewritten: every write this runner performs is either creating a path
that did not exist, or replacing a body region this same runner is the first-ever author of.
Ordering mirrors ``init``'s own: the managed surface is (re)written first (mirroring
``Service.refresh_managed``), then any not-yet-indexed skill body just written is stamped as a
``SKILL`` item (mirroring ``Service.seed_bundled_skills``) — both idempotent, so a squad that
already carries this content (this repository's own squad, synced after the two types were
declared but before this runner shipped) sees no further writes at either step.

**Deliberately narrower than a full ``Service.sync()``.** This runner regenerates exactly the
surface a type declaration grows — the two new skills' bodies/pointers and the compiled
``CLAUDE.md``/``AGENTS.md`` regions — by calling the same backend methods ``sync`` calls
(``ensure_scaffold``, ``write_managed``) with the squad's current live roster read straight off
the index. It does **not** touch any existing role's own per-entry pointer (each role's resolved
preload-skill list, including any project-declared skill scoped to that role via a ``scopes``
ref edge) — that convergence is an ongoing ``sq sync`` responsibility independent of any schema
migration, not owed by the one-time act of a type's own folder/skill appearing. Running `sq
sync` after this migration remains the right move on a squad that customises role/skill scoping;
it converges to the identical result on one that does not, since the two live-roster reads
resolve to the same roster either way.

**Frozen against no wire-encoded corpus vocabulary, because none is read.** Every id/ref/status
literal this runner touches is either freshly minted (a new ``SKILL`` item's own id, allocated
the same way every other runner allocates one) or read from the *live* declared type/playbook
vocabulary — which is exactly the vocabulary the type declaration this runner depends on already
put in place, not a corpus-era value at risk of drifting out from under a frozen literal. See
``tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py`` for the boundary
this still respects: no id/ref/padding *formatting* primitive is imported from ``_models``
regardless.

Invoked by ``sq migrate up`` via ``_migrations._registry`` — never run directly (this module is
private).
"""

from pathlib import Path

from squads import _aio
from squads import _clock as clock
from squads._backends._base import BackendContext, OperatorView, RoleView
from squads._backends._registry import get_backend
from squads._index._store import IndexStore
from squads._interactions import get_playbook_spec, item_skill_name, skill_description
from squads._interactions._loader import PLAYBOOK_OVERRIDE_FILENAME, load_playbook
from squads._interactions._models import PlaybookSpec
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._models._vocab import prefix_for
from squads._paths import SquadPaths, number_for_id
from squads._roles._catalog import get_catalog
from squads._sections import join_frontmatter, split_frontmatter
from squads._workflow import ROSTER_OPERATOR, ROSTER_ROLE, ROSTER_SKILL, bundled_spec
from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME, load_workflow_spec
from squads._workflow._models import WorkflowSpec

#: The two type names this runner is chartered to bring onto an existing squad's disk. Declared
#: by the workflow spec, not invented here — this tuple only names *which* declared entries this
#: runner's own folder/surface step applies to; every value it uses to act on them (folder,
#: prefix, lifecycle) is read from the active spec at call time, never pinned locally.
_NEW_TYPES: tuple[str, ...] = ("contract", "milestone")

MANUAL = """\
## Schema 0.11 → 0.14 — two new item types

Two item types are now available:

- **contract** (`PRD`) — the living functional contract: what the product does for a user,
  right now, kept current in place as the product evolves.
- **milestone** (`MILE`) — a named target for a set of work (a release, a cycle, anything work
  can be aimed at); a work item joins one by carrying a `targets` ref to it.

No action is required. Optionally, seed a first item of either type for your squad's current
capabilities:

```
sq create contract
sq create milestone
```
"""


def _active_spec(paths: SquadPaths) -> WorkflowSpec:
    """The spec this runner scaffolds against — the bundled singleton, or a squad's own
    ``.overrides/workflow.toml`` merge when one is present. Mirrors how ``init``/``adopt``
    resolve the spec they scaffold against, so a squad whose override renamed or dropped one of
    the two new types gets exactly what its own declaration says, not the bundled default."""
    override_path = paths.squad_dir / WORKFLOW_OVERRIDE_FILENAME
    if not override_path.is_file():
        return bundled_spec()
    return load_workflow_spec(squad_dir=paths.squad_dir)


def _active_playbook(paths: SquadPaths, spec: WorkflowSpec) -> PlaybookSpec:
    """The playbook this runner renders per-type skill guidance from — mirrors
    ``resolve_playbook``'s own fast-path/merge split (``_services/_service.py``): the bundled
    singleton with no reparse when *spec* is the untouched bundled spec and no playbook override
    file exists, the merged document otherwise."""
    override_path = paths.squad_dir / PLAYBOOK_OVERRIDE_FILENAME
    if spec is bundled_spec() and not override_path.is_file():
        return get_playbook_spec()
    return load_playbook(get_catalog(), spec=spec, squad_dir=paths.squad_dir)


async def _ensure_type_folders(paths: SquadPaths, spec: WorkflowSpec) -> int:
    """Create each new type's folder if missing — idempotent, matching what ``init``/``adopt``
    do per declared type at creation time. A type an override has dropped from *spec* is skipped
    outright: this runner cannot, and must not, create a folder for a type the active squad no
    longer declares."""
    created = 0
    for item_type in _NEW_TYPES:
        if item_type not in spec.items:
            continue
        folder = paths.folder_for(item_type, spec)
        if not folder.is_dir():
            await _aio.mkdir(folder, parents=True, exist_ok=True)
            created += 1
    return created


async def _live_roster(
    paths: SquadPaths, spec: WorkflowSpec
) -> tuple[list[RoleView], list[OperatorView], dict[str, Path]]:
    """The live-roster views ``write_managed`` needs, read straight off the index — the same
    projection :meth:`Service.roster`/:meth:`Service.operators`/:meth:`Service._skill_paths`
    apply, reproduced locally because a migration runner has no ``Service`` to call (that would
    be a genuine import cycle: ``_services`` already imports the migration registry to run this
    module). Empty when the index does not exist yet (defensive; every real migrate target has
    one)."""
    if not paths.index_path.is_file():
        return [], [], {}
    db = await IndexStore(paths.index_path, paths.lock_path).load()
    role_live = spec.live_statuses(ROSTER_ROLE)
    op_live = spec.live_statuses(ROSTER_OPERATOR)
    skill_live = spec.live_statuses(ROSTER_SKILL)
    items = sorted(db.items.values(), key=lambda it: it.sequence_id)
    roster = [
        RoleView(
            slug=it.extra.get(X.SLUG, it.slug),
            full_name=it.extra.get(X.FULL_NAME, it.title),
            title=it.extra.get(X.TITLE, it.title),
            is_default=it.extra.get(X.IS_DEFAULT, False),
            mission=it.extra.get(X.MISSION, it.description),
            responsibilities=tuple(it.extra.get(X.RESPONSIBILITIES, ())),
        )
        for it in items
        if it.type == ROSTER_ROLE and it.status in role_live
    ]
    operators = [
        OperatorView(
            slug=it.extra.get(X.SLUG, it.slug), full_name=it.extra.get(X.FULL_NAME, it.title)
        )
        for it in items
        if it.type == ROSTER_OPERATOR and it.status in op_live
    ]
    skill_paths = {
        it.extra[X.SLUG]: paths.abspath(it.path)
        for it in items
        if it.type == ROSTER_SKILL and X.SLUG in it.extra and it.status in skill_live
    }
    return roster, operators, skill_paths


async def _regenerate_surface(
    paths: SquadPaths, spec: WorkflowSpec, playbook: PlaybookSpec
) -> None:
    """(Re)write every active backend's roster/version-dependent files — scaffolding plus
    ``write_managed`` — exactly the two calls ``Service.sync``'s own backend loop makes, so the
    two new types' skill bodies, their ``.claude`` pointers, and the compiled
    ``CLAUDE.md``/``AGENTS.md`` regions appear the same way they would on a fresh ``sq init``.
    Every *other* declared type's managed skill is rewritten too — ``write_managed`` has no
    narrower entry point — but each is a body-region-only regen against already-correct content,
    so an existing squad sees no effective change to anything but the two new types' files."""
    roster, operators, skill_paths = await _live_roster(paths, spec)
    ctx = BackendContext(paths=paths, skill_paths=skill_paths, spec=spec, playbook=playbook)
    for backend_name in paths.config.active_backends:
        backend = get_backend(backend_name)
        await backend.ensure_scaffold(ctx)
        await backend.write_managed(ctx, roster, operators)


async def _seed_new_type_skills(paths: SquadPaths, spec: WorkflowSpec) -> int:
    """Stamp a ``SKILL`` item onto each new type's skill body ``_regenerate_surface`` just wrote,
    the same allocate → stamp → rewrite-pointer shape every prior runner that seeds a skill
    uses. Scoped to exactly the two slugs this runner is chartered to introduce — narrower than
    ``Service.seed_bundled_skills``' full bundled-slug sweep, which is a standing ``sq sync``
    responsibility this runner does not need to duplicate.

    Idempotent per slug: a convention-named file (``SKILL-<NNNNNN>-sq-<type>.md``) already
    present is left untouched, matching what a squad synced after the type was declared but
    before this runner shipped already carries.
    """
    if not paths.index_path.is_file():
        return 0
    skill_prefix = prefix_for(ROSTER_SKILL, spec)
    skills_folder = paths.squad_dir / spec.items[ROSTER_SKILL].folder
    slugs = [item_skill_name(t) for t in _NEW_TYPES if t in spec.items]
    seeded = 0
    for slug in slugs:
        if list(skills_folder.glob(f"{skill_prefix}-*-{slug}.md")):
            continue  # already a convention-named SKILL item — nothing to do
        legacy_path = skills_folder / f"{slug}.md"
        if not legacy_path.is_file():
            continue  # nothing to seed (regeneration above didn't run, or wrote nowhere)
        existing_text = await _aio.read_text(legacy_path)
        fm, _ = split_frontmatter(existing_text)
        if fm.get("id"):
            continue  # already stamped under the legacy name — leave to a future repair/rename

        store = IndexStore(paths.index_path, paths.lock_path)
        now = clock.now()
        async with store.transaction() as db:
            item_id = db.allocate_id(ROSTER_SKILL, prefix=skill_prefix)
            seq = number_for_id(item_id)
            new_name = f"{skill_prefix}-{seq:0{db.padding}d}-{slug}.md"
            squad_rel = f"{spec.items[ROSTER_SKILL].folder}/{new_name}"
            item = Item(
                sequence_id=db.counter,
                type=ROSTER_SKILL,
                prefix=skill_prefix,
                title=slug,
                slug=slug,
                status=spec.live_initial(ROSTER_SKILL),
                description=skill_description(slug),
                author=slug,
                path=squad_rel,
                created_at=now,
                updated_at=now,
                extra={X.SLUG: slug},
            )
            stamped_text = join_frontmatter(item.to_frontmatter_dict(), existing_text)
            new_path = skills_folder / new_name
            await _aio.write_text(new_path, stamped_text)
            await _aio.path_unlink(legacy_path)
            db.add(item)
        # Rewrite each backend's pointer to reflect the now-indexed skill — mirrors
        # seed_bundled_skills' own closing step. For these two system skills the pointer's
        # content does not actually depend on the item (its description is the compiled one,
        # not item.extra), so this is defensive symmetry with every other seeding runner
        # rather than a fix for a real drift.
        ctx = BackendContext(paths=paths, spec=spec, playbook=None)
        for backend_name in paths.config.active_backends:
            await get_backend(backend_name).generate_skill_entry(ctx, item)
        seeded += 1
    return seeded


async def migrate(paths: SquadPaths) -> int:
    """Create the two new types' folders, regenerate the managed agent-facing surface so their
    skills/pointers/compiled regions appear, and stamp each new skill as an indexed ``SKILL``
    item. Returns the count of folders created plus skills seeded (0 on a squad already carrying
    this content — e.g. one synced after the two types were declared in code but before this
    runner shipped)."""
    spec = _active_spec(paths)
    playbook = _active_playbook(paths, spec)
    changed = await _ensure_type_folders(paths, spec)
    await _regenerate_surface(paths, spec, playbook)
    changed += await _seed_new_type_skills(paths, spec)
    return changed
