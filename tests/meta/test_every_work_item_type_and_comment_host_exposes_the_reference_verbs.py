"""Every work-item type, roster host and comment host exposes the reference verbs with the
reference parameters, compared by signature (kind, required, flag, multiplicity, arity, hidden,
default), a hidden alias included.

Only what the spec decides may differ: sub-entity verbs, `retype`, `remove`, and kind and field
options. Expectations are read from the bundled spec.
"""

from collections.abc import Mapping
from dataclasses import dataclass, fields, replace

import pytest
import typer.core
from typer._click.core import Context

from squads._workflow import bundled_spec
from squads._workflow._models import WorkflowSpec
from tests._cli_surface import (
    ADD_KIND,
    ADDRESS_SEGMENT,
    COMMENT,
    COMMENTS,
    KIND,
    KIND_SEGMENTS,
    KINDS,
    ROSTER_REFERENCE,
    ROSTER_SHARED_VERBS,
    ParamSignature,
    node_params,
    param_name,
    param_signature,
)
from tests._help_tree import Node, command_nodes

#: The work-item type every other type is held to: it hosts a kind and is not roster, so it
#: carries every verb the builder mounts.
REFERENCE_TYPE = "task"

#: What every `create` command carries, including one that is written by hand rather than built.
CREATE_CORE = frozenset(
    {"TITLE", "--author", "--parent", "--desc", "--assignee", "--message", "--file", "--json"}
)

#: A command's parameters by name; ``None`` is a parameter the spec declares, which any signature
#: satisfies.
type Sig = ParamSignature | None
type VerbPath = tuple[str, ...]
type Signatures = dict[str, Sig]
type Verbs = dict[VerbPath, Signatures]

#: The signature fields a message names when two signatures differ.
SIGNATURE_FIELDS = tuple(f.name for f in fields(ParamSignature))


def _canonical(path: tuple[str, ...], spec: WorkflowSpec) -> tuple[str, ...]:
    """*path* with a type alias (``t``, ``create t``) replaced by the type it names."""
    segments = list(path)
    if segments:
        segments[0] = spec.alias_to_type.get(segments[0], segments[0])
    if len(segments) > 1 and segments[0] == "create":
        segments[1] = spec.alias_to_type.get(segments[1], segments[1])
    return tuple(segments)


@dataclass(frozen=True)
class Tree:
    """The tree's commands by path with the address segment dropped, each with its parameters.

    A hidden alias is folded onto the command it names; ``alias_problems`` holds it to that
    command's signatures.
    """

    params: dict[tuple[str, ...], Signatures]
    classes: dict[tuple[str, ...], str]
    alias_problems: list[str]

    @staticmethod
    def of(nodes: list[Node], spec: WorkflowSpec) -> Tree:
        params: dict[tuple[str, ...], Signatures] = {}
        classes: dict[tuple[str, ...], str] = {}
        aliases: dict[tuple[str, ...], Signatures] = {}
        for node in nodes:
            path = tuple(s for s in node.path if s != ADDRESS_SEGMENT)
            signatures: Signatures = {param_name(p): param_signature(p) for p in node_params(node)}
            if _canonical(path, spec) != path:
                aliases.setdefault(path, {}).update(signatures)
                continue
            params.setdefault(path, {}).update(signatures)
            classes.setdefault(path, type(node.command).__qualname__)
        problems: list[str] = []
        for path, signatures in aliases.items():
            canonical = _canonical(path, spec)
            problems += differences(
                f"alias {' '.join(path)}", {(): params.get(canonical, {})}, {(): signatures}
            )
        return Tree(params, classes, problems)

    def below(self, host: tuple[str, ...]) -> Verbs:
        """The commands under *host*, keyed by their path relative to it."""
        n = len(host)
        return {p[n:]: v for p, v in self.params.items() if p[:n] == host}


def item_verbs(tree: Tree, item_type: str, spec: WorkflowSpec) -> Verbs:
    """The verbs of *item_type* with its kind's names folded, the comment verbs left out."""
    kind = spec.item_subentity_kind(item_type)
    folded: Verbs = {}
    for verb, names in tree.below((item_type,)).items():
        if COMMENT in verb:
            continue
        if kind is not None and verb:
            verb = (_fold_kind(verb[0], kind, spec), *verb[1:])
        folded[verb] = names
    return folded


