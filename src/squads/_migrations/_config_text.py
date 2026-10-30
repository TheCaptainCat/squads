"""The ``.squads.toml`` text a migration writes: a verified one-value schema edit, or a
regeneration when the file carries the keys an older release wrote."""

import math
import re
import tomllib
from dataclasses import dataclass
from typing import Any, cast

from pydantic import ValidationError

from squads._endpoint import parse_daemon
from squads._errors import SquadsError
from squads._models._config import DisplaySettings, SquadsConfig

_LEGACY_KEYS = ("default_backend", "default_role")
_CARRIED_KEYS = frozenset(SquadsConfig.model_fields) - {
    "init_names",
    "display_problems",
    "daemon_problems",
}
_KEY = re.compile(r"^[ \t]*[\"']?schema_version[\"']?[ \t]*=")
_STAMP = re.compile(
    r"^([ \t]*([\"']?)schema_version\2[ \t]*=[ \t]*)(\"[^\"\\\n]*\"|'[^'\n]*')([ \t]*(?:#.*)?)$"
)


@dataclass(frozen=True)
class ConfigRewrite:
    """The text to write to ``.squads.toml`` and the keys the write drops."""

    text: str
    dropped: tuple[str, ...] = ()


def _uncarried(table: dict[str, Any]) -> tuple[str, ...]:
    """The keys of *table* that the regenerated file cannot hold: top-level keys, ``init`` keys,
    an ``init.names`` that is not a table, and the ``[display]`` entries squads does not read."""
    keys = [k for k in table if k not in _CARRIED_KEYS and k not in {"init", *_LEGACY_KEYS}]
    init = table.get("init")
    if isinstance(init, dict):
        init_table = cast("dict[str, Any]", init)
        keys += [f"init.{k}" for k in init_table if k != "names"]
        if "names" in init_table and not isinstance(init_table["names"], dict):
            keys.append("init.names")
    elif "init" in table:
        keys.append("init")
    display = table.get("display")
    if isinstance(display, dict):
        keys += [
            f"display.{k}"
            for k, v in cast("dict[str, Any]", display).items()
            if k not in DisplaySettings.model_fields or not isinstance(v, bool)
        ]
    elif "display" in table:
        keys.append("display")
    if "daemon" in table:
        keys += [f"daemon.{p.key}" if p.key else "daemon" for p in parse_daemon(table["daemon"])[1]]
    return tuple(keys)


def _same(a: object, b: object) -> bool:
    """Whether two parsed TOML values are equal, a ``nan`` equal to a ``nan``."""
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return True
    if isinstance(a, dict) and isinstance(b, dict):
        da, db = cast("dict[str, Any]", a), cast("dict[str, Any]", b)
        return da.keys() == db.keys() and all(_same(da[k], db[k]) for k in da)
    if isinstance(a, list) and isinstance(b, list):
        la, lb = cast("list[Any]", a), cast("list[Any]", b)
        return len(la) == len(lb) and all(_same(x, y) for x, y in zip(la, lb, strict=True))
    return type(a) is type(b) and a == b  # pyright: ignore[reportUnknownArgumentType]


def _regenerated(table: dict[str, Any], schema: str, name: str) -> ConfigRewrite:
    """The whole file rebuilt from the model, refused unless it reads back to the same config."""
    text = ""
    try:
        config = SquadsConfig.from_toml_dict(table).model_copy(update={"schema_version": schema})
        text = config.to_toml()
        same = SquadsConfig.from_toml_dict(tomllib.loads(text)).model_dump() == config.model_dump()
    except (tomllib.TOMLDecodeError, ValidationError):  # fmt: skip
        same = False
    if not same:
        raise SquadsError(
            f"{name} carries legacy keys and cannot be regenerated without changing a setting; "
            "remove `default_backend` and `default_role` by hand, then re-run `sq migrate up`"
        )
    return ConfigRewrite(text, _uncarried(table))


def _stamped(original: str, table: dict[str, Any], schema: str, name: str) -> ConfigRewrite:
    """*original* with the value of its one ``schema_version`` line set to *schema*. Each line
    that starts like the key is tried, and the one whose edit changes nothing but the parsed
    top-level ``schema_version`` is the line; none or several is a refusal."""
    lines = original.splitlines(keepends=True)
    current = table.get("schema_version")
    wanted = {**table, "schema_version": schema}
    candidates = [i for i, ln in enumerate(lines) if _KEY.match(ln)]
    instruction = (
        f'write `schema_version = "{current}"` on a single line, then re-run `sq migrate up`'
    )
    hits: list[str] = []
    for n in candidates:
        bare = lines[n].rstrip("\r\n")
        match = _STAMP.match(bare)
        if match is None or match.group(3)[1:-1] != current:
            continue
        quote = match.group(3)[0]
        edited = f"{match.group(1)}{quote}{schema}{quote}{match.group(4)}{lines[n][len(bare) :]}"
        text = "".join([*lines[:n], edited, *lines[n + 1 :]])
        try:
            if _same(tomllib.loads(text), wanted):
                hits.append(text)
        except tomllib.TOMLDecodeError:
            continue
    if len(hits) != 1:
        where = ", ".join(str(i + 1) for i in candidates) or "none"
        raise SquadsError(
            f"cannot edit the top-level schema_version of {name} (candidate lines: {where}); "
            + instruction
        )
    return ConfigRewrite(hits[0])


def plan_config_rewrite(original: str, schema: str, name: str) -> ConfigRewrite:
    """The ``.squads.toml`` text a migration to *schema* writes, or a :class:`SquadsError`
    naming *name* and what to change by hand. Nothing is written here."""
    try:
        table = tomllib.loads(original)
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(f"malformed {name}: {exc}") from exc
    if any(k in table for k in _LEGACY_KEYS):
        return _regenerated(table, schema, name)
    return _stamped(original, table, schema, name)
