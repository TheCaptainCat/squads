"""Tests for TASK-000164: Advisory create-lane warning (FEAT-000122 Slice B / ADR-000163).

Three seam-level checks:
1. Table-pinning: each role's derived allowed_create_types equals Nina's §1 table exactly.
2. Service: CreateResult.lane_warning is set for out-of-lane creates, None for in-lane;
   manager and op-* are exempt; the reflog delta carries the advisory lane tag.
3. CLI smoke: out-of-lane create prints the warning and exits 0; --json includes it;
   sq role <slug> show surfaces the creates: row (+ create_lane in --json).
"""

import json

import pytest

from squads import _actor as actor
from squads._index._reflog import read_lines, reflog_path
from squads._interactions import (
    CREATE_LANES,
    DEV,
    LANED_TYPES,
    PLAYBOOK,
    allowed_create_types,
    in_lane_owner,
    is_lane_exempt,
)
from squads._models._enums import ItemType

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# 1. Table-pinning test (mandatory — ADR-000163 §2 / AC-B5)
# ---------------------------------------------------------------------------


class TestLaneTable:
    """Each role's derived lane must match Nina's §1 table exactly (FEAT-000122 body §1).

    This is the mandatory table-pinning test (ADR-000163 §2 / AC-B5).  CREATE_LANES is the
    single source co-located in _interactions.py; it is asserted here against Nina's §1 table
    so any future edit that silently shifts a lane fails CI.
    """

    def test_create_lanes_map_matches_nina_table(self):
        """CREATE_LANES itself must equal Nina's §1 table (the declarative source test)."""
        expected: dict[str, set[ItemType]] = {
            "product-owner": {ItemType.FEATURE, ItemType.EPIC},
            "tech-lead": {ItemType.TASK},
            "architect": {ItemType.DECISION, ItemType.GUIDE},
            "reviewer": {ItemType.REVIEW},
            "qa": {ItemType.BUG},
            "tech-writer": {ItemType.GUIDE},
            DEV: set(),
        }
        assert expected == CREATE_LANES, (
            "CREATE_LANES diverged from Nina's §1 table — update CREATE_LANES or this test "
            "to reflect the authoritative lane rules."
        )

    def test_create_lanes_roles_are_all_in_playbook(self):
        """Every non-DEV role in CREATE_LANES must appear as a RoleGuide slug in PLAYBOOK.

        This asserts CREATE_LANES is anchored to PLAYBOOK — a role that is no longer in the
        playbook should not remain in CREATE_LANES.
        """
        all_playbook_slugs: set[str] = set()
        for pb in PLAYBOOK.values():
            for guide in pb.roles:
                if guide.slug != DEV:
                    all_playbook_slugs.add(guide.slug)
        for slug in CREATE_LANES:
            if slug == DEV:
                continue
            assert slug in all_playbook_slugs, (
                f"CREATE_LANES entry {slug!r} is not a RoleGuide slug in PLAYBOOK — "
                "remove it or add the role to the playbook first."
            )

    def test_product_owner_lane(self):
        assert allowed_create_types("product-owner") == {ItemType.FEATURE, ItemType.EPIC}

    def test_tech_lead_lane(self):
        # task only — co-authors guide but GUIDE is not in CREATE_LANES for tech-lead
        assert allowed_create_types("tech-lead") == {ItemType.TASK}

    def test_architect_lane(self):
        assert allowed_create_types("architect") == {ItemType.DECISION, ItemType.GUIDE}

    def test_reviewer_lane(self):
        assert allowed_create_types("reviewer") == {ItemType.REVIEW}

    def test_qa_lane(self):
        assert allowed_create_types("qa") == {ItemType.BUG}

    def test_tech_writer_lane(self):
        assert allowed_create_types("tech-writer") == {ItemType.GUIDE}

    def test_dev_lane_is_empty(self):
        """Any *-dev slug derives an empty lane (DEV sentinel has no sq create author verb)."""
        assert allowed_create_types("python-dev") == set()
        assert allowed_create_types("dotnet-dev") == set()
        assert allowed_create_types("go-dev") == set()

    def test_devops_lane_is_empty(self):
        """devops has no entry in CREATE_LANES → empty lane."""
        assert allowed_create_types("devops") == set()

    def test_manager_lane_is_empty(self):
        """manager has no entry in CREATE_LANES — its exemption is via is_lane_exempt."""
        assert allowed_create_types("manager") == set()


class TestLaneExemptions:
    def test_manager_is_exempt(self):
        assert is_lane_exempt("manager") is True

    def test_op_slug_is_exempt(self):
        assert is_lane_exempt("op-pierre") is True
        assert is_lane_exempt("op-alice") is True

    def test_regular_role_not_exempt(self):
        assert is_lane_exempt("python-dev") is False
        assert is_lane_exempt("tech-lead") is False
        assert is_lane_exempt("qa") is False
        assert is_lane_exempt("reviewer") is False

    def test_op_prefix_required_exactly(self):
        # A slug that merely contains 'op-' inside is not exempt
        assert is_lane_exempt("devops") is False


