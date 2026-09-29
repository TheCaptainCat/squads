"""Shared test-only constants and helpers with no production analogue.

Kept separate from `conftest.py` (fixtures/autouse hooks) since these are plain importable
values, not pytest fixtures.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

_ANSI_SGR = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Drop ANSI SGR codes so width/flag assertions survive a color-forcing help console."""
    return _ANSI_SGR.sub("", text)


#: The exact badge glyph for each of the 9 built-in sub-entity statuses (subtask/story:
#: Todo/InProgress/Blocked/Done/Cancelled; review finding: Open/Fixed/Verified/WontFix).
#:
#: This is the test-layer's own golden reference — it has no production counterpart. Production
#: badge resolution is spec-driven (`WorkflowSpec.status_badge`, backed by the workflow TOML's
#: per-status `badge` field), which also covers custom statuses with a graceful default. This
#: dict exists purely so tests can pin the 9 built-in glyphs and catch accidental drift in the
#: spec's declared badges; update it deliberately if a built-in badge is ever meant to change.
EXPECTED_BUILTIN_STATUS_BADGES: dict[str, str] = {
    "Todo": "⚪",
    "InProgress": "🟡",
    "Blocked": "🔴",
    "Done": "🟢",
    "Cancelled": "⚫",
    "Open": "🔴",
    "Fixed": "🟡",
    "Verified": "🟢",
    "WontFix": "⚫",
}

#: The closed set of `[selected]` section names the workflow spec's loader will pass to
#: `squads._specmerge`'s merge engine — shared across the `test_specmerge_*` modules so the
#: accepted-section set is pinned in exactly one place, not duplicated per test file.
SPECMERGE_WORKFLOW_SECTIONS = frozenset(
    {"items", "statuses", "lifecycles", "collections", "subentity_kinds", "roles"}
)

#: Built-in type -> ID prefix, mirroring the bundled ``workflow.toml`` exactly.
#:
#: Test-only (no production analogue): production resolves this from the loaded
#: ``WorkflowSpec`` alone (the ``ItemType`` enum + reserved prefix map it used to
#: read this from are deleted). Tests that need a literal prefix — constructing an ``Item``
#: directly, or calling ``SquadsDB.allocate_id``/``format_id`` with an explicit prefix — use
#: this shared dict instead of each hardcoding their own copy.
BUILTIN_PREFIX: dict[str, str] = {
    "epic": "EPIC",
    "feature": "FEAT",
    "task": "TASK",
    "bug": "BUG",
    "decision": "ADR",
    "contract": "PRD",
    "milestone": "MILE",
    "review": "REV",
    "guide": "GUIDE",
    "role": "ROLE",
    "skill": "SKILL",
    "operator": "OP",
}

#: Built-in type -> squad-folder-relative subfolder, mirroring ``workflow.toml``.
#: Test-only — see :data:`BUILTIN_PREFIX`.
BUILTIN_FOLDER: dict[str, str] = {
    "epic": "epics",
    "feature": "features",
    "task": "tasks",
    "bug": "bugs",
    "decision": "adrs",
    "contract": "contracts",
    "milestone": "milestones",
    "review": "reviews",
    "guide": "guides",
    "role": "agents/roles",
    "skill": "agents/skills",
    "operator": "operators",
}

#: All 12 built-in type names, in the same order as :data:`BUILTIN_PREFIX`.
BUILTIN_TYPES: tuple[str, ...] = tuple(BUILTIN_PREFIX)

#: The 9 work-item types — excludes the 3 roster types (role/skill/operator).
WORK_TYPES: tuple[str, ...] = (
    "epic",
    "feature",
    "task",
    "bug",
    "decision",
    "contract",
    "milestone",
    "review",
    "guide",
)

#: The 3 roster types the engine binds by name.
ROSTER_TYPES: tuple[str, ...] = ("role", "skill", "operator")

#: All 23 built-in status names across every lifecycle (work/adr/review/bug/guide/agent +
#: sub-entity/finding), mirroring the bundled ``workflow.toml`` exactly.
#:
#: Test-only (no production analogue): production resolves the status vocabulary from the
#: loaded ``WorkflowSpec`` alone (the ``Status`` enum this used to enumerate is
#: deleted). Tests that need "every built-in status" (golden-lock set equality, terminal/
#: badge iteration) use this shared tuple instead of each hardcoding its own copy.
BUILTIN_STATUSES: tuple[str, ...] = (
    # work items
    "Draft",
    "Ready",
    "InProgress",
    "InReview",
    "Done",
    "Blocked",
    "Cancelled",
    # ADR / decision
    "Proposed",
    "Accepted",
    "Superseded",
    "Rejected",
    "Deprecated",
    # code review
    "Requested",
    "ChangesRequested",
    "Approved",
    # guide
    "Published",
    # role / skill / operator (agent lifecycle)
    "Active",
    "Archived",
    # sub-entities (subtasks / user stories)
    "Todo",
    # review findings
    "Open",
    "Fixed",
    "Verified",
    "WontFix",
)

#: The three statuses the bundled agent (role/skill/operator) lifecycle used to require before
#: the reserved-status floor was retired in favour of a role-keyed one — no status name is
#: reserved any more; these three remain ordinary declared vocabulary (Draft is now owned by
#: the work/guide lifecycles only, Active/Archived by the two-state agent lifecycle).
FLOOR_STATUSES: tuple[str, ...] = ("Draft", "Active", "Archived")

