"""Load the bundled ``sources.toml`` and merge a project's ``.overrides/sources.toml`` over it.

The document is read and merged by the shared engine, then built and validated against the
workflow spec the squad resolved: every failure is collected and reported together, each naming
the source, the map and the value.
"""

from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from squads._errors import SquadsError
from squads._models._participants import is_valid_slug
from squads._sources._converters import CONVERTERS
from squads._sources._filter import Expression, FilterSyntaxError, parse_expression
from squads._sources._registry import CONNECTORS
from squads._sources._spec import (
    ConnectorDefaults,
    SourceMaps,
    SourceScope,
    SourceSpec,
    SourcesSpec,
)
from squads._specload import (
    OverrideFiles,
    OverrideMessages,
    SpecDocument,
    bundled_raw,
    bundled_text,
    load_override,
)
from squads._specmerge import RawMapping, describe_spec_error
from squads._workflow._models import WorkflowSpec

#: Canonical location for the project sources override (relative to squad_dir).
SOURCES_OVERRIDE_FILENAME = ".overrides/sources.toml"

SOURCES_TOP_LEVEL_KEYS: frozenset[str] = frozenset({"connectors", "sources"})
SOURCES_SELECTED_SECTIONS: frozenset[str] = frozenset({"connectors", "sources"})

#: Every scope key any connector version declares; a source table holds these apart from its other
#: keys so a key of another connector is reported as a scope fault, not as an unknown key.
_SCOPE_KEYS: frozenset[str] = frozenset(
    key for entry in CONNECTORS.values() for key in entry.scope_keys
)

SOURCES_OVERRIDE_MESSAGES = OverrideMessages(
    malformed="malformed sources override {path}: {exc}",
    unreadable="cannot read sources override {path}: {exc}",
    not_utf8="sources override {path} is not valid UTF-8; save it as UTF-8 and re-run.",
)


class _Declaration(BaseModel):
    """A ``[sources.<name>]`` table as written, before the connector's defaults are applied."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    connector: str
    version: str | None = None
    base_url: str
    #: The ``filter`` table as written; its shape is checked against the connector version.
    filter: Any = None
    trusted: bool = False
    enabled: bool = True
    converter: str | None = None
    maps: SourceMaps = Field(default_factory=SourceMaps)


def _check_override_shape(raw: RawMapping, origin: str) -> None:
    for key in ("connectors", "sources"):
        if key in raw and not isinstance(raw[key], dict):
            raise SquadsError(f"{origin}: '{key}' must be a table, got {type(raw[key]).__name__}")


_DOCUMENT = SpecDocument(
    bundled_file="sources.toml",
    override_file=SOURCES_OVERRIDE_FILENAME,
    override_name="sources override",
    top_level_keys=SOURCES_TOP_LEVEL_KEYS,
    selected_sections=SOURCES_SELECTED_SECTIONS,
    messages=SOURCES_OVERRIDE_MESSAGES,
    check_override=_check_override_shape,
)


def bundled_sources_raw() -> RawMapping:
    """A copy of the packaged document's parse, for the shadowing test of a stamp finding."""
    return bundled_raw(_DOCUMENT)


def bundled_sources_toml_text() -> str:
    """The bundled ``sources.toml``'s raw text, the baseline ``sq override diff`` compares to."""
    return bundled_text(_DOCUMENT)


def _versions_of(connector: str) -> list[str]:
    return sorted(version for name, version in CONNECTORS if name == connector)


def _connector_problems(name: str, decl: _Declaration) -> tuple[str | None, list[str]]:
    """The version *decl* resolves to, and what is wrong with its connector and version."""
    known = _versions_of(decl.connector)
    if not known:
        names = ", ".join(sorted({c for c, _ in CONNECTORS}))
        return None, [f"source {name!r}: connector {decl.connector!r} is unknown (known: {names})"]
    if decl.version is None:
        if len(known) == 1:
            return known[0], []
        listed = ", ".join(known)
        return None, [
            f"source {name!r}: connector {decl.connector!r} has several versions, so `version` "
            f"is required (known: {listed})"
        ]
    if decl.version not in known:
        listed = ", ".join(known)
        return None, [
            f"source {name!r}: connector {decl.connector!r} has no version {decl.version!r} "
            f"(known: {listed})"
        ]
    return decl.version, []


def _overlay(base: dict[str, str], own: dict[str, str]) -> dict[str, str]:
    """*base* with *own* laid over it key by key; an entry set to ``""`` unmaps its key."""
    return {key: value for key, value in {**base, **own}.items() if value != ""}


