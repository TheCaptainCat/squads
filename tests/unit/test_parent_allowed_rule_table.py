"""The declared parent-type rule table (``parent_allowed``/``parent_hint``): a task's parent
must be a feature, a feature's parent must be an epic, an unconstrained type accepts any
parent, and the hint names both the allowed parent type and the ref-add escape hatch.
"""

from squads._workflow import bundled_spec


def test_parent_allowed_enforces_the_declared_rule_table() -> None:
    assert bundled_spec().parent_allowed("task", "feature")
    assert not bundled_spec().parent_allowed("task", "epic")
    assert not bundled_spec().parent_allowed("task", "bug")
    assert bundled_spec().parent_allowed("feature", "epic")
    assert not bundled_spec().parent_allowed("feature", "task")


def test_an_unconstrained_type_accepts_any_parent() -> None:
    assert bundled_spec().parent_allowed("bug", "epic")


def test_parent_hint_names_the_allowed_parent_type_and_the_ref_add_escape_hatch() -> None:
    hint = bundled_spec().parent_hint("task")
    assert "feature" in hint
    assert "sq task <n> ref add" in hint
