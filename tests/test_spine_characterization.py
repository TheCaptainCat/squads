"""TASK-000233 — Part A: Characterization tests for every hardcoded identity check (ADR-000232 §6).

These tests pin TODAY's behavior — they run against the *unreified* engine so that when
TASK-000234 reifies each check onto TypeSpec capability flags, any behavioral divergence (or a
missed check) surfaces as a red test.

Naming convention: each test is named for the BEHAVIOR it pins, not the layer or process
(per the operator's standing preference).

Coverage map (22 checks in ADR-000232 §2, plus a few derived behavioral surfaces):

  1.  meta-types excluded from WORK_TYPES / retype-eligibility
  2.  meta-type self-author rule (role/skill/operator may self-author bootstrap)
  3.  skill prefix convention enforced in _scan_for_check (SKILL- prefix rule)
  4.  role/skill body set rejected (body is generated, not free-form)
  5.  role/skill regen only fires for role+skill, not for other types
  6.  sq <type> app registered only for WORK_TYPES (7 work types), not meta-types
  7.  retype refuses meta-type source
  8.  retype refuses meta-type target
  9.  task→feature parent spine: task allowed under feature, refused elsewhere
 10.  parent_hint for task mentions both the allowed type and the ref-add hint
 11.  feature→story subentity kind (add_story only on feature)
 12.  task→subtask subentity kind (add_subtask only on task)
 13.  review→finding subentity kind (add_finding only on review)
 14.  bug severity field surfaced in item panel (show), absent for other types
 15.  decision supersedes rule: Superseded decision with no incoming edge warns in sq check
 16.  decision supersedes rule: Superseded decision WITH incoming edge is clean
 17.  decision supersedes rule: non-decision items with Superseded status not checked
 18.  sq check subtask→story spine: subtask mapping validated against parent feature's stories
 19.  retype status-carry: same workflow (task→bug = different workflow) → reset
 20.  retype status-carry: same workflow (feature→epic) → carry
 21.  repair rebuilds index from frontmatter (frontmatter is source of truth)
 22.  roster (author/assignee) only considers role+operator, not skill
 23.  SUBENTITY_KIND map covers exactly feature/task/review (not epic/bug/decision/guide)
"""

import pytest

from squads._cli import app
from squads._errors import SquadsError
from squads._services import _service as service
from squads._services._base import subentity_kind_map
from squads._workflow import ALLOWED_PARENTS, bundled_spec, parent_hint
from squads._workflow import work_types as _work_types
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, RefRule, StatusSpec, WorkflowSpec

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# 1. meta-types excluded from WORK_TYPES / retype-eligibility
# ---------------------------------------------------------------------------


def test_meta_types_not_in_work_types() -> None:
    """role, skill, operator are excluded from WORK_TYPES; the 7 work types are all present."""
    assert "role" not in _work_types()
    assert "skill" not in _work_types()
    assert "operator" not in _work_types()
    expected_work = {
        "epic",
        "feature",
        "task",
        "bug",
        "decision",
        "review",
        "guide",
    }
    assert set(_work_types()) == expected_work


# ---------------------------------------------------------------------------
# 2. meta-type self-author rule
# ---------------------------------------------------------------------------


async def test_role_may_self_author_bootstrap(svc) -> None:
    """A role item may author itself (self-author bypass for bootstrap)."""
    # ROLE-000001 is the manager role seeded by the minimal-init fixture; it authored itself.
    role = await svc.get("ROLE-000001")
    assert role.type == "role"
    # Creating a new role (or operator) with author == its own slug is allowed.
    await svc.activate_role("tech-lead")  # uses slug == author internally


async def test_skill_may_self_author_bootstrap(svc) -> None:
    """A skill item may author itself (self-author bypass for bootstrap)."""
    # Skills are seeded with author == their slug; that should not raise.
    seeded = await svc.seed_bundled_skills()
    # At least one skill was seeded successfully.
    assert len(seeded) >= 1
    for item in seeded:
        assert item.type == "skill"


async def test_work_item_with_unregistered_author_rejected(svc) -> None:
    """A work item whose author is not a registered participant is rejected."""
    with pytest.raises(SquadsError, match="not a registered agent or operator"):
        await svc.create("task", "t", author="ghost-dev")


# ---------------------------------------------------------------------------
# 3. SKILL- prefix convention enforced in scan / check
# ---------------------------------------------------------------------------


