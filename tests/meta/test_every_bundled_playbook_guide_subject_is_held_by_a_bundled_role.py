"""Every guide subject in the bundled playbook names something the bundled catalog declares: a
role slug, or a ``*<capability>`` that some bundled role or template holds. A guide addressed to
nobody is dead text, and the playbook loader checks grammar only."""

import pytest

from squads._interactions._playbook import get_playbook_spec
from squads._roles._catalog import get_catalog


def _subjects() -> list[tuple[str, str]]:
    return sorted(
        {
            (item_type, guide.slug)
            for item_type, playbook in get_playbook_spec().types.items()
            for guide in playbook.roles
        }
    )


@pytest.mark.parametrize(("item_type", "subject"), _subjects())
def test_a_bundled_guide_subject_is_declared_by_the_bundled_catalog(
    item_type: str, subject: str
) -> None:
    catalog = get_catalog()
    if subject.startswith("*"):
        held = {c for r in catalog.roles for c in r.capabilities} | {
            c for t in catalog.templates.values() for c in t.capabilities
        }
        assert subject[1:] in held, f"{item_type}: no bundled role or template holds {subject}"
    else:
        assert subject in {r.slug for r in catalog.roles}, (
            f"{item_type}: {subject} is not a bundled role"
        )
