"""A sub-entity — a user story, subtask, or review finding — tracked on its parent item.

Its **machine state** (status / assignee / severity / mapped story) lives here, in the parent
item's frontmatter (single-sourced and validated, like every other item field). The sub-entity's
**prose** — its ``:body`` and ``:discussion`` — stays in the parent's markdown markers; the heading
and the derived ``:head`` badge line are re-rendered from this state.
"""

from typing import Any

from pydantic import BaseModel

from squads._models._enums import Severity, Status


class SubEntity(BaseModel):
    #: Local id within its parent, kind-prefixed: ``US1`` story / ``ST1`` subtask / ``F1`` finding.
    local_id: str
    title: str = ""
    status: Status
    #: Registered agent slug responsible for it (optional).
    assignee: str | None = None
    #: Findings only — the finding's severity.
    severity: Severity | None = None
    #: Subtasks only — the mapped user story's local id (e.g. ``US1``).
    story: str | None = None

    model_config = {"use_enum_values": False}

    def to_frontmatter_dict(self) -> dict[str, Any]:
        """The compact mapping written into the parent's ``subentities`` frontmatter list."""
        data: dict[str, Any] = {
            "local_id": self.local_id,
            "title": self.title,
            "status": self.status.value,
        }
        if self.assignee:
            data["assignee"] = self.assignee
        if self.severity:
            data["severity"] = self.severity.value
        if self.story:
            data["story"] = self.story
        return data

    @classmethod
    def from_frontmatter(cls, data: dict[str, Any]) -> SubEntity:
        return cls(
            local_id=data["local_id"],
            title=data.get("title", ""),
            status=Status(data["status"]),
            assignee=data.get("assignee"),
            severity=Severity(data["severity"]) if data.get("severity") else None,
            story=data.get("story"),
        )
