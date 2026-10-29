"""Command options derived from the badge fields the active spec declares.

A field `urgency` gives `--urgency`, a field `work_size` gives `--work-size`; `update` also takes
`--no-<flag>` for an optional field, and the `list`/`tree` filters take `--min-<flag>` for a field
on an ordered collection. The options are added when a command's parameters are resolved, after
the per-invocation spec is bound, and file their values in the Click context: the command function
has no parameter to receive them.
"""

import contextlib
from typing import Any

import typer
import typer._click as _click  # underscore is upstream's own private module path, not ours
import typer.core

import squads._cli._common as common
from squads import _badges as badges
from squads._workflow._models import Field, WorkflowSpec

#: Context-meta keys under which the options file what they receive.
VALUES_KEY = "squads.field_values"
UNSET_KEY = "squads.field_unset"
MIN_KEY = "squads.field_min"


def flag_name(code: str) -> str:
    """The option name of a field code: its code with dashes (`work_size` is `--work-size`)."""
    return code.replace("_", "-")


def field_codes(field: Field, spec: WorkflowSpec) -> list[str]:
    """The badge codes of the collection *field* binds."""
    coll = spec.collections.get(field.collection)
    return [b.code for b in coll.badges] if coll else []


def field_help(field: Field, codes: list[str]) -> str:
    """Help for a field's value option: its label and the badge codes it takes."""
    return f"{field.label}: {'|'.join(codes)}." if codes else f"{field.label} badge code."


def _filer(key: str, prefix: str = "") -> Any:
    def callback(ctx: _click.Context, param: _click.Parameter, value: Any) -> None:
        if value is not None and value is not False and param.name is not None:
            ctx.meta.setdefault(key, {})[param.name.removeprefix(prefix)] = value

    return callback


def value_option(field: Field, help_text: str) -> Any:
    """`--<code> VALUE` for *field*, filed under its code."""
    return typer.core.TyperOption(
        param_decls=[f"--{flag_name(field.code)}", field.code],
        default=None,
        help=help_text,
        expose_value=False,
        callback=_filer(VALUES_KEY),
    )


def clear_option(field: Field) -> Any:
    """`--no-<code>` for *field*, filed under its code."""
    return typer.core.TyperOption(
        param_decls=[f"--no-{flag_name(field.code)}", f"no_{field.code}"],
        is_flag=True,
        default=False,
        help=f"Clear the {field.label.lower()}.",
        expose_value=False,
        callback=_filer(UNSET_KEY, "no_"),
    )


def min_option(field: Field, codes: list[str]) -> Any:
    """`--min-<code> VALUE` for an ordered *field*, filed under its code."""
    return typer.core.TyperOption(
        param_decls=[f"--min-{flag_name(field.code)}", f"min_{field.code}"],
        default=None,
        help=f"At least this {field.label.lower()}: {'|'.join(codes)}.",
        expose_value=False,
        callback=_filer(MIN_KEY, "min_"),
    )


def _flags(params: list[Any]) -> set[str]:
    return {opt.removeprefix("--") for p in params for opt in (*p.opts, *p.secondary_opts)}


def _extended(params: list[Any], extra: list[Any]) -> list[Any]:
    """*params* plus the options of *extra* whose flags no existing option already holds, placed
    before Click's help option."""
    taken = _flags(params)
    added = [o for o in extra if _flags([o]).isdisjoint(taken)]
    at = next((i for i, p in enumerate(params) if p.name == "help"), len(params))
    return [*params[:at], *added, *params[at:]]


def update_command_cls(item_type: str) -> type[typer.core.TyperCommand]:
    """The command class for `<type> <n> update`: a value option for each field *item_type*
    declares and a clearing option for each optional one.

    Fail-soft like :func:`common.spec_aware_command_cls`: the options are presentation of the
    live spec, and a spec that does not resolve is refused by the command body.
    """

    class _UpdateCommand(typer.core.TyperCommand):
        def get_params(self, ctx: Any) -> list[Any]:
            params = super().get_params(ctx)
            with contextlib.suppress(Exception):
                spec = common.get_active_spec()
                fields = spec.fields_for(item_type)
                extra = [value_option(f, field_help(f, field_codes(f, spec))) for f in fields]
                extra += [clear_option(f) for f in fields if not f.required]
                params = _extended(params, extra)
            return params

    return _UpdateCommand


class FilterCommand(typer.core.TyperCommand):
    """The command class for `list` and `tree`: `--<code>` for each field some non-roster type
    declares and `--min-<code>` for each on an ordered collection."""

    def get_params(self, ctx: Any) -> list[Any]:
        params = super().get_params(ctx)
        with contextlib.suppress(Exception):
            spec = common.get_active_spec()
            extra: list[Any] = []
            for field in badges.filterable_fields(spec):
                codes = badges.field_badge_codes(field.code, spec)
                extra.append(value_option(field, field_help(field, codes)))
                if spec.collections[field.collection].ordered:
                    extra.append(min_option(field, codes))
            params = _extended(params, extra)
        return params


def given_values(ctx: typer.Context) -> dict[str, str]:
    """The values the value options received, by field code."""
    return dict(ctx.meta.get(VALUES_KEY, {}))


def given_unset(ctx: typer.Context) -> list[str]:
    """The field codes whose clearing option was given."""
    return list(ctx.meta.get(UNSET_KEY, {}))


def given_min(ctx: typer.Context) -> dict[str, str]:
    """The thresholds the `--min-<code>` options received, by field code."""
    return dict(ctx.meta.get(MIN_KEY, {}))
