"""Every attribute a `sq create <type>` option writes is one the type declares settable, so the
generic `sq <type> <n> update --set <key>=<value>` reaches it too."""

from squads._cli._create import CREATE_ATTRIBUTE_KINDS, attribute_flag
from squads._workflow import bundled_spec


def test_every_create_attribute_option_is_settable_via_generic_set() -> None:
    spec = bundled_spec()
    written = {
        (item_type, attribute_flag(name))
        for item_type in spec.non_roster_types()
        for name, attribute in spec.item_attributes(item_type).items()
        if attribute.kind in CREATE_ATTRIBUTE_KINDS and attribute.settable
    }
    assert {("guide", "tags"), ("guide", "tech"), ("milestone", "target-date")} <= written
