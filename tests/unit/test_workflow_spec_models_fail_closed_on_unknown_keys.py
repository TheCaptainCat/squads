"""Every capability-flag-bearing model (``Lifecycle``, ``ItemSpec``, ``StatusSpec``,
``RefRule``, and ``WorkflowSpec``'s own top-level keys) rejects an unknown key at
construction (``extra="forbid"``) — and so does the TOML loader itself for an unknown key
inside a ``[items.*]`` section, one layer below the override-merge fail-closed guard
(cross-ref tests/unit/test_workflow_override_merge.py, same shape, one layer higher).
"""

import tomllib

import pytest
from pydantic import ValidationError

from squads._errors import SquadsError
from squads._workflow import load_workflow_spec
from squads._workflow._loader import _build_spec  # pyright: ignore[reportPrivateUsage]
from squads._workflow._models import ItemSpec, Lifecycle, RefRule, StatusSpec, WorkflowSpec


def test_lifecycle_rejects_an_unknown_key() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Lifecycle.model_validate({"initial": "Draft", "transitions": {}, "unexpected_key": "boom"})


def test_item_spec_rejects_an_unknown_key() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ItemSpec.model_validate(
            {"prefix": "TST", "folder": "tests", "lifecycle": "work", "unknown_field": "oops"}
        )


def test_status_spec_rejects_an_unknown_key() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        StatusSpec.model_validate({"terminal": False, "rogue_key": True})


def test_ref_rule_rejects_an_unknown_key() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RefRule.model_validate({"kind": "fixes", "hint": "", "bogus": "data"})


def test_workflow_spec_rejects_an_unknown_top_level_key() -> None:
    spec = load_workflow_spec()
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        WorkflowSpec.model_validate(
            {
                "items": dict(spec.items),
                "statuses": dict(spec.statuses),
                "lifecycles": dict(spec.lifecycles),
                "prefix_to_type": dict(spec.prefix_to_type),
                "alias_to_type": dict(spec.alias_to_type),
                "totally_bogus": "should_fail",
            }
        )


def test_the_toml_loader_rejects_an_unknown_key_inside_an_items_section() -> None:
    toml_text = """
[lifecycles.work]
initial = "Draft"
[lifecycles.work.transitions]
Draft = ["Done"]
Done = []

[lifecycles.agent]
initial = "Draft"
[lifecycles.agent.transitions]
Draft = ["Active"]
Active = ["Archived"]
Archived = ["Active"]

[items.task]
prefix = "TASK"
folder = "tasks"
lifecycle = "work"
UNKNOWN_BOGUS_KEY = "this should fail"

[items.role]
prefix = "ROLE"
folder = "agents/roles"
lifecycle = "agent"

[items.skill]
prefix = "SKILL"
folder = "agents/skills"
lifecycle = "agent"

[items.operator]
prefix = "OP"
folder = "operators"
lifecycle = "agent"
"""
    raw = tomllib.loads(toml_text)
    with pytest.raises(SquadsError):
        _build_spec(raw)


def test_the_bundled_spec_still_loads_cleanly_with_all_capability_flags_present() -> None:
    spec = load_workflow_spec()
    assert spec is not None
    assert spec.items["task"].parent_required == "feature"
    assert spec.items["role"].category == "roster"
