"""The command surface the CLI tests declare coverage of: the live tree folded onto keys, the
(key, parameter) pairs of those keys, and the pairs one call reaches.

A key is a command's path with the vocabulary folded away (`<type>`, `<kind>`, `<host>`) and the
hidden `_addr` dispatcher dropped; the root callback is the empty key. A parameter is named by its
first long flag, or by the usage name of an argument.
"""

import contextlib
import functools
import re
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any

import typer.main
from typer._click.core import Context, iter_params_for_processing

from squads._cli import app
from squads._cli._create import CREATE_ATTRIBUTE_KINDS
from squads._context import bind_context, get_context
from squads._workflow import bundled_spec
from squads._workflow._models import WorkflowSpec
from tests._help_tree import Node, command_nodes

type Pair = tuple[str, str | None]

ADDRESS_SEGMENT = "_addr"
HOST = "<host>"
TYPE = "<type>"
KIND = "<kind>"
ADD_KIND = "add-<kind>"
KINDS = "<kinds>"
KIND_SEGMENTS = (KIND, ADD_KIND, KINDS)
COMMENT = "comment"
COMMENTS = "comments"

#: The roster host every other roster host is folded onto for the verbs one registrar mounts on
#: all of them. It is the host whose `remove` also re-renders the managed roster section, so its
#: tests reach the widest effect of the shared verbs.
ROSTER_REFERENCE = "role"
#: The verbs `register_write_verbs` (`body`, `remove` with its hidden `rm`) and
#: `register_roster_status_verb` mount on each roster host.
ROSTER_SHARED_VERBS = ("body", "remove", "rm", "status")

#: Parameters the tree lists that squads does not declare, each with the reason it is left out.
EXCLUDED_PARAMS: dict[Pair, str] = {
    ("", "--install-completion"): "Typer's shell-completion installer, not declared by squads",
    ("", "--show-completion"): "Typer's shell-completion printer, not declared by squads",
}


FIELD = "<field>"
TARGET_KIND = "<target-kind>"


def _dashed(code: str) -> str:
    return code.replace("_", "-")


def derived_names(spec: WorkflowSpec) -> dict[str, str]:
    """The flags *spec* derives from its declarations, each with the name a marker holds it by, so
    one marker holds in every squad: `--<field>`, `--no-<field>` and `--min-<field>` for a badge
    field, `--<target-kind>` and `--no-<target-kind>` for a sub-entity mapping, and
    `--<attribute:str>`, `--<attribute:list>` or `--<attribute:date>` for a create-time attribute.
    """
    names: dict[str, str] = {}

    def field_flags(code: str) -> None:
        flag = _dashed(code)
        names.setdefault(f"--{flag}", f"--{FIELD}")
        names.setdefault(f"--no-{flag}", f"--no-{FIELD}")
        names.setdefault(f"--min-{flag}", f"--min-{FIELD}")

    for type_name, item in spec.items.items():
        if spec.item_is_roster(type_name):
            continue
        for declared in item.fields:
            field_flags(declared.code)
        for key, attribute in item.attributes.items():
            if attribute.settable and attribute.kind in CREATE_ATTRIBUTE_KINDS:
                names.setdefault(f"--{_dashed(key)}", f"--<attribute:{attribute.kind}>")
    for kind, kind_spec in spec.subentity_kinds.items():
        for declared in kind_spec.fields:
            field_flags(declared.code)
        target = spec.mapping_target_kind(kind)
        if target is not None:
            names.setdefault(f"--{_dashed(target)}", f"--{TARGET_KIND}")
            names.setdefault(f"--no-{_dashed(target)}", f"--no-{TARGET_KIND}")
    return names


def raw_param_name(param: Any) -> str:
    """The first long flag of an option, else its first flag, else the usage name of an argument."""
    if param.param_type_name == "option":
        longs = [o for o in param.opts if o.startswith("--")]
        return longs[0] if longs else param.opts[0]
    return param.human_readable_name


