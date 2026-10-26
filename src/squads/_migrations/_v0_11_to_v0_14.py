"""Schema 0.11 → 0.14 runner: two new bundled item types join the vocabulary. Both are declared
entirely in the bundled workflow spec (one ``[items.<type>]`` and one ``[lifecycles.<type>]`` block
each), which this runner does not own. It owes an existing squad what a declaration alone never
produces on disk: the type's folder and its generated agent-facing surface (a managed ``sq-<type>``
skill item, its ``.claude`` pointer, and the compiled ``CLAUDE.md``/``AGENTS.md`` regions
referencing it), which ``sq init``/``sq adopt`` write for a squad created after the declaration. The
skill's definition text is not among them, as a system skill renders from its template on every read
off the ``sq:view:item_skill`` tag in its ``sq:body`` (``squads._view_tags.expand_view_tags``, via
``ItemsMixin.read_body``).

No existing item data is rewritten, every write creating a path that did not exist. It follows
``init``'s order, writing the managed surface first (as ``Service.refresh_managed``) and then
stamping any newly created skill file as a ``SKILL`` item (as ``Service.seed_bundled_skills``), both
idempotent.

It is deliberately narrower than ``Service.sync()``: it calls the same backend methods
(``ensure_scaffold``, ``write_managed``) with the live roster read off the index, but touches no
existing role's per-entry pointer (its resolved preload list, including project skills scoped by a
``scopes`` edge), since that convergence is an ongoing ``sq sync`` duty, not owed by a type's folder
and skill appearing. An existing role interacting with either new type does carry a stale preload
list that ``sq check`` reports, so ``MANUAL`` names ``sq sync`` as the remedy rather than promising
a convergence this runner does not perform.

Every id, ref and status literal it touches is freshly minted (a new ``SKILL`` item's id, allocated
as other runners do) or read from the live declared type and playbook vocabulary that the
declaration put in place, so there is no corpus-era value to freeze. It still imports no id, ref or
padding formatting primitive from ``_models`` (see
``tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py``). It runs only through
``sq migrate up`` via ``_migrations._registry``.
"""

from pathlib import Path

from squads import _aio
from squads import _clock as clock
from squads._backends._base import BackendContext
from squads._backends._registry import get_backend
from squads._index._store import IndexStore
from squads._interactions._models import PlaybookSpec
from squads._interactions._skills import item_skill_name, skill_description
from squads._migrations._context import MigrationContext
from squads._migrations._legacy_extra import legacy_extra, with_legacy_extra
from squads._models._item import Item
from squads._models._vocab import prefix_for
from squads._paths import SquadPaths, number_for_id
from squads._roles._models import CatalogSource
from squads._roles._projection import OperatorView, RoleView
from squads._sections import join_frontmatter, split_frontmatter
from squads._workflow import ROSTER_OPERATOR, ROSTER_ROLE, ROSTER_SKILL
from squads._workflow._models import WorkflowSpec

#: The two type names this runner brings onto an existing squad's disk. They are declared by the
#: workflow spec; this tuple only names which declared entries the folder/surface step applies to,
#: and every value used to act on them (folder, prefix, lifecycle) is read from the active spec at
#: call time, never pinned.
_NEW_TYPES: tuple[str, ...] = ("contract", "milestone")

