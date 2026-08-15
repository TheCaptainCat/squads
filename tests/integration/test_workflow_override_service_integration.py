"""``open_service`` threads a squad's (possibly overridden) spec into the ``Service`` it
returns: it picks up a valid override, fails closed with a lint pointer on a structurally
invalid one, and — the AC5 guarantee — fails closed when an override drops a status/type still
referenced by a *live* item, rather than silently orphaning that item's data. With no override
at all it uses the pre-validated bundled singleton (no re-parse). ``sq check`` surfaces the same
class of problem instead of crashing.
"""

import json
from pathlib import Path

import pytest

from squads._errors import AlreadyInitializedError, SquadsError
from squads._index._store import IndexStore
from squads._services import _service as service
from squads._workflow import bundled_spec, load_workflow_spec
from squads._workflow._loader import validate_against_index

pytestmark = pytest.mark.anyio

_INCIDENT_V1 = """
[statuses.Triage]
[statuses.Resolved]
role = "done"

[lifecycles.incident_lc]
initial = "Triage"
[lifecycles.incident_lc.transitions]
Triage = ["Resolved"]
Resolved = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
"""

# v2 redeclares the SAME custom type with a lifecycle that no longer mentions "Triage" at all —
# structurally valid on its own, but a live incident item is still sitting at status "Triage".
_INCIDENT_V2_DROPS_TRIAGE = """
[statuses.Triage2]
[statuses.Resolved]
role = "done"

[lifecycles.incident_lc]
initial = "Triage2"
[lifecycles.incident_lc.transitions]
Triage2 = ["Resolved"]
Resolved = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
"""


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


# --------------------------------------------------------------------------- open_service basics


async def test_open_service_picks_up_a_valid_override(project) -> None:
    _write_override(project.squad_dir, _INCIDENT_V1)
    svc = service.open_service()
    assert "incident" in svc.spec.items


async def test_open_service_raises_with_a_lint_pointer_on_a_structurally_invalid_override(
    project,
) -> None:
    _write_override(
        project.squad_dir,
        '[items.broken]\nprefix = "BRK"\nfolder = "brokens"\nlifecycle = "nonexistent_lifecycle"\n',
    )
    with pytest.raises(SquadsError, match="sq workflow lint"):
        service.open_service()


async def test_open_service_with_no_override_uses_the_bundled_singleton_fast_path(project) -> None:
    """No override → svc.spec IS the cached bundled singleton, not a freshly re-parsed copy."""
    svc = service.open_service()
    assert svc.spec is bundled_spec()


# --------------------------------------------------------------------------- AC5: fail closed
# when a live item's status/type would be orphaned by the (possibly-overridden) spec


async def test_validate_against_index_flags_a_live_items_status_dropped_from_the_spec(
    project, svc
) -> None:
    result = await svc.create("task", "Test task", author="manager")
    task_id = result.item.id

    bundled = load_workflow_spec()
    statuses_no_draft = {k: v for k, v in bundled.statuses.items() if k != "Draft"}
    mock_spec = type("_MockSpec", (), {"items": bundled.items, "statuses": statuses_no_draft})()

    store = IndexStore(project.index_path, project.lock_path)
    async with store.transaction() as db:
        errors = validate_against_index(mock_spec, db)  # type: ignore[arg-type]

    assert any("Draft" in e and task_id in e for e in errors)


async def test_validate_against_index_flags_a_live_items_type_dropped_from_the_spec(
    project, svc
) -> None:
    result = await svc.create("bug", "Test bug", author="manager")

    bundled = load_workflow_spec()
    items_without_bug = {k: v for k, v in bundled.items.items() if k != "bug"}
    mock_spec = type("_MockSpec", (), {"items": items_without_bug, "statuses": bundled.statuses})()

    store = IndexStore(project.index_path, project.lock_path)
    async with store.transaction() as db:
        errors = validate_against_index(mock_spec, db)  # type: ignore[arg-type]

    assert any("bug" in e for e in errors)
    assert any(result.item.id in e for e in errors)


