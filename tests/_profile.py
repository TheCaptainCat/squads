"""The squad a `tests/cli` run is on, and the names it gives the things a case reaches.

A case never writes a type, kind, field or alias of the squad it runs on: it reads it from the
profile of that squad. `pytest --squad override` (or `SQUADS_TEST_SQUAD=override`) selects the
override test squad for the whole run; the default is the bundled one. A tests/meta guard resolves
every entry of both profiles against the spec of its squad.
"""

import os
from dataclasses import dataclass

#: The numbers of the populated squad: the host of the target kind, a reference item under it and
#: the third item, on both squads (the counter starts after the one role).
HOST = 2
REFERENCE = 3
THIRD = 4


@dataclass(frozen=True)
class Profile:
    """The vocabulary one squad gives the roles the surface cases play."""

    squad: str
    #: The type that hosts the target kind, its ID prefix, its alias and its title in the fixture.
    host: str
    host_prefix: str
    host_alias: str
    host_title: str
    #: The reference type: a child of the host whose sub-entities can map to the target kind.
    ref: str
    ref_prefix: str
    ref_folder: str
    ref_title: str
    ref_label: str
    ref_kind_one: str
    ref_kind_one_label: str
    ref_kind_two: str
    ref_kind_two_label: str
    ref_slug: str
    #: A third type with a sub-entity kind that has a field, and that kind.
    third: str
    third_prefix: str
    third_folder: str
    third_title: str
    #: The kind the reference type hosts and its local prefix, plural and heading.
    kind: str
    kind_prefix: str
    kind_plural: str
    #: The kind the host hosts, which the reference kind maps to.
    target_kind: str
    target_prefix: str
    target_plural: str
    #: The kind of the third type, its field, and a value of that field's collection.
    third_kind: str
    third_kind_prefix: str
    third_kind_plural: str
    third_field: str
    third_value: str
    third_other_value: str
    #: A badge field of the reference type, a value of it, another value, and an unset marker.
    badge: str
    badge_flag: str
    no_badge_flag: str
    badge_codes: str
    badge_value: str
    badge_other_value: str
    #: The status a reference item moves to from its initial status, and its initial status.
    initial: str
    moved: str
    #: The status a sub-entity of the reference kind starts at and one it moves to.
    kind_initial: str
    kind_moved: str

    def ref_id(self, number: int) -> str:
        return f"{self.ref_prefix}-{number}"

    def host_id(self, number: int) -> str:
        return f"{self.host_prefix}-{number}"

    def third_id(self, number: int) -> str:
        return f"{self.third_prefix}-{number}"

    def ref_path(self, number: int, slug: str | None = None) -> str:
        return f"{self.ref_folder}/{self.ref_prefix}-{number:06d}-{slug or self.ref_slug}.md"


BUNDLED = Profile(
    squad="bundled",
    host="feature",
    host_prefix="FEAT",
    host_alias="f",
    host_title="Search",
    ref="task",
    ref_prefix="TASK",
    ref_folder="tasks",
    ref_title="Build the query parser",
    ref_label="Task",
    ref_kind_one="fixes",
    ref_kind_one_label="Fixes",
    ref_kind_two="addresses",
    ref_kind_two_label="Addresses",
    ref_slug="build-the-query-parser",
    third="review",
    third_prefix="REV",
    third_folder="reviews",
    third_title="Review the query parser",
    kind="subtask",
    kind_prefix="ST",
    kind_plural="subtasks",
    target_kind="story",
    target_prefix="US",
    target_plural="stories",
    third_kind="finding",
    third_kind_prefix="F",
    third_kind_plural="findings",
    third_field="severity",
    third_value="High",
    third_other_value="Low",
    badge="priority",
    badge_flag="--priority",
    no_badge_flag="--no-priority",
    badge_codes="urgent, high, medium, low",
    badge_value="high",
    badge_other_value="low",
    initial="Draft",
    moved="Ready",
    kind_initial="Todo",
    kind_moved="InProgress",
)

OVERRIDE = Profile(
    squad="override",
    host="initiative",
    host_prefix="INI",
    host_alias="f",
    host_title="Search",
    ref="job",
    ref_prefix="JOB",
    ref_folder="jobs",
    ref_title="Build the query parser",
    ref_label="Job",
    ref_kind_one="blocks",
    ref_kind_one_label="Blocks",
    ref_kind_two="scopes",
    ref_kind_two_label="Scopes",
    ref_slug="build-the-query-parser",
    third="job",
    third_prefix="JOB",
    third_folder="jobs",
    third_title="Review the query parser",
    kind="action",
    kind_prefix="AC",
    kind_plural="actions",
    target_kind="outcome",
    target_prefix="OC",
    target_plural="outcomes",
    third_kind="action",
    third_kind_prefix="AC",
    third_kind_plural="actions",
    third_field="impact",
    third_value="large",
    third_other_value="small",
    badge="work_size",
    badge_flag="--work-size",
    no_badge_flag="--no-work-size",
    badge_codes="s, m, l",
    badge_value="m",
    badge_other_value="l",
    initial="Draft",
    moved="Ready",
    kind_initial="Todo",
    kind_moved="InProgress",
)

PROFILES: dict[str, Profile] = {BUNDLED.squad: BUNDLED, OVERRIDE.squad: OVERRIDE}


def selected() -> Profile:
    """The profile of the squad this run is on."""
    return PROFILES[os.environ.get("SQUADS_TEST_SQUAD", BUNDLED.squad)]
