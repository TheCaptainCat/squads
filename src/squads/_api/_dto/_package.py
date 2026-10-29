"""The package-data DTOs: the bundled docs and the migration changelog. They describe the
installed package, not a squad, so no operation answers with them: the function beside the data
builds them."""

from squads._api._dto._base import DTO


class DocEntry(DTO):
    """A bundled doc: the name ``sq docs`` takes, and its title."""

    name: str
    title: str


class DocIndex(DTO):
    """Every bundled doc, by name."""

    docs: list[DocEntry]


class Doc(DTO):
    """One bundled doc: its name and its markdown."""

    name: str
    markdown: str


class MigrationEntry(DTO):
    """A shipped migration: the release, the schema step, its summary and its manual steps
    (empty when it has none)."""

    version: str
    from_schema: str
    to_schema: str
    summary: str
    manual: str


class MigrationIndex(DTO):
    """Every migration squads ships, oldest first."""

    migrations: list[MigrationEntry]


class MigrationSteps(DTO):
    """The migrations with manual steps in the releases after *from_version* up to and including
    *to_version*."""

    from_version: str
    to_version: str
    migrations: list[MigrationEntry]
