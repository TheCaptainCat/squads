import pytest

from _helpers import BUILTIN_TYPES
from squads import _workflow as workflow
from squads._models._enums import Status


def test_work_item_happy_path():
    assert workflow.initial_status("task") == Status.DRAFT
    assert workflow.can_transition("task", Status.DRAFT, Status.READY)
    assert workflow.can_transition("task", Status.IN_PROGRESS, Status.DONE)


def test_work_item_illegal_skip():
    assert not workflow.can_transition("task", Status.DRAFT, Status.DONE)


def test_adr_workflow():
    assert workflow.initial_status("decision") == Status.PROPOSED
    assert workflow.can_transition("decision", Status.PROPOSED, Status.ACCEPTED)
    assert not workflow.can_transition("decision", Status.PROPOSED, Status.SUPERSEDED)


def test_review_and_guide_initials():
    assert workflow.initial_status("review") == Status.REQUESTED
    assert workflow.initial_status("guide") == Status.DRAFT
    assert workflow.can_transition("guide", Status.DRAFT, Status.PUBLISHED)


@pytest.mark.parametrize("t", list(BUILTIN_TYPES))
def test_every_type_has_workflow(t):
    wf = workflow.workflow_for(t)
    assert wf.initial in wf.states