def _overlay_sides(
    base: dict[str, dict[str, str]], own: dict[str, dict[str, str]]
) -> dict[str, dict[str, str]]:
    """*base* with *own* laid over it side by side and key by key."""
    merged = {side: _overlay(base.get(side, {}), own.get(side, {})) for side in {*base, *own}}
    return {side: table for side, table in merged.items() if table}


def _side_problems(where: str, maps: SourceMaps, known: tuple[str, ...]) -> list[str]:
    """The sides *maps* reads that the connector version does not expose."""
    used = {*maps.types, *(side for sides in maps.fields.values() for side in sides)}
    return [
        f"{where}: maps name the side {side!r}, which the connector does not have "
        f"(known: {', '.join(known)})"
        for side in sorted(used - set(known))
    ]


def _inherited(declared: dict[str, str], key: str) -> str:
    """The note on a map entry that the source did not write itself."""
    return "" if key in declared else " (inherited from the connector's defaults)"


def _type_problems(name: str, maps: SourceMaps, own: SourceMaps, spec: WorkflowSpec) -> list[str]:
    problems: list[str] = []
    types = set(spec.non_roster_types())
    for side, table in maps.types.items():
        for key, value in table.items():
            if value not in types:
                problems.append(
                    f"source {name!r}: maps.types.{side}: {key!r} -> {value!r} is not an item type"
                    f"{_inherited(own.types.get(side, {}), key)}"
                )
    return problems


def _field_problems(name: str, maps: SourceMaps, own: SourceMaps, spec: WorkflowSpec) -> list[str]:
    problems: list[str] = []
    declared: dict[str, set[str]] = {}
    for item_type in spec.items.values():
        for field in item_type.fields:
            declared.setdefault(field.code, set()).update(
                spec.collection(field.collection).badge_codes
            )
    for field_code, sides in maps.fields.items():
        if field_code not in declared:
            problems.append(
                f"source {name!r}: maps.fields.{field_code}: no item type has this field"
            )
            continue
        for side, table in sides.items():
            for key, value in table.items():
                if value not in declared[field_code]:
                    problems.append(
                        f"source {name!r}: maps.fields.{field_code}.{side}: {key!r} -> {value!r} "
                        f"is not a {field_code} value"
                        f"{_inherited(own.fields.get(field_code, {}).get(side, {}), key)}"
                    )
    return problems


def _map_problems(name: str, maps: SourceMaps, own: SourceMaps, spec: WorkflowSpec) -> list[str]:
    """What is wrong with the targets of *maps*, the overlay of *own* on the connector's defaults,
    in *spec*."""
    problems = [*_type_problems(name, maps, own, spec), *_field_problems(name, maps, own, spec)]
    for key, value in maps.links.items():
        if value not in spec.ref_kinds:
            problems.append(
                f"source {name!r}: maps.links: {key!r} -> {value!r} is not a ref kind"
                f"{_inherited(own.links, key)}"
            )
    return problems


def _scope_of(
    name: str, given: dict[str, Any], connector: str, version: str
) -> tuple[SourceScope | None, list[str]]:
    """The one scope *given* names for a source of ``connector@version``, or what is wrong."""
    keys = CONNECTORS[(connector, version)].scope_keys
    listed = ", ".join(keys)
    foreign = sorted(set(given) - set(keys))
    if foreign:
        return None, [
            f"source {name!r}: {key!r} is not a scope key of {connector}@{version} "
            f"(scope keys: {listed})"
            for key in foreign
        ]
    if len(given) != 1:
        found = "no scope key" if not given else f"{len(given)} scope keys ({', '.join(given)})"
        return None, [f"source {name!r}: {found}; name exactly one of: {listed}"]
    ((key, value),) = given.items()
    if not isinstance(value, str) or not value.strip():
        return None, [f"source {name!r}: scope key {key!r} must be a non-empty string"]
    return SourceScope(key=key, value=value), []


def _kind_of(value: Any) -> str:
    """What a TOML value is, as a message names it."""
    return "a string" if isinstance(value, str) else f"a {type(value).__name__}"


