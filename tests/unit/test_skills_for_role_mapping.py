"""``skills_for_role`` — the pure mapping from a role slug to its skill list — directly, one
layer below tests/unit/test_item_skill_dev_gate.py's proof of the same ``*dev`` sentinel gate
inside a rendered skill body: every role preloads the two always-on skills (squads, greeting);
a manager (no managed item type) gets nothing else; a specialist gets exactly the item skills
it interacts with, in order, after the always-on pair; and the ``*dev``/``DEV`` sentinel
expands to every declared item-skill interaction for any ``<tech>-dev`` slug.
"""

from squads import _interactions as interactions


def test_a_manager_with_no_managed_item_type_gets_only_the_always_on_pair() -> None:
    assert interactions.skills_for_role("manager") == ["squads", "greeting"]
    assert interactions.skills_for_role("devops") == ["squads", "greeting"]


def test_a_specialist_gets_exactly_its_interacted_item_skills_after_the_always_on_pair() -> None:
    assert interactions.skills_for_role("product-owner") == [
        "squads",
        "greeting",
        "sq-epic",
        "sq-feature",
    ]
    assert interactions.skills_for_role("tech-writer") == ["squads", "greeting", "sq-guide"]


def test_the_dev_sentinel_expands_to_every_declared_dev_interaction() -> None:
    assert interactions.skills_for_role("python-dev") == [
        "squads",
        "greeting",
        "sq-task",
        "sq-bug",
        "sq-review",
    ]