#: Default ``author`` for :func:`create_item` — a slug guaranteed present in every fixture-built
#: squad (the ``project``/``svc`` fixtures always init with the ``minimal`` roles bundle, which
#: registers only the manager role).
DEFAULT_TEST_AUTHOR = "manager"


async def create_item(svc: Any, item_type: str, title: str, **kwargs: Any) -> Any:
    """``svc.create()`` for call sites that have no opinion about who authored the item.

    ``Service.create()`` requires an explicit ``author`` — attribution is only knowable at the
    call site, so a caller that omits it fails there rather than acquiring a silent default (see
    ``_services/_base.py``). That is correct production behaviour, but it left several hundred
    setup-only test call sites (``svc.create("task", "t")`` as bare scaffolding for an unrelated
    assertion) with no attribution to give and no interest in one.

    This is the one place that invents a default, and it is visible and overridable: pass
    ``author=`` through ``kwargs`` to pick a specific slug (`setdefault` lets it win), or skip
    this helper and call ``svc.create`` directly whenever the test's actual subject is
    authorship, participation, or ``sq check``'s participant rules — those call sites should
    name the honest slug inline, not hide behind this default.
    """
    kwargs.setdefault("author", DEFAULT_TEST_AUTHOR)
    return await svc.create(item_type, title, **kwargs)


def throwaway_skill_item(slug: str, spec: Any) -> Any:
    """A well-formed, never-persisted ``skill`` item standing in for *slug* when no such item
    is (yet) on a service's live index — :func:`resolved_skill_definition`'s fallback when the
    caller has not seeded one.

    Test-only: production code has exactly one path to a skill's definition now
    (``ItemsMixin.read_body`` off a real, seeded item's own placement tag), and never needs a
    stand-in — a real skill item is seeded before a real read ever reaches one. This mirrors
    what production's own throwaway once did (the ``playbook``/``self`` source kinds a
    system-skill view declares constrain nothing beyond the host's *type*, and no bundled skill
    template ever reads an ``item.*`` field), so a test that wants "what would this skill's
    definition render as" without paying for a full seed still can.
    """
    from squads import _clock as clock
    from squads._models._item import Item
    from squads._workflow._models import ROSTER_SKILL

    now = clock.now()
    return Item(
        sequence_id=0,
        type=ROSTER_SKILL,
        title=slug,
        slug=slug,
        status=spec.live_initial(ROSTER_SKILL),
        path=f"agents/skills/{slug}.md",
        created_at=now,
        updated_at=now,
    )


async def resolved_skill_definition(svc: Any, slug: str) -> str:
    """The definition text a read would resolve for the template-owned skill named *slug*,
    against *svc*'s active spec/playbook/roster — the same source-resolution + presentation
    dispatch a real read expands a placement tag through (``squads._views.resolve_source`` /
    ``render_source_view``), against a real seeded item when one is on *svc*'s index and a
    :func:`throwaway_skill_item` otherwise.

    Test-only convenience: production never constructs this pair itself (:meth:`read_body`
    always has a real item), so there is no method on ``Service`` this wraps — see
    :func:`throwaway_skill_item` for why a stand-in is still test-legitimate.
    """
    from squads import _interactions as interactions
    from squads._models._extras import ExtraKey as X
    from squads._views import render_source_view, resolve_source
    from squads._workflow._models import ROSTER_SKILL

    # A permanently-system slug names its own view; every other template-owned slug is a
    # per-item-type skill and shares ITEM_SKILL_VIEW_NAME — whether or not *slug* still names a
    # declared type is resolved inside `resolve_source` itself (the emptiness case), never
    # pre-checked here.
    view_name = interactions.SYSTEM_SKILL_VIEW_NAMES.get(slug, interactions.ITEM_SKILL_VIEW_NAME)
    db = await svc.store.load()
    item = next(
        (
            it
            for it in db.items.values()
            if it.type == ROSTER_SKILL and it.extra.get(X.SLUG, it.slug) == slug
        ),
        None,
    ) or throwaway_skill_item(slug, svc.spec)
    view = svc.spec.views[view_name]
    result = resolve_source(
        view,
        view_name,
        item,
        db,
        svc.spec,
        svc.playbook,
        lambda: svc.roster_from_db(db),
        svc.paths.squad_dir,
    )
    rendered = render_source_view(view_name, result, item, svc.spec, svc.paths.config.squad_dir)
    return rendered.strip("\n")


def make_unreadable_by_the_os(path: Path) -> Callable[[], None]:
    """Make every read of *path* fail at the OS layer, on any platform, and return an undo.

    The obvious instrument -- ``path.chmod(0o000)`` -- is POSIX-only: on Windows ``os.chmod``
    can only toggle the read-only attribute and cannot withdraw read access at all, so the file
    stays perfectly readable, nothing degrades, and every assertion built on it reads a healthy
    corpus. Worse, the read-only attribute it *does* set makes the file an illegal ``os.replace``
    target, so a whole-corpus rewrite fails with a write error instead of the read error the
    test meant to stage.

    Replacing the file with a directory of the same name refuses the read everywhere instead:
    opening a directory raises ``IsADirectoryError`` on POSIX and ``PermissionError`` on Windows,
    both ``OSError``, both landing in the single ``except OSError`` arm of ``_aio.read_text`` and
    coming back out as ``UnreadableFileError``. The name still matches the ``*.md`` globs every
    corpus scan uses (``Path.glob`` does not filter directories), so the file is still *found*
    and then refused -- which is the state these tests are about.
    """
    original = path.read_bytes()
    path.unlink()
    path.mkdir()

    def _undo() -> None:
        path.rmdir()
        path.write_bytes(original)

    return _undo