def _filter_of(
    name: str, raw: Any, connector: str, version: str
) -> tuple[dict[str, Expression], list[str]]:
    """The parsed ``filter`` table of a source of ``connector@version``, or what is wrong."""
    if raw is None:
        return {}, []
    entry = CONNECTORS[(connector, version)]
    sides = ", ".join(entry.sides)
    if not isinstance(raw, dict):
        return {}, [
            f"source {name!r}: sources.{name}.filter is a table of one expression per side "
            f"(sides: {sides}), not {_kind_of(raw)}; the issues a source follows are "
            f"named by its scope, one of: {', '.join(entry.scope_keys)}"
        ]
    if not raw:
        return {}, [
            f"source {name!r}: sources.{name}.filter is an empty table; write a side ({sides}) "
            "or remove it"
        ]
    parsed: dict[str, Expression] = {}
    problems: list[str] = []
    for side, text in cast("dict[str, Any]", raw).items():
        where = f"source {name!r}: sources.{name}.filter.{side}"
        if side not in entry.sides:
            problems.append(f"{where}: the connector has no side {side!r} (sides: {sides})")
        elif not isinstance(text, str):
            problems.append(f"{where}: must be a string holding one expression")
        elif not text.strip(" \t\r\n"):
            problems.append(f"{where}: the expression is empty")
        else:
            try:
                parsed[side] = parse_expression(text)
            except FilterSyntaxError as exc:
                problems.append(f"{where}: {exc}")
    return parsed, problems


def _resolve(
    name: str,
    decl: _Declaration,
    scope_keys: dict[str, Any],
    defaults_by_key: dict[str, ConnectorDefaults],
    spec: WorkflowSpec,
) -> tuple[SourceSpec | None, list[str]]:
    problems: list[str] = []
    if not is_valid_slug(name):
        problems.append(f"source {name!r}: the name is not a slug (lowercase letters, digits, -)")
    if not decl.base_url.startswith(("http://", "https://")) or "//" not in decl.base_url:
        problems.append(f"source {name!r}: base_url {decl.base_url!r} is not an http(s) address")
    version, found = _connector_problems(name, decl)
    problems.extend(found)
    if version is None:
        return None, problems
    defaults = defaults_by_key.get(f"{decl.connector}@{version}", ConnectorDefaults())
    converter = (
        decl.converter
        or defaults.converter
        or CONNECTORS[(decl.connector, version)].default_converter
    )
    if converter not in CONVERTERS:
        known = ", ".join(sorted(CONVERTERS))
        problems.append(f"source {name!r}: converter {converter!r} is unknown (known: {known})")
    scope, found = _scope_of(name, scope_keys, decl.connector, version)
    problems.extend(found)
    selection, found = _filter_of(name, decl.filter, decl.connector, version)
    problems.extend(found)
    problems.extend(
        _side_problems(f"source {name!r}", decl.maps, CONNECTORS[(decl.connector, version)].sides)
    )
    maps = SourceMaps(
        types=_overlay_sides(defaults.maps.types, decl.maps.types),
        fields={
            field: _overlay_sides(
                defaults.maps.fields.get(field, {}), decl.maps.fields.get(field, {})
            )
            for field in {*defaults.maps.fields, *decl.maps.fields}
        },
        links=_overlay(defaults.maps.links, decl.maps.links),
    )
    if not maps.types:
        problems.append(
            f"source {name!r}: maps.types is empty; map at least one tracker type or label to an "
            "item type"
        )
    problems.extend(_map_problems(name, maps, decl.maps, spec))
    if problems or scope is None:
        return None, problems
    resolved = SourceSpec(
        name=name,
        connector=decl.connector,
        version=version,
        base_url=decl.base_url,
        scope=scope,
        filter=selection,
        trusted=decl.trusted,
        enabled=decl.enabled,
        converter=converter,
        maps=maps,
    )
    return resolved, []


def _parse[M: BaseModel](model: type[M], raw: Any, where: str) -> tuple[M | None, list[str]]:
    try:
        return model.model_validate(raw), []
    except ValidationError as exc:
        return None, [f"{where}: {describe_spec_error(exc, model)}"]


