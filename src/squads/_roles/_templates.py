"""Role templates: the placeholder grammar of a ``[templates.<name>]`` table and its
instantiation into a role.

Exactly three placeholders exist: ``{tech}`` (the value given to ``--tech``), ``{Tech}`` (the
same with its first letter upper-cased) and ``{first}`` (a ``name_pool`` entry, valid in ``name``
only). ``{{`` and ``}}`` escape a literal brace. In ``slug`` the substituted values are
slugified.
"""

import re
from collections.abc import Callable

from squads._roles._models import RoleTemplateSpec
from squads._util import slugify

PARAMETER_PLACEHOLDERS: tuple[str, ...] = ("tech", "Tech")
NAME_PLACEHOLDER = "first"

#: The template keys whose text may carry placeholders, with ``name`` the only one allowed
#: ``{first}``.
_TEXT_KEYS: tuple[str, ...] = ("slug", "name", "title", "description", "mission")
_TEXT_LIST_KEYS: tuple[str, ...] = ("responsibilities", "agreements")

_TOKEN = re.compile(r"\{\{|\}\}|\{([^{}]*)\}|[{}]")


def placeholders(text: str) -> list[str]:
    """The placeholder names *text* uses, in order, and each stray brace as ``"{"`` / ``"}"``.
    An escaped brace is not a placeholder."""
    found: list[str] = []
    for match in _TOKEN.finditer(text):
        token = match.group(0)
        if token in ("{{", "}}"):
            continue
        found.append(match.group(1) if match.group(1) is not None else token)
    return found


def _allowed(key: str) -> tuple[str, ...]:
    return (*PARAMETER_PLACEHOLDERS, NAME_PLACEHOLDER) if key == "name" else PARAMETER_PLACEHOLDERS


def _text_entries(template: RoleTemplateSpec) -> list[tuple[str, str]]:
    """Every ``(key, text)`` of *template* that may carry placeholders, list entries keyed
    ``responsibilities[0]``."""
    entries: list[tuple[str, str]] = []
    for key in _TEXT_KEYS:
        value: str | None = getattr(template, key)
        if value is not None:
            entries.append((key, value))
    for key in _TEXT_LIST_KEYS:
        entries.extend((f"{key}[{i}]", v) for i, v in enumerate(getattr(template, key)))
    return entries


def placeholder_problems(template: RoleTemplateSpec) -> list[str]:
    """One sentence per placeholder *template* may not use, each naming its key."""
    problems: list[str] = []
    for key, text in _text_entries(template):
        base_key = key.split("[", 1)[0]
        allowed = _allowed(base_key)
        for name in placeholders(text):
            if name in allowed:
                continue
            if name in ("{", "}"):
                problems.append(f"{key}: unbalanced brace {name!r}; write {name * 2!r} for a brace")
            elif name == NAME_PLACEHOLDER:
                problems.append(f"{key}: {{first}} is valid in `name` only")
            else:
                problems.append(
                    f"{key}: unknown placeholder {{{name}}}; the placeholders are "
                    "{tech}, {Tech}, and {first} in `name`"
                )
    return problems


def takes_parameter(template: RoleTemplateSpec) -> bool:
    """Whether *template* uses ``{tech}`` or ``{Tech}`` anywhere, so activation needs ``--tech``."""
    return any(
        name in PARAMETER_PLACEHOLDERS
        for _, text in _text_entries(template)
        for name in placeholders(text)
    )


def substitute(text: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        if token == "{{":
            return "{"
        if token == "}}":
            return "}"
        return values[match.group(1)]

    return _TOKEN.sub(replace, text)


def parameter_values(
    tech: str | None, *, slugifier: Callable[[str], str] | None = None
) -> dict[str, str]:
    """The ``{tech}`` / ``{Tech}`` values for *tech*, each passed through *slugifier* when given."""
    label = (tech or "").strip()
    upper = label[:1].upper() + label[1:]
    if slugifier is not None:
        return {"tech": slugifier(label), "Tech": slugifier(upper)}
    return {"tech": label, "Tech": upper}


def proposed_slug(
    template: RoleTemplateSpec,
    tech: str | None,
    *,
    slugifier: Callable[[str], str] | None = None,
) -> str | None:
    """The slug the template's pattern proposes, ``None`` when it declares no ``slug``."""
    if template.slug is None:
        return None
    return substitute(template.slug, parameter_values(tech, slugifier=slugifier or slugify))


def proposed_name(template: RoleTemplateSpec, tech: str | None, position: int) -> str | None:
    """The name the template's pattern gives, ``{first}`` drawn from ``name_pool`` at
    *position* (wrapping); ``None`` when it declares no ``name``."""
    if template.name is None:
        return None
    values = parameter_values(tech)
    if template.name_pool:
        values[NAME_PLACEHOLDER] = template.name_pool[position % len(template.name_pool)]
    return substitute(template.name, values)
