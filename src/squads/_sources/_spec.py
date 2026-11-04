"""The resolved ``sources.toml``: the sources a squad declares and what each connector version
supplies by default."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from squads._errors import SquadsError
from squads._sources._credentials import normalise_base_url
from squads._sources._filter import Expression

if TYPE_CHECKING:
    from squads._sources._connector import Issue


class SourceMaps(BaseModel):
    """How a tracker's types, field values and link types map onto the squad's vocabulary; types and
    field values are read from one named side of the issue at a time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: Tracker side to tracker value to item type.
    types: dict[str, dict[str, str]] = Field(default_factory=dict)
    #: Badge field to tracker side to tracker value to badge value.
    fields: dict[str, dict[str, dict[str, str]]] = Field(default_factory=dict)
    links: dict[str, str] = Field(default_factory=dict)


class SourceScope(BaseModel):
    """The part of a tracker a source follows: one scope key its connector version declares, and
    the project, group, repository or query it names."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    value: str


class SourceSpec(BaseModel):
    """A tracker a squad pulls issues from."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    name: str
    connector: str
    version: str
    base_url: str
    scope: SourceScope
    #: Tracker side to the parsed expression that side must satisfy; empty selects every issue.
    filter: dict[str, Expression] = Field(default_factory=dict)
    trusted: bool = False
    enabled: bool = True
    converter: str = ""
    maps: SourceMaps = Field(default_factory=SourceMaps)

    def accepts(self, issue: Issue) -> bool:
        """Whether *issue* passes the filter: every side it names is satisfied."""
        return all(expr.matches(issue.values(side)) for side, expr in self.filter.items())


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

    def peers(self, name: str) -> frozenset[str]:
        """The declared sources on the same tracker as *name* (its normalised base URL), itself
        included; empty when *name* is not declared."""
        own = self.sources.get(name)
        if own is None:
            return frozenset()
        url = normalise_base_url(own.base_url)
        return frozenset(
            n for n, s in self.sources.items() if normalise_base_url(s.base_url) == url
        )


type SourcesSource = Callable[[], SourcesSpec]