def _connector_defaults(
    raw: RawMapping,
) -> tuple[dict[str, ConnectorDefaults], list[str]]:
    """The defaults of each ``[connectors.<name>.<version>]`` table, keyed ``<name>@<version>``."""
    found: dict[str, ConnectorDefaults] = {}
    problems: list[str] = []
    for name, versions in cast("dict[str, Any]", raw.get("connectors", {})).items():
        if not isinstance(versions, dict):
            problems.append(f"connectors.{name}: must hold one table per version")
            continue
        for version, table in cast("dict[str, Any]", versions).items():
            where = f"connectors.{name}.{version}"
            if (name, version) not in CONNECTORS:
                problems.append(
                    f"{where}: no connector {name!r} has version {version!r} registered"
                )
                continue
            defaults, errors = _parse(ConnectorDefaults, table, where)
            problems.extend(errors)
            if defaults is not None:
                problems.extend(
                    _side_problems(where, defaults.maps, CONNECTORS[(name, version)].sides)
                )
                if defaults.converter and defaults.converter not in CONVERTERS:
                    problems.append(f"{where}: converter {defaults.converter!r} is unknown")
                found[f"{name}@{version}"] = defaults
    return found, problems


def _side_shape_problems(name: str, table: Any) -> list[str]:
    """The map entries of a ``[sources.<name>]`` table written as a value where a side is due."""
    if not isinstance(table, dict):
        return []
    maps = cast("dict[str, Any]", table).get("maps")
    if not isinstance(maps, dict):
        return []
    found = cast("dict[str, Any]", maps)
    known = _known_sides(cast("dict[str, Any]", table))
    sides = f"one of: {', '.join(known)}" if known else "a side of the connector"
    entries: list[str] = []
    types = found.get("types")
    if isinstance(types, dict):
        entries += [
            f"maps.types.{key}"
            for key, v in cast("dict[str, Any]", types).items()
            if not isinstance(v, dict)
        ]
    fields = found.get("fields")
    if isinstance(fields, dict):
        for code, by_side in cast("dict[str, Any]", fields).items():
            if not isinstance(by_side, dict):
                continue
            entries += [
                f"maps.fields.{code}.{key}"
                for key, v in cast("dict[str, Any]", by_side).items()
                if not isinstance(v, dict)
            ]
    return [
        f"source {name!r}: {entry} is a value, not a side: write it under {entry.rsplit('.', 1)[0]}"
        f".<side>, {sides}"
        for entry in entries
    ]


def _known_sides(table: dict[str, Any]) -> tuple[str, ...]:
    """The sides of the connector version *table* names, when it names one that is known."""
    connector, version = table.get("connector"), table.get("version")
    if not isinstance(connector, str):
        return ()
    versions = _versions_of(connector)
    if isinstance(version, str) and (connector, version) in CONNECTORS:
        return CONNECTORS[(connector, version)].sides
    if version is None and len(versions) == 1:
        return CONNECTORS[(connector, versions[0])].sides
    return ()


def _scope_part(table: Any) -> dict[str, Any]:
    """The scope keys of a ``[sources.<name>]`` table."""
    if not isinstance(table, dict):
        return {}
    return {k: v for k, v in cast("dict[str, Any]", table).items() if k in _SCOPE_KEYS}


def _without_scope(table: Any) -> Any:
    """The ``[sources.<name>]`` table without its scope keys."""
    if not isinstance(table, dict):
        return table
    return {k: v for k, v in cast("dict[str, Any]", table).items() if k not in _SCOPE_KEYS}


def _build(raw: RawMapping, spec: WorkflowSpec, prefix: str) -> SourcesSpec:
    connectors, problems = _connector_defaults(raw)
    sources: dict[str, SourceSpec] = {}
    for name, table in cast("dict[str, Any]", raw.get("sources", {})).items():
        shape = _side_shape_problems(name, table)
        if shape:
            problems.extend(shape)
            continue
        scope_keys = _scope_part(table)
        decl, errors = _parse(_Declaration, _without_scope(table), f"source {name!r}")
        problems.extend(errors)
        if decl is None:
            continue
        resolved, found = _resolve(name, decl, scope_keys, connectors, spec)
        problems.extend(found)
        if resolved is not None:
            sources[name] = resolved
    if problems:
        raise SquadsError(prefix + ":\n  " + "\n  ".join(problems))
    return SourcesSpec(connectors=connectors, sources=sources)


def load_sources(
    spec: WorkflowSpec, squad_dir: Path | None = None, files: OverrideFiles | None = None
) -> SourcesSpec:
    """The sources document merged for *squad_dir* and validated against *spec*. Raises
    ``SquadsError`` listing every problem, naming the file at fault."""
    raw = bundled_raw(_DOCUMENT)
    loaded = load_override(_DOCUMENT, squad_dir, lambda: raw, files)
    if loaded is None:
        return _build(raw, spec, "Invalid bundled sources.toml")
    return _build(loaded.raw, spec, f"{loaded.origin}: invalid sources after merge")
