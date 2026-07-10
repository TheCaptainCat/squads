"""The declared parent-type rule table (``parent_allowed``/``parent_hint``): a task's parent
must be a feature, a feature's parent must be an epic, an unconstrained type accepts any
parent, and the hint names both the allowed parent type and the ref-add escape hatch.
"""

from squads import _workflow as workflow


def test_parent_allowed_enforces_the_declared_rule_table() -> None:
    assert workflow.parent_allowed("task", "feature")
    assert not workflow.parent_allowed("task", "epic")
    assert not workflow.parent_allowed("task", "bug")
    assert workflow.parent_allowed("feature", "epic")
    assert not workflow.parent_allowed("feature", "task")


def test_an_unconstrained_type_accepts_any_parent() -> None:
    assert workflow.parent_allowed("bug", "epic")


def test_parent_hint_names_the_allowed_parent_type_and_the_ref_add_escape_hatch() -> None:
    hint = workflow.parent_hint("task")
    assert "feature" in hint
    assert "sq ref add" in hint
