"""Schema 0.16 → 0.17 runner. The 0.17 schema adds the Noted and Deferred finding states, which no
0.16 file can hold; the bump makes an older release stop at the schema gate with an upgrade message
once a squad is stamped 0.17. The runner also moves each role onto the base that now defines it: a
role storing ``tech`` is a developer and stores ``template: dev``; a catalog role or a
template-built role stores no ``description`` (it is resolved); a role no catalog declares whose
per-slug file loads as a complete role takes the file's definition into its own item (the file is
untouched and now layers over identical values); and a catalog role stores no ``model`` equal to the
one its definition resolves to (what earlier releases mirrored), a different model being an operator
setting that is kept and reported, so re-applying to a squad already at 0.17 is safe. A role whose
file does not load, and a role nothing backs, are listed in the report and never guessed into a
definition. It runs only through ``sq migrate up`` via ``_migrations._registry``.
"""

from pathlib import Path
from typing import Any, cast

from squads import _aio
from squads._errors import SquadsError
from squads._itemfile import read_frontmatter, write_text
from squads._migrations._context import MigrationContext
from squads._migrations._outcome import MigrationOutcome
from squads._models._attributes import AttributeKey
from squads._models._item import slug_from_stem
from squads._roles._catalog import RoleDef
from squads._roles._models import DEV_TEMPLATE_NAME
from squads._roles._resolver import resolve_role, role_defined_by_file
from squads._sections import replace_frontmatter
from squads._workflow._models import ROSTER_ROLE

MANUAL = (
    "Rename a `[dev]` table in `.overrides/roles.toml` to `[templates.dev]` before upgrading: "
    "`sq migrate up` refuses a squad whose role catalog still carries `[dev]`, and changes "
    "nothing. A role defined only by a per-slug file takes that definition into its own item; "
    "the file then layers over it, and `sq check` warns until you delete the file."
)
SUMMARY = (
    "Roles take their base into the item: developers store their template, custom roles their "
    "definition."
)

#: The definition keys a role that defines itself stores, as ``(attribute, RoleDef field)``.
_DEFINITION = (
    (AttributeKey.JOB_TITLE, "title"),
    (AttributeKey.MISSION, "mission"),
    (AttributeKey.RESPONSIBILITIES, "responsibilities"),
    (AttributeKey.AGREEMENTS, "agreements"),
    (AttributeKey.COLOR, "color"),
    (AttributeKey.CAN_SPAWN, "can_spawn"),
    (AttributeKey.CAPABILITIES, "capabilities"),
)


def _move_definition(data: dict[str, Any], role: RoleDef) -> None:
    """Write *role*'s definition into the frontmatter *data* of the item that now defines it."""
    data["description"] = role.description
    for key, field in _DEFINITION:
        value = getattr(role, field)
        if value:
            data[key] = list(cast("tuple[str, ...]", value)) if isinstance(value, tuple) else value
        else:
            data.pop(key, None)
    if role.model:
        data[AttributeKey.MODEL] = role.model
    else:
        data.pop(AttributeKey.MODEL, None)


def _migrated(
    ctx: MigrationContext, data: dict[str, Any], slug: str, report: list[str]
) -> dict[str, Any]:
    """*data* as the 0.17 shape stores it (the same mapping when nothing changes)."""
    out = dict(data)
    if out.get(AttributeKey.TEMPLATE):
        out.pop("description", None)
        return out
    if out.get(AttributeKey.MISSION):
        return out
    if out.get(AttributeKey.TECH):
        out[AttributeKey.TEMPLATE] = DEV_TEMPLATE_NAME
        out.pop("description", None)
        return out
    if any(r.slug == slug for r in ctx.catalog().roles):
        out.pop("description", None)
        _drop_mirrored_model(ctx, out, slug, report)
        return out
    defined = _file_definition(slug, ctx, report)
    if defined is not None:
        _move_definition(out, defined)
    elif out.get(AttributeKey.MODEL):
        report.append(f"{slug}: kept its stored model {out[AttributeKey.MODEL]!r}")
    return out


def _drop_mirrored_model(
    ctx: MigrationContext, data: dict[str, Any], slug: str, report: list[str]
) -> None:
    """Drop a catalog role's stored model when it is the value the definition resolves to, which
    is what an earlier release mirrored. A different value is kept as the operator's setting
    and reported, so applying the step again to a squad already at 0.17 loses nothing."""
    stored = data.get(AttributeKey.MODEL)
    if not stored:
        return
    try:
        resolved = resolve_role(slug, ctx.paths.squad_dir, catalog=ctx.catalog).model
    except SquadsError:
        resolved = None
    if stored == resolved:
        del data[AttributeKey.MODEL]
        report.append(f"{slug}: dropped its stored model {stored!r}, which the catalog also sets")
    else:
        report.append(
            f"{slug}: kept its stored model {stored!r}, which differs from the catalog's "
            f'{resolved!r}; clear it with `sq role {slug} update --model ""` if it is a leftover'
        )


def _file_definition(slug: str, ctx: MigrationContext, report: list[str]) -> RoleDef | None:
    """The role the per-slug file for *slug* defines by itself; a file that does not load, or no
    file, is reported and gives ``None``."""
    try:
        defined = role_defined_by_file(slug, ctx.paths.squad_dir)
    except SquadsError as exc:
        report.append(
            f"{slug}: .overrides/roles/{slug}.toml does not load as a complete role ({exc}); "
            "left as it was"
        )
        return None
    if defined is None:
        report.append(
            f"{slug}: no catalog entry and no role file; define it with "
            f"`sq role {slug} update --job-title … --desc … --mission …`"
        )
    return defined


def _role_files(folder: Path) -> list[Path]:
    return sorted(folder.glob("*.md")) if folder.is_dir() else []


async def migrate(ctx: MigrationContext) -> MigrationOutcome:
    """Move every role onto its base; ``sq migrate up`` repairs the index and stamps the schema
    itself."""
    folder: Path = ctx.paths.folder_for(ROSTER_ROLE, ctx.spec)
    changed = 0
    report: list[str] = []
    for path in _role_files(folder):
        text = (await _aio.read_bytes(path)).decode("utf-8")
        data = read_frontmatter(text=text, source=str(path))
        slug = str(
            data.get("slug") or slug_from_stem(path.stem, str(data.get("id", "")).split("-")[0])
        )
        out = _migrated(ctx, data, slug, report)
        if out == data:
            continue
        await write_text(path, replace_frontmatter(text, out, source=str(path)))
        changed += 1
    return MigrationOutcome(count=changed, report=tuple(report))