async def test_validate_against_index_flags_a_subentitys_status_dropped_from_the_spec(
    project, svc
) -> None:
    result = await svc.create("task", "Task with subtask", author="manager")
    await svc.add_subtask(result.item.id, "My subtask")

    bundled = load_workflow_spec()
    statuses_no_todo = {k: v for k, v in bundled.statuses.items() if k != "Todo"}
    mock_spec = type("_MockSpec", (), {"items": bundled.items, "statuses": statuses_no_todo})()

    store = IndexStore(project.index_path, project.lock_path)
    async with store.transaction() as db:
        errors = validate_against_index(mock_spec, db)  # type: ignore[arg-type]

    assert any("Todo" in e and result.item.id in e for e in errors)


async def test_open_service_fails_closed_end_to_end_when_a_new_override_orphans_a_live_status(
    project,
) -> None:
    """The full AC5 path through ``open_service`` itself (not just the lower-level cross-check
    function): a squad with a live custom-type item at a custom status, then an override
    revision that drops that exact status — reopening the service must refuse, naming the
    offending item and the dropped status, and pointing at ``sq workflow lint``."""
    _write_override(project.squad_dir, _INCIDENT_V1)
    svc = service.open_service()
    result = await svc.create("incident", "Live incident", author="manager")
    assert result.item.status == "Triage"

    _write_override(project.squad_dir, _INCIDENT_V2_DROPS_TRIAGE)
    with pytest.raises(SquadsError) as exc_info:
        service.open_service()
    message = str(exc_info.value)
    assert "Triage" in message
    assert result.item.id in message
    assert "sq workflow lint" in message


# --------------------------------------------------------------------------- roster lifecycle
# floor: open_service raises fail-closed on a roster type violating it. The roster type-key
# lock refuses a brand-new category="roster" type outright, so the only way to exercise the
# floor at all is to shadow one of the three built-in roster types' `lifecycle` field — an
# ordinary field-merge — pointing it at a custom lifecycle that fails the floor.

_ROLE_ZERO_LIVE = """
[statuses.Spinning]
[statuses.Retired]
role = "done"

[lifecycles.gadget_lc]
initial = "Spinning"
[lifecycles.gadget_lc.transitions]
Spinning = ["Retired"]
Retired = []

[items.role]
lifecycle = "gadget_lc"
"""


async def test_open_service_raises_fail_closed_on_a_roster_type_with_no_live_status(
    project,
) -> None:
    """A category='roster' type whose lifecycle declares zero live statuses is refused at
    load, naming the offending type — never a traceback."""
    _write_override(project.squad_dir, _ROLE_ZERO_LIVE)
    with pytest.raises(SquadsError) as exc_info:
        service.open_service()
    message = str(exc_info.value)
    assert "role" in message
    assert "no live status" in message


# --------------------------------------------------------------------------- corpus alignment:
# a type's prefix/folder must still match the values its own live items were written under.
# The field-merge itself is legal in the abstract (proven in test_workflow_override_merge.py
# against an item-less type) — this is the live-index cross-check that gates it against a
# corpus that already has items filed under the old value.


async def test_validate_against_index_flags_a_live_items_type_re_prefixed_in_the_spec(
    project, svc
) -> None:
    result = await svc.create("task", "Test task", author="manager")
    task_id = result.item.id

    bundled = load_workflow_spec()
    reprefixed_task = bundled.items["task"].model_copy(update={"prefix": "TSK2"})
    mock_spec = type(
        "_MockSpec",
        (),
        {"items": {**bundled.items, "task": reprefixed_task}, "statuses": bundled.statuses},
    )()

    store = IndexStore(project.index_path, project.lock_path)
    async with store.transaction() as db:
        errors = validate_against_index(mock_spec, db)  # type: ignore[arg-type]

    assert any("task" in e and task_id in e and "TSK2" in e for e in errors)
    # no migration is ever named — only the two performable ways forward.
    assert not any("repad" in e or "retype" in e for e in errors)


