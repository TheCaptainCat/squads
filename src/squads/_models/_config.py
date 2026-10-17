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


_HEADER_RE = re.compile(r"^[ \t]*\[\[?[ \t]*([^\]]*?)[ \t]*\]\]?")
_TOP_DISPLAY_RE = re.compile(r"^[ \t]*display[ \t]*[.=]")


def _is_display_header(line: str) -> bool | None:
    """Whether *line* is a table header of ``display`` (or below it); ``None`` for a non-header."""
    m = _HEADER_RE.match(line)
    if m is None:
        return None
    name = m.group(1).replace(" ", "")
    return name == "display" or name.startswith("display.")


def _display_source(text: str) -> tuple[str, str | None]:
    """The text of *text*'s ``display`` declaration, verbatim: ``(top-level lines, table text)``.

    The table text starts at the whitespace that separated it from the content above and ends
    with its last line, so putting it back after the rest of the file restores its bytes.
    """
    lines = text.splitlines(keepends=True)
    first_header = next((i for i, ln in enumerate(lines) if _HEADER_RE.match(ln)), len(lines))
    top: list[str] = []
    pending: list[str] = []
    for ln in lines[:first_header]:
        if _TOP_DISPLAY_RE.match(ln):
            top += [*pending, ln if ln.endswith("\n") else ln + "\n"]
            pending = []
        elif not ln.strip():
            pending.append(ln)
        else:
            pending = []
    start = next((i for i, ln in enumerate(lines) if _is_display_header(ln)), None)
    if start is None:
        return "".join(top), None
    end = start + 1
    while end < len(lines) and _is_display_header(lines[end]) in (None, True):
        end += 1
    body = lines[start:end]
    while len(body) > 1 and not body[-1].strip():
        body.pop()
    above = "".join(lines[:start]).rstrip()
    lead = "".join(lines[:start])[len(above) :]
    if not body[-1].endswith("\n") and end < len(lines):
        body[-1] += "\n"
    return "".join(top), lead + "".join(body)


class SquadsConfig(BaseModel):
    schema_version: NonEmpty = SCHEMA_VERSION
    #: Folder (relative to the project root) that holds the squad's content + .squads.json.
    squad_dir: NonEmpty = "squads"
    #: Active agent backends (ordered list; duplicates silently collapsed on read).
    active_backends: list[str] = Field(default_factory=lambda: ["claude_code"])
    #: squads version that last generated the managed (tool-owned) files.
    squads_version: NonEmpty = "0.0.0"
    #: Optional mapping of role slug → full name, seeded at ``sq init``.
    #: Written under ``[init.names]`` in the TOML.
    init_names: dict[str, str] = Field(default_factory=dict)
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
        backends_toml = "[" + ", ".join(f'"{b}"' for b in self.active_backends) + "]"
        lines = [
            "# squads project configuration",
            f'schema_version = "{self.schema_version}"',
            f'squad_dir = "{self.squad_dir}"',
            f"active_backends = {backends_toml}",
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

    def to_toml_keeping(self, original: str) -> str:
        """:meth:`to_toml`, with the ``display`` the *original* file text declares carried over
        exactly as written: a stamp never changes what the user wrote there, whether it is a
        default, an unusable value or an unknown key."""
        base = self.to_toml().rstrip("\n")
        top, section = _display_source(original)
        if top:
            marker = f'squads_version = "{self.squads_version}"'
            base = base.replace(marker, marker + "\n" + top.removesuffix("\n"), 1)
        if section is None:
            return base + "\n"
        return base + ("" if section.startswith("\n") else "\n\n") + section

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