class TestLanedTypes:
    """LANED_TYPES is the union of all item types in CREATE_LANES (REV-000165 F2)."""

    def test_laned_types_contains_all_create_lanes_values(self):
        """LANED_TYPES must be the union of every lane set in CREATE_LANES."""
        expected = frozenset(t for lane in CREATE_LANES.values() for t in lane)
        assert expected == LANED_TYPES

    def test_laned_types_does_not_contain_internal_artifact_types(self):
        """role, skill, and operator are internal artifact types — not laned."""
        assert ItemType.ROLE not in LANED_TYPES
        assert ItemType.SKILL not in LANED_TYPES
        assert ItemType.OPERATOR not in LANED_TYPES

    def test_laned_types_contains_all_playbook_types(self):
        """Every item type in PLAYBOOK is a laned type (they all appear in some lane)."""
        for item_type in PLAYBOOK:
            assert item_type in LANED_TYPES, (
                f"PLAYBOOK type {item_type.value!r} not in LANED_TYPES — "
                "update CREATE_LANES if a new laned type is added."
            )


class TestInLaneOwner:
    def test_feature_owner_is_product_owner(self):
        assert in_lane_owner(ItemType.FEATURE) == {"product-owner"}

    def test_task_owner_is_tech_lead(self):
        assert in_lane_owner(ItemType.TASK) == {"tech-lead"}

    def test_bug_owner_is_qa(self):
        assert in_lane_owner(ItemType.BUG) == {"qa"}

    def test_review_owner_is_reviewer(self):
        assert in_lane_owner(ItemType.REVIEW) == {"reviewer"}

    def test_decision_owner_is_architect(self):
        assert in_lane_owner(ItemType.DECISION) == {"architect"}

    def test_guide_owner_includes_architect_and_tech_writer(self):
        owners = in_lane_owner(ItemType.GUIDE)
        assert "architect" in owners
        assert "tech-writer" in owners

    def test_epic_owner_is_product_owner(self):
        assert in_lane_owner(ItemType.EPIC) == {"product-owner"}


# ---------------------------------------------------------------------------
# 2. Service-level tests (AC-B1, AC-B2, AC-B3, AC-B5, AC-B6)
# ---------------------------------------------------------------------------