async def test_validate_against_index_flags_a_live_items_type_re_foldered_in_the_spec(
    project, svc
) -> None:
    result = await svc.create("bug", "Test bug", author="manager")
    bug_id = result.item.id

    bundled = load_workflow_spec()
    refoldered_bug = bundled.items["bug"].model_copy(update={"folder": "defects"})
    mock_spec = type(
        "_MockSpec",
        (),
        {"items": {**bundled.items, "bug": refoldered_bug}, "statuses": bundled.statuses},
    )()

    store = IndexStore(project.index_path, project.lock_path)
    async with store.transaction() as db:
        errors = validate_against_index(mock_spec, db)  # type: ignore[arg-type]

    assert any("bug" in e and bug_id in e and "defects" in e for e in errors)


async def test_validate_against_index_leaves_an_item_less_types_re_prefix_unflagged(
    project, svc
) -> None:
    """The corpus-alignment check only ever fires against a type's OWN live items — a type with
    zero items in this squad is unaffected no matter what its prefix/folder become, which is
    what preserves the re-prefix/re-folder capability for the case it exists for."""
    await svc.create("task", "Unrelated live task", author="manager")

    bundled = load_workflow_spec()
    reprefixed_bug = bundled.items["bug"].model_copy(
        update={"prefix": "DEFECT", "folder": "defects"}
    )
    mock_spec = type(
        "_MockSpec",
        (),
        {"items": {**bundled.items, "bug": reprefixed_bug}, "statuses": bundled.statuses},
    )()

    store = IndexStore(project.index_path, project.lock_path)
    async with store.transaction() as db:
        errors = validate_against_index(mock_spec, db)  # type: ignore[arg-type]

    assert not any("bug" in e for e in errors)


async def test_a_trailing_slash_in_the_declared_folder_is_not_a_false_corpus_mismatch(
    project,
) -> None:
    """A folder spelled with a trailing slash (or any other path-syntax variant that names the
    same directory) must not read as a corpus misalignment: the item is filed under the
    directory the override declares, so reopening the service afterwards must not refuse."""
    _write_override(project.squad_dir, '[items.guide]\nfolder = "guides/"\n')
    svc = service.open_service()
    result = await svc.create("guide", "Trailing slash guide", author="manager")
    assert "guides" in result.path.parts

    # Every later command reopens the service the same way — must stay clean.
    reopened = service.open_service()
    assert "guide" in reopened.spec.items


async def test_open_service_fails_closed_on_a_re_folder_against_a_live_corpus(
    project,
) -> None:
    """A genuine folder change (not just a textual variant) against an existing corpus is
    still refused — the normalisation fix must not swallow a real mismatch."""
    svc = service.open_service()
    result = await svc.create("guide", "Live guide", author="manager")

    _write_override(project.squad_dir, '[items.guide]\nfolder = "handbooks"\n')
    with pytest.raises(SquadsError) as exc_info:
        service.open_service()
    message = str(exc_info.value)
    assert result.item.id in message
    assert "revert" in message


# --------------------------------------------------------------------------- badge-collection
# alignment: shrinking/replacing a badge collection a live item's field value still names is
# on the SAME cross-check plane as the type/status/prefix/folder walks above — never a load
# refusal that lint misses, and never left for the load-boundary vocab check
# (`_index/_store.py::_validate_badge_codes`) to discover with a misleading "run sq repair".


async def test_validate_against_index_flags_a_live_items_badge_code_dropped_from_its_collection(
    project, svc
) -> None:
    result = await svc.create("task", "Urgent task", author="manager", priority="urgent")

    bundled = load_workflow_spec()
    shrunk_priority = bundled.collections["priority"].model_copy(
        update={"badges": [b for b in bundled.collections["priority"].badges if b.code != "urgent"]}
    )
    mock_spec = type(
        "_MockSpec",
        (),
        {
            "items": bundled.items,
            "statuses": bundled.statuses,
            "collections": {**bundled.collections, "priority": shrunk_priority},
            "item_subentity_kind": bundled.item_subentity_kind,
            "subentity_kinds": bundled.subentity_kinds,
        },
    )()

    store = IndexStore(project.index_path, project.lock_path)
    async with store.transaction() as db:
        errors = validate_against_index(mock_spec, db)  # type: ignore[arg-type]

    assert any("priority" in e and "urgent" in e and result.item.id in e for e in errors)
    # never the misleading remedy no command actually performs.
    assert not any("run `sq repair`" in e for e in errors)


