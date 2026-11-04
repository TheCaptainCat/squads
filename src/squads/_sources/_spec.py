"""The resolved ``sources.toml``: the sources a squad declares and what each connector version
supplies by default."""

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from squads._errors import SquadsError


class SourceMaps(BaseModel):
    """How a tracker's types, field values and link types map onto the squad's vocabulary; types and
    field values are read from one named side of the issue at a time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: Tracker side to tracker value to item type.
    types: dict[str, dict[str, str]] = Field(default_factory=dict)
    #: Badge field to tracker side to tracker value to badge value.
    fields: dict[str, dict[str, dict[str, str]]] = Field(default_factory=dict)
    links: dict[str, str] = Field(default_factory=dict)


class SourceSpec(BaseModel):
    """A tracker a squad pulls issues from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    connector: str
    version: str
    base_url: str
    filter: str = ""
    trusted: bool = False
    enabled: bool = True
    converter: str = ""
    maps: SourceMaps = Field(default_factory=SourceMaps)


class ConnectorDefaults(BaseModel):
    """What a source of one connector version inherits: its converter and its maps."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    converter: str = ""
    maps: SourceMaps = Field(default_factory=SourceMaps)


class SourcesSpec(BaseModel):
    """The connector defaults and the sources a squad declares, each source fully resolved."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    connectors: dict[str, ConnectorDefaults] = Field(default_factory=dict)
    sources: dict[str, SourceSpec] = Field(default_factory=dict)

    def source(self, name: str) -> SourceSpec:
        """The source declared as *name*; an undeclared one is refused naming the declared ones."""
        found = self.sources.get(name)
        if found is None:
            declared = ", ".join(sorted(self.sources)) or "none"
            raise SquadsError(f"no source {name!r} is declared (declared: {declared})")
        return found


type SourcesSource = Callable[[], SourcesSpec]