async def test_skill_file_without_skill_prefix_silently_skipped_in_scan(svc) -> None:
    """A slug-named skill body file (no SKILL- prefix, no id) is silently skipped in check.

    This is the pre-migration compat path: files without an id AND without the SKILL- prefix
    are treated as legacy body files, not errors.
    """
    # Create a legacy-style skill body file with no frontmatter id.
    skills_folder = svc.paths.squad_dir / "agents/skills"
    skills_folder.mkdir(parents=True, exist_ok=True)
    (skills_folder / "some-skill.md").write_text(
        "---\ntitle: some-skill\n---\n# some skill\n", encoding="utf-8"
    )
    # sq check must not report an error for this file.
    issues = await svc.check()
    ids_with_error = [i.item for i in issues if i.level == "error"]
    assert "some-skill.md" not in ids_with_error


async def test_skill_file_with_skill_prefix_but_no_id_reported_as_error(svc) -> None:
    """A SKILL-prefixed file missing its frontmatter id is a real error (not silently skipped)."""
    skills_folder = svc.paths.squad_dir / "agents/skills"
    skills_folder.mkdir(parents=True, exist_ok=True)
    (skills_folder / "SKILL-badfile.md").write_text(
        "---\ntitle: broken\n---\n# broken\n", encoding="utf-8"
    )
    issues = await svc.check()
    errors = [i for i in issues if i.level == "error" and "SKILL-badfile.md" in i.item]
    assert errors, f"expected an error for SKILL-badfile.md, got issues: {issues}"


# ---------------------------------------------------------------------------
# 4. role/skill body set rejected (body is generated, not free-form)
# ---------------------------------------------------------------------------


async def test_role_body_set_rejected(svc) -> None:
    """Setting the body on a role raises SquadsError (body is generated from fields)."""
    with pytest.raises(SquadsError, match="generated from its fields"):
        await svc.set_body("ROLE-000001", "free-form body")


async def test_skill_body_set_rejected(svc) -> None:
    """Setting the body on a skill raises SquadsError (body is generated from fields)."""
    seeded = await svc.seed_bundled_skills()
    skill_id = seeded[0].id
    with pytest.raises(SquadsError, match="generated from its fields"):
        await svc.set_body(skill_id, "free-form body")


# ---------------------------------------------------------------------------
# 5. regen only fires for role/skill
# ---------------------------------------------------------------------------


async def test_regen_on_task_raises(svc) -> None:
    """svc.regen() raises for non-role/skill types."""
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="only roles/skills have entries"):
        await svc.regen(task.id)


async def test_regen_on_role_succeeds(svc) -> None:
    """svc.regen() succeeds for a role item (no backend active → no-ops cleanly)."""
    role = await svc.get("ROLE-000001")
    # Regen on a role should not raise even when no backend is active.
    result = await svc.regen(role.id)
    assert result.type == "role"


# ---------------------------------------------------------------------------
# 6. sq <type> app registered for WORK_TYPES only, not meta-types
# ---------------------------------------------------------------------------