async def test_validate_against_index_leaves_a_still_valid_badge_code_unflagged(
    project, svc
) -> None:
    await svc.create("task", "Normal task", author="manager", priority="high")

    bundled = load_workflow_spec()
    store = IndexStore(project.index_path, project.lock_path)
    async with store.transaction() as db:
        errors = validate_against_index(bundled, db)

    assert not any("field" in e and "priority" in e for e in errors)


async def test_open_service_fails_closed_end_to_end_when_a_shrunk_collection_bricks_a_live_corpus(
    project,
) -> None:
    """The full path a real adopter hits: an override shrinks a bundled badge collection while
    a live item still carries the removed code — `sq workflow lint` must report it (never
    "spec OK"), and reopening the service must refuse rather than silently loading."""
    from squads._workflow._loader import lint_workflow_spec

    svc = service.open_service()
    result = await svc.create("task", "Urgent task", author="manager", priority="urgent")

    _write_override(
        project.squad_dir,
        '[collections.priority]\nlabel = "Priority"\n'
        'badges = [{ code = "high", label = "High" }, { code = "low", label = "Low" }]\n',
    )

    findings = lint_workflow_spec(project.squad_dir)
    assert any(
        level == "error" and "priority" in msg and result.item.id in msg
        for level, _loc, msg, _hint in findings
    )

    with pytest.raises(SquadsError) as exc_info:
        service.open_service()
    message = str(exc_info.value)
    assert result.item.id in message
    assert "urgent" in message


async def test_open_service_fails_closed_end_to_end_on_a_re_prefix_against_a_live_corpus(
    project,
) -> None:
    """The full ``open_service`` path (not just the lower-level cross-check): a built-in type
    re-prefixed while it still has a live item is refused, naming the item and pointing to the
    two performable remedies — never a migration verb, since no shipped command realigns an
    existing corpus."""
    svc = service.open_service()
    result = await svc.create("task", "Live task", author="manager")

    _write_override(project.squad_dir, '[items.task]\nprefix = "TSK2"\n')
    with pytest.raises(SquadsError) as exc_info:
        service.open_service()
    message = str(exc_info.value)
    assert result.item.id in message
    assert "revert" in message
    assert "repad" not in message
    assert "retype" not in message


# --------------------------------------------------------------------------- sq check surfaces
# (not crashes on) a workflow-spec problem


async def test_check_reports_no_workflow_issue_when_the_spec_is_valid(project, svc, invoke) -> None:
    result = await invoke(["check"])
    assert "workflow config invalid" not in result.output


async def test_check_surfaces_a_one_line_workflow_warning_for_an_invalid_spec(
    project, svc, invoke
) -> None:
    _write_override(
        project.squad_dir,
        '[items.check_broken]\nprefix = "CHK"\nfolder = "check_brokens"\n'
        'lifecycle = "no_such_lifecycle_check"\n',
    )
    result = await invoke(["check"])
    assert "workflow config invalid" in result.output
    assert "sq workflow lint" in result.output
    assert result.exit_code in (1, 3)


async def test_check_does_not_call_a_valid_shadowing_spec_invalid_over_a_missing_stamp(
    project, svc, invoke
) -> None:
    """The stamp obligation is an error-level `sq workflow lint` finding, but absent
    provenance never blocks the spec from loading — `sq check` must report that one accurate
    fact once, never invent a second, false 'workflow config invalid' on top of it."""
    _write_override(project.squad_dir, '[items.guide]\nfolder = "handbooks"\n')

    # The spec itself loads and runs fine.
    lint_result = await invoke(["workflow", "lint"])
    assert lint_result.exit_code == 1  # the stamp finding is error-level
    list_result = await invoke(["list", "-a"])
    assert list_result.exit_code == 0

    check_result = await invoke(["check"])
    assert "override-base" in check_result.output  # the accurate finding is still reported
    assert "workflow config invalid" not in check_result.output  # but not this false one
    assert check_result.output.count("error") == 1


