"""The command surface the CLI tests declare coverage of: the live tree folded onto keys, the
(key, parameter) pairs of those keys, and the pairs one call reaches.

A key is a command's path with the vocabulary folded away (`<type>`, `<kind>`, `<host>`) and the
hidden `_addr` dispatcher dropped; the root callback is the empty key. A parameter is named by its
first long flag, or by the usage name of an argument.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import typer.main
from typer._click.core import Context

from squads._cli import app
from squads._workflow._models import WorkflowSpec
from tests._help_tree import Node

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
#: The verbs `register_body_verb`, `register_remove_verb` (with its hidden `rm`) and
#: `register_status_verb` mount on each roster host.
ROSTER_SHARED_VERBS = ("body", "remove", "rm", "status")

#: Parameters the tree lists that squads does not declare, each with the reason it is left out.
EXCLUDED_PARAMS: dict[Pair, str] = {
    ("", "--install-completion"): "Typer's shell-completion installer, not declared by squads",
    ("", "--show-completion"): "Typer's shell-completion printer, not declared by squads",
}


def param_name(param: Any) -> str:
    """The name a test declares *param* by: the first long flag, else the first flag, else the
    usage name of an argument."""
    if param.param_type_name == "option":
        longs = [o for o in param.opts if o.startswith("--")]
        return longs[0] if longs else param.opts[0]
    return param.human_readable_name


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


def built_create_class_name() -> str:
    """The class name of the ``create <type>`` commands the builder mounts, read from the
    reference type's command."""
    root: Any = typer.main.get_command(app)
    create: Any = root.get_command(Context(root, info_name="sq"), "create")
    leaf = create.get_command(Context(create, info_name="create"), "task")
    return type(leaf).__qualname__


def fold_path(path: tuple[str, ...], spec: WorkflowSpec, command: Any) -> str:
    """The key of the command at *path* (its names under ``sq``); *command* is that command.

    A ``create`` command the builder mounts folds onto ``create <type>``; a hand-written one
    keeps its type's name, so its parameters are required in their own right. The verbs one
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
            built = type(command).__qualname__ == built_create_class_name()
            segments[1] = TYPE if built else canonical
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
    """What the tree asks tests to declare."""

    pairs: frozenset[Pair]
    parameterless_leaves: frozenset[str]

    @property
    def required(self) -> frozenset[Pair]:
        return self.pairs | {(key, None) for key in self.parameterless_leaves}


def node_params(node: Node) -> list[Any]:
    """The parameters of *node* as a call sees them, Click's ``--help`` aside."""
    return [p for p in node.command.get_params(node.ctx) if p.name != "help"]


def surface_of(nodes: Iterable[Node], spec: WorkflowSpec) -> Surface:
    """Fold *nodes* onto keys: their (key, parameter) pairs and the leaf keys with no pair."""
    pairs: set[Pair] = set()
    leaves: set[str] = set()
    for node in nodes:
        key = fold_path(node.path, spec, node.command)
        if not hasattr(node.command, "list_commands"):
            leaves.add(key)
        pairs.update((key, param_name(p)) for p in node_params(node))
    pairs -= EXCLUDED_PARAMS.keys()
    keys_with_pairs = {key for key, _ in pairs}
    return Surface(frozenset(pairs), frozenset(leaves - keys_with_pairs))


def reached_pairs(args: list[str], spec: WorkflowSpec) -> set[Pair]:
    """The (key, parameter) pairs the argument list *args* names on the live tree.

    Parses each level with Click's own parser and routes an unknown token to the hidden address
    subgroup as the dispatching groups do. A parameter counts only when the call supplies a
    value for it. A level that does not parse, or that asks for ``--help``, ends the walk, keeping
    the pairs of the levels before it.
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
        key = fold_path(path, spec, command)
        reached.update(
            (key, param_name(p))
            for p in node_params(Node(path, command, ctx))
            if given.get(p.name) not in (None, ()) and (key, param_name(p)) not in EXCLUDED_PARAMS
        )
        if not hasattr(command, "list_commands") or not rest:
            if not hasattr(command, "list_commands"):
                reached.add((key, None))
            return reached
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


def declared_pairs(arguments: tuple[str, ...]) -> set[Pair]:
    """The pairs one marker declares: its key with each parameter, or the key alone."""
    key, *params = arguments
    return {(key, p) for p in params} or {(key, None)}
