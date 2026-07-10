"""Accepted (decision) and Published (guide) are terminal statuses — not merely "closed-looking"
— even though each has a legal outgoing transition (Accepted->Superseded/Deprecated,
Published->Draft/Deprecated). Terminal does not mean the graph dead-ends.
"""

from squads import _workflow as workflow


def test_accepted_and_published_are_in_the_terminal_set():
    assert "Accepted" in workflow.TERMINAL
    assert "Published" in workflow.TERMINAL


def test_accepted_and_published_are_not_open():
    assert not workflow.is_open("Accepted")
    assert not workflow.is_open("Published")


def test_accepted_can_still_transition_to_superseded_or_deprecated():
    assert workflow.can_transition("decision", "Accepted", "Superseded")
    assert workflow.can_transition("decision", "Accepted", "Deprecated")


def test_published_can_still_transition_to_draft_or_deprecated():
    assert workflow.can_transition("guide", "Published", "Draft")
    assert workflow.can_transition("guide", "Published", "Deprecated")