# --------------------------------------------------------------------------- lint is not
# self-blocked by the same AC5 check open_service enforces


async def test_lint_reports_but_does_not_crash_even_after_open_service_would_hard_stop(
    project,
) -> None:
    from squads._workflow._loader import lint_workflow_spec

    _write_override(project.squad_dir, _INCIDENT_V1)
    svc = service.open_service()
    await svc.create("incident", "Live incident", author="manager")

    _write_override(project.squad_dir, _INCIDENT_V2_DROPS_TRIAGE)
    # open_service now hard-stops (proven above); lint must still run and report cleanly.
    findings = lint_workflow_spec(project.squad_dir)
    errors = [f for f in findings if f[0] == "error"]
    assert errors
    assert any("Triage" in f[2] for f in errors)


# --------------------------------------------------------------------------- the crossed case:
# an override present that does NOT touch the badge collection a live item's field disagrees
# with, plus a stale index (the rebuildable cache, not the frontmatter, carrying the bad code).
# This combination — never exercised by the poles above (an override that DOES shrink the
# collection; a load-boundary test with no override at all) — is the whole finding: the badge
# cross-check must not attribute a plain stale-index problem to an override that never touched
# the relevant collection, and must never block `sq repair`, the actual remedy.


def _patch_index_item_by_seq(index_path, seq: int, **fields: object) -> None:
    import json

    data = json.loads(index_path.read_text(encoding="utf-8"))
    key = str(seq)
    data["items"][key] = {**data["items"][key], **fields}
    index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# An override that only ADDS a custom type — never touches [collections] at all.
_ADDS_A_CUSTOM_TYPE_ONLY = """
[lifecycles.triage]
initial = "Open"
[lifecycles.triage.transitions]
Open = ["Done"]
Done = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
"""


async def test_a_stale_index_badge_value_is_unflagged_when_the_override_never_touched_it(
    project, svc
) -> None:
    """The crossed case: an override is present (and genuinely shadows the bundled spec, so
    the stamp/shadow machinery sees it), but it never declares `[collections]` at all — the
    active `priority` collection is byte-identical to bundled. A code the index claims but the
    collection has always accepted-or-rejected the same way, either way, is not something this
    override caused, so this check must not report it.

    Reads the raw index the same way ``lint_workflow_spec``/``validate_against_index_fail_closed``
    do (``_load_index_sync``, bypassing ``IndexStore.load()``'s own load-boundary vocab check —
    that check is a *different* surface with its own, deliberately cause-agnostic message,
    covered separately in tests/integration/test_load_boundary_vocab.py)."""
    from squads._workflow._loader import _load_index_sync

    result = await svc.create("task", "Urgent task", author="manager", priority="urgent")
    _write_override(project.squad_dir, _ADDS_A_CUSTOM_TYPE_ONLY)
    _patch_index_item_by_seq(project.index_path, result.item.sequence_id, priority="bogus")

    merged = load_workflow_spec(squad_dir=project.squad_dir)
    db = _load_index_sync(project.squad_dir)
    errors = validate_against_index(merged, db)

    assert not any("priority" in e for e in errors)


async def test_open_service_and_repair_both_succeed_on_the_crossed_case(
    project, svc, invoke
) -> None:
    """End-to-end through the real CLI surfaces: with an unrelated override present and the
    index alone stale, `sq repair` must still run (and fix it) — the actual bug this finding is
    about — and a normal command must resolve to the corrected value afterward."""
    result = await svc.create("task", "Urgent task", author="manager", priority="urgent")
    _write_override(project.squad_dir, _ADDS_A_CUSTOM_TYPE_ONLY)
    _patch_index_item_by_seq(project.index_path, result.item.sequence_id, priority="bogus")

    repair_result = await invoke(["repair"])
    assert repair_result.exit_code == 0, repair_result.output

    list_result = await invoke(["list", "-a"])
    assert list_result.exit_code == 0, list_result.output
    assert "urgent" in list_result.output.lower()


