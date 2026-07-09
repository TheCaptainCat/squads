import pytest

from _helpers import BUILTIN_TYPES
from squads import _workflow as workflow


def test_work_item_happy_path():
    assert workflow.initial_status("task") == "Draft"
    assert workflow.can_transition("task", "Draft", "Ready")
    assert workflow.can_transition("task", "InProgress", "Done")


def test_work_item_illegal_skip():
    assert not workflow.can_transition("task", "Draft", "Done")


def test_adr_workflow():
    assert workflow.initial_status("decision") == "Proposed"
    assert workflow.can_transition("decision", "Proposed", "Accepted")
    assert not workflow.can_transition("decision", "Proposed", "Superseded")


def test_review_and_guide_initials():
    assert workflow.initial_status("review") == "Requested"
    assert workflow.initial_status("guide") == "Draft"
    assert workflow.can_transition("guide", "Draft", "Published")


@pytest.mark.parametrize("t", list(BUILTIN_TYPES))
def test_every_type_has_workflow(t):
    wf = workflow.workflow_for(t)
    assert wf.initial in wf.states