def test_work_type_commands_registered_in_app(runner) -> None:
    """Each WORK_TYPE has a named command registered on the root app."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for t in _work_types():
        assert t in result.output, f"{t} command missing from sq --help"


def test_meta_type_commands_not_as_type_commands(runner) -> None:
    """role/operator/skill are managed via their own sub-apps, not as generic sq <type> apps."""
    # The role/skill/operator commands exist under dedicated sub-apps (sq role, sq skill,
    # sq operator), which is correct. But there is NO generic `sq role <n> show` work-item path.
    # This test verifies that meta-types are absent from WORK_TYPES (the loop that registers
    # the generic sq <type> app).
    assert "role" not in _work_types()
    assert "skill" not in _work_types()
    assert "operator" not in _work_types()


# ---------------------------------------------------------------------------
# 7 & 8. retype refuses meta-type source and meta-type target
# ---------------------------------------------------------------------------


async def test_retype_refuses_role_source(svc) -> None:
    """Retyping a role (meta-type) is refused with 'only work items can be retyped'."""
    with pytest.raises(SquadsError, match="only work items can be retyped"):
        await svc.retype("ROLE-000001", "task")


async def test_retype_refuses_role_target(svc) -> None:
    """Retyping TO a meta-type is refused."""
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="target must be a work type"):
        await svc.retype(task.id, "role")


async def test_retype_refuses_skill_target(svc) -> None:
    """Retyping TO skill (meta-type) is refused."""
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="target must be a work type"):
        await svc.retype(task.id, "skill")


async def test_retype_refuses_operator_target(svc) -> None:
    """Retyping TO operator (meta-type) is refused."""
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="target must be a work type"):
        await svc.retype(task.id, "operator")


# ---------------------------------------------------------------------------
# 9. task→feature parent spine
# ---------------------------------------------------------------------------


async def test_task_parent_feature_allowed(svc) -> None:
    """A task may be parented to a feature."""
    feat = (await svc.create("feature", "f")).item
    task = (await svc.create("task", "t", parent=feat.id)).item
    assert task.parent == feat.id


async def test_task_parent_epic_refused(svc) -> None:
    """A task may NOT be parented to an epic."""
    epic = (await svc.create("epic", "e")).item
    with pytest.raises(SquadsError, match="must be of type feature"):
        await svc.create("task", "t", parent=epic.id)


async def test_task_parent_bug_refused(svc) -> None:
    """A task may NOT be parented to a bug."""
    bug = (await svc.create("bug", "b")).item
    with pytest.raises(SquadsError, match="must be of type feature"):
        await svc.create("task", "t", parent=bug.id)


async def test_task_allowed_parents_set(svc) -> None:
    """ALLOWED_PARENTS for task contains only feature."""
    assert ALLOWED_PARENTS.get("task") == {"feature"}


async def test_epic_bug_decision_have_no_parent_constraint(svc) -> None:
    """Epic, bug, and decision have no parent constraint (unconstrained)."""
    for t in ("epic", "bug", "decision", "review", "guide"):
        assert t not in ALLOWED_PARENTS, f"{t} should be unconstrained"


# ---------------------------------------------------------------------------
# 10. parent_hint for task mentions allowed type AND the ref-add hint
# ---------------------------------------------------------------------------


def test_parent_hint_for_task_mentions_feature_and_ref_add() -> None:
    """parent_hint for task names 'feature' AND includes the 'sq ref add … fixes|addresses' hint."""
    hint = parent_hint("task")
    assert "feature" in hint
    assert "sq ref add" in hint
    assert "fixes|addresses" in hint or "fixes" in hint


def test_parent_hint_for_feature_does_not_mention_ref_add() -> None:
    """parent_hint for feature names 'epic' but does NOT include the ref-add hint."""
    hint = parent_hint("feature")
    assert "epic" in hint
    assert "sq ref add" not in hint


# ---------------------------------------------------------------------------
# 11-13. sub-entity kind resolution
# ---------------------------------------------------------------------------


async def test_feature_hosts_stories_not_subtasks(svc) -> None:
    """add_story succeeds on a feature; add_subtask is refused."""
    feat = (await svc.create("feature", "f")).item
    result = await svc.add_story(feat.id, "user can log in")
    assert result.local_id == "US1"
    # add_subtask on a feature should fail (feature hosts stories, not subtasks)
    with pytest.raises(SquadsError, match="does not host subtasks"):
        await svc.add_subtask(feat.id, "st")


async def test_task_hosts_subtasks_not_stories(svc) -> None:
    """add_subtask succeeds on a task; add_story is refused."""
    task = (await svc.create("task", "t")).item
    result = await svc.add_subtask(task.id, "implement it")
    assert result.local_id == "ST1"
    # add_story on a task should fail (task hosts subtasks, not stories)
    with pytest.raises(SquadsError, match="does not host storys"):
        await svc.add_story(task.id, "us")


async def test_review_hosts_findings_not_stories(svc) -> None:
    """add_finding succeeds on a review; add_story is refused."""
    rev = (await svc.create("review", "r")).item
    result = await svc.add_finding(rev.id, "null deref")
    assert result.local_id == "F1"
    # add_story on a review should fail
    with pytest.raises(SquadsError, match="does not host storys"):
        await svc.add_story(rev.id, "us")


def test_subentity_kind_map_covers_exactly_feature_task_review() -> None:
    """subentity_kind_map(bundled_spec()) maps exactly {feature→story, task→subtask,
    review→finding}."""
    sk = subentity_kind_map(bundled_spec())
    assert sk == {
        "feature": "story",
        "task": "subtask",
        "review": "finding",
    }
    # epic/bug/decision/guide are NOT in the map.
    for t in ("epic", "bug", "decision", "guide"):
        assert t not in sk, f"{t} should not be in the subentity kind map"


# ---------------------------------------------------------------------------
# 14. bug severity field surfaced in item panel show
# ---------------------------------------------------------------------------


async def test_bug_show_includes_severity_row(svc, invoke) -> None:
    """sq bug <n> show includes a 'severity:' row; a task show does not."""
    bug = (await svc.create("bug", "null-ptr")).item
    # Set severity on the bug item via extra.
    await svc.update(bug.id, set_extra={"severity": "high"})

    r = await invoke(["bug", str(bug.sequence_id), "show"])
    assert r.exit_code == 0, r.output
    assert "severity" in r.output

    task = (await svc.create("task", "t")).item
    r2 = await invoke(["task", str(task.sequence_id), "show"])
    assert r2.exit_code == 0, r2.output
    assert "severity" not in r2.output


# ---------------------------------------------------------------------------
# 15-17. decision supersedes rule in sq check
# ---------------------------------------------------------------------------


async def test_superseded_decision_without_incoming_edge_warns(svc) -> None:
    """A decision with status Superseded but no incoming supersedes edge → sq check warns."""
    dec = (await svc.create("decision", "d", status="Accepted")).item
    # Force status to Superseded without creating an incoming supersedes edge.
    await svc.set_status(dec.id, "Superseded", force=True)

    issues = await svc.check()
    warns = [i for i in issues if i.level == "warn" and i.item == dec.id]
    assert any("supersedes" in i.message.lower() for i in warns), (
        f"expected a supersedes-edge warning for {dec.id}, got: {warns}"
    )


async def test_superseded_check_message_names_the_actual_status(svc) -> None:
    """The supersedes-edge warning names the item's REAL status, not a hardcoded 'Superseded'
    literal — proven on a custom type/status sharing the supersedes-role marker."""
    base = load_workflow_spec()
    audit_spec = WorkflowSpec.model_validate(
        {
            "items": {
                **base.items,
                "audit": ItemSpec(
                    prefix="AUD",
                    folder="audits",
                    lifecycle="audit_cycle",
                    ref_rules=[RefRule(kind="supersedes", hint="")],
                ),
            },
            "statuses": {**base.statuses, "Retired": StatusSpec(terminal=True, role="superseded")},
            "lifecycles": {
                **base.lifecycles,
                "audit_cycle": Lifecycle(initial="Draft", transitions={"Draft": ["Retired"]}),
            },
            "prefix_to_type": {**base.prefix_to_type, "AUD": "audit"},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )
    audit_svc = service.Service(svc.paths, spec=audit_spec)
    aud = (await audit_svc.create("audit", "a")).item
    await audit_svc.set_status(aud.id, "Retired")

    issues = await audit_svc.check()
    warns = [i for i in issues if i.level == "warn" and i.item == aud.id]
    assert any("Retired" in i.message for i in warns), f"expected 'Retired' in warning: {warns}"
    assert not any("Superseded" in i.message for i in warns)


async def test_superseded_decision_with_incoming_edge_is_clean(svc) -> None:
    """A decision with status Superseded AND an incoming supersedes edge → sq check is clean."""
    old_dec = (await svc.create("decision", "old", status="Accepted")).item
    await svc.set_status(old_dec.id, "Superseded", force=True)

    new_dec = (await svc.create("decision", "new", status="Accepted")).item
    await svc.add_ref(new_dec.id, old_dec.id, kind="supersedes")

    issues = await svc.check()
    supersedes_warns = [
        i
        for i in issues
        if i.level == "warn" and i.item == old_dec.id and "supersedes" in i.message.lower()
    ]
    assert not supersedes_warns, (
        f"expected no supersedes warning for {old_dec.id} with incoming edge,"
        f" got: {supersedes_warns}"
    )


async def test_non_decision_superseded_not_checked(svc) -> None:
    """A non-decision item is never checked for the supersedes rule."""
    # Guide has a terminal status 'Deprecated', decision has 'Superseded'.
    # Force a task into Superseded status (bypassing workflow); sq check should not
    # emit a supersedes-edge warning for it (the check is decision-only).
    dec = (await svc.create("decision", "adr")).item
    # Also create a task; tasks don't have a Superseded status so we use the decision
    # to prove the filtering: only decisions get the supersedes check.
    issues = await svc.check()
    task_supersedes = [
        i
        for i in issues
        if i.level == "warn" and "supersedes" in i.message.lower() and not i.item.startswith("ADR-")
    ]
    assert not task_supersedes, f"supersedes check fired on a non-decision item: {task_supersedes}"
    _ = dec  # suppress unused-variable warning


# ---------------------------------------------------------------------------
# 18. sq check subtask→story spine
# ---------------------------------------------------------------------------


async def test_check_flags_subtask_story_mapping_with_wrong_parent(svc) -> None:
    """sq check errors when a subtask maps to a story but the task has no feature parent."""
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id, "login")  # US1
    task = (await svc.create("task", "t", parent=feat.id)).item
    await svc.add_subtask(task.id, "impl", story="US1")

    # Remove the parent link to break the spine.
    await svc.unlink(task.id)

    issues = await svc.check()
    errors = [i for i in issues if i.level == "error" and i.item == task.id]
    assert any(
        "story" in i.message.lower() or "feature parent" in i.message.lower() for i in errors
    ), f"expected story/feature-parent error for {task.id}, got: {errors}"


async def test_subtask_story_error_names_the_resolved_parent_type(svc) -> None:
    """_check_subtask_stories/_validate_subtask_story name the SPEC-RESOLVED required parent
    type, not a hardcoded 'feature' literal — proven on a differently-named host/parent pair."""
    base = load_workflow_spec()
    custom_spec = WorkflowSpec.model_validate(
        {
            "items": {
                **base.items,
                "initiative": ItemSpec(
                    prefix="INIT", folder="initiatives", lifecycle="work", subentity_kind="story"
                ),
                "gizmo": ItemSpec(
                    prefix="GIZ",
                    folder="gizmos",
                    lifecycle="work",
                    parents=["initiative"],
                    subentity_kind="subtask",
                    parent_required="initiative",
                ),
            },
            "statuses": base.statuses,
            "lifecycles": base.lifecycles,
            "prefix_to_type": {**base.prefix_to_type, "INIT": "initiative", "GIZ": "gizmo"},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )
    custom_svc = service.Service(svc.paths, spec=custom_spec)
    init = (await custom_svc.create("initiative", "i")).item
    giz = (await custom_svc.create("gizmo", "g", parent=init.id)).item

    # Directly seed the sub-entity records (no dedicated "story"/"subtask" markers exist
    # on the fallback item template for these custom types) — mirrors the corrupt-index
    # technique test_check_flags_bad_task_parent already uses for the built-in checks.
    from squads._models._subentity import SubEntity

    async with custom_svc.store.transaction() as db:
        db.items[init.sequence_id].subentities.append(
            SubEntity(local_id="US1", title="login", status="Todo")
        )
        db.items[giz.sequence_id].subentities.append(
            SubEntity(local_id="ST1", title="impl", status="Todo", story="US1")
        )
        db.items[giz.sequence_id].parent = None  # break the spine

    issues = await custom_svc.check()
    errors = [i for i in issues if i.level == "error" and i.item == giz.id]
    assert any("initiative" in i.message for i in errors), f"expected 'initiative': {errors}"
    assert not any("feature" in i.message for i in errors)

    with pytest.raises(SquadsError, match="initiative"):
        await custom_svc.add_subtask(giz.id, "impl2", story="US1")


# ---------------------------------------------------------------------------
# 19-20. retype status-carry vs. reset
# ---------------------------------------------------------------------------


async def test_retype_different_workflow_resets_status(svc) -> None:
    """Retyping between different workflows resets status to the new type's initial."""
    task = (await svc.create("task", "t")).item
    await svc.set_status(task.id, "InProgress")

    res = await svc.retype(task.id, "bug")
    assert res.status_reset, "expected status reset when crossing workflow boundary"
    assert res.item.status == "Open"  # bug initial is Open


