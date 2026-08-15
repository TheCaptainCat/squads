"""Every ``WorkflowSpec`` accessor that takes a caller-supplied type/kind/status has a
stated, consistent contract for an undeclared value: either it degrades to a safe default
(mirroring ``item_subentity_kind``'s documented precedent — a dropped/renamed vocabulary
entry must cleanly lose the check, not crash the caller) or it raises ``KeyError`` like
``collection()`` (a vocabulary lookup by code with no sensible universal default). This
guards the contract, not just today's implementation, so a future accessor added to either
family can't silently regress into a bare ``KeyError`` the way ``item_is_roster`` once did.
"""

from collections.abc import Callable

import pytest

from squads._workflow import bundled_spec
from squads._workflow._models import FALLBACK_ROLE_NAME, WorkflowSpec

UNDECLARED_TYPE = "nope-type"
UNDECLARED_KIND = "nope-kind"
UNDECLARED_STATUS = "NopeStatus"


def test_degrading_accessors_return_a_safe_default_for_an_undeclared_type() -> None:
    spec = bundled_spec()
    assert spec.item_is_roster(UNDECLARED_TYPE) is False
    assert spec.item_subentity_kind(UNDECLARED_TYPE) is None
    assert spec.item_parent_required(UNDECLARED_TYPE) is None
    assert spec.item_extra_fields(UNDECLARED_TYPE) == []
    assert spec.item_ref_rules(UNDECLARED_TYPE) == []
    assert spec.fields_for(UNDECLARED_TYPE) == []
    assert spec.live_statuses(UNDECLARED_TYPE) == frozenset()
    assert spec.parent_allowed(UNDECLARED_TYPE, "epic") is False
    assert spec.first_active_status(UNDECLARED_TYPE) is None
    assert spec.first_settled_status(UNDECLARED_TYPE) is None


def test_parent_hint_never_raises_for_an_undeclared_child() -> None:
    spec = bundled_spec()
    msg = spec.parent_hint(UNDECLARED_TYPE)
    assert UNDECLARED_TYPE in msg
    assert "none" in msg


def test_role_for_and_hidden_by_default_degrade_for_an_undeclared_status() -> None:
    spec = bundled_spec()
    fallback = spec.roles[FALLBACK_ROLE_NAME]
    assert spec.role_for(UNDECLARED_STATUS) == fallback
    assert spec.hidden_by_default("task", UNDECLARED_STATUS) == fallback.hidden
    assert spec.status_role(UNDECLARED_STATUS) is None


@pytest.mark.parametrize(
    "call",
    [
        lambda spec: spec.machine_for(UNDECLARED_TYPE),
        lambda spec: spec.collection(UNDECLARED_KIND),
        lambda spec: spec.subentity_completion(UNDECLARED_KIND),
        lambda spec: spec.subentity_plural(UNDECLARED_KIND),
        lambda spec: spec.subentity_container_heading(UNDECLARED_KIND),
    ],
)
def test_vocabulary_lookup_accessors_raise_a_documented_key_error(
    call: Callable[[WorkflowSpec], object],
) -> None:
    spec = bundled_spec()
    with pytest.raises(KeyError):
        call(spec)


def test_bundled_declared_values_are_unaffected_by_the_degrade_paths() -> None:
    """Control: every accessor above still returns its normal value for real, declared
    vocabulary — the degrade path only ever fires for an undeclared key."""
    spec = bundled_spec()
    assert spec.item_is_roster("role") is True
    assert spec.item_is_roster("task") is False
    assert spec.item_subentity_kind("task") == "subtask"
    assert spec.item_parent_required("task") == "feature"
    assert spec.parent_allowed("task", "feature") is True
    assert spec.parent_allowed("task", "epic") is False
    assert spec.live_statuses("task") != frozenset()
    assert spec.subentity_plural("subtask") == "subtasks"
    assert spec.subentity_container_heading("subtask") == "Subtasks"
    assert spec.subentity_container_heading("story") == "User Stories"
