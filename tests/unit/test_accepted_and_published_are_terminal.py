"""Accepted (decision) and Published (guide) are terminal statuses — not merely "closed-looking"
— even though each has a legal outgoing transition (Accepted->Superseded/Deprecated,
Published->Draft/Deprecated). Terminal does not mean the graph dead-ends.
"""

from squads._workflow import bundled_spec


def test_accepted_and_published_are_in_the_terminal_set():
    assert "Accepted" in bundled_spec().terminal_set()
    assert "Published" in bundled_spec().terminal_set()


def test_accepted_and_published_are_not_open():
    assert not bundled_spec().is_open("Accepted")
    assert not bundled_spec().is_open("Published")


def test_accepted_can_still_transition_to_superseded_or_deprecated():
    assert bundled_spec().can_transition("decision", "Accepted", "Superseded")
    assert bundled_spec().can_transition("decision", "Accepted", "Deprecated")


def test_published_can_still_transition_to_draft_or_deprecated():
    assert bundled_spec().can_transition("guide", "Published", "Draft")
    assert bundled_spec().can_transition("guide", "Published", "Deprecated")