def _fold_kind(segment: str, kind: str, spec: WorkflowSpec) -> str:
    return {kind: KIND, f"add-{kind}": ADD_KIND, spec.subentity_plural(kind): KINDS}.get(
        segment, segment
    )


def kind_options(kind: str, spec: WorkflowSpec, verb: tuple[str, ...]) -> set[str]:
    """The options *kind* declares that sit on *verb*: its fields, its deferral target and its
    story mapping, on the verbs that add or update one."""
    adds = verb == (ADD_KIND,)
    updates = verb == (KIND, "update")
    if not (adds or updates):
        return set()
    options = {f"--{f.code}" for f in spec.fields_for(kind)}
    if spec.subentity_deferred_statuses(kind):
        options.add("--deferred-to")
    if spec.subentity_kinds[kind].maps_parent_story:
        options |= {"--story", "--no-story"} if updates else {"--story"}
    return options


def expected_item_verbs(
    reference: Verbs, item_type: str, reference_kind: str | None, spec: WorkflowSpec
) -> Verbs:
    """The reference verbs as *item_type* carries them under the spec's decisions."""
    kind = spec.item_subentity_kind(item_type)
    expected: Verbs = {}
    for verb, names in reference.items():
        if verb and verb[0] in KIND_SEGMENTS:
            if kind is None or reference_kind is None:
                continue
            names = {
                n: sig
                for n, sig in names.items()
                if n not in kind_options(reference_kind, spec, verb)
            } | dict.fromkeys(kind_options(kind, spec, verb))
        if verb and verb[0] in {"retype", "remove"} and spec.item_is_roster(item_type):
            continue
        expected[verb] = names
    return expected


def _differing(expected: ParamSignature, actual: ParamSignature) -> str:
    return ", ".join(
        f"{name} {getattr(expected, name)!r} != {getattr(actual, name)!r}"
        for name in SIGNATURE_FIELDS
        if getattr(expected, name) != getattr(actual, name)
    )


def differences(
    label: str,
    expected: Mapping[VerbPath, Mapping[str, Sig]],
    actual: Mapping[VerbPath, Mapping[str, Sig]],
) -> list[str]:
    """Every verb or parameter *actual* lacks, carries extra, names differently, or declares
    with another signature."""
    found = [
        f"{label}: missing verb {' '.join(v)}" for v in sorted(expected.keys() - actual.keys())
    ]
    found += [f"{label}: extra verb {' '.join(v)}" for v in sorted(actual.keys() - expected.keys())]
    for verb in sorted(expected.keys() & actual.keys()):
        where = f"{label}: {' '.join(verb) or '(group)'}"
        want, have = expected[verb], actual[verb]
        found += [f"{where} lacks {name}" for name in sorted(want.keys() - have.keys())]
        found += [f"{where} has extra {name}" for name in sorted(have.keys() - want.keys())]
        for name in sorted(want.keys() & have.keys()):
            signature, actual_signature = want[name], have[name]
            if (
                signature is not None
                and actual_signature is not None
                and signature != actual_signature
            ):
                found.append(f"{where} {name} differs: {_differing(signature, actual_signature)}")
    return found


def item_verb_problems(tree: Tree, spec: WorkflowSpec) -> list[str]:
    reference = item_verbs(tree, REFERENCE_TYPE, spec)
    reference_kind = spec.item_subentity_kind(REFERENCE_TYPE)
    found: list[str] = []
    for item_type in sorted(spec.non_roster_types()):
        expected = expected_item_verbs(reference, item_type, reference_kind, spec)
        found += differences(item_type, expected, item_verbs(tree, item_type, spec))
    return found


def create_problems(tree: Tree, spec: WorkflowSpec) -> list[str]:
    """`create <type>` exists for exactly the non-roster types; a built command carries the
    reference's options plus the field options its type declares, a hand-written one the core."""
    created = {p[1] for p in tree.params if len(p) == 2 and p[0] == "create"}
    found = (
        []
        if created == set(spec.non_roster_types())
        else [f"create: commands {sorted(created)} are not the non-roster types"]
    )
    reference = ("create", REFERENCE_TYPE)
    for item_type in sorted(set(spec.non_roster_types()) & created):
        path = ("create", item_type)
        fields_ = {f"--{f.code}": None for f in spec.fields_for(item_type) if f.code != "priority"}
        actual = tree.params[path]
        if tree.classes[path] == tree.classes[reference]:
            found += differences(
                f"create {item_type}", {(): tree.params[reference] | fields_}, {(): actual}
            )
        else:
            core = {n: s for n, s in tree.params[reference].items() if n in CREATE_CORE}
            found += differences(
                f"create {item_type}",
                {(): core},
                {(): {n: s for n, s in actual.items() if n in CREATE_CORE}},
            )
    return found


