"""``WorkflowSpec.hidden_by_default`` — the one default-visibility predicate shared by ``sq
list``/``sq tree``, keyed purely on the referenced role's ``hidden`` flag (no category branch:
the role object alone encodes the intended presence). For work/roster items this happens to
match ``is_open``'s inverse, because none of their reachable statuses carry the ``in_force``
role — the one role where ``settled`` and ``hidden`` diverge (a resting record that still
shows). ``Rejected`` carries the ``retired`` role (settled + hidden), so a rejected decision
hides by default.
"""

from squads._workflow import bundled_spec
from squads._workflow._models import CATEGORIES


def test_categories_catalog_is_the_closed_roster_work_records_set() -> None:
    assert set(CATEGORIES) == {"roster", "work", "records"}


def test_work_category_hides_on_a_settled_hidden_role() -> None:
    spec = bundled_spec()
    assert spec.hidden_by_default("task", "InProgress") is False
    assert spec.hidden_by_default("task", "Done") is True
    assert spec.hidden_by_default("task", "Cancelled") is True


def test_roster_category_hides_on_a_settled_hidden_role() -> None:
    spec = bundled_spec()
    assert spec.hidden_by_default("role", "Draft") is False
    assert spec.hidden_by_default("role", "Active") is False
    assert spec.hidden_by_default("role", "Archived") is True


def test_records_category_stays_visible_on_the_in_force_role() -> None:
    spec = bundled_spec()
    assert spec.hidden_by_default("decision", "Proposed") is False
    assert spec.hidden_by_default("decision", "Accepted") is False  # settled, but not hidden
    assert spec.hidden_by_default("guide", "Published") is False  # settled, but not hidden


def test_records_category_hides_on_a_retired_or_superseded_role() -> None:
    spec = bundled_spec()
    assert spec.hidden_by_default("decision", "Superseded") is True
    assert spec.hidden_by_default("decision", "Deprecated") is True
    assert spec.hidden_by_default("guide", "Deprecated") is True


def test_rejected_carries_the_retired_role_and_hides_by_default() -> None:
    """Rejected carries the ``retired`` role (settled + hidden), so a rejected decision hides
    by default."""
    spec = bundled_spec()
    assert spec.statuses["Rejected"].role == "retired"
    assert spec.hidden_by_default("decision", "Rejected") is True


def test_hidden_by_default_is_independent_of_item_type() -> None:
    """``hidden_by_default`` is purely role-derived — it does not consult ``item_type`` at
    all, so it returns the same answer for a given status regardless of which type asks."""
    spec = bundled_spec()
    for s in spec.statuses:
        seen = {spec.hidden_by_default(t, s) for t in spec.items}
        assert len(seen) == 1


def test_hidden_by_default_matches_is_open_inverse_except_for_the_in_force_role() -> None:
    """``hidden_by_default(t, s) == not is_open(s)`` for every status EXCEPT the one role where
    settled and hidden diverge — ``in_force`` (``Accepted``/``Published``): a resting record
    that stays visible. That single split — settled yet still shown — is exactly what the role
    object expresses."""
    spec = bundled_spec()
    for s in spec.statuses:
        if spec.status_role(s) == "in_force":
            continue
        assert spec.hidden_by_default("task", s) == (not spec.is_open(s))