MANUAL = """\
## Schema 0.11 → 0.14 — two new item types

Two item types are now available:

- **contract** (`PRD`) — the living functional contract: what the product does for a user,
  right now, kept current in place as the product evolves.
- **milestone** (`MILE`) — a named target for a set of work (a release, a cycle, anything work
  can be aimed at); a work item joins one by carrying a `targets` ref to it.

Run `sq sync` next. Any existing role that interacts with either type — the bundled playbook
covers `architect`, `product-owner`, `tech-lead` and every `<tech>-dev` — still carries its
pre-0.14 preload list in its own `.claude/agents/<slug>.md` pointer until then; `sq check` will
flag it in the meantime. Optionally, seed a first item of either type for your squad's current
capabilities:

```
sq sync
sq create contract
sq create milestone
```

## Stored regions and role metadata are removed from your item files

This happens in the **index rebuild at the end of `sq migrate up`**, not in the step above.
`sq repair`, `sq adopt` and `sq renumber` all reach the same rebuild and perform the same
removal. Expect a content diff across your corpus; review it before committing, and prefer a
clean working tree when you run any of them, since none can separate its changes from yours.
All four print one line counting the item files they rewrote, and name those items in the
reflog — `sq renumber` under its own entry, by their post-shift ids. That is a count and a list
of ids, not the change itself, so read `git diff` for what actually moved.

What goes, and what answers for it now:

- **The sub-entity roll-up table and each block's badge line**, from any item file that carries
  them. Both were snapshots of state that lives in the item's frontmatter, rewritten on every
  change and stale the moment two branches touched the same item. `sq <type> <n> show` renders
  both from the frontmatter on every read, so nothing is lost and nothing can disagree any more.
- **A role's stored body**, which was a rendered copy of its definition. `sq role <slug> show`
  renders that definition fresh on every call, from the role catalog and your own role
  overrides. If you defined a role yourself, check its `.overrides/roles/<slug>.toml` is in
  place first: a role item that resolves against neither the catalog nor an override has nothing
  left to render from once the stored copy is gone.
- **The `extra` keys a role item mirrored from that same definition** — `full_name`, `title`,
  `mission`, `responsibilities`, `agreements`, `color`, `can_spawn`, `description` and the
  `skills` cache. Nothing writes any of them any more.

A role's body is emptied, never deleted: the marker pair stays and only its contents go.

**What a role keeps:** its `slug`, its default-role designation if it holds one, and — on a
developer role — its `model`, `is_dev` and `tech`, since `sq dev add` and `sq role set-default`
still write those. A non-developer role's stored `model` is removed with the rest. A role's own
top-level `title`, `status`, `author`, timestamps and refs are untouched, so `sq role list` and
`sq role <slug> show` still name every role exactly as before.

**No skill body is touched.** A **custom** skill — one you created with `sq skill add` — is
authored storage, is byte-identical afterwards, and keeps rendering from what you wrote,
including one whose slug happens to start with `sq-`. A **template-owned** skill's stored body
is left alone too: whether a slug is template-owned is a question about today's vocabulary and
a stored body was written under an earlier one, so on disk the two are indistinguishable. What
a bundled or `sq-<type>` skill still stores is simply inert — `sq skill <slug> show` renders
that definition from its template on every call and never reads it.

Untouched as well: every sub-entity's body and discussion, every item body other than a role's,
every operator item, and every frontmatter field on anything that is not a role.

One behaviour changes with the bytes: text that lived only in a removed region is no longer
matched by `sq search`. Read a role's mission and responsibilities through `sq role <slug> show`
and a sub-entity's status through `sq <type> <n> show` or `sq list`.
"""


async def _ensure_type_folders(paths: SquadPaths, spec: WorkflowSpec) -> int:
    """Create each new type's folder if missing, idempotently, as ``init``/``adopt`` do per declared
    type. A type an override dropped from *spec* is skipped: this runner must not create a folder
    for a type the active squad no longer declares.
    """
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
    """The live-roster views ``write_managed`` needs, read straight off the index. The operator and
    skill-path halves are the projection :meth:`Service.operators` and :meth:`Service._skill_paths`
    apply, but the role half is not :meth:`Service.roster`'s: that resolves each role through the
    catalog (:func:`~squads._roles._resolver.resolve_role_for_item`, merging a project role
    override), while this reads each role's stored ``extra`` mirror, because a runner is frozen
    against the corpus vocabulary of the version it transforms and that corpus carries the mirror.
    On a squad with a role override the mirror has not caught up with, the managed region ``sq
    migrate up`` writes therefore differs from the next ``sq sync``'s, which ``MANUAL``'s
    instruction to run ``sq sync`` closes. It is local because ``_services`` imports the migration
    registry, so calling ``Service`` here would be an import cycle. Empty when no index exists.
    """
    if not paths.index_path.is_file():
        return [], [], {}
    db = await IndexStore(paths.index_path, paths.lock_path, spec=spec).load()
    role_live = spec.live_statuses(ROSTER_ROLE)
    op_live = spec.live_statuses(ROSTER_OPERATOR)
    skill_live = spec.live_statuses(ROSTER_SKILL)
    items = sorted(db.items.values(), key=lambda it: it.sequence_id)
    roster = [
        RoleView(
            slug=legacy_extra(it).get("slug", it.slug),
            full_name=legacy_extra(it).get("full_name", it.title),
            title=legacy_extra(it).get("title", it.title),
            is_default=legacy_extra(it).get("is_default", False),
            mission=legacy_extra(it).get("mission", it.description),
            responsibilities=tuple(legacy_extra(it).get("responsibilities", ())),
        )
        for it in items
        if it.type == ROSTER_ROLE and it.status in role_live
    ]
    operators = [
        OperatorView(
            slug=legacy_extra(it).get("slug", it.slug),
            full_name=legacy_extra(it).get("full_name", it.title),
        )
        for it in items
        if it.type == ROSTER_OPERATOR and it.status in op_live
    ]
    skill_paths = {
        legacy_extra(it)["slug"]: paths.abspath(it.path)
        for it in items
        if it.type == ROSTER_SKILL and "slug" in legacy_extra(it) and it.status in skill_live
    }
    return roster, operators, skill_paths