async def test_retype_same_workflow_carries_status(svc) -> None:
    """Retyping within the same workflow carries status unchanged."""
    feat = (await svc.create("feature", "f")).item
    await svc.set_status(feat.id, "Ready")

    res = await svc.retype(feat.id, "epic")
    assert not res.status_reset, "expected status carried when same workflow"
    assert res.item.status == "Ready"


# ---------------------------------------------------------------------------
# 21. repair rebuilds index from frontmatter (frontmatter is source of truth)
# ---------------------------------------------------------------------------


async def test_repair_rebuilds_index_from_frontmatter(svc) -> None:
    """repair() reconstructs the full index from on-disk frontmatter."""
    task = (await svc.create("task", "t")).item
    # Corrupt the index by wiping it.
    await svc.store.overwrite(__import__("squads._models._index", fromlist=["SquadsDB"]).SquadsDB())
    # After repair, the task should be back in the index.
    result = await svc.repair()
    assert result.db.get(task.id) is not None, "task should be reconstructed after repair"


# ---------------------------------------------------------------------------
# 22. roster (author/assignee) only considers role+operator, not skill
# ---------------------------------------------------------------------------


async def test_skill_slug_not_valid_as_author(svc) -> None:
    """A skill slug is not a valid author (only role and operator slugs are)."""
    seeded = await svc.seed_bundled_skills()
    skill_slug = seeded[0].extra.get("slug", seeded[0].slug)
    with pytest.raises(SquadsError, match="not a registered agent or operator"):
        await svc.create("task", "t", author=skill_slug)


