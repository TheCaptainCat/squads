"""``Service.playbook`` is the single carrier for the active/merged playbook — pins that no
second, parallel carrier (an ambient ``RequestContext`` field + accessor, resolved separately
with different failure semantics) exists to drift out of sync with it again.
"""

import dataclasses

from squads._context import RequestContext
from squads._interactions import _playbook as playbook_module


def test_request_context_carries_no_playbook_field() -> None:
    field_names = {f.name for f in dataclasses.fields(RequestContext)}
    assert "active_playbook" not in field_names


def test_playbook_module_exposes_no_ambient_playbook_accessor() -> None:
    assert not hasattr(playbook_module, "get_active_playbook_spec")