def comment_hosts(spec: WorkflowSpec) -> list[tuple[str, ...]]:
    """Every host of a comment group the spec declares: each type, and each type's kind."""
    hosts: list[tuple[str, ...]] = []
    for item_type in sorted(spec.items):
        hosts.append((item_type,))
        if (kind := spec.item_subentity_kind(item_type)) is not None:
            hosts.append((item_type, kind))
    return hosts


def comment_problems(tree: Tree, spec: WorkflowSpec) -> list[str]:
    """The `comment` group on every host, and the `comments` listing on every host that is an
    addressed item (a type or a roster entry, not a sub-entity)."""

    def comment_verbs(host: tuple[str, ...]) -> Verbs:
        verbs = {v[1:]: n for v, n in tree.below(host).items() if v and v[0] == COMMENT}
        if len(host) == 1 and (COMMENTS,) in tree.below(host):
            verbs[(COMMENTS,)] = tree.below(host)[(COMMENTS,)]
        return verbs

    reference = comment_verbs((REFERENCE_TYPE,))
    found = [] if reference else [f"{REFERENCE_TYPE}: has no comment verbs"]
    for host in comment_hosts(spec):
        expected = reference
        if len(host) > 1:
            expected = {v: n for v, n in reference.items() if v != (COMMENTS,)}
        found += differences(" ".join(host), expected, comment_verbs(host))
    return found


def roster_problems(tree: Tree, spec: WorkflowSpec) -> list[str]:
    """The verbs one registrar mounts on every roster host (`body`, `remove` and its hidden `rm`,
    `status`) carry the reference roster host's parameters on every other roster host."""
    shared = {(v,) for v in ROSTER_SHARED_VERBS}
    reference = {v: n for v, n in tree.below((ROSTER_REFERENCE,)).items() if v in shared}
    found = [] if reference.keys() == shared else [f"{ROSTER_REFERENCE}: lacks shared verbs"]
    for host in sorted(t for t in spec.items if spec.item_is_roster(t) and t != ROSTER_REFERENCE):
        actual = {v: n for v, n in tree.below((host,)).items() if v in shared}
        found += differences(host, reference, actual)
    return found


def _tree() -> Tree:
    return Tree.of(command_nodes(include_hidden=True), bundled_spec())


def test_every_work_item_type_exposes_the_reference_verbs_with_the_reference_parameters() -> None:
    assert item_verb_problems(_tree(), bundled_spec()) == []


def test_every_creatable_type_has_a_create_command_with_the_reference_options() -> None:
    assert create_problems(_tree(), bundled_spec()) == []


def test_every_comment_host_exposes_the_reference_comment_verbs() -> None:
    assert comment_problems(_tree(), bundled_spec()) == []


def test_every_roster_host_exposes_the_shared_verbs_with_the_reference_roster_parameters() -> None:
    assert roster_problems(_tree(), bundled_spec()) == []


def test_the_reference_roster_host_is_roster_and_the_others_exist() -> None:
    spec = bundled_spec()
    assert spec.item_is_roster(ROSTER_REFERENCE)
    assert {t for t in spec.items if spec.item_is_roster(t)} == {"role", "skill", "operator"}


def test_the_reference_type_hosts_a_kind_and_is_not_roster() -> None:
    spec = bundled_spec()
    assert spec.item_subentity_kind(REFERENCE_TYPE) is not None
    assert not spec.item_is_roster(REFERENCE_TYPE)


def test_the_reference_carries_the_verbs_the_other_types_are_held_to() -> None:
    verbs = item_verbs(_tree(), REFERENCE_TYPE, bundled_spec())
    assert {
        (),
        ("show",),
        ("update",),
        ("status",),
        ("body",),
        ("retype",),
        ("remove",),
        (ADD_KIND,),
        (KIND, "update"),
        (KINDS,),
    } <= verbs.keys()


# ---------------------------------------------------------------------------- the checks bite


def _sig(**changes: object) -> ParamSignature:
    base = ParamSignature("option", False, False, False, 1, False, "None")
    return replace(base, **changes)  # type: ignore[arg-type]


