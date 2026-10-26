"""The rules `sq check` reports that are not validator-catalog members.

A catalog finding carries its validator's declared name (``VALIDATOR_NAMES`` and
``SQUAD_GLOBAL_VALIDATOR_NAMES``), so those names are not repeated here. Every rule below is
binding: it runs in every squad and no ``validators`` selection can turn it off.
"""

from squads._workflow._validator_names import SQUAD_GLOBAL_VALIDATOR_NAMES, VALIDATOR_NAMES

#: Rule name -> the source that reports it.
BINDING_RULES: dict[str, str] = {
    "markers_balanced": "raw-text scan",
    "view_target_resolves": "raw-text scan",
    "view_tag_in_region": "raw-text scan",
    "seeded_view_resolves": "raw-text scan",
    "body_regions_present": "raw-text scan",
    "block_in_container": "raw-text scan",
    "file_readable": "file load",
    "frontmatter_parses": "file load",
    "id_present": "file load",
    "id_well_formed": "file load",
    "fields_valid": "file load",
    "timestamps_present": "file load",
    "override_stamped": "override checks",
    "override_current": "override checks",
    "override_loads": "override checks",
    "skill_type_declared": "orphaned skills",
    "ids_unique": "duplicate ids",
    "numbers_unique": "duplicate ids",
    "frontmatter_matches_index": "cross-source",
    "playbook_loads": "config load",
    "workflow_loads": "config load",
    "corpus_scans": "config load",
}


def is_registered(rule: str) -> bool:
    """Whether *rule* is a binding rule or a validator-catalog name."""
    return rule in BINDING_RULES or rule in VALIDATOR_NAMES or rule in SQUAD_GLOBAL_VALIDATOR_NAMES