class TestServiceLaneWarning:
    async def test_out_of_lane_create_returns_warning(self, svc, frozen_time):
        """python-dev creating a feature → lane_warning names python-dev + product-owner."""
        await svc.add_dev("python")
        actor.set_actor("python-dev")
        res = await svc.create(ItemType.FEATURE, "Oops", author="python-dev")
        assert res.lane_warning is not None
        assert "python-dev" in res.lane_warning
        assert "product-owner" in res.lane_warning
        assert "feature" in res.lane_warning
        assert "advisory" in res.lane_warning
        # Item still created (AC-B1)
        assert res.item.id is not None

    async def test_in_lane_create_returns_no_warning(self, svc, frozen_time):
        """tech-lead creating a task → no warning (task is in tech-lead's derived lane)."""
        await svc.activate_role("tech-lead")
        actor.set_actor("tech-lead")
        res = await svc.create(ItemType.TASK, "Fix stuff", author="tech-lead")
        assert res.lane_warning is None

    async def test_manager_is_exempt_no_warning(self, svc, frozen_time):
        """manager creating any type → no warning (fully exempt)."""
        actor.set_actor("manager")
        res = await svc.create(ItemType.FEATURE, "Manager feature", author="manager")
        assert res.lane_warning is None

    async def test_op_slug_is_exempt_no_warning(self, svc, frozen_time):
        """op-* slugs are exempt from lane checks."""
        # Register an operator so the author check passes
        await svc.add_operator("Pierre", slug="op-pierre")
        actor.set_actor("op-pierre")
        res = await svc.create(ItemType.FEATURE, "Human feature", author="op-pierre")
        assert res.lane_warning is None

    async def test_dev_creates_bug_returns_warning(self, svc, frozen_time):
        """python-dev creating a bug → advisory warning (dev lane is empty, owner is qa).

        ADR-000163 §2a: dev-authored bugs are ALLOWED and proceed with the standard
        advisory warning — no special code path, no --author qa requirement.
        """
        await svc.add_dev("python")
        actor.set_actor("python-dev")
        res = await svc.create(ItemType.BUG, "Found a defect", author="python-dev")
        assert res.lane_warning is not None
        assert "python-dev" in res.lane_warning
        assert "qa" in res.lane_warning
        assert "advisory" in res.lane_warning
        # Item still created
        assert res.item.id is not None

    async def test_lane_warning_not_in_warning_text_when_in_lane(self, svc, frozen_time):
        """qa creating a bug → no warning."""
        await svc.activate_role("qa")
        actor.set_actor("qa")
        res = await svc.create(ItemType.BUG, "Known defect", author="qa")
        assert res.lane_warning is None

    async def test_out_of_lane_warning_recorded_in_reflog(self, svc, frozen_time):
        """The create reflog delta carries the advisory lane_warning tag (AC-B2)."""
        await svc.add_dev("python")
        actor.set_actor("python-dev")
        res = await svc.create(ItemType.FEATURE, "Bad feature", author="python-dev")
        lines = await read_lines(reflog_path(svc.paths.squad_dir))
        create_lines = [ln for ln in lines if ln.op == "create" and ln.target == res.item.id]
        assert len(create_lines) == 1
        delta = create_lines[0].delta
        assert "lane_warning" in delta
        lw = delta["lane_warning"]
        assert isinstance(lw, dict)
        assert lw["advisory"] is True
        assert lw["actor"] == "python-dev"
        assert "product-owner" in lw["expected"]
        assert lw["type"] == "feature"

    async def test_in_lane_create_reflog_has_no_lane_warning_key(self, svc, frozen_time):
        """In-lane create reflog delta has no lane_warning key."""
        await svc.activate_role("tech-lead")
        actor.set_actor("tech-lead")
        res = await svc.create(ItemType.TASK, "Clean task", author="tech-lead")
        lines = await read_lines(reflog_path(svc.paths.squad_dir))
        create_lines = [ln for ln in lines if ln.op == "create" and ln.target == res.item.id]
        assert len(create_lines) == 1
        assert "lane_warning" not in create_lines[0].delta

    async def test_status_mutation_does_not_trigger_lane_check(self, svc, frozen_time):
        """Status transitions are not laned in Slice B (AC-B6 — Option A)."""
        from squads._models._enums import Status

        actor.set_actor("python-dev")
        res = await svc.create(ItemType.FEATURE, "Feature", author="manager")
        # A python-dev transitioning a feature status should not raise or warn.
        # (The lane check only fires on create; this call should succeed silently.)
        await svc.set_status(res.item.id, Status.IN_PROGRESS)

    async def test_non_laned_type_role_creates_no_lane_warning(self, svc, frozen_time):
        """Creating a role item (internal artifact type) produces no lane warning (REV-000165 F2).

        role/skill/operator are outside the lane domain; ServiceCore.create must skip
        the lane check entirely for them — no warning, no lane_warning key in the reflog,
        regardless of what author slug is used.
        """
        # activate_role calls svc.create(ItemType.ROLE, …, author=role.slug) — self-authored.
        # This is a real internal flow: sq dev add / role activation go through ServiceCore.create.
        role_item = await svc.activate_role("architect")
        lines = await read_lines(reflog_path(svc.paths.squad_dir))
        create_lines = [ln for ln in lines if ln.op == "create" and ln.target == role_item.id]
        assert len(create_lines) == 1
        assert "lane_warning" not in create_lines[0].delta, (
            "Non-laned type ROLE create reflog delta must not carry a lane_warning key"
        )

    async def test_non_laned_type_operator_creates_no_lane_warning(self, svc, frozen_time):
        """Operator create (internal artifact type) produces no lane warning (REV-000165 F2)."""
        # add_operator internally calls svc.create(ItemType.OPERATOR, …) and returns the Item.
        op_item = await svc.add_operator("Test User", slug="op-test")
        # Check the reflog: the operator create delta must not carry a lane_warning key
        lines = await read_lines(reflog_path(svc.paths.squad_dir))
        op_create_lines = [ln for ln in lines if ln.op == "create" and ln.target == op_item.id]
        assert len(op_create_lines) == 1
        assert "lane_warning" not in op_create_lines[0].delta, (
            "Non-laned type OPERATOR create reflog delta must not carry a lane_warning key"
        )


# ---------------------------------------------------------------------------
# 3. CLI smoke tests (AC-B1, AC-B4, AC-B7)
# ---------------------------------------------------------------------------