_EXPECTED: Verbs = {
    ("show",): {"--json": _sig(is_flag=True, default="False"), "--raw": _sig(is_flag=True)},
    ("body",): {"--append": _sig(is_flag=True)},
}


def _copy(verbs: Verbs) -> Verbs:
    return {v: dict(s) for v, s in verbs.items()}


def test_identical_verbs_have_no_difference() -> None:
    assert differences("t", _EXPECTED, _copy(_EXPECTED)) == []


def test_a_missing_verb_is_reported() -> None:
    assert differences("t", _EXPECTED, {("show",): _EXPECTED[("show",)]}) == [
        "t: missing verb body"
    ]


def test_a_stale_verb_is_reported() -> None:
    actual = {**_EXPECTED, ("old",): {}}
    assert differences("t", _EXPECTED, actual) == ["t: extra verb old"]


def test_a_missing_parameter_is_reported() -> None:
    actual = _copy(_EXPECTED)
    del actual[("show",)]["--raw"]
    assert differences("t", _EXPECTED, actual) == ["t: show lacks --raw"]


def test_a_stale_parameter_is_reported() -> None:
    actual = _copy(_EXPECTED)
    actual[("body",)]["--old"] = _sig()
    assert differences("t", _EXPECTED, actual) == ["t: body has extra --old"]


@pytest.mark.parametrize(
    ("change", "reported"),
    [
        ({"required": True}, "required False != True"),
        ({"is_flag": False}, "is_flag True != False"),
        ({"multiple": True}, "multiple False != True"),
        ({"hidden": True}, "hidden False != True"),
        ({"default": "True"}, "default 'False' != 'True'"),
        ({"nargs": 2}, "nargs 1 != 2"),
        ({"kind": "argument"}, "kind 'option' != 'argument'"),
    ],
)
def test_a_parameter_declared_differently_is_reported(
    change: dict[str, object], reported: str
) -> None:
    actual = _copy(_EXPECTED)
    actual[("show",)]["--json"] = replace(actual[("show",)]["--json"], **change)  # type: ignore[arg-type]
    assert differences("t", _EXPECTED, actual) == [f"t: show --json differs: {reported}"]


def test_a_parameter_the_spec_declares_matches_any_signature() -> None:
    expected = {("add",): {"--code": None}}
    actual = {("add",): {"--code": _sig(required=True, multiple=True)}}
    assert differences("t", expected, actual) == []


def _alias_node(command: typer.core.TyperCommand, *path: str) -> Node:
    return Node(path, command, Context(command))


def _command(name: str, *options: typer.core.TyperOption) -> typer.core.TyperCommand:
    return typer.core.TyperCommand(name, params=list(options))


def test_an_alias_is_held_to_the_signatures_of_the_command_it_names() -> None:
    spec = bundled_spec()
    full = _command("show", typer.core.TyperOption(param_decls=["--json"], is_flag=True))
    drifted = _command(
        "show", typer.core.TyperOption(param_decls=["--json"], is_flag=True, required=True)
    )
    nodes = [_alias_node(full, "task", "show"), _alias_node(drifted, "t", "show")]
    assert Tree.of(nodes, spec).alias_problems == [
        "alias t show: (group) --json differs: required False != True"
    ]


def test_an_alias_that_matches_the_command_it_names_is_not_reported() -> None:
    spec = bundled_spec()
    full = _command("show", typer.core.TyperOption(param_decls=["--json"], is_flag=True))
    nodes = [_alias_node(full, "task", "show"), _alias_node(full, "t", "show")]
    assert Tree.of(nodes, spec).alias_problems == []


def test_every_hidden_alias_matches_the_command_it_names() -> None:
    assert _tree().alias_problems == []


def test_a_roster_host_whose_shared_verb_drifts_is_reported() -> None:
    spec = bundled_spec()
    tree = _tree()
    status = ("skill", "status")
    drifted: Signatures = {
        n: replace(sig, required=True) if n == "--force" else sig
        for n, sig in tree.params[status].items()
        if sig
    }
    tree.params[status] = drifted
    assert roster_problems(tree, spec) == ["skill: status --force differs: required False != True"]


def test_a_roster_host_without_a_shared_verb_is_reported() -> None:
    spec = bundled_spec()
    tree = _tree()
    del tree.params[("operator", "rm")]
    assert roster_problems(tree, spec) == ["operator: missing verb rm"]