async def test_lint_gives_a_badge_specific_fix_hint_not_the_status_transition_one(
    project, svc
) -> None:
    """The type/status/prefix/folder family's shared fix hint ends in `sq <type> <n> status
    <new>` — a status transition, which cannot touch a priority. The badge family must carry
    its own hint naming the actual remedy (`update --<field> <code>`), never that one."""
    from squads._workflow._loader import lint_workflow_spec

    await svc.create("task", "Urgent task", author="manager", priority="urgent")
    _write_override(
        project.squad_dir,
        '[collections.priority]\nlabel = "Priority"\n'
        'badges = [{ code = "high", label = "High" }, { code = "low", label = "Low" }]\n',
    )

    findings = lint_workflow_spec(project.squad_dir)
    badge_findings = [f for f in findings if "priority" in f[2] and "collection" in f[2]]
    assert len(badge_findings) == 1
    fix_hint = badge_findings[0][3]
    assert "update --" in fix_hint
    assert "status <new>" not in fix_hint


async def test_repair_still_runs_even_when_the_override_genuinely_shrank_the_collection(
    project, svc, invoke
) -> None:
    """The non-crossed (true-positive) case, for contrast: repair must remain runnable here
    too, even though — unlike the crossed case — the refusal for every OTHER command is
    genuinely override-caused and repair cannot make it go away (the frontmatter itself still
    carries the code the shrunk collection rejects)."""
    await svc.create("task", "Urgent task", author="manager", priority="urgent")
    _write_override(
        project.squad_dir,
        '[collections.priority]\nlabel = "Priority"\n'
        'badges = [{ code = "high", label = "High" }, { code = "low", label = "Low" }]\n',
    )

    list_result = await invoke(["list", "-a"])
    assert list_result.exit_code != 0  # still refuses — this override DID cause it

    repair_result = await invoke(["repair"])
    assert repair_result.exit_code == 0, repair_result.output


# --------------------------------------------------------------------------- repair/adopt vs a
# re-foldered/re-prefixed type's corpus: `repair`/`adopt` rebuild straight from disk, globbing
# only the ACTIVE spec's declared folder/prefix — a re-foldered or re-prefixed type's files sit
# somewhere that glob can no longer see, and a naive rebuild would report them as deleted
# instead of refusing. Both must refuse loudly, never silently drop a live item whose file is
# still on disk.


async def test_repair_refuses_rather_than_discard_a_re_foldered_types_corpus(
    project, svc, invoke
) -> None:
    r1 = await svc.create("task", "Task one", author="manager")
    r2 = await svc.create("task", "Task two", author="manager")
    _write_override(project.squad_dir, '[items.task]\nfolder = "tickets"\n')

    repair_result = await invoke(["repair"])
    assert repair_result.exit_code != 0
    assert "(deleted?)" not in repair_result.output
    assert r1.item.id in repair_result.output
    assert r2.item.id in repair_result.output

    # Nothing was written: the files are untouched and the previous index still has both items.
    assert sorted((project.squad_dir / "tasks").glob("TASK-*.md")).__len__() == 2
    (project.squad_dir / ".overrides" / "workflow.toml").unlink()
    list_result = await invoke(["list", "-a"])
    assert r1.item.id in list_result.output
    assert r2.item.id in list_result.output


