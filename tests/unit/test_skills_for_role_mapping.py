"""``skills_for_role`` — the pure mapping from a role slug to its skill list — directly, one
layer below tests/unit/test_item_skill_dev_gate.py's proof of the same ``*dev`` sentinel gate
inside a rendered skill body: every role preloads the three always-on skills (squads, greeting,
sq-memory); a manager (no managed item type) gets nothing else; a specialist gets exactly the
item skills it interacts with, in order, after the always-on trio; and the ``*dev``/``DEV``
sentinel expands to every declared item-skill interaction for any ``<tech>-dev`` slug.
"""

from squads._interactions import _role_guidance as role_guidance
from squads._interactions import get_playbook_spec
from squads._workflow import bundled_spec

_PB = get_playbook_spec()
_BUNDLED = bundled_spec()


def test_a_manager_with_no_managed_item_type_gets_only_the_always_on_trio() -> None:
    assert role_guidance.skills_for_role("manager", _BUNDLED, _PB) == [
        "squads",
        "greeting",
        "sq-memory",
    ]
    assert role_guidance.skills_for_role("devops", _BUNDLED, _PB) == [
        "squads",
        "greeting",
        "sq-memory",
    ]


def test_a_specialist_gets_exactly_its_interacted_item_skills_after_the_always_on_trio() -> None:
    assert role_guidance.skills_for_role("product-owner", _BUNDLED, _PB) == [
        "squads",
        "greeting",
        "sq-memory",
        "sq-epic",
        "sq-feature",
        "sq-contract",
        "sq-milestone",
    ]
    assert role_guidance.skills_for_role("tech-writer", _BUNDLED, _PB) == [
        "squads",
        "greeting",
        "sq-memory",
        "sq-guide",
    ]


def test_the_dev_sentinel_expands_to_every_declared_dev_interaction() -> None:
    assert role_guidance.skills_for_role("python-dev", _BUNDLED, _PB) == [
        "squads",
        "greeting",
        "sq-memory",
        "sq-task",
        "sq-bug",
        "sq-contract",
        "sq-review",
    ]


def test_a_dropped_type_stops_being_implied_by_a_roles_preload_list() -> None:
    """PLAYBOOK is bundled-only and has no idea a type was dropped from the active spec — but
    threading the spec in must still stop that type's stale skill from lingering on a role's
    preload list, the exact shape a dropped built-in's orphaned pointer entry comes from."""
    bundled = _BUNDLED
    dropped = {k: v for k, v in bundled.items.items() if k != "guide"}
    spec = bundled.model_copy(update={"items": dropped})

    assert "guide" not in role_guidance.item_types_for_role("tech-writer", spec, _PB)
    assert "sq-guide" not in role_guidance.skills_for_role("tech-writer", spec, _PB)
    # unaffected roles/types are untouched.
    assert role_guidance.skills_for_role("product-owner", spec, _PB) == [
        "squads",
        "greeting",
        "sq-memory",
        "sq-epic",
        "sq-feature",
        "sq-contract",
        "sq-milestone",
    ]


def test_a_renamed_type_drops_the_old_name_and_gets_no_preload_under_the_new_one() -> None:
    """A rename (drop the old key, add a new one with no PLAYBOOK entry of its own) is the
    same degradation a project-declared custom type already gets: no preload data exists for
    it, so it contributes nothing here — but critically, the OLD name must not linger either."""
    bundled = _BUNDLED
    renamed = {k: v for k, v in bundled.items.items() if k != "feature"}
    renamed["story"] = bundled.items["feature"]
    spec = bundled.model_copy(update={"items": renamed})

    assert role_guidance.item_types_for_role("product-owner", spec, _PB) == [
        "epic",
        "contract",
        "milestone",
    ]
    assert "sq-feature" not in role_guidance.skills_for_role("product-owner", spec, _PB)
    assert "sq-story" not in role_guidance.skills_for_role("product-owner", spec, _PB)
