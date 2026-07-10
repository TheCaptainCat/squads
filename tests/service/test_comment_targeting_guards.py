"""``Service.comment()``'s target-resolution guards: at most one of ``--story``/``--subtask``/
``--finding`` may be given, and the named sub-entity's discussion section must actually exist
on disk (i.e. the local id is real) before a comment can be appended to it.
"""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_comment_rejects_specifying_more_than_one_sub_entity_target(svc):
    feat = (await svc.create("feature", "f")).item
    with pytest.raises(SquadsError, match="only one"):
        await svc.comment(feat.id, ["x"], story="US1", subtask="ST1")


async def test_comment_raises_when_the_targeted_sub_entity_section_does_not_exist(svc):
    epic = (await svc.create("epic", "e")).item
    with pytest.raises(SquadsError):
        await svc.comment(epic.id, ["x"], story="US1")  # epic hosts no such story