async def test_repair_refuses_rather_than_discard_a_re_prefixed_types_corpus(
    project, svc, invoke
) -> None:
    """Identical mechanism to the folder-rename case above, but the folder is unchanged and
    only the prefix moves — the normal scan globs the NEW prefix in the (correct) folder and
    finds nothing."""
    result = await svc.create("task", "Prefix task", author="manager")
    _write_override(project.squad_dir, '[items.task]\nprefix = "TICKET"\n')

    repair_result = await invoke(["repair"])
    assert repair_result.exit_code != 0
    assert "(deleted?)" not in repair_result.output
    assert result.item.id in repair_result.output

    assert sorted((project.squad_dir / "tasks").glob("TASK-*.md")).__len__() == 1
    (project.squad_dir / ".overrides" / "workflow.toml").unlink()
    list_result = await invoke(["list", "-a"])
    assert result.item.id in list_result.output


# --------------------------------------------------------------------------- repair vs a
# dropped-type corpus and the global counter: a type dropped via `[selected]` is the same
# corpus-alignment hazard as a re-foldered/re-prefixed one above, but the failure mode caught
# here is different — the counter itself is a high-water mark that must never regress, and a
# freed sequence number must never be handed to a new item, no matter how the previous index
# read went.

_DROP_GUIDE_SELECTED = (
    '[selected]\nitems = ["epic", "feature", "task", "bug", "decision", "review", '
    '"role", "skill", "operator"]\n'
)


async def test_repair_refuses_rather_than_discard_a_dropped_types_corpus(
    project, svc, invoke
) -> None:
    """The `[selected]`-drop variant of the re-foldered/re-prefixed corpus-alignment refusal:
    the type's folder/prefix did not move, it simply stopped being declared at all, but its
    file is still sitting right there — repair must refuse rather than rebuild an index that
    silently treats it as deleted."""
    result = await svc.create("guide", "How to deploy", author="manager")
    _write_override(project.squad_dir, _DROP_GUIDE_SELECTED)

    repair_result = await invoke(["repair"])
    assert repair_result.exit_code != 0
    assert "(deleted?)" not in repair_result.output
    assert result.item.id in repair_result.output

    assert sorted((project.squad_dir / "guides").glob("GUIDE-*.md")).__len__() == 1
    (project.squad_dir / ".overrides" / "workflow.toml").unlink()
    list_result = await invoke(["list", "-a"])
    assert result.item.id in list_result.output


async def test_repair_never_regresses_the_counter_or_reissues_a_freed_number(
    project, svc, invoke
) -> None:
    """The counterpart to the refusal case above: once the dropped type's corpus is genuinely
    gone (not merely invisible to the active spec), repair must rebuild successfully — and the
    rebuilt counter must stay at the prior high-water mark, never fall back to the count of
    items actually found. A regression here would let the next created item's sequence number
    collide with the still-on-disk file it silently orphaned."""
    result = await svc.create("guide", "How to deploy", author="manager")
    index_before = json.loads((project.squad_dir / ".squads.json").read_text())
    counter_before = index_before["counter"]

    # Genuinely gone this time (contrast the refusal test above): remove the file so no
    # stranded corpus remains for the corpus-alignment guard to catch.
    result.path.unlink()
    _write_override(project.squad_dir, _DROP_GUIDE_SELECTED)

    repair_result = await invoke(["repair"])
    assert repair_result.exit_code == 0, repair_result.output

    index_after = json.loads((project.squad_dir / ".squads.json").read_text())
    assert index_after["counter"] == counter_before  # never regresses below the high-water mark

    create_result = await invoke(["create", "epic", "Reuser", "--author", "manager"])
    assert create_result.exit_code == 0, create_result.output
    index_final = json.loads((project.squad_dir / ".squads.json").read_text())
    new_sequence_ids = {int(k) for k in index_final["items"]}
    assert result.item.sequence_id not in new_sequence_ids  # the freed number was never reissued
    assert max(new_sequence_ids) > counter_before


