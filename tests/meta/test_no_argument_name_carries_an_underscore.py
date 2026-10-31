"""An argument of the live command tree is shown with hyphens, never underscores: Typer names an
argument after its Python parameter unless a metavar says otherwise, so the shown name is read
from both ``human_readable_name`` and the declared ``metavar``."""

from typer.core import TyperArgument

from tests._help_tree import command_nodes


def test_no_argument_name_carries_an_underscore() -> None:
    offenders = [
        f"{node.label}: {param.human_readable_name!r} (metavar {param.metavar!r})"
        for node in command_nodes(include_hidden=True)
        for param in node.command.params
        if isinstance(param, TyperArgument)
        and "_" in f"{param.human_readable_name}{param.metavar or ''}"
    ]
    assert not offenders, "\n".join(offenders)
