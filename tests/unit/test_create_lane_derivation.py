"""Advisory create-lanes: which role owns creating which item type.

The lane is DERIVED from the playbook document — each role guide's declared ``authors``
flag — so there is one source and no table to keep in step with it. These tests pin the
derivation against the authoritative product table AND against the document itself, in both
directions, so a guide that gains or loses ``authors`` cannot pass silently.

The advisory warning's actual service/CLI behaviour lives in
tests/service/test_create_lane_advisory.py and tests/cli/test_create_lane_advisory_cli.py;
an override-declared authoring role is exercised end to end in
tests/integration/test_an_override_declared_authoring_role_is_in_lane.py.
"""

from squads._interactions import PLAYBOOK, get_playbook_spec
from squads._interactions._role_guidance import (
    DEV,
    allowed_create_types,
    catalog_default_slug,
    create_lanes,
    in_lane_owner,
    is_lane_exempt,
    laned_types,
)
from squads._roles._catalog import get_catalog
from squads._workflow import bundled_spec

_PB = get_playbook_spec()
_SPEC = bundled_spec()

#: The authoritative product table: role slug → the types it is in-lane to author.
_PRODUCT_TABLE: dict[str, set[str]] = {
    "product-owner": {"feature", "epic", "contract", "milestone"},
    "tech-lead": {"task"},
    "architect": {"decision", "guide"},
    "reviewer": {"review"},
    "qa": {"bug"},
    "tech-writer": {"guide"},
}


class TestLaneTable:
    def test_the_derived_lanes_match_the_product_table(self) -> None:
        assert create_lanes(_PB) == _PRODUCT_TABLE

    def test_the_dev_sentinel_declares_no_lane(self) -> None:
        assert DEV not in create_lanes(_PB)

    def test_every_lane_is_a_declared_authors_guide_in_the_playbook(self) -> None:
        """Forward direction: nothing enters a lane that the document didn't declare."""
        declared = {
            (item_type, guide.slug)
            for item_type, entry in PLAYBOOK.items()
            for guide in entry.roles
            if guide.authors
        }
        derived = {(t, slug) for slug, types in create_lanes(_PB).items() for t in types}
        assert derived == declared

    def test_a_guide_that_only_reads_a_type_is_not_in_its_lane(self) -> None:
        """Reverse direction: interacting with a type is not the same as authoring it."""
        assert "bug" not in allowed_create_types(
            "tech-lead", _SPEC, _PB
        )  # triages bugs, doesn't file them
        assert "feature" not in allowed_create_types(
            "qa", _SPEC, _PB
        )  # verifies features, doesn't author
        assert "epic" not in allowed_create_types(
            "architect", _SPEC, _PB
        )  # shapes epics, doesn't author


class TestAllowedCreateTypes:
    def test_every_product_table_role_derives_its_own_lane(self) -> None:
        for slug, expected in _PRODUCT_TABLE.items():
            assert allowed_create_types(slug, _SPEC, _PB) == expected, slug

    def test_dev_lane_is_empty(self) -> None:
        assert allowed_create_types("python-dev", _SPEC, _PB) == set()

    def test_devops_lane_is_empty(self) -> None:
        assert allowed_create_types("devops", _SPEC, _PB) == set()

    def test_default_role_lane_is_empty(self) -> None:
        """The coordinator has no lane of its own — it is exempt from the check entirely."""
        default = catalog_default_slug(get_catalog())
        assert default is not None
        assert allowed_create_types(default, _SPEC, _PB) == set()


class TestLaneExemptions:
    def test_the_default_role_is_exempt(self) -> None:
        default = catalog_default_slug(get_catalog())
        assert default is not None
        assert is_lane_exempt(default, default) is True

    def test_the_exemption_follows_a_supplied_default_slug(self) -> None:
        """A squad that designates another role as its coordinator moves the exemption."""
        assert is_lane_exempt("tech-lead", "tech-lead") is True
        assert is_lane_exempt("manager", "tech-lead") is False

    def test_op_slug_is_exempt(self) -> None:
        assert is_lane_exempt("op-alice", None) is True

    def test_a_regular_role_is_not_exempt(self) -> None:
        assert is_lane_exempt("tech-lead", None) is False

    def test_op_prefix_is_required_exactly(self) -> None:
        assert is_lane_exempt("operations", None) is False  # starts with "op" but not "op-"


class TestLanedTypes:
    def test_contains_every_derived_lane_value(self) -> None:
        for types in create_lanes(_PB).values():
            assert types <= laned_types(_PB)

    def test_excludes_roster_types(self) -> None:
        for roster_type in ("role", "skill", "operator"):
            assert roster_type not in laned_types(_PB)


class TestInLaneOwner:
    def test_each_type_resolves_to_its_declared_authors(self) -> None:
        expected: dict[str, set[str]] = {}
        for slug, types in _PRODUCT_TABLE.items():
            for item_type in types:
                expected.setdefault(item_type, set()).add(slug)
        for item_type, owners in expected.items():
            assert in_lane_owner(item_type, _PB) == owners, item_type

    def test_a_type_with_no_declared_author_has_no_owner(self) -> None:
        assert in_lane_owner("role", _PB) == set()