async def test_adopt_refuses_rather_than_import_fewer_than_the_real_corpus(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """The `sq adopt` variant, which is worse — no previous index to compare against,
    so nothing at all warned before this fix. Two real tasks on disk, a pre-placed override
    that re-folders the type, and no prior sq state whatsoever (a legacy tree, `adopt`'s exact
    use case)."""
    monkeypatch.chdir(tmp_path)
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init.paths)
    r1 = await svc.create("task", "Legacy task one", author="manager")
    r2 = await svc.create("task", "Legacy task two", author="manager")
    (tmp_path / ".squads.toml").unlink()
    (tmp_path / "squads" / ".squads.json").unlink()
    _write_override(tmp_path / "squads", '[items.task]\nfolder = "tickets"\n')

    with pytest.raises(SquadsError) as exc_info:
        await service.adopt(root=tmp_path)
    message = str(exc_info.value)
    assert "(deleted?)" not in message
    assert r1.item.id in message
    assert r2.item.id in message

    assert sorted((tmp_path / "squads" / "tasks").glob("TASK-*.md")).__len__() == 2

    # Recoverable: revert the override, adopt cleanly imports both.
    (tmp_path / "squads" / ".overrides" / "workflow.toml").unlink()
    result = await service.adopt(root=tmp_path)
    assert result.imported == 3  # the manager role + the two legacy tasks


# --------------------------------------------------------------------------- init/adopt vs a bad
# pre-placed override: validating it must happen before any state is written, so a bad override
# means the command never starts rather than wedging a half-created squad a retry can neither
# finish nor cleanly restart from.


async def test_init_never_writes_state_when_a_pre_placed_override_is_malformed(
    tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    override_dir = tmp_path / "squads" / ".overrides"
    override_dir.mkdir(parents=True)
    (override_dir / "workflow.toml").write_text("[items.task\n", encoding="utf-8")  # missing ']'

    with pytest.raises(SquadsError):
        await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)

    assert not (tmp_path / ".squads.toml").exists()
    assert not (tmp_path / "squads" / ".squads.json").exists()

    # Fixing the override and retrying just works — no --force, no AlreadyInitializedError.
    (override_dir / "workflow.toml").write_text("", encoding="utf-8")
    result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    assert (tmp_path / ".squads.toml").exists()
    assert result.paths.index_path.exists()


async def test_init_never_writes_state_when_a_pre_placed_override_violates_the_floor(
    tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    override_dir = tmp_path / "squads" / ".overrides"
    override_dir.mkdir(parents=True)
    (override_dir / "workflow.toml").write_text(
        '[items.task]\nlifecycle = "nope"\n', encoding="utf-8"
    )

    with pytest.raises(SquadsError):
        await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)

    assert not (tmp_path / ".squads.toml").exists()

    # A second attempt without --force must not raise AlreadyInitializedError — nothing landed.
    (override_dir / "workflow.toml").write_text("", encoding="utf-8")
    try:
        await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    except AlreadyInitializedError:
        pytest.fail("init wedged .squads.toml on the first, failed attempt")


# --------------------------------------------------------------------------- badge-collection
# alignment must attribute per VALUE, not per collection: a collection that only ever grew must
# never be blamed for a stale code it never removed.


async def test_a_stale_badge_code_is_unflagged_when_the_override_only_added_codes(
    project, svc
) -> None:
    """The collection strictly grew (every bundled priority code is still present, plus
    one new one) — 'bogus' was never valid under bundled or under the merged spec, so this is a
    plain corpus/frontmatter data problem, not something the override caused."""
    from squads._workflow._loader import _load_index_sync

    result = await svc.create("task", "Urgent task", author="manager", priority="urgent")
    _write_override(
        project.squad_dir,
        '[collections.priority]\nlabel = "Priority"\nbadges = [\n'
        '{ code = "blocker", label = "Blocker" }, { code = "urgent", label = "Urgent" },\n'
        '{ code = "high", label = "High" }, { code = "medium", label = "Medium" },\n'
        '{ code = "low", label = "Low" }, { code = "extra", label = "Extra" },\n]\n',
    )
    _patch_index_item_by_seq(project.index_path, result.item.sequence_id, priority="bogus")

    merged = load_workflow_spec(squad_dir=project.squad_dir)
    db = _load_index_sync(project.squad_dir)
    errors = validate_against_index(merged, db)

    assert not any("bogus" in e for e in errors)
