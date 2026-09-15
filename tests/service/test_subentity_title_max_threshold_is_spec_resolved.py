"""``subentity_title_max``'s threshold is resolved from the spec, per type, and read by both
the ``sq check`` advisory (``CATALOG["subentity_title_max"]``) and the create-time advisory
(``add-<kind>``'s own check in ``_services/_subentities.py``) through the one accessor,
``WorkflowSpec.item_subentity_title_max`` — never the bundled module constant. A type
overriding it gets the same number at both call sites; a type that does not override it
reproduces today's 120-character default exactly, byte for byte (message text included).
"""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads._interactions import TITLE_ADVISORY_MAX
from squads._services import _service as service

pytestmark = pytest.mark.anyio


def _service_with_override(squad_dir: Path, override_body: str) -> service.Service:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{override_body}", encoding="utf-8"
    )
    return service.open_service()


_BETWEEN_80_AND_120 = "x" * 85  # over an 80-char override, under the 120-char bundled default


async def test_a_type_declaring_no_override_reproduces_the_bundled_default_exactly(svc):
    """Falsification baseline: unmodified, an 85-char title is under the 120-char bundled
    default — no create-time advisory, and no ``sq check`` finding either."""
    feat = (await create_item(svc, "feature", "f")).item
    res = await svc.add_story(feat.id, _BETWEEN_80_AND_120)
    assert res.title_advisory is None

    issues = await svc.check()
    assert not [i for i in issues if i.item == feat.id and "title is" in i.message]


async def test_a_declared_threshold_moves_where_the_create_time_advisory_fires(project):
    """The same 85-char title, on a type that overrides the threshold to 80, now trips the
    create-time advisory — the number that changed is the spec's, not the constant's."""
    svc = _service_with_override(
        project.squad_dir, '[items.feature]\nvalidators = ["subentity_title_max:80"]\n'
    )
    feat = (await create_item(svc, "feature", "f")).item
    res = await svc.add_story(feat.id, _BETWEEN_80_AND_120)
    assert res.title_advisory is not None
    assert str(len(_BETWEEN_80_AND_120)) in res.title_advisory


async def test_a_declared_threshold_moves_where_sq_check_fires_with_the_same_number(project):
    """``sq check``'s own advisory fires at the identical 80-char threshold, and its message
    names 80, not the bundled 120 — the two call sites read one resolved value, not two."""
    svc = _service_with_override(
        project.squad_dir, '[items.feature]\nvalidators = ["subentity_title_max:80"]\n'
    )
    feat = (await create_item(svc, "feature", "f")).item
    await svc.add_story(feat.id, _BETWEEN_80_AND_120)

    issues = await svc.check()
    matching = [i for i in issues if i.item == feat.id and "title is" in i.message]
    assert len(matching) == 1
    assert matching[0].level == "warn"
    assert "(threshold: 80)" in matching[0].message
    assert "(threshold: 120)" not in matching[0].message


async def test_the_bundled_default_message_text_is_unchanged(svc):
    """Byte-for-byte parity with the bundled default, for a type declaring no override — the
    threshold is resolved through ``WorkflowSpec.item_subentity_title_max``, and its number and
    wording must match ``TITLE_ADVISORY_MAX`` exactly."""
    feat = (await create_item(svc, "feature", "f")).item
    await svc.add_story(feat.id, "x" * (TITLE_ADVISORY_MAX + 1))
    issues = await svc.check()
    matching = [i for i in issues if i.item == feat.id and "title is" in i.message]
    assert len(matching) == 1
    assert f"(threshold: {TITLE_ADVISORY_MAX})" in matching[0].message
    assert "put the detail in the body" in matching[0].message
