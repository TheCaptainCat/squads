"""Project configuration, persisted as ``.squads.toml`` at the project root."""

import re
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


class DisplaySettings(BaseModel):
    """The ``[display]`` table: presentation preferences for sq's own human renderers.

    A key belongs here only if changing it alters nothing but what those renderers print: never
    stored data, ``--json``, exit codes or generated files. Every key is a boolean.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: Print ``Name (pronouns)`` wherever a role or operator name carries pronouns.
    pronouns: bool = True


def parse_display(raw: Any) -> tuple[DisplaySettings, list[str]]:
    """The settings *raw* declares, with a problem for each part that is not usable.

    Never raises: an unknown key, a value that is not ``true`` or ``false`` (a quoted
    ``"false"`` is a string) or a ``[display]`` that is not a table falls back to the default
    and is returned as a problem for ``sq check`` to report.
    """
    if not isinstance(raw, dict):
        return DisplaySettings(), [f"[display] must be a table, got {type(raw).__name__}"]
    table = cast("dict[str, Any]", raw)
    usable: dict[str, bool] = {}
    problems: list[str] = []
    for key, value in table.items():
        if key not in DisplaySettings.model_fields:
            problems.append(f"[display] has an unknown key {key!r}")
        elif not isinstance(value, bool):
            problems.append(f"[display] {key} must be true or false, got {value!r}")
        else:
            usable[key] = value
    return DisplaySettings(**usable), problems


_BARE_KEY = re.compile(r"[A-Za-z0-9_-]+")


def _toml_escape(value: str) -> str:
    """*value* made safe inside a TOML basic string (backslashes and double quotes)."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


class SquadsConfig(BaseModel):
    schema_version: NonEmpty = SCHEMA_VERSION
    #: Folder (relative to the project root) that holds the squad's content + .squads.json.
    squad_dir: NonEmpty = "squads"
    #: Active agent backends (ordered list; duplicates silently collapsed on read).
    active_backends: list[str] = Field(default_factory=lambda: ["claude_code"])
    #: Optional mapping of role slug → full name, seeded at ``sq init``.
    #: Written under ``[init.names]`` in the TOML.
    init_names: dict[str, str] = Field(default_factory=dict)
    #: The ``working_language`` value as read: a language tag when usable, ``None`` when the key
    #: is absent, any other TOML value kept as read so it reads as unusable.
    working_language: Any = None
    #: Presentation preferences of sq's human renderers; written under ``[display]``.
    display: DisplaySettings = Field(default_factory=DisplaySettings)
    #: What was unusable in the ``[display]`` table that was read; never written back.
    display_problems: list[str] = Field(default_factory=list[str], exclude=True)

    model_config = {"extra": "ignore"}

    @model_validator(mode="before")
    @classmethod
    def _tolerate_display(cls, data: Any) -> Any:
        """Read ``display`` without ever failing: the unusable parts fall back to defaults and
        are recorded in ``display_problems``."""
        if not isinstance(data, dict):
            return data
        # The problems are derived from `display`, never read from the file.
        table = {k: v for k, v in cast("dict[str, Any]", data).items() if k != "display_problems"}
        if "display" not in table or isinstance(table["display"], DisplaySettings):
            return table
        settings, problems = parse_display(table["display"])
        return {**table, "display": settings, "display_problems": problems}

    @field_validator("active_backends", mode="after")
    @classmethod
    def _dedup_active_backends(cls, v: list[str]) -> list[str]:
        """Collapse duplicate backend names, preserving first-occurrence order."""
        return _dedup_preserving_order(v)

    def to_toml(self) -> str:
        backends_toml = "[" + ", ".join(f'"{_toml_escape(b)}"' for b in self.active_backends) + "]"
        lines = [
            "# squads project configuration",
            f'schema_version = "{self.schema_version}"',
            f'squad_dir = "{_toml_escape(self.squad_dir)}"',
            f"active_backends = {backends_toml}",
        ]
        if isinstance(self.working_language, str):
            lines.append(f'working_language = "{_toml_escape(self.working_language)}"')
        lines.append("")
        if self.display != DisplaySettings():
            lines.append("[display]")
            lines.extend(f"{k} = {str(v).lower()}" for k, v in self.display.model_dump().items())
            lines.append("")
        if self.init_names:
            lines.append("[init.names]")
            for slug, name in sorted(self.init_names.items()):
                # Escape backslashes and double-quotes for basic TOML string safety.
                safe_name = _toml_escape(name)
                key = slug if _BARE_KEY.fullmatch(slug) else f'"{_toml_escape(slug)}"'
                lines.append(f'{key} = "{safe_name}"')
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