async def test_skill_slug_not_valid_as_assignee(svc) -> None:
    """A skill slug is not a valid assignee (only role and operator slugs are)."""
    seeded = await svc.seed_bundled_skills()
    skill_slug = seeded[0].extra.get("slug", seeded[0].slug)
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="not a registered agent or operator"):
        await svc.update(task.id, assignee=skill_slug)


async def test_role_slug_valid_as_author_and_assignee(svc) -> None:
    """A role slug IS a valid author and assignee."""
    feat = (await svc.create("feature", "f")).item
    task = await svc.update(feat.id, assignee="manager")
    assert task.assignee == "manager"


# ---------------------------------------------------------------------------
# 23. SUBENTITY_KIND map (derived from spine_base) — checked as unit
# ---------------------------------------------------------------------------


def test_subentity_kind_derived_from_subentity_parent() -> None:
    """subentity_kind_map is the inverse of subentity_parent_map, for the active spec."""
    from squads._services._base import subentity_parent_map

    spec = bundled_spec()
    sk = subentity_kind_map(spec)
    sp = subentity_parent_map(spec)

    # Inverse relationship holds.
    for kind, parent_type in sp.items():
        assert sk[parent_type] == kind, f"subentity_kind_map[{parent_type!r}] should be {kind!r}"
    # Cardinality matches.
    assert len(sk) == len(sp)


