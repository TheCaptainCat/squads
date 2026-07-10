"""Advisory create-lanes: which role owns creating which item type.

CREATE_LANES is the single declarative source; this pins it against the authoritative
product table and proves every derived helper (allowed_create_types/in_lane_owner/
is_lane_exempt/LANED_TYPES) is consistent with it. The advisory warning's actual
service/CLI behaviour lives in tests/service/test_create_lane_advisory.py and
tests/cli/test_create_lane_advisory_cli.py.
"""

from squads._interactions import (
    CREATE_LANES,
    DEV,
    LANED_TYPES,
    PLAYBOOK,
    allowed_create_types,
    in_lane_owner,
    is_lane_exempt,
)


class TestLaneTable:
    def test_create_lanes_matches_the_product_table(self) -> None:
        expected: dict[str, set[str]] = {
            "product-owner": {"feature", "epic"},
            "tech-lead": {"task"},
            "architect": {"decision", "guide"},
            "reviewer": {"review"},
            "qa": {"bug"},
            "tech-writer": {"guide"},
            DEV: set(),
        }
        assert expected == CREATE_LANES

    def test_every_lane_role_is_a_real_playbook_role(self) -> None:
        playbook_slugs = {guide.slug for entry in PLAYBOOK.values() for guide in entry.roles}
        for role in CREATE_LANES:
            if role == DEV:
                continue
            assert role in playbook_slugs, f"{role!r} is not a real playbook role"


class TestAllowedCreateTypes:
    def test_product_owner_lane(self) -> None:
        assert allowed_create_types("product-owner") == {"feature", "epic"}

    def test_tech_lead_lane(self) -> None:
        assert allowed_create_types("tech-lead") == {"task"}

    def test_architect_lane(self) -> None:
        assert allowed_create_types("architect") == {"decision", "guide"}

    def test_reviewer_lane(self) -> None:
        assert allowed_create_types("reviewer") == {"review"}

    def test_qa_lane(self) -> None:
        assert allowed_create_types("qa") == {"bug"}

    def test_tech_writer_lane(self) -> None:
        assert allowed_create_types("tech-writer") == {"guide"}

    def test_dev_lane_is_empty(self) -> None:
        assert allowed_create_types("python-dev") == set()

    def test_devops_lane_is_empty(self) -> None:
        assert allowed_create_types("devops") == set()

    def test_manager_lane_is_empty(self) -> None:
        """Manager has no lane of its own — it is exempt from the check entirely."""
        assert allowed_create_types("manager") == set()


class TestLaneExemptions:
    def test_manager_is_exempt(self) -> None:
        assert is_lane_exempt("manager") is True

    def test_op_slug_is_exempt(self) -> None:
        assert is_lane_exempt("op-pierre") is True

    def test_a_regular_role_is_not_exempt(self) -> None:
        assert is_lane_exempt("tech-lead") is False

    def test_op_prefix_is_required_exactly(self) -> None:
        assert is_lane_exempt("operations") is False  # starts with "op" but not "op-"


class TestLanedTypes:
    def test_contains_every_create_lanes_value(self) -> None:
        for types in CREATE_LANES.values():
            assert types <= LANED_TYPES

    def test_excludes_internal_artifact_types(self) -> None:
        for meta_type in ("role", "skill", "operator"):
            assert meta_type not in LANED_TYPES


class TestInLaneOwner:
    def test_feature_is_owned_by_product_owner(self) -> None:
        assert in_lane_owner("feature") == {"product-owner"}

    def test_task_is_owned_by_tech_lead(self) -> None:
        assert in_lane_owner("task") == {"tech-lead"}

    def test_bug_is_owned_by_qa(self) -> None:
        assert in_lane_owner("bug") == {"qa"}

    def test_review_is_owned_by_reviewer(self) -> None:
        assert in_lane_owner("review") == {"reviewer"}

    def test_decision_is_owned_by_architect(self) -> None:
        assert in_lane_owner("decision") == {"architect"}

    def test_guide_is_owned_by_both_architect_and_tech_writer(self) -> None:
        assert in_lane_owner("guide") == {"architect", "tech-writer"}

    def test_epic_is_owned_by_product_owner(self) -> None:
        assert in_lane_owner("epic") == {"product-owner"}
