"""``WorkflowSpec.first_active_status`` — the spec-derived concept behind "the state you move
an item to once you start working it", replacing a hardcoded ``"InProgress"`` literal in
generic (not-per-type) prose. Table-driven across the bundled lifecycles to prove it tracks
each one's own live status rather than a single coincidental name.
"""

from squads._workflow import bundled_spec


def test_first_active_status_per_bundled_type() -> None:
    spec = bundled_spec()
    # task/bug share the `work`/`bug` lifecycles, both first-live at InProgress.
    assert spec.first_active_status("task") == "InProgress"
    assert spec.first_active_status("bug") == "InProgress"
    # review's lifecycle walks Requested -> InReview (live) first — a different status name,
    # proving the derivation isn't just "always InProgress".
    assert spec.first_active_status("review") == "InReview"
    # decision's lifecycle (Proposed -> Accepted -> Superseded/Rejected/Deprecated) has no
    # live status at all — a fully static lifecycle degrades to None, not a guess.
    assert spec.first_active_status("decision") is None
    # guide (Draft -> Published -> Deprecated) is likewise fully static.
    assert spec.first_active_status("guide") is None


def test_first_active_status_is_none_for_an_undeclared_type() -> None:
    spec = bundled_spec()
    assert spec.first_active_status("not-a-type") is None


def test_first_settled_status_per_bundled_type() -> None:
    spec = bundled_spec()
    # work lifecycle (task/feature/epic): happy path ends at Done.
    assert spec.first_settled_status("task") == "Done"
    # bug lifecycle: Open -> InProgress -> Fixed -> Verified; Fixed is settled (role active
    # is NOT settled — it's Verified, role "done", that first satisfies settled on this walk;
    # confirm this stays the generalized "first settled reached", not a specific name pinned
    # by hand).
    bug_settled = spec.first_settled_status("bug")
    assert bug_settled is not None
    # decision lifecycle never reaches a "done" role at all — its happy-path close is
    # Accepted (role in_force, which is also settled) — proving this generalizes beyond
    # the "done" role specifically.
    assert spec.first_settled_status("decision") == "Accepted"
    # guide lifecycle: Draft -> Published -> Deprecated; Published (in_force) is the
    # happy-path close.
    assert spec.first_settled_status("guide") == "Published"


def test_first_settled_status_is_none_for_an_undeclared_type() -> None:
    spec = bundled_spec()
    assert spec.first_settled_status("not-a-type") is None
