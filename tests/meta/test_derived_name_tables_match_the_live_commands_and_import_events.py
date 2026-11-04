"""The fixed names the spec-load collision check compares derived flags and import keys against are
the options the live commands declare and the keys the live import events take, once the names the
bundled spec derives are set aside."""

from squads._services import _import_model as services_importmodel
from squads._workflow import _derived_names as workflow_derivednames
from squads._workflow import bundled_spec
from tests._cli_surface import ADDRESS_SEGMENT, fold_path, node_params
from tests._help_tree import Node, command_nodes

#: The type whose commands stand for every type's.
HOST = "task"
SURFACES = {
    "create": ("create <type>", ("create", HOST)),
    "update": ("<type> update", (HOST, "update")),
    "list": ("list", ("list",)),
    "tree": ("tree", ("tree",)),
    "add-<kind>": ("<type> add-<kind>", ("review", "add-finding")),
    "<kind> update": ("<type> <kind> update", ("review", "finding", "update")),
}


def _node(path: tuple[str, ...]) -> Node:
    nodes = [
        n
        for n in command_nodes(include_hidden=True)
        if tuple(s for s in n.path if s != ADDRESS_SEGMENT) == path
    ]
    assert nodes, path
    return nodes[0]


def _derived(surface: str) -> set[str]:
    """The long options *surface* carries because the bundled spec declares something."""
    spec = bundled_spec()
    if surface in ("list", "tree"):
        fields = {f.code: f for t in spec.non_roster_types() for f in spec.fields_for(t)}
        derived = {workflow_derivednames.flag_name(code) for code in fields}
        return derived | {
            f"min-{workflow_derivednames.flag_name(code)}"
            for code, f in fields.items()
            if spec.collections[f.collection].ordered
        }
    owner = "finding" if "kind" in surface else HOST
    fields = spec.fields_for(owner)
    derived = {workflow_derivednames.flag_name(f.code) for f in fields}
    if surface == "update":
        derived |= {
            f"no-{workflow_derivednames.flag_name(f.code)}" for f in fields if not f.required
        }
    if surface == "create":
        derived |= {
            workflow_derivednames.flag_name(name)
            for name, attribute in spec.item_attributes(HOST).items()
            if attribute.settable and attribute.kind in ("str", "list", "date")
        }
    target = spec.mapping_target_kind(owner) if owner != HOST else None
    if target is not None:
        derived |= {workflow_derivednames.flag_name(target)}
        if surface == "<kind> update":
            derived |= {f"no-{workflow_derivednames.flag_name(target)}"}
    return derived


def test_the_fixed_options_are_the_options_the_commands_declare_besides_the_derived_ones() -> None:
    for surface, (key, path) in SURFACES.items():
        node = _node(path)
        assert fold_path(node.path, bundled_spec()) == key
        declared = {
            opt.removeprefix("--")
            for p in node_params(node)
            for opt in (*p.opts, *p.secondary_opts)
            if opt.startswith("--")
        }
        assert declared - _derived(surface) == workflow_derivednames.FIXED_OPTIONS[surface] - {
            "help"
        }, surface


def test_the_fixed_import_keys_are_the_keys_the_events_take() -> None:
    def keys(
        model: type[services_importmodel.AddSubEvent] | type[services_importmodel.CommentEvent],
    ) -> set[str]:
        return {f.alias or name for name, f in model.model_fields.items()}

    assert (
        keys(services_importmodel.AddSubEvent)
        == workflow_derivednames.FIXED_IMPORT_KEYS["add-<kind>"]
    )
    assert (
        keys(services_importmodel.CommentEvent)
        == workflow_derivednames.FIXED_IMPORT_KEYS["comment"]
    )


def test_a_mapping_kinds_target_flag_is_the_only_option_beyond_the_fixed_and_field_ones() -> None:
    spec = bundled_spec()
    target = workflow_derivednames.flag_name(spec.mapping_target_kind("subtask") or "")
    for surface, extra in (("add-<kind>", {target}), ("<kind> update", {target, f"no-{target}"})):
        path = (HOST, "add-subtask") if surface == "add-<kind>" else (HOST, "subtask", "update")
        declared = {
            opt.removeprefix("--")
            for p in node_params(_node(path))
            for opt in (*p.opts, *p.secondary_opts)
            if opt.startswith("--")
        }
        fields = {workflow_derivednames.flag_name(f.code) for f in spec.fields_for("subtask")}
        assert declared - fields - extra == workflow_derivednames.FIXED_OPTIONS[surface] - {
            "help",
            "deferred-to",
        }