def param_name(param: Any, spec: WorkflowSpec | None = None) -> str:
    """The name a test declares *param* by: its raw name, a flag *spec* derives from its
    declarations by its derivation."""
    raw = raw_param_name(param)
    if param.param_type_name != "option":
        return raw
    return derived_names(spec or bundled_spec()).get(raw, raw)


@dataclass(frozen=True)
class ParamSignature:
    """What a parameter declares besides its name: two hosts of one registration must agree."""

    kind: str
    required: bool
    is_flag: bool
    multiple: bool
    nargs: int
    hidden: bool
    default: str


def param_signature(param: Any) -> ParamSignature:
    """The signature of *param*."""
    return ParamSignature(
        kind=param.param_type_name,
        required=bool(param.required),
        is_flag=bool(getattr(param, "is_flag", False)),
        multiple=bool(param.multiple),
        nargs=int(param.nargs),
        hidden=bool(getattr(param, "hidden", False)),
        default=repr(param.default),
    )


def fold_path(path: tuple[str, ...], spec: WorkflowSpec) -> str:
    """The key of the command at *path* (its names under ``sq``).

    Every ``create <type>`` command folds onto ``create <type>``. The verbs one
    registrar mounts on every roster host fold onto the reference roster host, and the
    ``comments`` listing onto ``<host> comments``.
    """
    segments = [s for s in path if s != ADDRESS_SEGMENT]
    if segments:
        segments[0] = spec.alias_to_type.get(segments[0], segments[0])
    if segments and segments[0] in spec.non_roster_types():
        item_type = segments[0]
        segments[0] = TYPE
        if len(segments) > 1:
            segments[1] = _fold_kind_segment(segments[1], item_type, spec)
    elif len(segments) > 1 and segments[0] == "create":
        canonical = spec.alias_to_type.get(segments[1], segments[1])
        if canonical in spec.non_roster_types():
            segments[1] = TYPE
    if COMMENT in segments[1:]:
        segments[: segments.index(COMMENT)] = [HOST]
    elif len(segments) == 2 and segments[1] == COMMENTS:
        segments[0] = HOST
    elif (
        len(segments) == 2
        and segments[1] in ROSTER_SHARED_VERBS
        and _is_roster_host(segments[0], spec)
    ):
        segments[0] = ROSTER_REFERENCE
    return " ".join(segments)


def _is_roster_host(name: str, spec: WorkflowSpec) -> bool:
    return name in spec.items and spec.item_is_roster(name)


def _fold_kind_segment(segment: str, item_type: str, spec: WorkflowSpec) -> str:
    kind = spec.item_subentity_kind(item_type)
    if kind is None:
        return segment
    if segment == kind:
        return KIND
    if segment == f"add-{kind}":
        return ADD_KIND
    if segment == spec.subentity_plural(kind):
        return KINDS
    return segment


@dataclass(frozen=True)
class Surface:
    """What the tree asks tests to declare: its (key, parameter) pairs and its leaf keys."""

    pairs: frozenset[Pair]
    leaves: frozenset[str]

    @property
    def parameterless_leaves(self) -> frozenset[str]:
        return self.leaves - {key for key, _ in self.pairs}

    @property
    def required(self) -> frozenset[Pair]:
        """The pairs some test must declare: every pair, and the bare call of a leaf that has no
        parameter."""
        return self.pairs | {(key, None) for key in self.parameterless_leaves}

    @property
    def known(self) -> frozenset[Pair]:
        """The pairs a marker may name: every pair, and the bare call of any leaf."""
        return self.pairs | {(key, None) for key in self.leaves}


def node_params(node: Node) -> list[Any]:
    """The parameters of *node* as a call sees them, Click's ``--help`` aside."""
    return [p for p in node.command.get_params(node.ctx) if p.name != "help"]


def surface_of(nodes: Iterable[Node], spec: WorkflowSpec) -> Surface:
    """Fold *nodes* onto keys: their (key, parameter) pairs and their leaf keys."""
    pairs: set[Pair] = set()
    leaves: set[str] = set()
    for node in nodes:
        key = fold_path(node.path, spec)
        if not hasattr(node.command, "list_commands"):
            leaves.add(key)
        pairs.update((key, param_name(p, spec)) for p in node_params(node))
    pairs -= EXCLUDED_PARAMS.keys()
    return Surface(frozenset(pairs), frozenset(leaves))


