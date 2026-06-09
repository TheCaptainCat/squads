"""Project configuration, persisted as ``.squads.toml`` at the project root."""

from typing import Any

from pydantic import BaseModel

from squads._models._schema import SCHEMA_VERSION
from squads._util import NonEmpty


class SquadsConfig(BaseModel):
    schema_version: NonEmpty = SCHEMA_VERSION
    #: Folder (relative to the project root) that holds the squad's content + .squads.json.
    squad_dir: NonEmpty = "squads"
    default_backend: NonEmpty = "claude_code"
    #: Role slug impersonated when the operator names no agent.
    default_role: NonEmpty = "manager"
    #: squads version that last generated the managed (tool-owned) files.
    squads_version: NonEmpty = "0.0.0"

    model_config = {"extra": "ignore"}

    def to_toml(self) -> str:
        lines = [
            "# squads project configuration",
            f'schema_version = "{self.schema_version}"',
            f'squad_dir = "{self.squad_dir}"',
            f'default_backend = "{self.default_backend}"',
            f'default_role = "{self.default_role}"',
            f'squads_version = "{self.squads_version}"',
            "",
        ]
        return "\n".join(lines)

    @classmethod
    def from_toml_dict(cls, data: dict[str, Any]) -> SquadsConfig:
        return cls.model_validate(data)


CONFIG_FILENAME = ".squads.toml"
INDEX_FILENAME = ".squads.json"
LOCK_FILENAME = ".squads.json.lock"
