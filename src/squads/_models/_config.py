"""Project configuration, persisted as ``.squads.toml`` at the project root."""

from typing import Any, cast

from pydantic import BaseModel, Field, field_validator

from squads._models._schema import SCHEMA_VERSION
from squads._util import NonEmpty


def _dedup_preserving_order(items: list[str]) -> list[str]:
    """Deduplicate a list preserving first-occurrence order."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


class SquadsConfig(BaseModel):
    schema_version: NonEmpty = SCHEMA_VERSION
    #: Folder (relative to the project root) that holds the squad's content + .squads.json.
    squad_dir: NonEmpty = "squads"
    #: Active agent backends (ordered list; duplicates silently collapsed on read).
    active_backends: list[str] = Field(default_factory=lambda: ["claude_code"])
    #: Role slug impersonated when the operator names no agent.
    default_role: NonEmpty = "manager"
    #: squads version that last generated the managed (tool-owned) files.
    squads_version: NonEmpty = "0.0.0"
    #: Optional mapping of role slug → full name, seeded at ``sq init``.
    #: Written under ``[init.names]`` in the TOML.
    init_names: dict[str, str] = Field(default_factory=dict)

    model_config = {"extra": "ignore"}

    @field_validator("active_backends", mode="after")
    @classmethod
    def _dedup_active_backends(cls, v: list[str]) -> list[str]:
        """Collapse duplicate backend names, preserving first-occurrence order."""
        return _dedup_preserving_order(v)

    def to_toml(self) -> str:
        backends_toml = "[" + ", ".join(f'"{b}"' for b in self.active_backends) + "]"
        lines = [
            "# squads project configuration",
            f'schema_version = "{self.schema_version}"',
            f'squad_dir = "{self.squad_dir}"',
            f"active_backends = {backends_toml}",
            f'default_role = "{self.default_role}"',
            f'squads_version = "{self.squads_version}"',
            "",
        ]
        if self.init_names:
            lines.append("[init.names]")
            for slug, name in sorted(self.init_names.items()):
                # Escape backslashes and double-quotes for basic TOML string safety.
                safe_name = name.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{slug} = "{safe_name}"')
            lines.append("")
        return "\n".join(lines)

    @classmethod
    def from_toml_dict(cls, data: dict[str, Any]) -> SquadsConfig:
        # Hoist the [init.names] nested table into init_names for validation.
        flat: dict[str, Any] = dict(data)
        init_section: Any = flat.pop("init", None)
        if isinstance(init_section, dict):
            init_as_str_any = cast("dict[str, Any]", init_section)
            names: Any = init_as_str_any.get("names")
            if isinstance(names, dict):
                flat["init_names"] = names
        # Back-compat: translate legacy default_backend → active_backends on read.
        # No migration is needed — the read itself is tolerant of the old field.
        if "active_backends" not in flat:
            legacy: Any = flat.pop("default_backend", None)
            if isinstance(legacy, str) and legacy:
                flat["active_backends"] = [legacy]
            else:
                flat["active_backends"] = ["claude_code"]
        else:
            flat.pop("default_backend", None)  # discard if both somehow present
        return cls.model_validate(flat)


CONFIG_FILENAME = ".squads.toml"
INDEX_FILENAME = ".squads.json"
LOCK_FILENAME = ".squads.json.lock"