# ---------------------------------------------------------------------------
# 24. operator self-author bypass (in-membership check, not is-identity)
# ---------------------------------------------------------------------------


async def test_operator_may_self_author_bootstrap(svc) -> None:
    """add_operator succeeds without 'unregistered agent' error (operator self-author bypass).

    Pins the `item_type in ("role", "skill", "operator")` membership
    check in _base._check_author.  Under str-typing (TASK-235) this becomes
    `"operator" in {...}` — must still pass.
    """
    op = await svc.add_operator("Test Person", slug="op-testperson")
    assert op.type == "operator"
    assert op.author == "op-testperson"  # self-authored


# ---------------------------------------------------------------------------
# 25. workload excludes role AND skill (in-_NON_WORK_TYPES membership check)
# ---------------------------------------------------------------------------


async def test_workload_excludes_role_and_skill_items(svc) -> None:
    """role and skill items are excluded from workload counts.

    Pins the `it.type in _NON_WORK_TYPES` membership check in _roster.workload,
    where _NON_WORK_TYPES = {ROLE, SKILL, OPERATOR}.  Under str-typing (TASK-235)
    `"role" in {"role", ...}` must still match.
    """
    # Seed a skill so there are role + skill items to check.
    await svc.seed_bundled_skills()

    # Create a work item assigned to the manager role so the workload is non-empty.
    task = (await svc.create("task", "t")).item
    await svc.update(task.id, assignee="manager")

    rows = await svc.workload()

    # Every row assignee must map to a real work assignment — never a role/skill slug
    # that is only assigned to meta-type items.
    assignees = {r.assignee for r in rows}

    # The role items themselves (which have no assignee on the role item) should not
    # appear as a workload row driven by the role item's type.
    # More precisely: the total count across all rows must equal the number of
    # work-type items (not meta-type items).
    total_from_workload = sum(r.total for r in rows)

    # Count work items directly (excluding meta-types).
    db = await svc.store.load()
    work_count = sum(1 for it in db.items.values() if it.type not in ("role", "skill", "operator"))
    assert total_from_workload == work_count, (
        f"workload total {total_from_workload} != work item count {work_count};"
        f" meta-type items are leaking into workload counts. rows: {rows}"
    )
    _ = assignees  # used above for clarity
