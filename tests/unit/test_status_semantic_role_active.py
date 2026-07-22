"""``default_workflow.toml`` declares ``role = "active"`` on the two working states —
``InProgress`` (work-item lifecycle) and ``Active`` (roster/agent lifecycle) — a non-settled,
shown role, distinct from ``Superseded``'s settled ``"superseded"`` role.
"""

from squads._workflow import bundled_spec


def test_in_progress_carries_the_active_role_and_stays_non_settled() -> None:
    spec = bundled_spec()
    st = spec.statuses["InProgress"]
    assert st.role == "active"
    assert spec.roles["active"].settled is False


def test_roster_active_carries_the_active_role_and_stays_non_settled() -> None:
    spec = bundled_spec()
    st = spec.statuses["Active"]
    assert st.role == "active"
    assert spec.roles["active"].settled is False


def test_superseded_role_is_unaffected_by_the_active_role() -> None:
    spec = bundled_spec()
    st = spec.statuses["Superseded"]
    assert st.role == "superseded"
    assert spec.roles["superseded"].settled is True


def test_status_role_accessor_resolves_the_active_role() -> None:
    spec = bundled_spec()
    assert spec.status_role("InProgress") == "active"
    assert spec.status_role("Active") == "active"
