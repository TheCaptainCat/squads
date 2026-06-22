"""Keys used inside ``Item.extra`` (the per-type metadata bag).

Centralised so the same string literal isn't scattered across service/backend/cli/catalog.
"""


class ExtraKey:
    # agent roles
    SLUG = "slug"
    FULL_NAME = "full_name"
    TITLE = "title"
    MISSION = "mission"
    RESPONSIBILITIES = "responsibilities"
    MODEL = "model"
    COLOR = "color"
    IS_DEFAULT = "is_default"
    CAN_SPAWN = "can_spawn"
    DESCRIPTION = "description"
    SKILLS = "skills"
    AGREEMENTS = "agreements"
    # developers
    IS_DEV = "is_dev"
    TECH = "tech"
    # skills
    WHEN_TO_USE = "when_to_use"
    ALLOWED_TOOLS = "allowed_tools"
    # guides
    TAGS = "tags"
    # reviews
    TARGET_REF = "target_ref"
    # bugs
    SEVERITY = "severity"