def reached_pairs(
    args: list[str],
    spec: WorkflowSpec,
    refusal: str | None = None,
    known: frozenset[Pair] | None = None,
) -> set[Pair]:
    """The (key, parameter) pairs the argument list *args* names on the live tree.

    Each level is parsed with Click's parser, an unknown token routed to the address subgroup. A
    parameter counts when the call gives it a value, when Click's missing-parameter error names it,
    or when a flag appears in the *refusal* of a failed call; a leaf given none adds `(key, None)`.
    A parameter outside *known* (the bundled tree's pairs) is not reached, nor is it a bare call.
    """
    root = typer.main.get_command(app)
    ctx = Context(root, info_name="sq")
    command: Any = root
    path: tuple[str, ...] = ()
    reached: set[Pair] = set()
    remaining = list(args)
    while True:
        try:
            given, rest, _ = command.make_parser(ctx).parse_args(args=remaining)
        except Exception:  # pylint: disable=broad-except  # an unparsable level ends the walk
            return reached
        if given.get("help"):
            return reached
        key = fold_path(path, spec)
        params = node_params(Node(path, command, ctx))
        given_pairs = {
            (key, param_name(p, spec))
            for p in params
            if given.get(p.name) not in (None, ())
            and (key, param_name(p, spec)) not in EXCLUDED_PARAMS
        }
        level = {pair for pair in given_pairs if known is None or pair in known}
        reached |= level
        if not hasattr(command, "list_commands") or not rest:
            if not hasattr(command, "list_commands"):
                reached |= {(key, None)} if not given_pairs else set()
                reached |= _missing(key, params, given, spec)
            return reached | _named(key, params, refusal or "", spec)
        child = command.get_command(ctx, rest[0])
        if child is not None:
            name, remaining = rest[0], rest[1:]
        elif command.get_command(ctx, ADDRESS_SEGMENT) is not None:
            child, name, remaining = (
                command.get_command(ctx, ADDRESS_SEGMENT),
                ADDRESS_SEGMENT,
                rest,
            )
        else:
            return reached
        path = (*path, name)
        ctx = Context(child, info_name=name, parent=ctx)
        command = child


def _missing(key: str, params: list[Any], given: dict[str, Any], spec: WorkflowSpec) -> set[Pair]:
    """The pair of the required parameter Click's missing-parameter error names for a leaf call
    that leaves it out: the first one Click processes."""
    absent = [p for p in params if p.required and given.get(p.name) in (None, ())]
    first = next(iter(iter_params_for_processing([], absent)), None)
    return {(key, param_name(first, spec))} if first is not None else set()


def _named(key: str, params: list[Any], refusal: str, spec: WorkflowSpec) -> set[Pair]:
    """The pairs of the options of the command a call ended on that have a flag, short or long,
    in *refusal*."""
    return {
        (key, param_name(p, spec))
        for p in params
        if p.param_type_name == "option"
        and any(
            re.search(rf"(?<![\w-]){re.escape(flag)}(?![\w-])", refusal)
            for flag in (*p.opts, *p.secondary_opts)
        )
        and (key, param_name(p, spec)) not in EXCLUDED_PARAMS
    }


def declared_pairs(arguments: tuple[str, ...]) -> set[Pair]:
    """The pairs one marker declares: its key with each parameter, or the key alone."""
    key, *params = arguments
    return {(key, p) for p in params} or {(key, None)}


@functools.cache
def bundled_known() -> frozenset[Pair]:
    """Every pair a marker may name: the pairs of the bundled tree and the bare call of its
    leaves, read from a directory outside any squad with no active spec bound, so the options the
    caller's squad derives never enter the cached answer."""
    prior = get_context()
    bind_context(replace(prior, active_spec=None))
    try:
        with tempfile.TemporaryDirectory() as empty, contextlib.chdir(empty):
            return surface_of(command_nodes(include_hidden=True), bundled_spec()).known
    finally:
        bind_context(prior)