async def _regenerate_surface(
    paths: SquadPaths, spec: WorkflowSpec, playbook: PlaybookSpec, catalog: CatalogSource
) -> None:
    """(Re)write every active backend's roster- and version-dependent files with the two calls
    ``Service.sync``'s backend loop makes (scaffolding and ``write_managed``), so the new types'
    skill files, ``.claude`` pointers and compiled ``CLAUDE.md``/``AGENTS.md`` regions appear as on
    a fresh ``sq init``. Every other type's managed skill passes through too, as ``write_managed``
    has no narrower entry point, but an existing skill file is left byte-untouched.
    """
    roster, operators, skill_paths = await _live_roster(paths, spec)
    ctx = BackendContext(
        paths=paths, skill_paths=skill_paths, spec=spec, playbook=playbook, catalog=catalog
    )
    # A frozen runner: it names its backends itself rather than taking the service's.
    for backend_name in paths.config.active_backends:
        backend = get_backend(backend_name)
        await backend.ensure_scaffold(ctx)
        await backend.write_managed(ctx, roster, operators)


async def _seed_new_type_skills(
    paths: SquadPaths, spec: WorkflowSpec, playbook: PlaybookSpec, catalog: CatalogSource
) -> int:
    """Stamp a ``SKILL`` item onto each new type's skill file :func:`_regenerate_surface` just
    created (allocate, stamp, rewrite the pointer, as every prior skill-seeding runner does), scoped
    to the two slugs this runner introduces rather than ``Service.seed_bundled_skills``' full sweep,
    which stays a ``sq sync`` duty. It is idempotent per slug: an existing convention-named file
    (``SKILL-<NNNNNN>-sq-<type>.md``) is untouched.
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

        store = IndexStore(paths.index_path, paths.lock_path, spec=spec)
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
                attributes=with_legacy_extra({"slug": slug}),
            )
            stamped_text = join_frontmatter(item.to_frontmatter_dict(), existing_text)
            new_path = skills_folder / new_name
            await _aio.write_text(new_path, stamped_text)
            await _aio.path_unlink(legacy_path)
            db.add(item)
        # Rewrite each backend's pointer to reflect the now-indexed skill, as seed_bundled_skills'
        # closing step does; for these system skills the pointer does not depend on the item, so
        # this is defensive symmetry with other seeding runners, not a drift fix.
        ctx = BackendContext(paths=paths, spec=spec, playbook=playbook, catalog=catalog)
        for backend_name in paths.config.active_backends:
            await get_backend(backend_name).generate_skill_entry(ctx, item)
        seeded += 1
    return seeded


async def migrate(ctx: MigrationContext) -> int:
    """Create the two new types' folders, regenerate the managed agent-facing surface so their
    skill files/pointers/compiled regions appear, and stamp each new skill as an indexed
    ``SKILL`` item. Returns the count of folders created plus skills seeded (0 on a squad
    already carrying this content — e.g. one synced after the two types were declared in code
    but before this runner shipped)."""
    paths, spec = ctx.paths, ctx.spec
    changed = await _ensure_type_folders(paths, spec)
    await _regenerate_surface(paths, spec, ctx.playbook, ctx.catalog)
    changed += await _seed_new_type_skills(paths, spec, ctx.playbook, ctx.catalog)
    return changed