class TestCLILaneWarning:
    async def test_out_of_lane_create_prints_warning_exit_0(self, project, svc, invoke):
        """sq create feature --author python-dev prints the advisory warning, exit 0 (AC-B1)."""
        await svc.add_dev("python")
        result = await invoke(["create", "feature", "Bad Feature", "--author", "python-dev"])
        assert result.exit_code == 0, result.output
        assert "advisory" in result.output
        assert "python-dev" in result.output
        assert "product-owner" in result.output

    async def test_out_of_lane_create_still_creates_item(self, project, svc, invoke):
        """The item is created despite the lane warning (AC-B1)."""
        await svc.add_dev("python")
        result = await invoke(["create", "feature", "My Feature", "--author", "python-dev"])
        assert result.exit_code == 0, result.output
        # 'created' line appears before the warning
        assert "created" in result.output

    async def test_in_lane_create_no_warning(self, project, svc, invoke):
        """tech-lead creating a task produces no advisory warning."""
        await svc.activate_role("tech-lead")
        result = await invoke(["create", "task", "A task", "--author", "tech-lead"])
        assert result.exit_code == 0, result.output
        assert "advisory" not in result.output

    async def test_json_out_includes_lane_warning_field(self, project, svc, invoke):
        """--json output carries the lane_warning field for an out-of-lane create (AC-B1)."""
        await svc.add_dev("python")
        result = await invoke(
            ["create", "feature", "JSON Feature", "--author", "python-dev", "--json"]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "lane_warning" in data
        assert data["lane_warning"] is not None
        assert "advisory" in data["lane_warning"]

    async def test_json_out_in_lane_no_lane_warning_field(self, project, svc, invoke):
        """--json output for an in-lane create has no lane_warning key (or None)."""
        await svc.activate_role("tech-lead")
        result = await invoke(["create", "task", "In-lane task", "--author", "tech-lead", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        # lane_warning must be absent or None for in-lane creates
        assert data.get("lane_warning") is None

    async def test_manager_exempt_no_warning_on_cli(self, project, invoke):
        """manager is exempt — no advisory warning, exit 0 (AC-B3)."""
        result = await invoke(["create", "feature", "Manager Feature", "--author", "manager"])
        assert result.exit_code == 0, result.output
        assert "advisory" not in result.output

    async def test_create_guide_out_of_lane_prints_warning(self, project, svc, invoke):
        """sq create guide --author python-dev prints the advisory warning (create_guide path)."""
        await svc.add_dev("python")
        result = await invoke(["create", "guide", "My Guide", "--author", "python-dev"])
        assert result.exit_code == 0, result.output
        assert "advisory" in result.output

    async def test_role_show_surfaces_creates_row(self, project, invoke):
        """sq role <slug> show prints a 'creates:' row next to 'can spawn:' (AC-B7)."""
        result = await invoke(["role", "product-owner", "show"])
        assert result.exit_code == 0, result.output
        assert "creates:" in result.output

    async def test_role_show_creates_row_in_lane(self, project, invoke):
        """product-owner show lists feature and epic in the creates row."""
        result = await invoke(["role", "product-owner", "show"])
        assert result.exit_code == 0, result.output
        output = result.output
        # Both feature and epic should appear somewhere after 'creates:'
        assert "feature" in output
        assert "epic" in output

    async def test_role_show_creates_empty_lane_advisory_message(self, project, invoke):
        """devops show shows the empty-lane advisory message (devops is in PREDEFINED)."""
        # devops is a bundled (predefined) role with an empty CREATE_LANES entry
        result = await invoke(["role", "devops", "show"])
        assert result.exit_code == 0, result.output
        # Empty lane shows the advisory note
        assert "out-of-lane creates warn" in result.output

    async def test_role_show_json_includes_create_lane(self, project, invoke):
        """sq role <slug> show --json includes a create_lane array (AC-B7)."""
        result = await invoke(["role", "product-owner", "show", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "create_lane" in data
        assert isinstance(data["create_lane"], list)
        assert "feature" in data["create_lane"]
        assert "epic" in data["create_lane"]

    async def test_role_show_json_dev_create_lane_empty(self, project, svc, invoke):
        """python-dev show --json has an empty create_lane array."""
        await svc.add_dev("python")
        result = await invoke(["role", "python-dev", "show", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "create_lane" in data
        assert data["create_lane"] == []

    async def test_role_show_json_tech_lead_create_lane(self, project, invoke):
        """tech-lead show --json has create_lane = ['task']."""
        result = await invoke(["role", "tech-lead", "show", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "create_lane" in data
        assert data["create_lane"] == ["task"]

    async def test_advisory_wording_no_security_claims(self, project, svc, invoke):
        """Warning text is advisory/best-effort; no enforcement-grade claims (AC-B4)."""
        await svc.add_dev("python")
        result = await invoke(["create", "feature", "Test Feature", "--author", "python-dev"])
        assert result.exit_code == 0
        # Must use advisory language
        output = result.output.lower()
        assert "advisory" in output or "best-effort" in output
        # Must NOT claim tamper-evident/forge-proof/security enforcement
        for forbidden in ("tamper-evident", "forge-proof", "security", "blocked", "prevented"):
            assert forbidden not in output, (
                f"warning must not contain {forbidden!r}; output: {result.output!r}"
            )
